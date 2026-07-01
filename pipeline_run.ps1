# =============================================================
#  PIPELINE - IMPORTACIONES DE MAQUINARIA PESADA
#  Uso: Abrir PowerShell en la carpeta del proyecto y ejecutar:
#       .\pipeline_run.ps1
# =============================================================

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ─────────────────────────────────────────────────────────────
#  PARTIDAS ADUANERAS
#  Estas son las partidas que se descargan de Veritrade.
#  En Veritrade buscas por "8429" y seleccionas todas.
# ─────────────────────────────────────────────────────────────
$PARTIDAS = @(
    [PSCustomObject]@{ Codigo = "8429110000"; Descripcion = "Bulldozers / Topadoras de oruga" },
    [PSCustomObject]@{ Codigo = "8429200000"; Descripcion = "Motoniveladoras" },
    [PSCustomObject]@{ Codigo = "8429400000"; Descripcion = "Compactadoras vibratorias" },
    [PSCustomObject]@{ Codigo = "8429510000"; Descripcion = "Cargadoras frontales (Wheel Loaders)" },
    [PSCustomObject]@{ Codigo = "8429520000"; Descripcion = "Excavadoras (superestructura giratoria 360)" },
    [PSCustomObject]@{ Codigo = "8429590000"; Descripcion = "Retroexcavadoras y otras autopropulsadas" }
)

# ─────────────────────────────────────────────────────────────
#  CONFIGURACION
# ─────────────────────────────────────────────────────────────
$PYTHON     = ".venv\Scripts\python.exe"
$INPUTS_DIR = "inputs"
$OUTPUTS_DIR= "outputs"

# ─────────────────────────────────────────────────────────────
#  FUNCIONES
# ─────────────────────────────────────────────────────────────
function Titulo($texto) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $texto" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Paso($n, $texto) {
    Write-Host ""
    Write-Host "--- PASO $n : $texto" -ForegroundColor Yellow
}

function OK($texto)    { Write-Host "  [OK] $texto"    -ForegroundColor Green  }
function WARN($texto)  { Write-Host "  [!]  $texto"    -ForegroundColor Yellow }
function ERROR($texto) { Write-Host "  [X]  $texto"    -ForegroundColor Red    }

function Preguntar($pregunta) {
    Write-Host ""
    $resp = Read-Host "$pregunta [S/N]"
    return ($resp -match "^[Ss]")
}

# ─────────────────────────────────────────────────────────────
#  INICIO
# ─────────────────────────────────────────────────────────────
Titulo "PIPELINE MAQUINARIA PESADA - VERITRADE"

# Verificar entorno
if (-not (Test-Path $PYTHON)) {
    ERROR "No se encontro el entorno virtual. Ejecuta primero:"
    Write-Host "  python -m venv .venv" -ForegroundColor Gray
    Write-Host "  .venv\Scripts\pip install -r requirements.txt" -ForegroundColor Gray
    exit 1
}

if (-not (Test-Path ".env")) {
    WARN "No se encontro .env con la API key de DeepSeek."
    WARN "Crea el archivo .env con: DEEPSEEK_API_KEY=sk-..."
}

# Mostrar partidas
Write-Host ""
Write-Host "  PARTIDAS A DESCARGAR DE VERITRADE:" -ForegroundColor White
foreach ($p in $PARTIDAS) {
    Write-Host ("  {0}  {1}" -f $p.Codigo, $p.Descripcion) -ForegroundColor Gray
}
Write-Host ""
Write-Host "  Filtros en Veritrade: Pais=Peru | Tipo=Importacion | Estado=NUEVO" -ForegroundColor Gray

# ─────────────────────────────────────────────────────────────
#  PASO 0 - Verificar archivos nuevos en inputs/
# ─────────────────────────────────────────────────────────────
Paso 0 "Verificar archivos en inputs/"

$archivos_input = Get-ChildItem "$INPUTS_DIR\*.xlsx" -ErrorAction SilentlyContinue
if ($archivos_input.Count -eq 0) {
    ERROR "No hay archivos .xlsx en $INPUTS_DIR/"
    Write-Host "  Descarga los archivos de Veritrade y ponlos en la carpeta inputs/" -ForegroundColor Gray
    exit 1
}

OK "$($archivos_input.Count) archivo(s) encontrado(s) en $INPUTS_DIR/"
foreach ($f in $archivos_input) {
    $mb = [math]::Round($f.Length / 1MB, 2)
    Write-Host "     $($f.Name) ($mb MB)" -ForegroundColor Gray
}

# ─────────────────────────────────────────────────────────────
#  PASO 1 - Validar inputs
# ─────────────────────────────────────────────────────────────
Paso 1 "Validar archivos de Veritrade"

$env:PYTHONIOENCODING = "utf-8"
& $PYTHON scripts\validar_input.py

if ($LASTEXITCODE -ne 0) {
    ERROR "La validacion encontro errores criticos. Revisa los archivos antes de continuar."
    if (-not (Preguntar "Continuar de todas formas?")) { exit 1 }
} else {
    OK "Validacion OK"
}

# ─────────────────────────────────────────────────────────────
#  PASO 2 - Fase A: Estructurar y clasificar
# ─────────────────────────────────────────────────────────────
Paso 2 "Fase A - Estructuracion y clasificacion (extract_descripcion.py)"
Write-Host "  Clasifica tipo de maquinaria, detecta marcas por reglas, filtra NUEVO y FOB > 5000" -ForegroundColor Gray

if (Preguntar "Ejecutar Fase A?") {
    & $PYTHON scripts\extract_descripcion.py
    if ($LASTEXITCODE -ne 0) {
        ERROR "Fase A termino con errores."
        if (-not (Preguntar "Continuar con Fase B de todas formas?")) { exit 1 }
    } else {
        OK "Fase A completada"
    }
} else {
    WARN "Fase A omitida"
}

# ─────────────────────────────────────────────────────────────
#  PASO 3 - Fase B: Normalizar con LLM (DeepSeek)
# ─────────────────────────────────────────────────────────────
Paso 3 "Fase B - Normalizacion con LLM (extract_llm.py)"
Write-Host "  Usa DeepSeek para extraer marca/modelo de descripciones con confianza MEDIA/BAJA" -ForegroundColor Gray
Write-Host "  Requiere: DEEPSEEK_API_KEY en .env y creditos disponibles" -ForegroundColor Gray

$archivos_struct = Get-ChildItem "$OUTPUTS_DIR\*_estructurado.xlsx" -ErrorAction SilentlyContinue
if ($archivos_struct.Count -eq 0) {
    WARN "No hay archivos _estructurado.xlsx en outputs/ - ejecuta Fase A primero"
} else {
    OK "$($archivos_struct.Count) archivo(s) estructurado(s) listos para Fase B"
}

if (Preguntar "Ejecutar Fase B (consume creditos de DeepSeek)?") {
    & $PYTHON scripts\extract_llm.py
    if ($LASTEXITCODE -ne 0) {
        ERROR "Fase B termino con errores."
        if (-not (Preguntar "Continuar con comprimir de todas formas?")) { exit 1 }
    } else {
        OK "Fase B completada"
    }
} else {
    WARN "Fase B omitida"
}

# ─────────────────────────────────────────────────────────────
#  PASO 4 - Comprimir: generar parquet
# ─────────────────────────────────────────────────────────────
Paso 4 "Comprimir - Generar datos_maquinaria.parquet (comprimir.py)"
Write-Host "  Une todos los _normalizado.xlsx, elimina duplicados, excluye partes, etiqueta SIN MARCA" -ForegroundColor Gray

$archivos_norm = Get-ChildItem "$OUTPUTS_DIR\*_normalizado.xlsx" -ErrorAction SilentlyContinue
if ($archivos_norm.Count -eq 0) {
    ERROR "No hay archivos _normalizado.xlsx. Ejecuta las Fases A y B primero."
    exit 1
}
OK "$($archivos_norm.Count) archivo(s) normalizado(s) para comprimir"

if (Preguntar "Generar parquet?") {
    & $PYTHON comprimir.py
    if ($LASTEXITCODE -ne 0) {
        ERROR "comprimir.py termino con errores."
        exit 1
    } else {
        $parquet = Get-Item "datos_maquinaria.parquet" -ErrorAction SilentlyContinue
        if ($parquet) {
            $mb = [math]::Round($parquet.Length / 1MB, 2)
            OK "Parquet generado: $mb MB"
        }
    }
} else {
    WARN "Compresion omitida"
}

# ─────────────────────────────────────────────────────────────
#  PASO 5 - Verificar resultado
# ─────────────────────────────────────────────────────────────
Paso 5 "Verificar parquet"

if (Test-Path "datos_maquinaria.parquet") {
    $resultado = & $PYTHON -c "
import pandas as pd
df = pd.read_parquet('datos_maquinaria.parquet')
fecha_min = df['fecha_dua'].min()
fecha_max = df['fecha_dua'].max()
print(f'{len(df):,} registros | {fecha_min} -> {fecha_max}')
" 2>&1
    OK $resultado
} else {
    ERROR "No se encontro datos_maquinaria.parquet"
}

# ─────────────────────────────────────────────────────────────
#  PASO 6 - Subir a GitHub
# ─────────────────────────────────────────────────────────────
Paso 6 "Subir a GitHub (Streamlit Cloud se actualiza automaticamente)"

if (Preguntar "Subir datos_maquinaria.parquet a GitHub?") {
    $mes = Read-Host "  Descripcion del commit (ej: julio 2026)"
    git add datos_maquinaria.parquet
    git commit -m "Datos actualizados: $mes"
    git push origin main
    if ($LASTEXITCODE -eq 0) {
        OK "Push exitoso - el dashboard se actualizara en ~1 minuto"
    } else {
        ERROR "Error en git push"
    }
} else {
    WARN "Push omitido - recorda subirlo manualmente"
}

# ─────────────────────────────────────────────────────────────
#  FIN
# ─────────────────────────────────────────────────────────────
Titulo "PIPELINE COMPLETADO"
