# LLM Lab

> Una app del ecosistema [**Quasar**](../../README.md). Ver el README de la raíz para la visión global.
> Apps hermanas: [SocialLab](../sociallab/README.md) (bases poliglotas) · [PreproLab](../preprolab/README.md) (Tema 5).

**Laboratorio de preparación de corpus para modelos de lenguaje (LLMs).**

Enseña cómo se limpia un corpus masivo antes de entrenar un modelo de lenguaje, reproduciendo en pequeño el pipeline que usan proyectos reales (CommonCrawl, RedPajama, FineWeb): ingesta → limpieza → deduplicación → tokenización → entrenamiento. La demo culminante es entrenar el mismo nanoGPT sobre el corpus **sin limpiar** y sobre el corpus **limpio**, y comparar la calidad de generación.

## Estado actual: Fase 14 (ingesta + bloque clean operativos)

| Bloque | Técnicas | Estado |
|---|---|---|
| **Ingest** | Corpus sintético tipo Wikipedia ES + 10 categorías de ruido | **Fase 13 OK** |
| `clean` | fix_encoding, strip_html, length_filter, language_filter, pii_removal, pipeline | **Fase 14 OK** |
| `dedup` | exact + MinHash + LSH + grafo `:Document -[:SIMILAR_TO]-> :Document` en Neo4j + Cypher | **Fase 15 OK** |
| `tokenize` | Tokenizer BPE desde cero + shards `.bin` estilo nanoGPT | **Fase 16 OK** |
| `train` | nanoGPT (PyTorch) con presets tiny/small/medium/large + comparativa sucio vs limpio | Fase 17 |

### Ingesta (Fase 13)

`./lab.sh llmprep ingest` genera `infra/data/llmprep/raw/corpus.json` (~5450 docs, ~7 MB) con 10 categorías de ruido inyectado: exact_dup, near_dup, html_residual, boilerplate, wrong_lang, broken_encoding, pii, gibberish, too_short, too_long. Cada documento lleva un campo `_noise` con sus problemas (ground truth, no existiría en un corpus real).

### Bloque CLEAN (Fase 14)

Seis ejercicios scaffold/solución, cada uno validado contra el ground truth:

| Ejercicio | Endpoint | Resultado verificado |
|---|---|---|
| CLEAN-1 | `/api/llmprep/clean/fix_encoding` | 396 docs reparados (gt 404) |
| CLEAN-2 | `/api/llmprep/clean/strip_html` | 1456 docs, 108k chars eliminados |
| CLEAN-3 | `/api/llmprep/clean/length_filter` | descarta cortos/largos |
| CLEAN-4 | `/api/llmprep/clean/language_filter` | **P=1.0, R=0.64** (heurística stopwords ES/EN) |
| CLEAN-5 | `/api/llmprep/clean/pii_removal` | 632 redacciones |
| CLEAN-6 | `/api/llmprep/clean/pipeline` | corpus -56% chars, -15% docs |

Endpoint no-gateado: `corpus_stats`. El R=0.64 de language_filter es un buen punto de enseñanza: la heurística no detecta lorem ipsum como inglés (queda en 'unknown'), lo que muestra los límites de la detección por stopwords.

### Bloque DEDUP (Fase 15)

Cinco ejercicios sobre deduplicación + grafo Neo4j (la pata poliglota de LLM Lab). MinHash y LSH implementados desde cero (sin datasketch):

| Ejercicio | Endpoint | Técnica |
|---|---|---|
| DEDUP-1 | `GET /api/llmprep/dedup/exact` | Duplicados exactos por md5 del texto |
| DEDUP-2 | `GET /api/llmprep/dedup/minhash` | Firmas MinHash (64 hashes, shingles k=3) |
| DEDUP-3 | `GET /api/llmprep/dedup/lsh_candidates` | LSH banding (16 bandas × 4 filas) → pares near-dup |
| DEDUP-4 | `POST /api/llmprep/dedup/build_graph` | Carga `:Document -[:SIMILAR_TO {jaccard}]->` a Neo4j |
| DEDUP-5 | `GET /api/llmprep/dedup/graph_clusters` | Cypher: docs con más vecinos (content farms) |

Validación end-to-end:
- **exact**: 605 duplicados (gt 200) — el extra son colisiones naturales del generador de plantillas; **buen punto de enseñanza**: el dedup exacto encuentra más de lo "etiquetado" porque los corpus reales tienen colisiones inesperadas.
- **lsh_candidates**: 7472 pares candidatos → 2385 confirmados (jaccard ≥ 0.5), 404 involucran un dup conocido.
- **build_graph**: carga 727 nodos + 2385 aristas SIMILAR_TO a Neo4j.
- **graph_clusters**: Cypher devuelve docs con hasta 33 vecinos (avg jaccard ~0.9) → candidatos a content farm. Explorable en el Neo4j browser (`:7474`).

Esto conecta directamente con lo que el alumno aprendió en SocialLab (Cypher, grafos), aplicado ahora a un problema de NLP real.

### Bloque TOKENIZE (Fase 16)

Cuatro ejercicios sobre tokenización BPE (implementado desde cero en `src/tokenize/bpe.py`, estilo Sennrich sobre tabla de frecuencias de palabras):

| Ejercicio | Endpoint | Resultado |
|---|---|---|
| TOK-1 | `GET /api/llmprep/tokenize/train` | 500 merges, vocab 547. Primeros merges: `de`, `me`, `ti`, `re`, `co` (bigramas españoles frecuentes) |
| TOK-2 | `GET /api/llmprep/tokenize/encode` | Round-trip exacto, compresión 3.92 chars/token |
| TOK-3 | `GET /api/llmprep/tokenize/vocab_stats` | Compresión 5.37 sobre 1.2M chars → 222k tokens |
| TOK-4 | `POST /api/llmprep/tokenize/build_shards` | train.bin (1.2 MB) + val.bin + vocab.json (uint16) |

Los shards generados (`gold/train.bin`, `gold/val.bin`) son exactamente el formato que el bloque train memory-mapea, igual que en nanoGPT de Karpathy.

## Arranque rápido

```bash
./lab.sh llmprep up        # arranca app-llmprep + dependencias
./lab.sh llmprep status    # estado actual
./lab.sh llmprep down      # para SOLO llmprep
```

Web: <http://localhost:8001>

## Modo laboratorio

```bash
./lab.sh llmprep unlock clean      # desbloquea un bloque
./lab.sh llmprep solutions          # desbloquea todos
./lab.sh llmprep exercises          # bloquea todos (scaffold)
```

## Estructura

```text
apps/llmprep/
├── src/
│   ├── config/      # configuración (importa de infra/shared)
│   ├── web/         # FastAPI + SPA con Plotly.js
│   ├── ingest/      # descarga Wikipedia + inyección de ruido (Fase 13)
│   ├── spark/       # bloque clean + dedup (Fases 14-15)
│   ├── tokenize/    # BPE (Fase 16)
│   └── train/       # nanoGPT (Fase 17)
├── main.py · Dockerfile · requirements.txt · .env.example
```

## API expuesta (Fase 12)

| Endpoint | Descripción |
|---|---|
| `GET /api/health` | `{"status": "ok", "app": "llmprep"}` |
| `GET /api/llmprep/lab/status` | Bloques desbloqueados según `LAB_LLMPREP` |
