"""Generador del corpus sucio para LLM Lab.

Simula un volcado de artículos tipo enciclopedia en español al que se le
han inyectado los problemas típicos de un corpus web crudo (estilo
CommonCrawl/Wikipedia dump sin procesar). El alumno debe limpiarlo en los
bloques posteriores antes de tokenizar y entrenar.

Por qué sintético y no descarga real de Wikipedia:
  - Reproducible: misma semilla → mismo corpus, sin depender de red ni de
    versiones del dump.
  - Self-contained: funciona dentro del contenedor sin descargar GB.
  - Control total: sabemos exactamente qué ruido hay y en qué proporción,
    para poder validar que la limpieza del alumno funciona.

Output (JSON Lines en infra/data/llmprep/raw/corpus.json):
  {id, title, text, lang_declared, source, char_count, _noise: [tipos]}

El campo _noise lista qué problemas tiene cada documento (ground truth
para validar la limpieza). En un corpus real no existiría — aquí lo
guardamos para que los bloques clean/dedup puedan medir su precisión.

10 categorías de ruido inyectado:
  1. exact_dup       Documento duplicado exacto (página espejo)
  2. near_dup        Casi-duplicado (cambios mínimos, content farm)
  3. html_residual   <ref>, {{cite}}, [[wikilinks]], etiquetas HTML
  4. boilerplate     "Véase también", "Referencias", listas de navegación
  5. wrong_lang      Texto en inglés/latín declarado como español
  6. broken_encoding Mojibake (Ã¡, Ã©, ...)
  7. pii             Emails y teléfonos plantados
  8. gibberish       Lorem ipsum / placeholders sin sentido
  9. too_short       Documento de <200 caracteres (stub)
  10. too_long       Documento de >15000 caracteres (lista mal convertida)

Uso:
    ./lab.sh llmprep ingest
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from src.config import RAW_PATH

random.seed(1234)

NUM_DOCS = 5000
EXACT_DUP_RATIO = 0.04
NEAR_DUP_RATIO = 0.05
HTML_RESIDUAL_RATIO = 0.18
BOILERPLATE_RATIO = 0.15
WRONG_LANG_RATIO = 0.06
BROKEN_ENCODING_RATIO = 0.08
PII_RATIO = 0.05
GIBBERISH_RATIO = 0.03
TOO_SHORT_RATIO = 0.05
TOO_LONG_RATIO = 0.02

# ============================================================
# Vocabulario para generar artículos sintéticos coherentes
# ============================================================

TEMAS = [
    ("la fotosíntesis", "biología", ["plantas", "clorofila", "luz solar", "dióxido de carbono", "oxígeno", "glucosa"]),
    ("el Imperio Romano", "historia", ["Roma", "emperador", "legiones", "Mediterráneo", "senado", "provincias"]),
    ("la mecánica cuántica", "física", ["partículas", "energía", "incertidumbre", "función de onda", "átomos", "fotones"]),
    ("el río Amazonas", "geografía", ["agua", "selva", "Brasil", "afluentes", "biodiversidad", "cuenca"]),
    ("la Revolución Francesa", "historia", ["1789", "monarquía", "burguesía", "libertad", "París", "guillotina"]),
    ("los algoritmos", "informática", ["instrucciones", "datos", "eficiencia", "complejidad", "ordenador", "lógica"]),
    ("el sistema solar", "astronomía", ["Sol", "planetas", "órbitas", "gravedad", "asteroides", "satélites"]),
    ("la economía de mercado", "economía", ["oferta", "demanda", "precios", "competencia", "empresas", "consumidores"]),
    ("la teoría de la evolución", "biología", ["selección natural", "especies", "adaptación", "Darwin", "genética", "fósiles"]),
    ("el cambio climático", "medio ambiente", ["temperatura", "emisiones", "atmósfera", "glaciares", "energía", "carbono"]),
    ("la inteligencia artificial", "informática", ["modelos", "datos", "aprendizaje", "redes neuronales", "predicción", "algoritmos"]),
    ("la música barroca", "arte", ["Bach", "compositores", "armonía", "orquesta", "contrapunto", "siglo XVII"]),
    ("la fotosíntesis celular", "biología", ["células", "energía", "membrana", "mitocondrias", "metabolismo", "ATP"]),
    ("la arquitectura gótica", "arte", ["catedrales", "arcos", "vitrales", "piedra", "Edad Media", "bóvedas"]),
    ("el ADN", "biología", ["genes", "nucleótidos", "doble hélice", "herencia", "proteínas", "cromosomas"]),
]

PLANTILLAS_PARRAFO = [
    "{tema} es un concepto fundamental dentro de {campo}. Su estudio permite comprender mejor {a} y {b}.",
    "Los expertos en {campo} consideran que {tema} desempeña un papel central. Está estrechamente relacionado con {a}, {b} y {c}.",
    "Históricamente, {tema} ha sido objeto de numerosos estudios. La relación entre {a} y {b} resulta especialmente relevante.",
    "Para entender {tema}, conviene analizar primero {a}. A partir de ahí se puede explicar cómo influye {b} en el proceso.",
    "Una característica esencial de {tema} es su conexión con {a}. Diversos investigadores han documentado el impacto de {b} y {c}.",
    "En el ámbito de {campo}, {tema} representa un pilar del conocimiento. Sin {a}, sería imposible comprender {b}.",
]

# Fragmentos en inglés/latín para wrong_lang
WRONG_LANG_TEXTS = [
    "This article describes a fundamental concept. The relationship between the main components is essential for understanding the whole system. Many researchers have studied this topic extensively over the past decades.",
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation.",
    "The study of this subject requires careful analysis of multiple factors. Scientists have proposed several theories to explain the observed phenomena and their underlying mechanisms.",
]

GIBBERISH = [
    "asdf qwerty zxcvb 12345 placeholder TODO FIXME xxxxx yyyyy zzzzz lorem ipsum",
    "[PENDIENTE DE REDACTAR] -- texto provisional -- borrar antes de publicar -- aaa bbb ccc",
    "test test test 000 111 222 contenido de prueba no usar en produccion qwertyuiop",
]

BOILERPLATE_BLOCKS = [
    "\n\n== Véase también ==\n* Artículo relacionado 1\n* Artículo relacionado 2\n* Artículo relacionado 3",
    "\n\n== Referencias ==\n<references />\n[1] Autor, A. (2020). Título. Editorial.\n[2] Otro, B. (2019). Otro título.",
    "\n\n== Enlaces externos ==\n* [http://ejemplo.org Sitio oficial]\n* [http://ejemplo.org/wiki Más información]",
    "\n\nCategorías: Artículos destacados | Wikipedia | Conocimiento | Ciencia",
    "\n\nEste artículo es un esbozo. Puedes ayudar a Wikipedia ampliándolo.",
]

HTML_FRAGMENTS = [
    "<ref name='fuente1'>Referencia incrustada que no debería estar en el texto limpio.</ref>",
    "{{cite web|url=http://ejemplo.org|title=Fuente|fecha=2020}}",
    "[[Enlace interno wiki|texto visible]]",
    "<div class='infobox'>Tabla de información lateral</div>",
    "{{Ficha de concepto|nombre=X|tipo=Y}}",
    "<!-- comentario HTML que sobró del parsing -->",
]


def _mojibake(text: str) -> str:
    rep = {"á": "Ã¡", "é": "Ã©", "í": "Ã­", "ó": "Ã³", "ú": "Ãº", "ñ": "Ã±", "ü": "Ã¼", "¿": "Â¿", "¡": "Â¡"}
    for k, v in rep.items():
        text = text.replace(k, v)
    return text


def _fake_email() -> str:
    nombres = ["autor", "editor", "contacto", "info", "redaccion"]
    return f"{random.choice(nombres)}{random.randint(1, 99)}@ejemplo-corpus.org"


def _fake_phone() -> str:
    return f"+34 9{random.randint(10_000_000, 99_999_999)}"


def _generate_clean_article(tema_tuple, n_paragraphs: int) -> tuple[str, str]:
    """Genera un artículo 'limpio' base a partir de una plantilla temática."""
    tema, campo, conceptos = tema_tuple
    title = tema.capitalize()
    paragraphs = []
    for _ in range(n_paragraphs):
        plantilla = random.choice(PLANTILLAS_PARRAFO)
        sample = random.sample(conceptos, min(3, len(conceptos)))
        while len(sample) < 3:
            sample.append(random.choice(conceptos))
        para = plantilla.format(
            tema=tema, campo=campo, a=sample[0], b=sample[1], c=sample[2],
        )
        paragraphs.append(para)
    return title, "\n\n".join(paragraphs)


def generate_corpus() -> list[dict]:
    docs: list[dict] = []

    for i in range(NUM_DOCS):
        tema_tuple = random.choice(TEMAS)
        n_par = random.randint(2, 6)
        title, text = _generate_clean_article(tema_tuple, n_par)
        noise: list[str] = []
        lang = "es"
        source = f"wiki-es-dump/{random.randint(1, 50)}"

        # too_short: artículo stub
        if random.random() < TOO_SHORT_RATIO:
            text = text.split("\n\n")[0][:180]
            noise.append("too_short")

        # too_long: lista mal convertida (texto inflado)
        if random.random() < TOO_LONG_RATIO:
            text = text + "\n\n" + "\n".join(
                f"* Elemento de lista número {j} con descripción larga y repetitiva." for j in range(400)
            )
            noise.append("too_long")

        # html_residual
        if random.random() < HTML_RESIDUAL_RATIO:
            frag = random.choice(HTML_FRAGMENTS)
            pos = random.randint(0, max(1, len(text) - 1))
            text = text[:pos] + " " + frag + " " + text[pos:]
            noise.append("html_residual")

        # boilerplate
        if random.random() < BOILERPLATE_RATIO:
            text = text + random.choice(BOILERPLATE_BLOCKS)
            noise.append("boilerplate")

        # wrong_lang: documento entero en otro idioma
        if random.random() < WRONG_LANG_RATIO:
            text = random.choice(WRONG_LANG_TEXTS)
            noise.append("wrong_lang")

        # gibberish
        if random.random() < GIBBERISH_RATIO:
            text = random.choice(GIBBERISH)
            noise.append("gibberish")

        # pii
        if random.random() < PII_RATIO:
            text = text + f"\n\nPara más información, contacte con {_fake_email()} o llame al {_fake_phone()}."
            noise.append("pii")

        # broken_encoding (se aplica al final, después del texto español)
        if random.random() < BROKEN_ENCODING_RATIO and "wrong_lang" not in noise:
            text = _mojibake(text)
            title = _mojibake(title)
            noise.append("broken_encoding")

        docs.append({
            "id": f"doc_{i:06d}",
            "title": title,
            "text": text,
            "lang_declared": lang,
            "source": source,
            "char_count": len(text),
            "_noise": noise,
        })

    # exact_dup: duplicar documentos enteros con nuevo id
    n_exact = int(NUM_DOCS * EXACT_DUP_RATIO)
    for k in range(n_exact):
        original = random.choice(docs[:NUM_DOCS])
        dup = dict(original)
        dup["id"] = f"doc_dup_{k:06d}"
        dup["source"] = f"mirror-site/{random.randint(1, 20)}"
        dup["_noise"] = list(original["_noise"]) + ["exact_dup"]
        docs.append(dup)

    # near_dup: duplicar con cambios mínimos (content farm)
    n_near = int(NUM_DOCS * NEAR_DUP_RATIO)
    for k in range(n_near):
        original = random.choice(docs[:NUM_DOCS])
        near = dict(original)
        near["id"] = f"doc_near_{k:06d}"
        # cambios mínimos: prefijo + alguna palabra cambiada
        modified = "Según diversas fuentes, " + original["text"]
        modified = modified.replace("fundamental", "esencial").replace("central", "principal")
        near["text"] = modified
        near["char_count"] = len(modified)
        near["source"] = f"content-farm/{random.randint(1, 30)}"
        near["_noise"] = list(original["_noise"]) + ["near_dup"]
        docs.append(near)

    random.shuffle(docs)
    return docs


def write_corpus(docs: list[dict]) -> Path:
    path = RAW_PATH / "corpus.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    return path


def main() -> None:
    print("=" * 64)
    print("LLM Lab — Generador del corpus sucio (estilo Wikipedia ES dump)")
    print("=" * 64)
    print(f"Output: {RAW_PATH}")
    print(f"Semilla: 1234 (reproducible)")
    print()

    docs = generate_corpus()
    path = write_corpus(docs)
    size_mb = path.stat().st_size / 1024 / 1024

    # Estadísticas de ruido
    from collections import Counter
    noise_counter: Counter = Counter()
    for d in docs:
        for n in d["_noise"]:
            noise_counter[n] += 1

    print(f"  corpus.json: {len(docs):,d} documentos → {path} ({size_mb:.1f} MB)")
    print()
    print("Verificación de ruido inyectado:")
    for noise_type in [
        "exact_dup", "near_dup", "html_residual", "boilerplate", "wrong_lang",
        "broken_encoding", "pii", "gibberish", "too_short", "too_long",
    ]:
        count = noise_counter.get(noise_type, 0)
        pct = 100 * count / len(docs)
        print(f"  {noise_type:16s} {count:>6,d}  ({pct:.1f}%)")

    total_clean = sum(1 for d in docs if not d["_noise"])
    print()
    print(f"  Documentos completamente limpios: {total_clean:,d} ({100*total_clean/len(docs):.1f}%)")
    print(f"  Documentos con algún problema:    {len(docs)-total_clean:,d}")


if __name__ == "__main__":
    main()
