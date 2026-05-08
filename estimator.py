"""
ReqPOOL Estimation Manager - Schaetz-Engine
============================================
Dieses Modul berechnet aus den Projekteingaben und der Projektskizze
einen geschaetzten Aufwand in Personentagen (PT).

Vorgehen:
1. Basis-Aufwand = Summe(Anzahl x Aufwand_pro_Einheit) je Kategorie
2. Komplexitaetsfaktor aus Projektskizze (Keyword-Heuristik)
3. Zwischenergebnis = Basis-Aufwand x Komplexitaetsfaktor
4. Aufschlaege (PM, Tests, Doku) werden separat aufgeschlagen
5. Min/Max-Range aus Konfiguration
"""

from dataclasses import dataclass, field
from typing import Dict, List
import re


# ---------------------------------------------------------------------
# Datenklassen fuer typsichere Ergebnisse
# ---------------------------------------------------------------------

@dataclass
class KategorieErgebnis:
    """Ergebnis fuer eine einzelne Eingabe-Kategorie."""
    name: str             # Anzeigename, z.B. "Pages"
    anzahl: int           # vom User eingegebene Anzahl
    pt_pro_einheit: float # Aufwand pro Einheit aus Config
    summe_pt: float       # anzahl * pt_pro_einheit


@dataclass
class KomplexitaetsErgebnis:
    """Ergebnis der Komplexitaetsanalyse."""
    faktor: float                       # finaler Multiplikator (z.B. 1.25)
    gefundene_keywords_plus: List[str]  # Keywords, die erhoeht haben
    gefundene_keywords_minus: List[str] # Keywords, die reduziert haben
    wortanzahl: int                     # Anzahl Woerter in der Skizze
    begruendung: str                    # menschenlesbare Erklaerung


@dataclass
class AufschlagErgebnis:
    """Ein einzelner prozentualer Aufschlag."""
    name: str       # z.B. "Projektmanagement"
    prozent: float  # z.B. 15.0
    pt: float       # berechneter PT-Wert


@dataclass
class SchaetzErgebnis:
    """Vollstaendiges Schaetzungsergebnis."""
    kategorien: List[KategorieErgebnis] = field(default_factory=list)
    basis_pt: float = 0.0                # Summe aller Kategorien (vor Faktor)
    komplexitaet: KomplexitaetsErgebnis = None
    pt_nach_komplexitaet: float = 0.0    # basis_pt * komplexitaetsfaktor
    aufschlaege: List[AufschlagErgebnis] = field(default_factory=list)
    aufschlaege_summe_pt: float = 0.0
    gesamt_pt: float = 0.0               # finale Schaetzung
    gesamt_pt_min: float = 0.0           # untere Range
    gesamt_pt_max: float = 0.0           # obere Range


# ---------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------

# Mapping: interner Schluessel -> Anzeigename (Deutsch)
KATEGORIE_LABELS = {
    "pages": "Pages",
    "use_cases": "Use Cases",
    "business_objects": "Business Objects",
    "interfaces": "Interfaces",
    "batches": "Batches",
    "languages": "Languages",
    "roles": "Roles",
    "users": "Users",
}


def _normalisiere_text(text: str) -> str:
    """Vereinheitlicht den Text fuer das Keyword-Matching.

    - alles in Kleinbuchstaben
    - deutsche Umlaute durch ASCII ersetzen (damit z.B. 'hochverfuegbar'
      auch 'hochverfügbar' findet)
    """
    text = text.lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    text = text.replace("ß", "ss")
    return text


def berechne_komplexitaet(
    skizze: str,
    config: Dict,
) -> KomplexitaetsErgebnis:
    """Berechnet den Komplexitaetsfaktor aus der Projektskizze.

    Heuristik:
    - Start bei basis_faktor (z.B. 1.0)
    - Jedes gefundene "erhoehen"-Keyword addiert seinen Zuschlag
    - Jedes gefundene "reduzieren"-Keyword zieht seinen Wert ab
    - Ergebnis wird auf [faktor_min, faktor_max] begrenzt
    - Sehr lange Skizzen (>500 Woerter) deuten auf Komplexitaet hin
      und geben einen kleinen Bonus.
    """
    konf = config["komplexitaet"]
    faktor = konf["basis_faktor"]

    # Wortzaehler (einfach: alles zwischen Whitespace zaehlt)
    wortanzahl = len(skizze.split()) if skizze else 0

    # Text fuer Keyword-Suche normalisieren
    text_norm = _normalisiere_text(skizze)

    gefundene_plus: List[str] = []
    gefundene_minus: List[str] = []

    # Erhoehende Keywords pruefen
    # Wir nutzen Wortgrenzen (\b), damit "ki" nicht in "kindergarten" matcht.
    for keyword, zuschlag in konf["keywords_erhoehen"].items():
        # Bindestriche im Keyword erlauben Match auf "machine-learning" etc.
        muster = r"\b" + re.escape(keyword) + r"\b"
        if re.search(muster, text_norm):
            faktor += zuschlag
            gefundene_plus.append(keyword)

    # Reduzierende Keywords pruefen
    for keyword, abzug in konf["keywords_reduzieren"].items():
        muster = r"\b" + re.escape(keyword) + r"\b"
        if re.search(muster, text_norm):
            faktor -= abzug
            gefundene_minus.append(keyword)

    # Bonus fuer sehr lange Skizzen (Indiz fuer Komplexitaet)
    laengen_bonus = 0.0
    if wortanzahl > 500:
        laengen_bonus = 0.10
    elif wortanzahl > 300:
        laengen_bonus = 0.05
    faktor += laengen_bonus

    # Auf erlaubten Bereich beschraenken
    faktor = max(konf["faktor_min"], min(konf["faktor_max"], faktor))
    faktor = round(faktor, 2)

    # Begruendungstext zusammenbauen
    teile = [f"Basis: {konf['basis_faktor']:.2f}"]
    if gefundene_plus:
        teile.append(
            "Erhoehende Begriffe: " + ", ".join(sorted(set(gefundene_plus)))
        )
    if gefundene_minus:
        teile.append(
            "Reduzierende Begriffe: " + ", ".join(sorted(set(gefundene_minus)))
        )
    if laengen_bonus > 0:
        teile.append(
            f"Laengen-Bonus (Skizze hat {wortanzahl} Woerter): "
            f"+{laengen_bonus:.2f}"
        )
    if not gefundene_plus and not gefundene_minus and laengen_bonus == 0:
        teile.append("Keine Schluesselbegriffe erkannt - neutraler Faktor.")
    begruendung = " | ".join(teile) + f" -> Faktor: {faktor:.2f}"

    return KomplexitaetsErgebnis(
        faktor=faktor,
        gefundene_keywords_plus=sorted(set(gefundene_plus)),
        gefundene_keywords_minus=sorted(set(gefundene_minus)),
        wortanzahl=wortanzahl,
        begruendung=begruendung,
    )


def berechne_schaetzung(
    inputs: Dict[str, int],
    skizze: str,
    config: Dict,
    aufwand_pro_einheit_override: Dict[str, float] = None,
) -> SchaetzErgebnis:
    """Hauptfunktion: berechnet die komplette Schaetzung.

    Parameter
    ---------
    inputs : dict
        Eingabewerte, z.B. {"pages": 10, "use_cases": 5, ...}
    skizze : str
        Projektskizze als Freitext.
    config : dict
        Geladene config.yaml als Dict.
    aufwand_pro_einheit_override : dict, optional
        Wenn gesetzt, ersetzt die Werte aus config["aufwand_pro_einheit"].
        Damit kann der User in der UI die Werte uebersteuern.
    """
    # Aufwandswerte: entweder aus Override (UI) oder aus Config
    aufwand = (
        aufwand_pro_einheit_override
        if aufwand_pro_einheit_override
        else config["aufwand_pro_einheit"]
    )

    ergebnis = SchaetzErgebnis()

    # 1) Pro Kategorie: Anzahl x PT_pro_Einheit
    for key, label in KATEGORIE_LABELS.items():
        anzahl = int(inputs.get(key, 0) or 0)
        pt_pro_einheit = float(aufwand.get(key, 0))
        summe = round(anzahl * pt_pro_einheit, 2)
        ergebnis.kategorien.append(
            KategorieErgebnis(
                name=label,
                anzahl=anzahl,
                pt_pro_einheit=pt_pro_einheit,
                summe_pt=summe,
            )
        )
        ergebnis.basis_pt += summe

    ergebnis.basis_pt = round(ergebnis.basis_pt, 2)

    # 2) Komplexitaetsfaktor aus Projektskizze
    ergebnis.komplexitaet = berechne_komplexitaet(skizze, config)

    # 3) Zwischenergebnis nach Komplexitaet
    ergebnis.pt_nach_komplexitaet = round(
        ergebnis.basis_pt * ergebnis.komplexitaet.faktor, 2
    )

    # 4) Prozentuale Aufschlaege (PM, Tests, Doku)
    aufschlaege_konf = config["aufschlaege_prozent"]
    aufschlag_labels = {
        "projektmanagement": "Projektmanagement",
        "tests": "Tests",
        "dokumentation": "Dokumentation",
    }
    summe_aufschlaege = 0.0
    for key, label in aufschlag_labels.items():
        prozent = float(aufschlaege_konf.get(key, 0))
        pt_wert = round(ergebnis.pt_nach_komplexitaet * prozent / 100.0, 2)
        ergebnis.aufschlaege.append(
            AufschlagErgebnis(name=label, prozent=prozent, pt=pt_wert)
        )
        summe_aufschlaege += pt_wert

    ergebnis.aufschlaege_summe_pt = round(summe_aufschlaege, 2)

    # 5) Gesamtaufwand und Min/Max-Range
    gesamt = ergebnis.pt_nach_komplexitaet + ergebnis.aufschlaege_summe_pt
    ergebnis.gesamt_pt = round(gesamt, 2)

    range_proz = float(config.get("range_prozent", 20))
    ergebnis.gesamt_pt_min = round(gesamt * (1 - range_proz / 100.0), 2)
    ergebnis.gesamt_pt_max = round(gesamt * (1 + range_proz / 100.0), 2)

    return ergebnis


def erzeuge_scope_beschreibung(
    inputs: Dict[str, int],
    skizze: str,
) -> str:
    """Erzeugt einen lesbaren Scope-Text aus den Inputs.

    Wird sowohl in der App als auch im PDF angezeigt.
    """
    teile = []
    teile.append("Das Projekt umfasst die Entwicklung einer Software mit")
    teile.append(f"folgendem Umfang:")
    teile.append("")

    eintraege = []
    for key, label in KATEGORIE_LABELS.items():
        anzahl = int(inputs.get(key, 0) or 0)
        if anzahl > 0:
            eintraege.append(f"- {anzahl} {label}")

    if eintraege:
        teile.extend(eintraege)
    else:
        teile.append("(Keine Mengenangaben - reine Skizzen-Schaetzung)")

    teile.append("")
    teile.append("Projektbeschreibung:")
    teile.append(skizze.strip() if skizze.strip() else "(keine Beschreibung erfasst)")

    return "\n".join(teile)
