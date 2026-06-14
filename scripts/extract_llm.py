#!/usr/bin/env python3
"""Fase B — Extracción estructurada con LLM (DeepSeek), híbrida y normalizada.
   [ORQUESTADOR OPTIMIZADO: Solo envía a la IA los de confianza MEDIA/BAJA]"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
from pathlib import Path

def load_dotenv(path=".env"):
    p = Path(path)
    if not p.exists(): return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, _, val = line.partition("=")
        os.environ.setdefault(k.strip(), val.strip().strip('"').strip("'"))

import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.llm import report, sampler, validate, vocab as vocab_mod
from scripts.llm.cache import Cache, text_key

INPUTS_DIR, OUTPUTS_DIR = "inputs", "outputs"

def load_v1_data(v1_path):
    """Carga los datos de la Fase A (Estructurado). Ya contiene la descripción."""
    df = pd.read_excel(v1_path, sheet_name="estructurado")
    if "_descripcion" not in df.columns:
        df["_descripcion"] = ""
    df["row_key"] = df.apply(lambda r: f"{r.get('dua_dam','')}|{r.get('vin', r.get('chasis',''))}", axis=1)
    return df

def make_on_batch():
    def on_batch(content, batch, keymap, cache):
        parsed = validate.parse_json_lenient(content)
        items = validate.items_by_index(parsed)
        for i, (_, desc) in enumerate(batch):
            item = items.get(i)
            if item is not None: cache.put(keymap[i], item)
    return on_batch

def process_file(raw_path, v1_path, out_path, v, cache, args):
    print(f"\n=== {raw_path.name} ===")
    
    df = load_v1_data(v1_path)
    use_sample = bool(args.sample) and not args.all
    sub = sampler.sample(df, v, n=args.sample) if use_sample else df
    print(f"Filas totales a evaluar: {len(sub)} (de {len(df)})")
    
    sub = sub.copy()
    
    if "_descripcion" not in sub.columns:
        print("⚠️  No hay columna '_descripcion'. Saltando llamado a LLM.")
        sub["_descripcion"] = ""
    
    sub["_tkey"] = sub["_descripcion"].map(text_key)
    
    pendientes = {}
    for _, r in sub.iterrows():
        k = r["_tkey"]
        confianza = str(r.get("confianza_clasificacion", "")).strip().upper()
        if confianza != "ALTA" and k not in cache and k not in pendientes and isinstance(r.get("_descripcion"), str) and r["_descripcion"]:
            pendientes[k] = r["_descripcion"]
            
    print(f"Textos pendientes para la IA (DeepSeek): {len(pendientes)} (Se omiten los resueltos por reglas)")
    
    if args.dry_run:
        from scripts.llm.client import Stats; stats = Stats()
    else:
        from scripts.llm.client import DeepSeekClient
        model = args.model or None
        client = DeepSeekClient(v, **({"model": model} if model else {}), batch_size=args.batch_size, workers=args.workers)
        on_batch = make_on_batch()
        pend = dict(pendientes)
        for paso in range(3):
            if not pend: break
            client.batch_size = args.batch_size if paso == 0 else 1
            client.run(list(pend.items()), cache, on_batch=on_batch)
            pend = {k: d for k, d in pendientes.items() if k not in cache}
        stats = client.stats
    
    recs = []
    modelo_usado = args.model or os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
    fecha = _dt.date.today().isoformat()
    
    for _, r in sub.iterrows():
        confianza = str(r.get("confianza_clasificacion", "")).strip().upper()
        
        if confianza == "ALTA":
            rec = {
                "marca_raw_llm": None, "marca_norm": r.get("marca"), "marca_in_vocab": True, "marca_sugerencia": None,
                "modelo_raw_llm": None, "modelo_match": r.get("modelo"), "modelo_score": 100.0, "modelo_flag": "reglas_alta",
                "tren_rodaje_norm": r.get("tren_rodaje"), "tren_rodaje_valido": True,
                "combustible_norm": r.get("combustible"), "combustible_valido": True,
                "categoria_maquinaria_norm": r.get("categoria_maquinaria"), "categoria_maquinaria_valido": True,
                "subcategoria_norm": r.get("subcategoria"),
                "fuente": "Reglas (Etapa 3)"
            }
        else:
            raw = cache.get(r["_tkey"])
            rec = validate.normalize_record(raw, v) if raw else validate.empty_record()
            
            # HÍBRIDO: Si Fase A ya encontró modelo, NO lo pierdas
            modelo_fase_a = r.get("modelo")
            if pd.notna(modelo_fase_a) and str(modelo_fase_a).strip() != "":
                rec["modelo_match"] = modelo_fase_a
                rec["modelo_flag"] = "recuperado_fase_a"
                rec["modelo_score"] = 100.0
            
            rec["fuente"] = f"LLM_Hibrido:{modelo_usado}@{fecha}"
            
        recs.append(rec)
    
    norm_df = pd.DataFrame(recs, index=sub.index)
    out = pd.concat([sub.drop(columns=["_tkey"]), norm_df], axis=1)
    
    try:
        stats
    except NameError:
        from scripts.llm.client import Stats
        stats = Stats()
    
    try:
        rep = report.build(out, stats)
        print("\n=== REPORTE ===")
        print(rep.to_string(index=False))
    except Exception:
        rep = pd.DataFrame()
        print("\n⚠️ Nota: No se pudo generar el reporte.")
    
    revisar = out[
        out["modelo_flag"].isin(["low", "nomatch", "alias"]) | 
        (~out["marca_in_vocab"].fillna(False).astype(bool)) | 
        (~out["tren_rodaje_valido"].fillna(True).astype(bool)) | 
        (~out["combustible_valido"].fillna(True).astype(bool)) | 
        (~out["categoria_maquinaria_valido"].fillna(True).astype(bool))
    ]
    
    nuevos = out[(~out["marca_in_vocab"]) & out["marca_norm"].notna()]
    vocab_nuevo = pd.DataFrame()
    if not nuevos.empty:
        vocab_nuevo = (nuevos.groupby("marca_norm").agg(
            unidades=("marca_norm", "size"),
            sugerencia=("marca_sugerencia", "first"),
            modelos=("modelo_raw_llm", lambda s: ", ".join(sorted({str(x) for x in s if pd.notna(x)})[:10]))
        ).sort_values("unidades", ascending=False).reset_index())
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as xw:
        out.to_excel(xw, sheet_name="normalizado_final", index=False)
        if not revisar.empty:
            revisar.to_excel(xw, sheet_name="_revisar_final", index=False)
        if not vocab_nuevo.empty:
            vocab_nuevo.to_excel(xw, sheet_name="_vocab_nuevo", index=False)
        if not rep.empty:
            rep.to_excel(xw, sheet_name="_reporte", index=False)
            
    print(f"✅ Escrito: {out_path} ({len(out)} filas)")
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs-dir", default=INPUTS_DIR)
    ap.add_argument("--outputs-dir", default=OUTPUTS_DIR)
    ap.add_argument("--input")
    ap.add_argument("--vocab", default=None)
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--model", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    
    load_dotenv()
    v = vocab_mod.load(args.vocab) if args.vocab else vocab_mod.load()
    
    srcs = [Path(args.input)] if args.input else sorted(Path(args.inputs_dir).glob("*.xlsx"))
    if not srcs:
        print("❌ No se encontraron archivos en la carpeta de origen.", file=sys.stderr)
        return 1
    
    out_dir = Path(args.outputs_dir)
    cache = Cache()
    ok = 0
    for raw in srcs:
        v1 = out_dir / f"{raw.stem}_estructurado.xlsx"
        if not v1.exists():
            print(f"⚠️ Falta {v1}. Corre primero la Fase A (extract_descripcion.py).", file=sys.stderr)
            continue
        out = out_dir / f"{raw.stem}_normalizado.xlsx"
        if process_file(raw, v1, out, v, cache, args):
            ok += 1
            
    print(f"\n🎉 Listo: {ok}/{len(srcs)} archivos normalizados con éxito.")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())