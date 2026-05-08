"""
ReqPOOL Estimation Manager - Speicherung
=========================================
Speichert Schaetzungen entweder in einer JSON-Datei (lokal) oder
im Streamlit Session-State (Cloud / Demo-Modus ohne Schreibzugriff).

Wir versuchen zuerst, in 'data/estimations.json' zu schreiben.
Wenn das fehlschlaegt (z.B. read-only Filesystem auf Streamlit Cloud),
fallen wir automatisch auf einen In-Memory-Speicher zurueck, der
nur fuer die Dauer der Browser-Session gilt.
"""

import json
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

from estimator import SchaetzErgebnis


# Pfad zur Speicherdatei (im Projektverzeichnis)
SPEICHER_PFAD = Path(__file__).parent / "data" / "estimations.json"

# Session-State-Key fuer den In-Memory-Fallback
_SESSION_KEY = "_reqpool_estimations_memory"


# ---------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------

def _datei_speicher_verfuegbar() -> bool:
    """Prueft, ob wir die JSON-Datei schreiben koennen.

    Versucht das Verzeichnis anzulegen und eine leere Datei zu schreiben.
    Schlaegt das fehl (Permission, read-only FS), nutzen wir Session-State.
    """
    try:
        SPEICHER_PFAD.parent.mkdir(parents=True, exist_ok=True)
        if not SPEICHER_PFAD.exists():
            SPEICHER_PFAD.write_text("[]", encoding="utf-8")
        # Test-Schreibvorgang
        with SPEICHER_PFAD.open("a", encoding="utf-8") as f:
            pass
        return True
    except (OSError, PermissionError):
        return False


def _ergebnis_zu_dict(ergebnis: SchaetzErgebnis) -> Dict:
    """Wandelt das Dataclass-Ergebnis rekursiv in ein Dict um."""
    return {
        "basis_pt": ergebnis.basis_pt,
        "komplexitaet_faktor": ergebnis.komplexitaet.faktor,
        "komplexitaet_keywords_plus": ergebnis.komplexitaet.gefundene_keywords_plus,
        "komplexitaet_keywords_minus": ergebnis.komplexitaet.gefundene_keywords_minus,
        "pt_nach_komplexitaet": ergebnis.pt_nach_komplexitaet,
        "aufschlaege_summe_pt": ergebnis.aufschlaege_summe_pt,
        "gesamt_pt": ergebnis.gesamt_pt,
        "gesamt_pt_min": ergebnis.gesamt_pt_min,
        "gesamt_pt_max": ergebnis.gesamt_pt_max,
        "kategorien": [asdict(k) for k in ergebnis.kategorien],
        "aufschlaege": [asdict(a) for a in ergebnis.aufschlaege],
    }


def _lade_alle_aus_datei() -> List[Dict]:
    if not SPEICHER_PFAD.exists():
        return []
    with SPEICHER_PFAD.open("r", encoding="utf-8") as f:
        return json.load(f)


def _speichere_alle_in_datei(daten: List[Dict]) -> None:
    with SPEICHER_PFAD.open("w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=2)


def _lade_alle_aus_session() -> List[Dict]:
    return st.session_state.get(_SESSION_KEY, [])


def _speichere_alle_in_session(daten: List[Dict]) -> None:
    st.session_state[_SESSION_KEY] = daten


# ---------------------------------------------------------------------
# Oeffentliche API
# ---------------------------------------------------------------------

def ist_persistent() -> bool:
    """True, wenn die Schaetzungen dauerhaft gespeichert werden.

    Wird von der UI verwendet, um einen Hinweis-Banner anzuzeigen,
    falls wir nur im Session-State arbeiten.
    """
    return _datei_speicher_verfuegbar()


def speichere_schaetzung(
    titel: str,
    inputs: Dict[str, int],
    skizze: str,
    ergebnis: SchaetzErgebnis,
) -> str:
    """Speichert eine neue Schaetzung und liefert deren ID zurueck."""
    eintrag = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "titel": titel or "Unbenannte Schaetzung",
        "inputs": inputs,
        "skizze": skizze,
        "ergebnis": _ergebnis_zu_dict(ergebnis),
    }

    if _datei_speicher_verfuegbar():
        daten = _lade_alle_aus_datei()
        daten.append(eintrag)
        _speichere_alle_in_datei(daten)
    else:
        daten = _lade_alle_aus_session()
        daten.append(eintrag)
        _speichere_alle_in_session(daten)

    return eintrag["id"]


def lade_alle_schaetzungen() -> List[Dict]:
    """Liefert alle gespeicherten Schaetzungen, neueste zuerst."""
    if _datei_speicher_verfuegbar():
        daten = _lade_alle_aus_datei()
    else:
        daten = _lade_alle_aus_session()
    return sorted(daten, key=lambda e: e.get("timestamp", ""), reverse=True)


def lade_schaetzung(id_: str) -> Optional[Dict]:
    """Liefert eine einzelne Schaetzung anhand ihrer ID."""
    for e in lade_alle_schaetzungen():
        if e["id"] == id_:
            return e
    return None


def loesche_schaetzung(id_: str) -> bool:
    """Loescht eine Schaetzung anhand ihrer ID."""
    if _datei_speicher_verfuegbar():
        daten = _lade_alle_aus_datei()
        neue = [e for e in daten if e["id"] != id_]
        if len(neue) == len(daten):
            return False
        _speichere_alle_in_datei(neue)
    else:
        daten = _lade_alle_aus_session()
        neue = [e for e in daten if e["id"] != id_]
        if len(neue) == len(daten):
            return False
        _speichere_alle_in_session(neue)
    return True
