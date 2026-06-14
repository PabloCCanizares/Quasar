# Quasar Hub

> La app central del ecosistema [**Quasar**](../../README.md). La puerta de entrada.

**App ligera (sin Spark ni base de datos propia) que orquesta y explica el ecosistema.** Es el único puerto que el alumno o el profesor necesita conocer: `http://localhost:8080`.

## Las 4 responsabilidades

| Vista | Qué hace |
|---|---|
| **Inicio** | Landing con la narrativa de Quasar + tarjetas de las 3 apps (con indicador online/offline en vivo) + enlaces para abrirlas |
| **Estado** | Dashboard agregado: consulta health + `lab/status` de las 3 apps y muestra todo en una pantalla (qué está arriba, qué bloques desbloqueados) |
| **Configuración** | Panel del profesor: desbloquea/bloquea cada bloque de cada app **con un clic desde la web** (sin terminal) |
| **Primeros pasos** | Guía de onboarding paso a paso para un alumno que llega de cero |

## Cómo funciona el panel de configuración

El mecanismo que permite cambiar los ejercicios desde la web:

1. El Hub edita la variable `LAB_*` correspondiente en `infra/compose/.env.docker` (el mismo archivo que usa `lab.sh` por CLI).
2. Reinicia el contenedor de la app vía el **Docker socket** (`/var/run/docker.sock`, montado en el Hub).
3. La app, al re-arrancar, lee el flag actualizado del `.env.docker` que tiene montado (`infra/shared/lab_flags.read_lab_flag`) y re-evalúa qué bloques sirve como solución vs scaffold.

Esto equivale exactamente a `./lab.sh <app> unlock <bloque>` pero desde una interfaz web, pensado para que un profesor destape ejercicios en mitad de una clase sin tocar el terminal.

## Arranque

```bash
./lab.sh hub up        # arranca solo el Hub
./lab.sh tour          # arranca TODO el ecosistema (incluye el Hub)
```

Web: <http://localhost:8080>

## API

| Endpoint | Descripción |
|---|---|
| `GET /api/health` | `{"status": "ok", "app": "hub"}` |
| `GET /api/hub/catalog` | Catálogo estático de las 3 apps |
| `GET /api/hub/status` | Estado agregado en vivo (health + bloques de las 3 apps) |
| `GET /api/hub/flags` | Valor actual de cada flag `LAB_*` |
| `POST /api/hub/flag` | Desbloquea/bloquea un bloque y reinicia la app |

## Estructura

```text
apps/hub/
├── src/
│   ├── config/      # catálogo de apps (URLs, contenedores, flags)
│   └── web/
│       ├── app.py
│       └── routes/
│           ├── status.py    # estado agregado (httpx a las 3 apps)
│           └── control.py    # editar flag + restart vía docker socket
├── main.py · Dockerfile · requirements.txt
```

Dependencias propias: `httpx` (consultar las apps) y `docker` (reiniciar contenedores). Sin Spark ni Java — imagen ligera.
