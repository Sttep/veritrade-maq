"""Carga del vocabulario controlado desde diccionario_maquinaria.xlsx.

Expone marcas canónicas, modelos por marca, los enums cerrados
y tablas de sinónimos para normalizar valores crudos.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# ✅ CORREGIDO: Apunta al diccionario de maquinaria
DEFAULT_PATH = "data/diccionario_maquinaria.xlsx"
EXTRA_PATH = "data/vocab_extra.json"

# Sinónimos -> valor canónico (claves en MAYÚSCULAS, normalizadas con norm_key)
COMBUSTIBLE_SYN = {
    "DIESEL": "Diesel", "PETROLEO": "Diesel", "DIESELPETROLEO": "Diesel",
    "BIODIESEL": "Diesel", "PETROLEODIESEL": "Diesel",
    "GASOLINA": "Gasolina", "NAFTA": "Gasolina",
    "GNV": "GNV", "GASNATURAL": "GNV", "GAS": "GNV",
    "GLP": "GLP",
    "ELECTRICO": "Electrico", "ELECTRIC": "Electrico", "ELECTRICA": "Electrico",
    "BATERIA": "Electrico", "BATTERY": "Electrico", "BEV": "Electrico",
    "HIBRIDO": "Hibrido", "HYBRID": "Hibrido", "HIBRIDA": "Hibrido",
}

# ✅ NUEVO: Sinónimos de maquinaria
TREN_RODAJE_SYN = {
    "ORUGAS": "Orugas", "ORUGA": "Orugas", "CADENAS": "Orugas",
    "CRAWLER": "Orugas", "TRACK": "Orugas", "TRACKED": "Orugas",
    "RUEDAS": "Ruedas", "RUEDA": "Ruedas", "NEUMATICOS": "Ruedas",
    "NEUMATICO": "Ruedas", "WHEEL": "Ruedas", "WHEELED": "Ruedas",
    "LLANTAS": "Ruedas",
}

CATEGORIA_MAQUINARIA_SYN = {
    "EXCAVADORA": "Excavadora", "EXCAVATOR": "Excavadora",
    "CRAWLER EXCAVATOR": "Excavadora", "EXCAVADORA HIDRAULICA": "Excavadora",
    "PALA EXCAVADORA": "Excavadora",
    "CARGADOR FRONTAL": "Cargador Frontal", "CARGADORA FRONTAL": "Cargador Frontal",
    "WHEEL LOADER": "Cargador Frontal", "FRONT LOADER": "Cargador Frontal",
    "PALA CARGADORA": "Cargador Frontal", "LOADER": "Cargador Frontal",
    "CARGADOR DE RUEDAS": "Cargador Frontal",
    "BULLDOZER": "Bulldozer", "TOPADORA": "Bulldozer", "DOZER": "Bulldozer",
    "TRACTOR DE CADENAS": "Bulldozer", "TRACTOR ORUGA": "Bulldozer",
    "TRACTOR SOBRE ORUGA": "Bulldozer",
    "RETROEXCAVADORA": "Retroexcavadora", "BACKHOE": "Retroexcavadora",
    "BACKHOE LOADER": "Retroexcavadora", "RETRO EXCAVADORA": "Retroexcavadora",
    "RETROCARGADORA": "Retroexcavadora",
    "MOTONIVELADORA": "Motoniveladora", "GRADER": "Motoniveladora",
    "NIVELADORA": "Motoniveladora", "MOTO NIVELADORA": "Motoniveladora",
    "COMPACTADOR": "Compactador", "RODILLO": "Compactador",
    "COMPACTADORA": "Compactador", "VIBROCOMPACTADOR": "Compactador",
    "APISONADOR": "Compactador",
    "TELEHANDLER": "Telehandler", "MANIPULADOR TELESCOPICO": "Telehandler",
    "MANITOU": "Telehandler",
    "PALA HIDRAULICA": "Pala Hidraulica", "PALA HIDRAULICA GRANDE": "Pala Hidraulica",
    "PALA MINERA": "Pala Minera", "PALA ELECTRICA": "Pala Minera",
    "PALA DE CABLE": "Pala Minera",
    "EXCLUIDO": "Excluido",
}

# Mantenidos por compatibilidad
CAJA_SYN = {
    "MECANICO": "Mecanico", "MECANICA": "Mecanico", "MANUAL": "Mecanico",
    "AUTOMATICO": "Automatico", "AUTOMATICA": "Automatico",
}
TRACCION_SYN = {
    "4X2": "4x2", "4X4": "4x4", "6X4": "6x4", "6X2": "6x2", "8X4": "8x4",
}
CLASIFICACION_SYN = {"N1": "N1", "N2": "N2", "N3": "N3"}


def norm_key(s: str) -> str:
    """Normaliza para comparar: mayúsculas, sin acentos triviales ni separadores."""
    s = (s or "").strip().upper()
    s = s.replace("Ó", "O").replace("Í", "I").replace("Á", "A").replace("É", "E").replace("Ú", "U")
    return re.sub(r"[\s\-_/().]", "", s)


@dataclass
class Vocab:
    marcas: list[str]
    modelos_por_marca: dict[str, list[str]]
    traccion: list[str]
    combustible: list[str]
    clasificacion: list[str]
    caja: list[str]
    tren_rodaje: list[str] = field(default_factory=list)
    categoria_maquinaria: list[str] = field(default_factory=list)
    _marca_idx: dict[str, str] = field(default_factory=dict)
    _alias_idx: dict[str, str] = field(default_factory=dict)
    _model_alias: dict[str, dict[str, str]] = field(default_factory=dict)

    def marca_canonica(self, raw: str) -> str | None:
        k = norm_key(raw)
        return self._marca_idx.get(k) or self._alias_idx.get(k)

    def modelo_alias(self, marca_canon: str, raw: str) -> str | None:
        return self._model_alias.get(marca_canon, {}).get(norm_key(raw))

    def enum_norm(self, campo: str, raw: str) -> str | None:
        if raw is None:
            return None
        k = norm_key(raw)
        table, allowed = {
            "traccion": (TRACCION_SYN, self.traccion),
            "combustible": (COMBUSTIBLE_SYN, self.combustible),
            "clasificacion": (CLASIFICACION_SYN, self.clasificacion),
            "caja": (CAJA_SYN, self.caja),
            "tren_rodaje": (TREN_RODAJE_SYN, self.tren_rodaje),
            "categoria_maquinaria": (CATEGORIA_MAQUINARIA_SYN, self.categoria_maquinaria),
        }[campo]
        val = table.get(k)
        return val if val in allowed else None


# ✅ CORREGIDO: Carga desde diccionario_maquinaria.xlsx (5 pestañas)
def load(path: str | Path = DEFAULT_PATH) -> Vocab:
    """Carga marcas y modelos desde el diccionario de maquinaria (5 pestañas)."""
    p = Path(path)
    
    marcas_canonicas: list[str] = []
    modelos_dict: dict[str, list[str]] = {}
    
    if p.exists():
        try:
            # 1. Cargar pestaña de marcas
            df_marcas = pd.read_excel(p, sheet_name="marcas")
            marcas_canonicas = (
                df_marcas['marca_estandar']
                .dropna()
                .unique()
                .tolist()
            )
            
            # 2. Cargar pestaña de modelos
            df_modelos = pd.read_excel(p, sheet_name="modelos")
            for marca, group in df_modelos.groupby('marca'):
                marca_str = str(marca).strip()
                modelos_dict[marca_str] = (
                    group['modelo']
                    .dropna()
                    .astype(str)
                    .tolist()
                )
                
        except Exception as e:
            print(f"⚠️  Advertencia al leer {p.name}: {e}")
    
    # Enums válidos para maquinaria
    tro = ["Orugas", "Ruedas", "Orugas/Ruedas (Ambas)"]
    cma = [
        "Excavadora", "Cargador Frontal", "Bulldozer",
        "Retroexcavadora", "Motoniveladora", "Compactador",
        "Telehandler", "Pala Hidraulica", "Pala Minera",
    ]
    
    v = Vocab(
        marcas=marcas_canonicas,
        modelos_por_marca=modelos_dict,
        traccion=["4x2", "4x4", "6x2", "6x4", "8x4"],  # Compatibilidad
        combustible=["Diesel", "Gasolina", "GNV", "GLP", "Electrico", "Hibrido"],
        clasificacion=["N1", "N2", "N3"],              # Compatibilidad
        caja=["Automatico", "Mecanico", "AMT"],        # Compatibilidad
        tren_rodaje=sorted(tro),
        categoria_maquinaria=sorted(cma),
    )
    
    v._marca_idx = {norm_key(m): m for m in marcas_canonicas}
    _merge_extra(v, EXTRA_PATH)
    return v


def _merge_extra(v: Vocab, path: str | Path) -> None:
    """Fusiona data/vocab_extra.json: marcas nuevas + alias hacia canónicas."""
    p = Path(path)
    if not p.exists():
        return
    extra = json.loads(p.read_text(encoding="utf-8"))
    
    for marca, modelos in (extra.get("marcas") or {}).items():
        marca = marca.strip()
        if norm_key(marca) not in v._marca_idx:
            v.marcas.append(marca)
            v._marca_idx[norm_key(marca)] = marca
        v.modelos_por_marca.setdefault(marca, [])
        for mod in modelos or []:
            if mod not in v.modelos_por_marca[marca]:
                v.modelos_por_marca[marca].append(str(mod).strip())
    
    for alias, canon in (extra.get("aliases") or {}).items():
        canon = canon.strip()
        if norm_key(canon) not in v._marca_idx:
            raise ValueError(f"alias '{alias}' apunta a marca inexistente '{canon}'")
        v._alias_idx[norm_key(alias)] = v._marca_idx[norm_key(canon)]
    
    for marca, mapping in (extra.get("model_aliases") or {}).items():
        canon_marca = v._marca_idx.get(norm_key(marca))
        if not canon_marca:
            raise ValueError(f"model_aliases para marca inexistente '{marca}'")
        dst = v._model_alias.setdefault(canon_marca, {})
        for raw, modelo in mapping.items():
            dst[norm_key(raw)] = modelo


if __name__ == "__main__":
    v = load()
    print("marcas:", len(v.marcas))
    print("modelos:", sum(len(x) for x in v.modelos_por_marca.values()))
    print("tren_rodaje:", v.tren_rodaje)
    print("categoria_maquinaria:", v.categoria_maquinaria)