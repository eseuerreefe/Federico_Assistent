# server/commands.py
# ====================================
# Intenciones "rápidas" (atajos) sin pasar por el LLM
#  - leer noticias (RSS)
#  - temporizador / alarma (solo confirma de momento)
#  - listar amigos (lee amigos.txt)
#  - "cállate" (responde corto)
# ====================================

from __future__ import annotations

import os
import re
import unicodedata
import requests
import xml.etree.ElementTree as ET
from html import unescape
from typing import Tuple

from .config import (
    INTENT_NEWS_KEYWORDS,
    INTENT_TIMER_KEYWORDS,
    INTENT_FRIENDS_KEYWORDS,
    INTENT_SHUTUP_KEYWORDS,
    NEWS_FEEDS,
    debug_enabled,
)

# -----------------------
# Normalización sencilla
# -----------------------
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def _norm(s: str) -> str:
    s = _strip_accents((s or "").lower())
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# -----------------------
# Detectores de intención
# -----------------------
def _has_any(text: str, keywords: list[str]) -> bool:
    n = _norm(text)
    return any(_norm(k) in n for k in keywords)

def is_news(text: str) -> bool:
    return _has_any(text, INTENT_NEWS_KEYWORDS)

def is_timer(text: str) -> bool:
    return _has_any(text, INTENT_TIMER_KEYWORDS)

def is_list_friends(text: str) -> bool:
    return _has_any(text, INTENT_FRIENDS_KEYWORDS)

def is_shutup(text: str) -> bool:
    return _has_any(text, INTENT_SHUTUP_KEYWORDS)

# -----------------------
# Utilidades
# -----------------------
def _rss_items(url: str, limit: int = 5) -> list[str]:
    try:
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        # RSS <channel><item>
        chan = root.find("channel")
        if chan is not None:
            for it in chan.findall("item")[:limit]:
                tit = it.findtext("title") or ""
                tit = unescape(tit).strip()
                if tit:
                    items.append(tit)
        else:
            # Atom <feed><entry>
            for it in root.findall("{http://www.w3.org/2005/Atom}entry")[:limit]:
                tit_el = it.find("{http://www.w3.org/2005/Atom}title")
                tit = (tit_el.text if tit_el is not None else "") or ""
                tit = unescape(tit).strip()
                if tit:
                    items.append(tit)
        return items
    except Exception as e:
        if debug_enabled():
            print("[NEWS] Error leyendo feed:", url, e)
        return []

def get_news(limit_total: int = 6) -> str:
    titulares: list[str] = []
    for f in NEWS_FEEDS:
        if len(titulares) >= limit_total:
            break
        ts = _rss_items(f, limit=limit_total)
        for t in ts:
            if t not in titulares:
                titulares.append(t)
            if len(titulares) >= limit_total:
                break
    if not titulares:
        return "No pude traer titulares ahora mismo."
    return "Titulares: " + "; ".join(titulares[:limit_total]) + "."

# --- Temporizador ---
# Parse sencillo de duraciones en lenguaje natural
def parse_duration_seconds(text: str, default_s: int = 300) -> int:
    t = _strip_accents(text.lower())

    # Formato hh:mm(:ss) o mm:ss
    m = re.search(r"\b(\d+)\s*:\s*(\d+)(?:\s*:\s*(\d+))?\b", t)
    if m:
        if m.group(3):
            h = int(m.group(1)); mi = int(m.group(2)); s = int(m.group(3))
            return max(1, h*3600 + mi*60 + s)
        mi = int(m.group(1)); s = int(m.group(2))
        if mi <= 59 and s <= 59:
            return max(1, mi*60 + s)

    # Números + unidades
    total = 0.0
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(horas?|hrs?|h|minutos?|mins?|m|segundos?|segs?|s)\b", t):
        val = float(num)
        if unit.startswith(("h","hr")):
            total += val * 3600
        elif unit.startswith(("m","min")):
            total += val * 60
        else:
            total += val

    # "en X" sin unidad -> minutos
    if total == 0:
        e = re.search(r"\ben\s+(\d+(?:\.\d+)?)\b", t)
        if e:
            total = float(e.group(1)) * 60

    # número suelto -> minutos
    if total == 0:
        n = re.search(r"\b(\d+(?:\.\d+)?)\b", t)
        if n:
            total = float(n.group(1)) * 60

    if total <= 0:
        total = default_s
    return int(round(total))

def build_timer_reply(user_text: str) -> str:
    secs = parse_duration_seconds(user_text, default_s=300)
    mins = secs // 60
    return f"Temporizador apuntado: {mins} minutos y {secs%60} segundos. Te avisaría al terminar."

# --- Amigos ---
def list_friends() -> str:
    path = os.path.join(os.path.dirname(__file__), "amigos.txt")
    if not os.path.exists(path):
        return "No encontré la lista de amigos."
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        if not lines:
            return "La lista de amigos está vacía."
        return "Tus amigos: " + ", ".join(lines) + "."
    except Exception as e:
        if debug_enabled():
            print("[FRIENDS] Error:", e)
        return "No pude leer la lista de amigos."

# -----------------------
# Enrutador principal
# -----------------------
def handle_intents(user_text: str) -> Tuple[bool, str]:
    """
    Devuelve (handled, reply_text).
    handled=True si se trató como atajo y reply_text contiene la respuesta.
    """
    txt = user_text or ""
    if is_shutup(txt):
        return True, "Vale, hago silencio."

    if is_news(txt):
        return True, get_news()

    if is_timer(txt):
        return True, build_timer_reply(txt)

    if is_list_friends(txt):
        return True, list_friends()

    return False, ""
