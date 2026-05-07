# ==========================================================
# SocialLab - laboratorio en Docker (Windows / PowerShell)
#
# Equivalente Windows de lab.sh. Permite arrancar el ecosistema
# completo y "destapar" bloques de ejercicios (Cypher de Neo4j
# y modelos ML) sin tocar codigo.
#
# Uso: .\lab.ps1 <comando> [args]
# ==========================================================

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command = "help",

    [Parameter(Position = 1)]
    [string]$Arg1,

    [Parameter(Position = 2)]
    [string]$Arg2
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8

# Trabajamos siempre desde el directorio del script
Set-Location -LiteralPath $PSScriptRoot

$EnvFile = ".env.docker"
$script:ComposeCmd  = $null
$script:ComposeArgs = @()

# ----------------------------------------------------------
# Logging con color
# ----------------------------------------------------------
function Write-Log     { param([string]$Msg) Write-Host "[lab] $Msg" -ForegroundColor Blue }
function Write-Ok      { param([string]$Msg) Write-Host "[OK]  $Msg" -ForegroundColor Green }
function Write-WarnMsg { param([string]$Msg) Write-Host "[!]   $Msg" -ForegroundColor Yellow }
function Write-ErrMsg  { param([string]$Msg) Write-Host "[ERR] $Msg" -ForegroundColor Red }

# ----------------------------------------------------------
# Verifica que docker / docker compose esten disponibles y
# fija $script:ComposeCmd / $script:ComposeArgs.
# ----------------------------------------------------------
function Ensure-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-ErrMsg "docker no esta instalado o no esta en PATH"
        Write-Host  "  Instala Docker Desktop: https://www.docker.com/products/docker-desktop"
        exit 1
    }

    # docker compose v2 (plugin)
    & docker compose version *> $null
    if ($LASTEXITCODE -eq 0) {
        $script:ComposeCmd  = "docker"
        $script:ComposeArgs = @("compose")
        return
    }

    # docker-compose legacy
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        $script:ComposeCmd  = "docker-compose"
        $script:ComposeArgs = @()
        return
    }

    Write-ErrMsg "Docker Compose no esta disponible"
    Write-Host  "  Instala/actualiza Docker Desktop, o instala el binario legacy 'docker-compose'."
    exit 1
}

function Invoke-Compose {
    & $script:ComposeCmd @script:ComposeArgs @args
}

# ----------------------------------------------------------
# Edicion del flag en .env.docker (delegado a Python para
# mantener la misma logica que lab.sh).
#   Var    : LAB_NEO4J | LAB_ML
#   Action : unlock | lock | all | none
#   Block  : basic | intermediate | advanced | supervised | ...
# Devuelve por stdout el nuevo valor.
# ----------------------------------------------------------
function Update-Flag {
    param(
        [string]$Var,
        [string]$Action,
        [string]$Block
    )

    $pythonScript = @'
import re, sys

var, action, block, env_file = sys.argv[1:5]

NEO4J_BLOCKS = {"basic", "intermediate", "advanced"}
ML_BLOCKS = {"supervised", "unsupervised", "graph_ml"}
ALL = NEO4J_BLOCKS if var == "LAB_NEO4J" else ML_BLOCKS

with open(env_file) as f:
    content = f.read()

m = re.search(rf'^{var}=(.*)$', content, re.MULTILINE)
current = m.group(1).strip() if m else ""

if current == "all":
    blocks = set(ALL)
else:
    blocks = {b.strip() for b in current.split(",") if b.strip()}

if action == "unlock":
    if block not in ALL:
        sys.stderr.write(f"Bloque desconocido: {block}. Validos: {sorted(ALL)}\n")
        sys.exit(2)
    blocks.add(block)
elif action == "lock":
    blocks.discard(block)
elif action == "all":
    blocks = set(ALL)
elif action == "none":
    blocks = set()
else:
    sys.stderr.write(f"Action desconocida: {action}\n")
    sys.exit(2)

new_value = ",".join(sorted(blocks))
content = re.sub(rf'^{var}=.*$', f'{var}={new_value}', content, flags=re.MULTILINE)

with open(env_file, "w") as f:
    f.write(content)

print(new_value if new_value else "(empty)")
'@

    # Volcamos el script a un fichero temporal (mas robusto que
    # piping por stdin en PowerShell 5.1 con encodings raros).
    $tempFile = [System.IO.Path]::GetTempFileName() + ".py"
    try {
        Set-Content -LiteralPath $tempFile -Value $pythonScript -Encoding UTF8
        $result = & python $tempFile $Var $Action $Block $EnvFile
        if ($LASTEXITCODE -ne 0) {
            throw "Update-Flag fallo: var=$Var action=$Action block=$Block"
        }
        return $result
    }
    finally {
        Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
    }
}

function Restart-App {
    Write-Log "Recreando el contenedor 'app' para recoger nuevos flags..."
    Invoke-Compose up -d app
    Write-Ok  "Listo. Recarga el navegador."
}

function Clear-MLArtifacts {
    if (Test-Path -LiteralPath "data/gold/models") {
        Write-Log "Limpiando modelos ML generados previamente (data/gold/models)..."
        Remove-Item -LiteralPath "data/gold/models" -Recurse -Force
    }
}

function Train-MLArtifacts {
    Clear-MLArtifacts
    Write-Log "Entrenando modelos ML segun LAB_ML actual..."
    Invoke-Compose exec app python -m src.spark.models.run_all
    Write-Ok  "Modelos ML actualizados. Recarga la vista Spark/ML."
}

function Ensure-RawData {
    $missing = $false
    foreach ($file in @("users", "posts", "likes", "follows")) {
        $path = "data/raw/$file.json"
        $item = Get-Item -LiteralPath $path -ErrorAction SilentlyContinue
        if (-not $item -or $item.Length -eq 0) {
            $missing = $true
        }
    }

    if ($missing) {
        Write-WarnMsg "No encuentro data/raw/{users,posts,likes,follows}.json."
        Write-Log     "Generando datos raw automaticamente antes del ETL..."
        Invoke-Compose exec app python -m src.seed.generate_dirty_data
    }
}

# ----------------------------------------------------------
# Dispatch
# ----------------------------------------------------------
switch ($Command) {

    # ------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------
    "up" {
        Ensure-Docker
        $mode = $Arg1
        if ($mode) {
            switch ($mode) {
                "exercises" {
                    Update-Flag "LAB_NEO4J" "none" "" | Out-Null
                    Update-Flag "LAB_ML"    "none" "" | Out-Null
                    Write-Log "Modo: ejercicios (todos los algoritmos como scaffold)"
                }
                { $_ -in "solutions", "all" } {
                    Update-Flag "LAB_NEO4J" "all" "" | Out-Null
                    Update-Flag "LAB_ML"    "all" "" | Out-Null
                    Write-Log "Modo: soluciones (todos los algoritmos resueltos)"
                }
                default {
                    Write-ErrMsg "Modo desconocido: $mode"
                    Write-Host  "  Modos validos: exercises | solutions"
                    exit 1
                }
            }
        }
        else {
            Write-Log "Arrancando con la configuracion actual de $EnvFile"
        }
        Invoke-Compose up -d --build
        Write-Ok "Web:  http://localhost:8000"
        Write-Ok "Neo4j browser: http://localhost:7474  (neo4j / neo4jneo4j)"
        break
    }

    "down" {
        Ensure-Docker
        Write-Log "Parando contenedores (volumenes preservados)..."
        Invoke-Compose down
        break
    }

    "cloud" {
        if (-not (Test-Path -LiteralPath ".env.cloud")) {
            Write-ErrMsg "Falta .env.cloud. Copia la plantilla y rellena las URIs:"
            Write-Host  "  Copy-Item .env.cloud.example .env.cloud"
            Write-Host  "  # rellena MONGO_URI, NEO4J_URI, NEO4J_PASSWORD con tus credenciales"
            Write-Host  ""
            Write-Host  "Guia paso a paso: docs/MIGRACION_CLOUD.md"
            Write-Host  ""
            Write-Host  "Alternativa sin Docker (alumno muy ligero):"
            Write-Host  "  Copy-Item .env.cloud .env ; python main.py   # usa el venv local"
            exit 1
        }
        Ensure-Docker
        # Si el modo local esta corriendo, los puertos chocan (8000)
        $running = Invoke-Compose ps --status running --quiet 2>$null
        if ($running) {
            Write-Log "Modo local detectado - parandolo primero (mongo/neo4j locales se quedan)..."
            Invoke-Compose stop
        }
        Write-Log "Arrancando solo el contenedor 'app' apuntando a Atlas/Aura..."
        Invoke-Compose -f docker-compose.cloud.yml up -d --build
        Write-Ok "Web: http://localhost:8000"
        Write-Ok "Mongo y Neo4j viven en cloud - no hay contenedores locales para esas BBDD"
        break
    }

    "cloud-down" {
        Ensure-Docker
        Write-Log "Parando contenedor cloud..."
        Invoke-Compose -f docker-compose.cloud.yml down
        break
    }

    "reset" {
        Ensure-Docker
        Write-WarnMsg "Esto borrara TODOS los datos:"
        Write-WarnMsg "  - volumenes Docker (mongo_data, neo4j_data, neo4j_logs, spark_ivy)"
        Write-WarnMsg "  - contenido de data/{raw,silver,gold}/"
        $ans = Read-Host "Escribe 'yes' para continuar"
        if ($ans -ne "yes") {
            Write-Log "Cancelado"
            exit 0
        }
        Invoke-Compose down -v
        Remove-Item -LiteralPath "data/raw/*.json" -Force -ErrorAction SilentlyContinue
        Remove-Item -Path "data/silver/*" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -Path "data/gold/*"   -Recurse -Force -ErrorAction SilentlyContinue
        Write-Ok "Estado limpio. Arranca con: .\lab.ps1 up"
        break
    }

    # ------------------------------------------------------
    # Modo laboratorio
    # ------------------------------------------------------
    "unlock" {
        $kind  = $Arg1
        $block = $Arg2
        if (-not $kind -or -not $block) {
            Write-ErrMsg "Uso: .\lab.ps1 unlock {neo4j|ml} <bloque>"
            Write-Host  "  neo4j: basic | intermediate | advanced"
            Write-Host  "  ml:    supervised | unsupervised | graph_ml"
            exit 1
        }
        switch ($kind) {
            "neo4j" {
                $new = Update-Flag "LAB_NEO4J" "unlock" $block
                Write-Ok "LAB_NEO4J = $new"
            }
            "ml" {
                $new = Update-Flag "LAB_ML" "unlock" $block
                Write-Ok "LAB_ML    = $new"
            }
            default {
                Write-ErrMsg "kind debe ser 'neo4j' o 'ml'"
                exit 1
            }
        }
        Ensure-Docker
        Restart-App
        if ($kind -eq "ml") {
            Train-MLArtifacts
        }
        break
    }

    "lock" {
        $kind  = $Arg1
        $block = $Arg2
        if (-not $kind -or -not $block) {
            Write-ErrMsg "Uso: .\lab.ps1 lock {neo4j|ml} <bloque>"
            exit 1
        }
        switch ($kind) {
            "neo4j" {
                $new = Update-Flag "LAB_NEO4J" "lock" $block
                Write-Ok "LAB_NEO4J = $new"
            }
            "ml" {
                $new = Update-Flag "LAB_ML" "lock" $block
                Write-Ok "LAB_ML    = $new"
                Clear-MLArtifacts
            }
            default {
                Write-ErrMsg "kind debe ser 'neo4j' o 'ml'"
                exit 1
            }
        }
        Ensure-Docker
        Restart-App
        break
    }

    "solutions" {
        Update-Flag "LAB_NEO4J" "all" "" | Out-Null
        Update-Flag "LAB_ML"    "all" "" | Out-Null
        Write-Ok "Todo desbloqueado: LAB_NEO4J=all, LAB_ML=all"
        Ensure-Docker
        Restart-App
        Train-MLArtifacts
        break
    }

    "exercises" {
        Update-Flag "LAB_NEO4J" "none" "" | Out-Null
        Update-Flag "LAB_ML"    "none" "" | Out-Null
        Clear-MLArtifacts
        Write-Ok "Todo en modo ejercicio (scaffold)"
        Ensure-Docker
        Restart-App
        break
    }

    "status" {
        Write-Host ""
        Write-Log "Estado de los flags ($EnvFile):"
        if (Test-Path -LiteralPath $EnvFile) {
            Get-Content -LiteralPath $EnvFile |
                Where-Object { $_ -match '^LAB_NEO4J=|^LAB_ML=' } |
                ForEach-Object { "    $_" }
        }
        else {
            Write-WarnMsg "  $EnvFile no existe"
        }
        Write-Host ""
        if (Get-Command docker -ErrorAction SilentlyContinue) {
            Write-Log "Servicios Docker:"
            Ensure-Docker
            $psOut = Invoke-Compose ps 2>$null
            if ($LASTEXITCODE -eq 0 -and $psOut) {
                $psOut | ForEach-Object { "    $_" }
            }
            else {
                Write-WarnMsg "Compose no esta corriendo"
            }
        }
        Write-Host ""
        break
    }

    # ------------------------------------------------------
    # Pipeline de datos (dentro del contenedor app)
    # ------------------------------------------------------
    "seed" {
        Ensure-Docker
        Clear-MLArtifacts
        Write-Log "Generando datos sucios en data/raw/..."
        Invoke-Compose exec app python -m src.seed.generate_dirty_data
        break
    }

    "etl" {
        Ensure-Docker
        Clear-MLArtifacts
        Ensure-RawData
        Write-Log "Ejecutando Spark ETL completo (raw -> silver -> gold + carga Mongo/Neo4j)..."
        Invoke-Compose exec app python -m src.spark.run_pipeline --all
        break
    }

    "train" {
        Ensure-Docker
        Train-MLArtifacts
        break
    }

    "logs" {
        Ensure-Docker
        $svc = $Arg1
        if ($svc) {
            Invoke-Compose logs -f $svc
        }
        else {
            Invoke-Compose logs -f
        }
        break
    }

    # ------------------------------------------------------
    # Ayuda
    # ------------------------------------------------------
    default {
        @'
SocialLab - laboratorio en Docker (Windows / PowerShell)

Uso: .\lab.ps1 <comando> [args]

Ciclo de vida (modo local - todo en Docker):
    up [exercises|solutions]    Arranca el ecosistema completo (mongo+neo4j+app).
                                Sin argumento usa lo que haya en .env.docker.
    down                         Para los contenedores. Datos preservados.
    reset                        Borra volumenes y data/{raw,silver,gold} (pide confirmacion).
    status                       Muestra los flags actuales y estado de los servicios.

Ciclo de vida (modo cloud - Atlas + Aura, free tier):
    cloud                        Arranca SOLO el contenedor 'app' apuntando a las BBDD
                                cloud definidas en .env.cloud. Requiere haberlo creado
                                con: Copy-Item .env.cloud.example .env.cloud (y rellenar URIs).
                                Guia: docs/MIGRACION_CLOUD.md
    cloud-down                   Para el contenedor cloud.

Modo laboratorio:
    unlock {neo4j|ml} <bloque>  Marca un bloque como resuelto y reinicia el contenedor app.
    lock   {neo4j|ml} <bloque>  Vuelve a esconderlo (scaffold) y reinicia.
    solutions                    Desbloquea todo (atajo: LAB_NEO4J=all, LAB_ML=all).
    exercises                    Bloquea todo (todos los algoritmos como scaffold).

  Bloques Neo4j: basic | intermediate | advanced
  Bloques ML:    supervised | unsupervised | graph_ml

Pipeline de datos (se ejecuta dentro del contenedor app):
    seed                         Genera datos sucios en data/raw/.
    etl                          Spark: raw -> silver -> gold + carga MongoDB y Neo4j.
    train                        Entrena los modelos ML del LAB_ML actual.

Otros:
    logs [servicio]              Sigue logs (de todos o de mongodb|neo4j|app).
    help                         Esta ayuda.

Nota Windows: si PowerShell se queja con "no se puede cargar el script
porque la ejecucion de scripts esta deshabilitada", lanzalo asi una vez:
    powershell -ExecutionPolicy Bypass -File .\lab.ps1 <comando>
O bien (recomendado, una vez por usuario):
    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

Flujo tipico (primer arranque, alumno):
    .\lab.ps1 up exercises       # ecosistema en scaffold
    .\lab.ps1 seed               # genera raw data
    .\lab.ps1 etl                # carga la red social en Mongo+Neo4j
    # ... el alumno trabaja sobre los archivos *_ex.py ...

Flujo tipico (profesor en clase, va destapando):
    .\lab.ps1 unlock neo4j basic          # tras la clase de Cypher basico
    .\lab.ps1 unlock ml supervised        # tras la clase de clasificacion
    .\lab.ps1 status                      # comprobar que se desbloqueo

Flujo tipico (alumno con poco ordenador - modo cloud free):
    Copy-Item .env.cloud.example .env.cloud  # plantilla
    # editar .env.cloud con URIs de Atlas / Aura del profesor
    .\lab.ps1 cloud                       # ~150 MB RAM, sin mongo/neo4j locales

Web (ambos modos):     http://localhost:8000
Neo4j browser (local): http://localhost:7474   (neo4j / neo4jneo4j)
'@ | Write-Host
        break
    }
}
