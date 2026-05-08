"""
ReqPOOL Estimation Manager - Speicherung
=========================================
Speichert Schaetzungen als JSON-Datei, damit eine Historie aller
durchgefuehrten Schaetzungen erhalten bleibt.

Datenformat: Liste von Eintraegen, jeder Eintrag enthaelt
- id (UUID)
- timestamp (ISO-Format)
- titel
- inputs (dict)
- skizze (str)
- ergebnis_zusammenfassung (dict mit den wichtigsten Zahlen)
"""

import json
import os
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from estimator import SchaetzErgebnis


# Pfad zur Speicherdatei (im Projektverzeichnis)
SPEICHER_PFAD = Path(__file__).parent / "data" / "estimations.json"


def _stelle_sicher_dass_datei_existiert() -> None:
    """Erzeugt das data-Verzeichnis und eine leere Datei, falls noetig."""
    SPEICHER_PFAD.parent.mkdir(parents=True, exist_ok=True)
    if not SPEICHER_PFAD.exists():
        SPEICHER_PFAD.write_text("[]", encoding="utf-8")


def _ergebnis_zu_dict(ergebnis: SchaetzErgebnis) -> Dict:
    """Wandelt das Dataclass-Ergebnis rekursiv in ein Dict um.

    Wir speichern nur die wichtigsten Werte, damit die JSON-Datei
    klein bleibt und beim Wiederladen einfach handhabbar ist.
    """
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


def speichere_schaetzung(
    titel: str,
    inputs: Dict[str, int],
    skizze: str,
    ergebnis: SchaetzErgebnis,
) -> str:
    """Speichert eine neue Schaetzung und liefert deren ID zurueck."""
    _stelle_sicher_dass_datei_existiert()

    eintrag = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "titel": titel or "Unbenannte Schaetzung",
        "inputs": inputs,
        "skizze": skizze,
        "ergebnis": _ergebnis_zu_dict(ergebnis),
    }

    with SPEICHER_PFAD.open("r", encoding="utf-8") as f:
        daten: List[Dict] = json.load(f)

    daten.append(eintrag)

    with SPEICHER_PFAD.open("w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=2)

    return eintrag["id"]


def lade_alle_schaetzungen() -> List[Dict]:
    """Liefert alle gespeicherten Schaetzungen, neueste zuerst."""
    _stelle_sicher_dass_datei_existiert()
    with SPEICHER_PFAD.open("r", encoding="utf-8") as f:
        daten: List[Dict] = json.load(f)
    # Neueste zuerst
    return sorted(daten, key=lambda e: e.get("timestamp", ""), reverse=True)


def lade_schaetzung(id_: str) -> Optional[Dict]:
    """Liefert eine einzelne Schaetzung anhand ihrer ID."""
    for e in lade_alle_schaetzungen():
        if e["id"] == id_:
            return e
    return None


def loesche_schaetzung(id_: str) -> bool:
    """Loescht eine Schaetzung anhand ihrer ID."""
    _stelle_sicher_dass_datei_existiert()
    with SPEICHER_PFAD.open("r", encoding="utf-8") as f:
        daten: List[Dict] = json.load(f)

    neue_daten = [e for e in daten if e["id"] != id_]
    if len(neue_daten) == len(daten):
        return False

    with SPEICHER_PFAD.open("w", encoding="utf-8") as f:
        json.dump(neue_daten, f, ensure_ascii=False, indent=2)
    return True
