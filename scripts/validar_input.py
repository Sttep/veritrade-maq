#!/usr/bin/env python3
"""
Validador de archivos de entrada de Veritrade antes de correr el pipeline.
Uso: python scripts/validar_input.py --input inputs/Veritrade_ARCHIVO.xlsx
     python scripts/validar_input.py   (valida todos los archivos en inputs/)
"""
import sys
import argparse
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

HEADER_ROW = 6

COLUMNAS_REQUERIDAS = {
    "Fecha":                  "fecha_dua",
    "Importador":             "importador",
    "U$ FOB Tot":             "fob_usd",
    "U$ CIF Tot":             "cif_usd",
    "Descripcion Comercial":  "_descripcion",
    "Estado":                 "estado",
    "Kg Bruto":               "kg_bruto",
    "DUA / DAM":              "dua_dam",
}

COLUMNAS_OPCIONALES = [
    "Partida Aduanera", "Aduana", "Qty 1", "Und 1",
    "U$ CFR Tot", "Pais de Origen", "Ad Valorem",
]

# Maquinaria esperada en el dataset
CATEGORIAS_ESPERADAS = [
    "EXCAVADORA", "RETROEXCAVADORA", "CARGADOR FRONTAL",
    "COMPACTADOR", "MINICARGADOR FRONTAL", "MOTONIVELADORA", "BULLDOZER",
]

# Umbrales de alerta
FOB_MIN_MAQUINARIA   = 5_000
FOB_MAX_RAZONABLE    = 8_000_000
REGISTROS_MES_MINIMO = 80    # por debajo de esto es sospechoso
REGISTROS_MES_ALERTA = 120   # zona gris


def separador(titulo=""):
    ancho = 60
    if titulo:
        print(f"\n{'─' * 3} {titulo} {'─' * (ancho - len(titulo) - 5)}")
    else:
        print("─" * ancho)


def validar_archivo(ruta: Path) -> dict:
    errores   = []
    alertas   = []
    info      = []

    print(f"\n{'=' * 60}")
    print(f"  VALIDANDO: {ruta.name}")
    print(f"{'=' * 60}")

    # ── 1. Existe y es legible ─────────────────────────────────
    separador("1. Archivo")
    if not ruta.exists():
        errores.append(f"No se encontró el archivo: {ruta}")
        print(f"  ❌ No existe: {ruta}")
        return {"errores": errores, "alertas": alertas, "info": info}

    tam_mb = ruta.stat().st_size / 1_048_576
    print(f"  ✅ Existe — {tam_mb:.2f} MB")
    if tam_mb < 0.05:
        alertas.append("Archivo muy pequeño (< 50 KB) — puede estar vacío o incompleto")
        print(f"  ⚠️  Muy pequeño ({tam_mb*1024:.0f} KB)")

    # ── 2. Carga con la cabecera correcta ─────────────────────
    separador("2. Estructura")
    try:
        df = pd.read_excel(ruta, header=HEADER_ROW - 1)
    except Exception as e:
        errores.append(f"No se pudo leer el Excel: {e}")
        print(f"  ❌ Error al abrir: {e}")
        return {"errores": errores, "alertas": alertas, "info": info}

    if df.empty:
        errores.append("El archivo está vacío después de la cabecera")
        print("  ❌ Sin datos")
        return {"errores": errores, "alertas": alertas, "info": info}

    print(f"  ✅ {len(df):,} filas cargadas, {len(df.columns)} columnas")

    # ── 3. Columnas requeridas ─────────────────────────────────
    separador("3. Columnas requeridas")
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        for c in faltantes:
            errores.append(f"Columna requerida faltante: '{c}'")
            print(f"  ❌ Falta: '{c}'")
    else:
        print(f"  ✅ Todas las columnas requeridas presentes")

    opcionales_faltantes = [c for c in COLUMNAS_OPCIONALES if c not in df.columns]
    if opcionales_faltantes:
        alertas.append(f"Columnas opcionales faltantes: {opcionales_faltantes}")
        print(f"  ⚠️  Opcionales faltantes: {opcionales_faltantes}")

    if faltantes:
        return {"errores": errores, "alertas": alertas, "info": info}

    # ── 4. Fechas ──────────────────────────────────────────────
    separador("4. Rango de fechas")
    df["_fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    nulos_fecha = df["_fecha"].isna().sum()
    if nulos_fecha > 0:
        alertas.append(f"{nulos_fecha} fechas no parseables")
        print(f"  ⚠️  {nulos_fecha} fechas inválidas")

    fecha_min = df["_fecha"].min()
    fecha_max = df["_fecha"].max()
    print(f"  📅 Desde: {fecha_min.date() if pd.notna(fecha_min) else 'N/A'}")
    print(f"  📅 Hasta: {fecha_max.date() if pd.notna(fecha_max) else 'N/A'}")

    if pd.notna(fecha_min) and pd.notna(fecha_max):
        meses = df.groupby([df["_fecha"].dt.year, df["_fecha"].dt.month]).size()
        for (año, mes), n in meses.items():
            estado = "✅" if n >= REGISTROS_MES_ALERTA else ("⚠️ " if n >= REGISTROS_MES_MINIMO else "❌")
            print(f"  {estado} {año}-{mes:02d}: {n} registros", end="")
            if n < REGISTROS_MES_MINIMO:
                alertas.append(f"{año}-{mes:02d} tiene solo {n} registros (mínimo esperado: {REGISTROS_MES_MINIMO})")
                print("  ← MUY POCOS", end="")
            elif n < REGISTROS_MES_ALERTA:
                print("  ← revisar", end="")
            print()
        info.append(f"Período: {fecha_min.date()} → {fecha_max.date()}, {len(df):,} registros en {len(meses)} mes(es)")

    # ── 5. Estado (nuevo vs usado) ─────────────────────────────
    separador("5. Estado de la mercancía")
    estados = df["Estado"].value_counts()
    total = len(df)
    nuevos_kw = ["NUEVO", "NUEVA", "NEW", "0 KM", "SIN USO"]
    nuevos = df["Estado"].apply(lambda x: any(k in str(x).upper() for k in nuevos_kw) if pd.notna(x) else False).sum()
    pct_nuevos = nuevos / total * 100 if total > 0 else 0
    print(f"  {'✅' if pct_nuevos > 50 else '⚠️ '} Nuevos: {nuevos:,} ({pct_nuevos:.0f}%) de {total:,} total")
    if pct_nuevos < 50:
        alertas.append(f"Solo {pct_nuevos:.0f}% de registros son NUEVO — revisar filtros en Veritrade")
    for estado, n in estados.head(5).items():
        print(f"       {str(estado)[:40]}: {n}")

    # ── 6. FOB ────────────────────────────────────────────────
    separador("6. Valores FOB")
    fob = pd.to_numeric(df["U$ FOB Tot"], errors="coerce")
    nulos_fob = fob.isna().sum()
    if nulos_fob > 0:
        alertas.append(f"{nulos_fob} registros sin FOB")
        print(f"  ⚠️  {nulos_fob} sin valor FOB")

    fob_valido = fob.dropna()
    if len(fob_valido) > 0:
        partes = ((fob_valido > 0) & (fob_valido < FOB_MIN_MAQUINARIA)).sum()
        outliers_altos = (fob_valido > FOB_MAX_RAZONABLE).sum()
        print(f"  📊 Mínimo:  ${fob_valido[fob_valido > 0].min():>12,.2f}")
        print(f"  📊 Promedio: ${fob_valido[fob_valido > 0].mean():>11,.0f}")
        print(f"  📊 Máximo:  ${fob_valido.max():>12,.0f}")
        if partes > 0:
            alertas.append(f"{partes} registros con FOB < ${FOB_MIN_MAQUINARIA:,} (probables partes/repuestos — serán filtrados)")
            print(f"  ⚠️  {partes} con FOB < ${FOB_MIN_MAQUINARIA:,} (se filtrarán como partes)")
        if outliers_altos > 0:
            alertas.append(f"{outliers_altos} registros con FOB > ${FOB_MAX_RAZONABLE:,} — verificar")
            print(f"  ⚠️  {outliers_altos} con FOB > ${FOB_MAX_RAZONABLE:,} — verificar")

    # ── 7. Descripción comercial ───────────────────────────────
    separador("7. Descripción Comercial")
    sin_desc = df["Descripcion Comercial"].isna().sum()
    pct_sin_desc = sin_desc / total * 100 if total > 0 else 0
    print(f"  {'✅' if pct_sin_desc < 5 else '⚠️ '} Sin descripción: {sin_desc} ({pct_sin_desc:.1f}%)")
    if pct_sin_desc > 10:
        errores.append(f"{pct_sin_desc:.0f}% de registros sin descripción — el LLM no podrá procesar estos")
    elif pct_sin_desc > 5:
        alertas.append(f"{pct_sin_desc:.1f}% de registros sin descripción")

    desc_muestra = df["Descripcion Comercial"].dropna().head(3)
    print("  Muestra:")
    for i, d in enumerate(desc_muestra, 1):
        print(f"    {i}. {str(d)[:100]}{'...' if len(str(d)) > 100 else ''}")

    # ── 8. Duplicados ─────────────────────────────────────────
    separador("8. Duplicados")
    dups = df.duplicated(subset=["DUA / DAM"], keep=False).sum() if "DUA / DAM" in df.columns else 0
    if dups > 0:
        alertas.append(f"{dups} filas con DUA duplicado — posibles registros repetidos")
        print(f"  ⚠️  {dups} filas con DUA duplicado")
    else:
        print(f"  ✅ Sin DUAs duplicados")

    return {"errores": errores, "alertas": alertas, "info": info}


def resumen_final(resultados: dict[str, dict]):
    separador()
    print("\n" + "=" * 60)
    print("  RESUMEN FINAL")
    print("=" * 60)

    todo_ok = True
    for archivo, r in resultados.items():
        errores  = r["errores"]
        alertas  = r["alertas"]
        info     = r["info"]

        if errores:
            estado = "❌ NO PROCESAR"
            todo_ok = False
        elif alertas:
            estado = "⚠️  REVISAR ANTES"
        else:
            estado = "✅ LISTO"

        print(f"\n  {estado} — {archivo}")
        for i in info:
            print(f"    ℹ️  {i}")
        for e in errores:
            print(f"    ❌ {e}")
        for a in alertas:
            print(f"    ⚠️  {a}")

    print()
    if todo_ok and all(not r["errores"] for r in resultados.values()):
        print("  → Podés continuar con: python scripts/extract_descripcion.py")
    else:
        print("  → Resolvé los errores antes de continuar con el pipeline.")
    print("=" * 60)


def main():
    ap = argparse.ArgumentParser(description="Valida archivos de Veritrade antes del pipeline")
    ap.add_argument("--input", help="Archivo específico a validar")
    ap.add_argument("--inputs-dir", default="inputs", help="Carpeta de inputs (default: inputs/)")
    args = ap.parse_args()

    if args.input:
        archivos = [Path(args.input)]
    else:
        archivos = sorted(Path(args.inputs_dir).glob("*.xlsx"))
        if not archivos:
            print(f"❌ No se encontraron .xlsx en '{args.inputs_dir}/'")
            return 1

    resultados = {}
    for archivo in archivos:
        r = validar_archivo(archivo)
        resultados[archivo.name] = r

    resumen_final(resultados)

    hay_errores = any(r["errores"] for r in resultados.values())
    return 1 if hay_errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
