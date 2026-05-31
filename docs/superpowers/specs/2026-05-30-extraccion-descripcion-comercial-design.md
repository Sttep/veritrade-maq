# Extracción estructurada de la Descripción Comercial — Diseño

**Fecha:** 2026-05-30
**Estado:** Aprobado (v1 exploratoria)

## Contexto / Origen de los datos

Archivo fuente: `Veritrade_JOSE.GOMEZ@DWMOTORS.PE_PE_I_20260430094944.xlsx`

- **Fuente:** Veritrade (inteligencia de comercio exterior, data de aduanas).
- **Descargado por:** `JOSE.GOMEZ@DWMOTORS.PE` (DW Motors, Perú).
- **Contenido:** Perú – Importaciones, partida aduanera `8704229000` ("SUPERIOR A 9,3 T", camiones diésel de carga).
- **Período:** Ene-2023 a Abr-2026.
- **Volumen:** 12.417 registros (la hoja tiene 5 filas de banner + 1 de cabecera en la fila 6 + datos desde la fila 7). 56 columnas.
- Una fila = una unidad importada (un vehículo, identificado por VIN/chasis).

## Objetivo

Producir una **tabla limpia para análisis exploratorio** (set ampliado, ~24 columnas extraídas + columnas duras), exportada a **.xlsx**. El structured output avanzado / enfoque LLM se decide en una fase posterior, usando el reporte de cobertura de esta v1.

## Hallazgos relevantes (exploración previa)

- La columna `Descripción Comercial` (col. 39) es **idéntica** a la concatenación de `Descripcion1–5` (cols. 48–52). Misma longitud carácter a carácter; no hay información extra.
- El campo es **semi-estructurado** con un diccionario de códigos estándar de aduana peruana (`MARCA:`, `MODELO:`, `CC:`, `EJ:`, etc.), separados por comas o espacios de forma **no uniforme** entre filas.
- **Truncamiento en origen:** Veritrade corta la descripción alrededor de 380–454 caracteres (a veces a media palabra). Afecta sobre todo a códigos del final (suspensión `SD/SP`, a veces `KILOMETRAJE`). Los campos del set ampliado aparecen al inicio del texto, por lo que son mayormente recuperables. **Limitación conocida, no recuperable.**
- Cobertura de códigos clave (sobre 12.417 registros con descripción): `MO`,`CO`,`PA`,`AN`,`AL`,`TT`,`FR`,`CC` ~100%; `EJ`,`PM` 99%; `VI` 98%; `CH` 97%; `MODELO` 75%; `MARCA` 46%; `KILOMETRAJE` 45%. (La marca/modelo en texto aparecen también embebidos en el token inicial `N3 MARCA:...`, a recuperar en el parser.)

## Columnas de la tabla final

### Columnas "duras" (copiadas del export)
Partida Aduanera, Aduana, DUA/DAM, Fecha, Importador, Embarcador/Exportador, Kg Bruto, Kg Neto, U$ FOB Tot, U$ CFR Tot, U$ CIF Tot, País de Origen, País de Compra, Puerto de Embarque, Vía, Agente de Aduana, Estado (nuevo/usado), Ad Valorem, IGV, ISC, IPM, Fecha Embarque.

### Columnas extraídas de la Descripción Comercial (~24)
`categoria` (N1/N2/N3), `marca`, `modelo`, `version`, `anio_modelo`, `vin`, `chasis`, `motor_serie`, `combustible`, `color`, `num_cilindros`, `cilindrada_cc`, `potencia`, `ejes`, `traccion`, `transmision`, `carroceria`, `asientos`, `puertas`, `peso_bruto`, `peso_neto`, `carga_util`, `largo_mm`, `ancho_mm`, `alto_mm`, `dist_ejes`, `kilometraje`.

Mapeo de códigos → columnas:

| Código | Columna | Tipo |
|---|---|---|
| (token inicial N1/N2/N3) | categoria | texto |
| MARCA | marca | texto |
| MODELO | modelo | texto |
| VERSION | version | texto |
| AÑO MOD / AÑO | anio_modelo | entero |
| VI | vin | texto |
| CH | chasis | texto |
| MO | motor_serie | texto |
| CO | combustible | texto |
| C1 | color | texto |
| NC | num_cilindros | entero |
| CC | cilindrada_cc | número |
| PM | potencia | texto crudo + HP numérico extraído |
| EJ | ejes | entero |
| FR | traccion | texto |
| TT | transmision | texto |
| CA | carroceria | texto |
| AS | asientos | entero |
| PA | puertas | entero |
| PB | peso_bruto | número |
| PN | peso_neto | número |
| CU | carga_util | número |
| LA | largo_mm | número |
| AN | ancho_mm | número |
| AL | alto_mm | número |
| DE | dist_ejes | número |
| KILOMETRAJE | kilometraje | número |

Nota: `CO` (combustible) y `C1` (color) a veces aparecen entremezclados en el texto; el parser los separa por código explícito, no por posición.

## Lógica del parser (Enfoque A — determinístico)

1. Leer el xlsx con cabecera en la fila 6, datos desde la fila 7 (`openpyxl`/`pandas`, `skiprows`).
2. Conservar las columnas duras.
3. Parsear `Descripción Comercial`:
   - Diccionario `CÓDIGO → (columna, tipo)`.
   - Regex tolerante que corta en pares `CÓDIGO:valor`, manejando separadores variables (coma/espacio) y el token inicial `N1/N2/N3`.
   - El valor de cada código se toma hasta el siguiente código conocido.
4. Normalización por tipo:
   - Numéricos → `float`/`int` (limpiando unidades).
   - Texto → trim + casing consistente.
   - `potencia` (ej. `132@2500`) → texto crudo + intento de extraer HP numérico a una columna auxiliar.
5. Lo que no matchea un código conocido se descarta (no se inventan datos).

## Salida y control de calidad

- Script Python único (pandas + openpyxl), reproducible.
- Salida: `camiones_8704229000_estructurado.xlsx`, una fila por unidad, columnas duras + extraídas.
- **Reporte de cobertura** impreso: % de filas con valor no nulo por campo extraído. Es el insumo para decidir el enfoque B (LLM) en la siguiente fase: si un campo importante queda muy vacío, se evalúa el híbrido solo para ese campo.
- Hoja opcional `_sin_parsear` con descripciones cuyo parseo quedó muy incompleto, para inspección manual.

## Fuera de alcance (v1)

- Enfoque B (LLM) y el structured output avanzado — se decide después con el reporte de cobertura.
- Recuperar texto truncado en origen (no es posible).
- Análisis/visualización del mercado (esta fase solo produce la tabla limpia).
