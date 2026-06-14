Especificación Técnica: Extracción Estructurada de Maquinaria Pesada
Fecha: 2026-06-09
Estado: Activo (v1.0 - Producción)
Basado en: 2026-05-30-extraccion-descripcion-comercial-design.md (camiones)

1. Contexto y Objetivo
1.1 Origen de los datos
Fuente: Veritrade (inteligencia de comercio exterior, data de aduanas peruanas)
Partidas: 8429.51, 8429.59, 8429.20, 8429.30, 8429.40, 8474.20, etc. (maquinaria pesada)
Formato: Archivos Excel con 5 filas de banner + 1 de cabecera (fila 6) + datos desde fila 7
Columnas: 56 columnas estándar de Veritrade (mismas que camiones)
Una fila = una unidad importada (identificada por VIN/chasis)

1.2 Objetivo
Transformar descripciones comerciales semi-estructuradas en una tabla limpia con:
22 columnas duras (copiadas del export)
45 columnas extraídas (parseadas de la Descripción Comercial + Descripción1/2)
Clasificación jerárquica con trazabilidad total
Exportación a Excel con pestañas de auditoría

1.3 Enfoque Híbrido
text
┌─────────────────────────────────────────────────────────────┐
│                    FASE A: Parser Determinístico              │
│  importacion_maquinaria.py                                    │
│  • Regex + diccionarios locales                               │
│  • Procesa el 100% de los registros                           │
│  • Clasifica con confianza ALTA/MEDIA/BAJA                    │
│  • Costo: $0                                                  │
│  • Tiempo: ~30s para 10k filas                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              FASE B: Rescate por IA (DeepSeek)                │
│  scripts/extract_llm.py                                       │
│  • Solo procesa registros con confianza ≠ "ALTA"             │
│  • Usa caché local para no repetir llamadas                   │
│  • Costo: ~$0.001 por registro nuevo                          │
│  • Tiempo: ~1-2s por registro                                 │
└─────────────────────────────────────────────────────────────┘
2. Arquitectura del Pipeline
text
VERITRADE-IMPORTS-MAQ/
├── diccionario_maquinaria.xlsx        ← ÚNICA FUENTE DE VERDAD
├── data/
│   └── vocab_extra.json               ← Extensiones curadas por SME
├── inputs/                            ← Archivos crudos de Veritrade
├── outputs/                           ← Resultados
│   ├── *_estructurado.xlsx            ← Fase A
│   ├── *_normalizado.xlsx             ← Fase A + B
│   └── *_revisar_final.xlsx           ← Registros dudosos
├── scripts/
│   ├── importacion_maquinaria.py      ← Fase A (parser determinístico)
│   ├── extract_llm.py                 ← Fase B (normalización LLM)
│   └── llm/
│       ├── vocab.py                   ← Carga vocabulario desde diccionario
│       ├── validate.py                ← Validación y normalización
│       ├── client.py                  ← Cliente API DeepSeek
│       ├── cache.py                   ← Caché de respuestas LLM
│       ├── report.py                  ← Generación de reportes
│       └── sampler.py                 ← Muestreo para pruebas
└── .env                               ← API key de DeepSeek
3. Diccionario Maestro: diccionario_maquinaria.xlsx
La única fuente de verdad. Cuando agregas una fila aquí, todo el ecosistema se actualiza automáticamente.

3.1 Pestaña marcas
Columna	Tipo	Descripción
marca_estandar	texto	Nombre canónico (ej: CATERPILLAR)
variacion	texto	Cómo aparece en aduanas (ej: CARTERPILLA)
prioridad	número	1=Alta, 2=Media, 3=Baja
es_mineria_sub	bool	TRUE si es marca de minería subterránea

3.2 Pestaña modelos
Columna	Tipo	Descripción
modelo	texto	Código del modelo (ej: 320D)
marca	texto	Marca estándar asociada
categoria	texto	EXCAVADORA, CARGADOR_FRONTAL, etc.
subcategoria	texto	ESTANDAR, MINI
tren_rodaje_default	texto	ORUGAS, RUEDAS

3.3 Pestaña grupos_importador
Columna	Tipo	Descripción
keyword	texto	Palabra clave en razón social
grupo	texto	Grupo empresarial (ej: GRUPO FERREYCORP)

3.4 Pestaña exclusiones
Columna	Tipo	Descripción
termino	texto	Palabra a detectar
categoria_exclusion	texto	REPUESTO, JUGUETE, SUBTERRANEO, USADO
es_exclusion_total	bool	TRUE = invalida siempre; FALSE = solo si no hay modelo

3.5 Pestaña palabras_clave
Columna	Tipo	Descripción
palabra	texto	Palabra clave (ej: BACKHOE)
categoria_asignada	texto	Categoría que asigna
peso	número	1=Definitivo, 2=Fuerte, 3=Débil

4. Columnas de Salida

4.1 Columnas Duras (22)
text
Partida Aduanera, Aduana, DUA/DAM, Fecha, Importador,
Embarcador/Exportador, Kg Bruto, Kg Neto, Qty 1, Und 1,
Qty 2, Und 2, U$ FOB Tot, U$ CFR Tot, U$ CIF Tot,
País Origen, País Compra, Puerto Embarque, Vía,
Agente Aduana, Estado, Ad Valorem, IGV, ISC, IPM,
Fecha Embarque, Descripción Comercial, Descripción1, Descripción2
4.2 Columnas Extraídas (45)
text
# Temporales
año_dua, mes_dua, trimestre_dua

# Clasificación principal
categoria_maquinaria, subcategoria, categoria_peso,
grupo_importador, confianza_clasificacion, regla_aplicada

# Identificación
marca, modelo, version, anio_modelo,
vin, chasis, motor_serie

# Motor y rendimiento
combustible, tipo_combustible, sub_tipo_combustible,
motor_marca, num_cilindros, cilindrada_cc,
potencia, potencia_hp, velocidad_max_kmh

# Dimensiones y pesos
peso_bruto_kg, peso_neto_kg, peso_operativo_kg,
largo_mm, ancho_mm, alto_mm, dist_ejes_mm

# Específicos de maquinaria
tren_rodaje, capacidad_cucharon_m3,
alcance_maximo_mm, profundidad_excavacion_mm

# Tren de fuerza y cabina
transmision_tipo, frenos_tipo,
control_tipo, aire_acondicionado, cabina_cerrada

# Otros
color, horas_uso, kilometraje, tanque_combustible_l,
desc_prefijo
4.3 Mapeo de Códigos → Columnas
Código	Columna	Tipo
MARCA	marca_codigo	texto
MODELO	modelo_codigo	texto
VERSION	version	texto
AÑO MOD / AÑO	anio_modelo	entero
VI	vin	texto
CH	chasis	texto
MO	motor_serie	texto
CO / COMB	combustible	texto
C1	color	texto
NC	num_cilindros	entero
CC	cilindrada_cc	número
PM	potencia	power
PB	peso_bruto_kg	número
PN	peso_neto_kg	número
LA	largo_mm	número
AN	ancho_mm	número
AL	alto_mm	número
DE	dist_ejes_mm	número
KILOMETRAJE	kilometraje	número
HORAS / HM	horas_uso	número
PE / PO	peso_operativo_kg	número
CU / CA	capacidad_cucharon_m3	número
ALC	alcance_maximo_mm	número
PR	profundidad_excavacion_mm	número
TR	tren_rodaje_codigo	texto
CT	control_tipo	texto
AC	aire_acondicionado	texto
VEL	velocidad_max_kmh	número
TAN	tanque_combustible_l	número
FR	frenos_tipo	texto
TRANS	transmision_tipo	texto
MOT / MOTOR	motor_marca	texto

5. Lógica del Parser (Fase A)

5.1 Etapas de Procesamiento
text
ETAPA 0: Validación pre-vuelo
├── Cargar diccionario_maquinaria.xlsx
├── Validar estructura de las 5 pestañas
└── Ejecutar tests de regresión (8 casos conocidos)

ETAPA 1: Carga
└── Leer Excel con header en fila 6

ETAPA 2: Parseo vectorizado
├── Extraer códigos estructurados (CO:, PM:, LA:, etc.)
├── Extraer marca (regex compilada + variaciones)
├── Extraer modelo (diccionario + regex con \b)
└── Extraer año, color, dimensiones

ETAPA 3: Clasificación jerárquica (con escape temprano)
├── 3.1 Excluir (repuestos, juguetes, subterráneo)
├── 3.2 Clasificar por modelo conocido → confianza ALTA
├── 3.3 Clasificar por palabras clave → confianza MEDIA
├── 3.4 Clasificar por inferencia → confianza BAJA
├── 3.5 Caso especial PALA (lookaheads + peso)
├── 3.6 Subcategoría MINI/ESTANDAR
└── 3.7 Tren de rodaje

ETAPA 4: Columnas derivadas
├── Grupo importador
├── Tipo combustible
└── Categoría peso (Kg Bruto × Qty 1 / 1000)

ETAPA 5: Filtros
├── Estado NUEVO
├── Kilometraje ≤ 100 km
├── Horas ≤ 50
└── Excluir categorías EXCLUIDO

ETAPA 6: Auditoría
├── Distribución de confianza
├── Alertas de coherencia peso/categoría
└── Importadores no mapeados

ETAPA 7: Exportación
├── Pestaña "estructurado" (datos completos)
├── Pestaña "_revisar" (confianza BAJA)
└── Pestaña "_auditoria" (métricas)

5.2 Reglas de Clasificación
Prioridad de clasificación:
Modelo exacto en diccionario → Categoría del diccionario (confianza ALTA)
Palabras clave con peso 1 → Categoría asignada (confianza ALTA)
Palabras clave con peso 2-3 → Categoría asignada (confianza MEDIA)
Inferencia por marca → Categoría más común de la marca (confianza BAJA)
Sin información suficiente → OTROS / REVISAR (confianza BAJA)
Caso especial PALA:

Texto	Contexto	Clasificación
PALA + ELÉCTRICA/CABLE	Cualquiera	PALA MINERA (EXCLUIDA)
PALA + EXCAVADORA	Cualquiera	EXCAVADORA
PALA + CARGADORA	Cualquiera	CARGADOR FRONTAL
PALA + HIDRÁULICA	Peso > 50t	PALA HIDRAULICA GRANDE
PALA + HIDRÁULICA	Peso ≤ 50t	EXCAVADORA
PALA solo	Sin contexto	PALA (REVISAR)

5.3 Escape Temprano
Si el 80% de registros se clasifica en la etapa 3.2 (por modelo), las etapas 3.3 y 3.4 solo procesan el 20% restante. Esto reduce el tiempo de procesamiento proporcionalmente.

6. Fase B: Rescate por IA (DeepSeek)

6.1 ¿Qué se envía al LLM?
Solo registros con confianza_clasificacion != "ALTA"
El texto crudo de la Descripción Comercial
Se usa caché local para no repetir llamadas

6.2 ¿Qué devuelve el LLM?
json
{
  "items": [
    {
      "i": 0,
      "marca": "CATERPILLAR",
      "modelo_codigo": "320D",
      "tren_rodaje": "Orugas",
      "combustible": "Diesel",
      "categoria_maquinaria": "Excavadora"
    }
  ]
}

6.3 Validación post-LLM
Fuzzy match del modelo contra el vocabulario (≥90% = ok, ≥75% = low, <75% = nomatch)
Normalización de enums vía sinónimos (TREN_RODAJE_SYN, CATEGORIA_MAQUINARIA_SYN)
Alias de modelo curados por SME (model_aliases en vocab_extra.json)

6.4 Columnas generadas por la Fase B
text
marca_raw_llm, marca_norm, marca_in_vocab, marca_sugerencia,
modelo_raw_llm, modelo_match, modelo_score, modelo_flag,
tren_rodaje_norm, tren_rodaje_valido,
combustible_norm, combustible_valido,
categoria_maquinaria_norm, categoria_maquinaria_valido,
fuente

6.5 Pestañas del output normalizado
Pestaña	Contenido
normalizado_llm	Todos los registros (Fase A + B)
_revisar_llm	Registros con flags (low, nomatch, alias, fuera de vocab)
_vocab_nuevo	Marcas nuevas encontradas (para retroalimentar el diccionario)
_reporte	Métricas de la ejecución

7. Reglas de Negocio

7.1 Filtros obligatorios
Estado: Solo NUEVO, NUEVA, NEW, 0 KM, SIN USO (10 variaciones)
Kilometraje: ≤ 100 km (o nulo)
Horas de uso: ≤ 50 (o nulo)
Exclusiones totales: REPUESTO, JUGUETE, SUBTERRANEO, USADO → Invalidan el registro
Exclusiones parciales: MARTILLO, PARA → Solo invalidan si NO hay modelo detectado

7.2 Trazabilidad
Cada registro tiene una columna regla_aplicada que explica exactamente por qué se clasificó:

text
"Regla: Modelo 320D → EXCAVADORA"
"Regla: PALA + EXCAVADORA → EXCAVADORA"
"Regla: Keyword 'WHEEL LOADER' → CARGADOR FRONTAL"
"Regla: Inferido por marca CATERPILLAR → EXCAVADORA"
"Regla: Sin suficiente información → REVISAR"

7.3 Confianza
ALTA: Modelo exacto en diccionario o keyword peso 1
MEDIA: Keyword peso 2-3 o PALA con contexto claro
BAJA: Inferencia por marca o sin información suficiente

8. Mantenibilidad

8.1 Agregar una nueva marca
Abrir diccionario_maquinaria.xlsx → pestaña marcas
Agregar fila: marca_estandar, variacion, prioridad, es_mineria_sub
Abrir pestaña modelos → agregar modelos de esa marca
Guardar. El código no se toca.

8.2 Agregar un nuevo modelo
Abrir diccionario_maquinaria.xlsx → pestaña modelos
Agregar fila: modelo, marca, categoria, subcategoria, tren_rodaje_default
Guardar. El código no se toca.

8.3 Agregar un nuevo grupo importador
Abrir diccionario_maquinaria.xlsx → pestaña grupos_importador
Agregar fila: keyword, grupo
Guardar. El código no se toca.

9. Ejecución

9.1 Fase A (Parser Determinístico)
bash
# Procesar todos los archivos en inputs/
python scripts/importacion_maquinaria.py

# Procesar un archivo específico
python scripts/importacion_maquinaria.py --input "inputs/veritrade_2025.xlsx"

# Procesar con muestra (pruebas)
python scripts/importacion_maquinaria.py --input "inputs/veritrade_2025.xlsx" --sample 100

9.2 Fase B (Rescate LLM)
bash
# Procesar con DeepSeek
python scripts/extract_llm.py --input "inputs/veritrade_2025.xlsx"

# Modo dry-run (sin llamar a la API)
python scripts/extract_llm.py --input "inputs/veritrade_2025.xlsx" --dry-run

# Solo procesar una muestra
python scripts/extract_llm.py --input "inputs/veritrade_2025.xlsx" --sample 50

10. Control de Calidad

10.1 Tests de regresión
8 casos de prueba se ejecutan antes de cada corrida:
CATERPILLAR 320D → Excavadora
PALA CARGADORA SDLG L958 → Cargador Frontal
KOMATSU PC200-10 → Excavadora
VOLVO L150H → Cargador Frontal
PALA ELECTRICA P&H → Pala Minera (Excluida)
CAT D8T → Bulldozer
CASE 580SN → Retroexcavadora
JOHN DEERE 670G → Motoniveladora

10.2 Métricas de auditoría
Distribución de confianza (ALTA/MEDIA/BAJA)
Alertas de coherencia (MINI con peso > 8t)
Importadores no mapeados con alto volumen

10.3 Pestañas de revisión
_revisar: Registros con confianza BAJA (revisión humana)
_revisar_llm: Registros donde el LLM tuvo dudas
_vocab_nuevo: Marcas nuevas para agregar al diccionario

11. Fuera de Alcance (v1)
Análisis/visualización de mercado
Predicción de tendencias
Integración con bases de datos externas
Recuperación de texto truncado en origen (no es posible)
