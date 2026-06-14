# LLM Lab

> Una app del ecosistema [**Quasar**](../../README.md). Ver el README de la raíz para la visión global.
> Apps hermanas: [SocialLab](../sociallab/README.md) (bases poliglotas) · [PreproLab](../preprolab/README.md) (Tema 5).

**Laboratorio de preparación de corpus para modelos de lenguaje (LLMs).**

Enseña cómo se limpia un corpus masivo antes de entrenar un modelo de lenguaje, reproduciendo en pequeño el pipeline que usan proyectos reales (CommonCrawl, RedPajama, FineWeb): ingesta → limpieza → deduplicación → tokenización → entrenamiento. La demo culminante es entrenar el mismo nanoGPT sobre el corpus **sin limpiar** y sobre el corpus **limpio**, y comparar la calidad de generación.

## Estado actual: Fase 12 (esqueleto)

El chasis está montado: FastAPI en `:8001`, contenedor en el compose, SPA con los 4 bloques del pipeline. La lógica se implementa en fases posteriores.

| Bloque | Técnicas planificadas | Estado |
|---|---|---|
| `clean` | Normalización Unicode, fix encoding, HTML strip, filtro de longitud, idioma, PII | Fase 14 |
| `dedup` | Near-duplicates con MinHash/LSH + grafo `:Document -[:SIMILAR_TO]-> :Document` en Neo4j | Fase 15 |
| `tokenize` | Tokenizer BPE (HuggingFace) + shards `.bin` estilo nanoGPT | Fase 16 |
| `train` | nanoGPT (PyTorch) con presets tiny/small/medium/large + comparativa sucio vs limpio | Fase 17 |

Antes de los bloques, la **Fase 13** implementa la ingesta: descarga un subset de Wikipedia ES e inyecta 10 categorías de ruido intencionado (HTML residual, encoding roto, duplicados, PII plantada, etc.) para que el alumno tenga algo que limpiar.

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
