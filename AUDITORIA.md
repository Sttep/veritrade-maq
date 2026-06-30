# Auditoría del Proyecto — Dashboard Maquinaria
**Fecha:** 2026-06-30  
**Estado general:** 🟡 FUNCIONAL CON RIESGOS DE SEGURIDAD

---

## Resumen Ejecutivo

| Aspecto | Estado | Notas |
|---|---|---|
| Estructura | ✅ Buena | Separación limpia entre pipeline, dashboard y backend+frontend |
| Dependencias | ✅ Correctas | Todos los imports cubiertos (resto es stdlib) |
| Datos | ✅ Presentes | 20,610 registros, columnas correctas, parquet optimizado (3.4 MB) |
| Código | 🟡 Aceptable | 13 funciones bien definidas, pero try/except genéricos |
| Seguridad | 🔴 CRÍTICA | Clave API expuesta en historial de git |
| Configuración | 🟠 Incompleta | Falta `.streamlit/config.toml`, `netlify.toml` huérfano |
| Documentación | 🟡 Parcial | README presente, funciones sin docstring |

---

## 🔴 Críticos (Acción Inmediata)

### 1. Clave DeepSeek API expuesta en historial de git
**Archivo:** `.env` — commit `a922b71d1852` (Jun 21, 2026)

La clave `DEEPSEEK_API_KEY=sk-f7a098eb...` estuvo en el repositorio y puede haber quedado en el historial de GitHub aunque luego se quitara del árbol.

**Acción requerida:**
1. Revocar la clave actual en [platform.deepseek.com](https://platform.deepseek.com)
2. Generar una nueva clave
3. Configurar la nueva clave en **Streamlit Cloud → Secrets** (no en `.env` local)
4. Limpiar el historial de git:
```bash
git filter-branch --tree-filter 'rm -f .env' -- --all
git push --force origin main
```

---

### 2. Errores silenciosos en carga de datos
**Archivo:** `dashboard.py` líneas 479–482

```python
# ACTUAL (problemático):
try:
    df_temp = pd.read_excel(f, sheet_name='normalizado_final')
except:
    pass  # <-- el usuario NUNCA sabe qué archivo falló
```

Si un archivo Excel de `outputs/` falla al cargar, la app sigue sin mostrar nada. El usuario solo ve "No se encontraron datos procesables."

**Fix sugerido:**
```python
except Exception as e:
    print(f"[ERROR] No se pudo leer {f.name}: {e}")
```

---

### 3. COL_FOB / COL_CIF pueden ser None → KeyError
**Archivo:** `dashboard.py` líneas 531–535 y 419

`MAPEO_COLUMNAS` busca columnas con fallbacks. Si ninguna variante existe en el parquet, `COL_FOB` queda como `None`, lo que genera un `KeyError` en tiempo de ejecución en línea 419.

**Fix sugerido:** agregar validación después de línea 535:
```python
if COL_FOB is None:
    st.error("Error: No se encontró columna de valor FOB en los datos.")
    st.stop()
```

---

### 4. Falta `.streamlit/config.toml`
Sin este archivo, en Streamlit Cloud no hay control sobre:
- Timeouts (por defecto 30s — puede fallar con datasets grandes)
- Tema visual (light/dark)
- Tamaño máximo de uploads

**Fix sugerido:** crear `.streamlit/config.toml`:
```toml
[server]
maxUploadSize = 500

[theme]
base = "light"
```

---

## 🟠 Advertencias (Revisar Pronto)

### 5. `try/except` genéricos
**Archivo:** `dashboard.py` líneas 447, 452, 504–509

Capturan `Exception` sin especificar tipo. Ocultan errores reales como permisos de archivo, memoria insuficiente, etc.

### 6. `netlify.toml` huérfano
**Archivo:** `netlify.toml` en la raíz

El deploy es en **Streamlit Cloud**, no Netlify. Este archivo corresponde al frontend React (que es una app separada). Puede confundir a quien trabaje en el proyecto o a bots de Netlify si la cuenta está conectada.

**Acción:** documentar que aplica solo al frontend, o moverlo a `frontend/netlify.toml`.

### 7. CSS embebido de 220 líneas
**Archivo:** `dashboard.py` función `cargar_css()` (líneas 62–282)

Es mantenible pero mezclado con la lógica. Si el dashboard crece, esto se vuelve difícil de editar.

**Acción (opcional):** mover a `.streamlit/style.css` e inyectar con:
```python
with open(".streamlit/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
```

### 8. `openpyxl` posiblemente innecesario en producción
**Archivo:** `requirements.txt`

Solo se usa si `datos_maquinaria.parquet` no existe y el dashboard cae al fallback de leer XLSXs de `outputs/`. En Streamlit Cloud ese fallback nunca ocurre (no hay XLSXs subidos).

**Acción:** mantenerlo por seguridad, o agregar comentario explicando su rol.

---

## 🟡 Mejoras Recomendadas

| # | Mejora | Esfuerzo |
|---|---|---|
| 9 | Agregar versión de Python en `requirements.txt` o `runtime.txt`: `python-3.11` | 2 min |
| 10 | Crear `.streamlit/secrets.toml.example` como plantilla (sin claves reales) | 5 min |
| 11 | Agregar docstrings a las 13 funciones (especialmente `cargar_y_transformar_datos`) | 30 min |
| 12 | Tests unitarios para `normalizar_columnas()` y `calc_var()` | 2 horas |
| 13 | Documentar en README la relación entre dashboard y backend+frontend | 15 min |

---

## Estructura del Proyecto (Referencia)

```
veritrade-imports -maq/
├── dashboard.py          # App principal Streamlit (2,993 líneas)
├── datos_maquinaria.parquet  # Base de datos de producción (3.4 MB, 20,610 filas)
├── requirements.txt      # Dependencias (OK para Streamlit Cloud)
├── netlify.toml          # ⚠️ Solo aplica al frontend React
├── .env                  # 🔴 NO commitear — contiene API key
├── comprimir.py          # Script manual: outputs/*.xlsx → parquet
├── agregar_withmory.py   # Script manual: actualiza diccionario
├── resumen_fase_a/b.py   # Scripts de QA del pipeline
├── data/                 # Vocabulario controlado (diccionarios)
├── inputs/               # XLSXs crudos de Veritrade (11 MB, privado)
├── outputs/              # XLSXs procesados intermedios (17 MB)
├── scripts/              # Pipeline ETL con LLM (Fase A y B)
├── backend/              # FastAPI — app SEPARADA del dashboard
└── frontend/             # React/TypeScript — app SEPARADA del dashboard
```

---

## Próximos Pasos Prioritarios

1. **Revocar y rotar la clave DeepSeek** (inmediato)
2. **Agregar logging** en `cargar_y_transformar_datos()` línea 480
3. **Crear `.streamlit/config.toml`** con timeout y tema
4. **Validar** que `COL_FOB` y `COL_CIF` no sean `None` antes de usarlos
5. Mover `netlify.toml` al lugar que corresponde o documentarlo
