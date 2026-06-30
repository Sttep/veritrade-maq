# Pipeline de Datos — Importaciones de Maquinaria Pesada

## Qué hace este sistema

Toma archivos Excel crudos de Veritrade (declaraciones de importación de Aduanas Perú) y los convierte en un dashboard interactivo. El proceso tiene 4 etapas en cadena.

```
inputs/          Fase A             Fase B            Consolidar        Dashboard
Veritrade  →  extract_descripcion  →  extract_llm  →  comprimir.py  →  dashboard.py
.xlsx             _estructurado.xlsx    _normalizado.xlsx   parquet
```

---

## Qué descargar de Veritrade cada mes

### Filtros que debes aplicar en Veritrade

| Campo | Valor |
|---|---|
| **País** | Perú |
| **Tipo operación** | Importación |
| **Partidas aduaneras** | 8429 (Bulldozers, Motoexcavadoras, Niveladoras) + 8430 (Otras máquinas de movimiento de tierra) |
| **Estado de la mercancía** | NUEVO |
| **Período** | El mes que quieres agregar (ej: junio 2024) |

### Formato de descarga

- Formato: **Excel (.xlsx)**
- Incluir: Descripción Comercial (columna `Descripcion Comercial`)
- La cabecera del Excel de Veritrade está en la **fila 6** — no cambiar esto
- El nombre del archivo lo asigna Veritrade automáticamente con timestamp

### Columnas que deben existir en el Excel descargado

El pipeline requiere estas columnas (Veritrade las incluye por defecto):

```
Partida Aduanera | Aduana | DUA / DAM | Fecha | Importador | Embarcador / Exportador
Kg Bruto | Kg Neto | Qty 1 | Und 1 | U$ FOB Tot | U$ CFR Tot | U$ CIF Tot
Pais de Origen | Estado | Ad Valorem | Descripcion Comercial
```

### ¿Cuántos archivos descargar?

Veritrade limita la cantidad de filas por descarga. Si un mes tiene muchos registros, puede requerir **2 o más archivos** con rangos de fechas distintos. Todos los archivos del mismo mes se procesan juntos — el pipeline maneja múltiples archivos automáticamente.

---

## Paso a paso para agregar un mes nuevo

### Requisitos previos

- Python con el entorno virtual activado: `.venv\Scripts\Activate.ps1`
- Archivo `.env` en la raíz con: `DEEPSEEK_API_KEY=sk-...`
- Créditos disponibles en [platform.deepseek.com](https://platform.deepseek.com)

---

### PASO 0 — Validar el archivo antes de procesar (SIEMPRE HACER ESTO PRIMERO)

```bash
python scripts/validar_input.py --input inputs/Veritrade_NUEVO_ARCHIVO.xlsx
```

Este script revisa que el archivo sea correcto antes de gastar tiempo y créditos de API. Si reporta errores críticos, no continuar.

---

### PASO 1 — Mover el archivo descargado a `inputs/`

Copiar el Excel de Veritrade a la carpeta `inputs/`. No renombrar — el nombre con timestamp de Veritrade está bien.

```
inputs/
  Veritrade_JOSE.GOMEZ@DWMOTORS.PE_PE_I_20260609145232.xlsx  ← existente
  Veritrade_JOSE.GOMEZ@DWMOTORS.PE_PE_I_20260701120000.xlsx  ← nuevo
```

---

### PASO 2 — Fase A: Estructurar y clasificar

Extrae la información de cada declaración, clasifica el tipo de maquinaria y detecta marcas conocidas por reglas.

**Para procesar solo el archivo nuevo:**
```bash
python scripts/extract_descripcion.py --input inputs/Veritrade_NOMBRE_ARCHIVO.xlsx
```

**Para reprocesar todos los archivos:**
```bash
python scripts/extract_descripcion.py
```

**Salida:** `outputs/Veritrade_NOMBRE_ARCHIVO_estructurado.xlsx`

**Qué hace internamente:**
- Etapa 1: Carga el Excel (cabecera fila 6)
- Etapa 2: Extrae marca, modelo, VIN, potencia, peso, combustible de la descripción comercial
- Etapa 3: Clasifica tipo de maquinaria (EXCAVADORA, CARGADOR FRONTAL, RETROEXCAVADORA, etc.)
- Etapa 4: Asigna grupo importador y categoría de peso
- Etapa 5: Filtra registros que no cumplen criterios:
  - Solo estado NUEVO / 0 KM / SIN USO
  - Máximo 100 km o 50 horas de uso
  - FOB mayor a $5,000 (para excluir partes y repuestos)
  - Excluye maquinaria minera subterránea

---

### PASO 3 — Fase B: Normalización con LLM (DeepSeek)

Para los registros donde la Fase A no pudo identificar la marca con alta confianza, consulta a DeepSeek para extraerla de la descripción en lenguaje libre.

**Para procesar solo el archivo nuevo:**
```bash
python scripts/extract_llm.py --input inputs/Veritrade_NOMBRE_ARCHIVO.xlsx
```

**Para procesar todos:**
```bash
python scripts/extract_llm.py --all
```

**Salida:** `outputs/Veritrade_NOMBRE_ARCHIVO_normalizado.xlsx`

**Notas importantes:**
- Solo envía al LLM los registros con confianza MEDIA o BAJA — los de confianza ALTA se resuelven por reglas y no gastan créditos
- Tiene caché: si un texto ya fue procesado antes, no lo vuelve a enviar
- El archivo `_normalizado.xlsx` tiene 4 hojas:
  - `normalizado_final` — datos completos para el dashboard
  - `_revisar_final` — registros que el LLM tampoco pudo resolver
  - `_vocab_nuevo` — marcas detectadas que no están en el vocabulario
  - `_reporte` — estadísticas de cobertura

---

### PASO 4 — Comprimir y actualizar el parquet

Consolida todos los `_normalizado.xlsx` de `outputs/` en un único archivo parquet para el dashboard.

```bash
python comprimir.py
```

**Lo que hace:**
- Une todos los archivos normalizados
- Excluye registros con FOB < $5,000 (partes/repuestos)
- Etiqueta automáticamente como "SIN MARCA" los registros con "S/M" en la descripción
- Genera `datos_maquinaria.parquet` (el archivo que lee el dashboard)

---

### PASO 5 — Verificar y publicar

```bash
# Verificar que el parquet se generó bien
python -c "import pandas as pd; df=pd.read_parquet('datos_maquinaria.parquet'); print(f'{len(df):,} registros, hasta {df[chr(102)+chr(101)+chr(99)+chr(104)+chr(97)+chr(95)+chr(100)+chr(117)+chr(97)].max()}')"

# Subir a GitHub (Streamlit Cloud se actualiza automáticamente)
git add datos_maquinaria.parquet
git commit -m "Datos actualizados: [MES AÑO]"
git push
```

---

## Estructura de carpetas

```
veritrade-imports-maq/
├── inputs/                    ← Excel crudos de Veritrade (NO se suben a GitHub)
├── outputs/                   ← Excel procesados intermedios (NO se suben a GitHub)
├── data/
│   ├── diccionario_maquinaria.xlsx   ← Vocabulario principal (marcas, modelos, exclusiones)
│   └── vocab_extra.json              ← Extensión editable del vocabulario
├── scripts/
│   ├── extract_descripcion.py        ← Fase A
│   ├── extract_llm.py                ← Fase B
│   └── llm/                          ← Módulos del cliente DeepSeek
├── datos_maquinaria.parquet   ← Base de datos para el dashboard (SE SUBE a GitHub)
├── dashboard.py               ← App Streamlit
├── comprimir.py               ← Genera el parquet
└── .env                       ← API key DeepSeek (NUNCA subir a GitHub)
```

---

## Calendario de actualización recomendado

| Cuándo | Qué hacer |
|---|---|
| Primer lunes de cada mes | Descargar el mes anterior completo de Veritrade |
| Mismo día | Correr Fase A → Fase B → comprimir → push |
| Antes de reuniones comerciales | Verificar que el parquet tenga datos del mes previo |

**Importante:** Veritrade puede tener un rezago de 15-30 días en sus datos. Si descargas el mes actual a mediados de mes, los datos estarán incompletos. El dashboard avisa automáticamente cuando detecta un mes parcial.

---

## Solución de problemas frecuentes

| Problema | Causa probable | Solución |
|---|---|---|
| "No se encontró 'Descripcion Comercial'" | El Excel no tiene esa columna | Verificar la descarga en Veritrade, revisar que incluya descripciones |
| Fase B termina sin procesar nada | Falta `_estructurado.xlsx` | Correr Fase A primero |
| Error de API key | `.env` no existe o clave incorrecta | Verificar `.env` y saldo en platform.deepseek.com |
| Parquet vacío después de comprimir | FOB filter eliminó todo | Revisar que los datos sean NUEVOS y tengan FOB > $5,000 |
| El dashboard muestra mes incompleto | Los datos descargados no cubren el mes entero | Normal — el aviso es informativo, no un error |
| Junio 2024 excavadoras muy bajas | Mes no descargado | Descargar ese mes de Veritrade y reprocesar |
