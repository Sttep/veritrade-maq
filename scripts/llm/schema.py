"""Construcción del prompt para DeepSeek (JSON mode) y forma del JSON esperado.

El prefijo (system) es ESTABLE entre requests (marcas + enums + few-shot) para
maximizar el prompt-cache de DeepSeek; solo varían los items del mensaje user.
"""
from __future__ import annotations

import json

from .vocab import Vocab

# ✅ CORREGIDO: Las variables que necesitamos que extraiga DeepSeek
OUTPUT_KEYS = ["marca", "modelo", "tren_rodaje", "combustible", "categoria_maquinaria", "subcategoria"]


def build_system_prompt(v: Vocab) -> str:
    # Extraemos las listas del diccionario (cargadas vía vocab.py)
    marcas = ", ".join(v.marcas)
    categorias = ", ".join(v.categoria_maquinaria)
    rodaje = ", ".join(v.tren_rodaje)
    combustibles = ", ".join(v.combustible)
    
    return f"""Eres un experto normalizador de descripciones aduaneras de maquinaria pesada y equipos de construcción.
Recibes un JSON con una lista `items`, cada uno con `i` (índice) y `desc` (texto de la descripción comercial).
Para CADA item, extrae y normaliza EXACTAMENTE estos 6 campos y responde SOLO con JSON válido.

Campos y valores permitidos:
- marca: la marca de la maquinaria. Esta lista de referencia tiene la forma canónica preferida:
  Lista de referencia: {marcas}
  IMPORTANTE: la lista NO es exhaustiva. Si la marca del texto NO está en la lista, devuélvela igual tal como aparece en el texto. Solo usa null si realmente no hay marca identificable. NUNCA inventes una marca que no esté en el texto.
- modelo: el código/modelo de la máquina tal como aparece en el texto (p.ej. "320D", "WA380", "PC200", "L150H"). null si no se puede determinar. Evita confundir años (ej. 2022) con modelos alfanuméricos.
- tren_rodaje: una de [{rodaje}]. Deduce esto por el contexto del texto si no es explícito (ej. las excavadoras suelen ser de orugas). null si no aplica.
- combustible: una de [{combustibles}]. null si no aparece.
- categoria_maquinaria: una de [{categorias}]. Usa el contexto del texto para clasificar. Si es un repuesto, accesorio o juguete, usa 'Excluido'. null si no se puede determinar.
- subcategoria: una de [MINI, ESTANDAR]. Si el texto dice "MINI", "SKID STEER" o "COMPACTO", usa MINI. De lo contrario, asume ESTANDAR. null si no aplica.

Reglas:
- Responde con un objeto JSON: {{"items": [{{"i": <int>, "marca": ..., "modelo": ..., "tren_rodaje": ..., "combustible": ..., "categoria_maquinaria": ..., "subcategoria": ...}}, ...]}}
- Devuelve un item por cada `i` recibido, con el mismo `i`.
- Usa null (no cadena vacía) cuando un campo no se pueda determinar.
- No agregues texto fuera del JSON.

Ejemplo de entrada:
{{"items": [{{"i": 0, "desc": "EXCAVADORA HIDRAULICA SOBRE ORUGAS MARCA CATERPILLAR MODELO 320D AÑO 2023 CO:DIESEL"}}]}}
Ejemplo de salida:
{{"items": [{{"i": 0, "marca": "CATERPILLAR", "modelo": "320D", "tren_rodaje": "Orugas", "combustible": "Diesel", "categoria_maquinaria": "Excavadora", "subcategoria": "ESTANDAR"}}]}}"""


def build_user_message(batch: list[tuple[int, str]]) -> str:
    """batch: lista de (i, desc). Devuelve el JSON del mensaje user."""
    items = [{"i": i, "desc": desc} for i, desc in batch]
    return json.dumps({"items": items}, ensure_ascii=False)