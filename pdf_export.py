"""
ReqPOOL Estimation Manager - PDF-Export
========================================
Erstellt aus einem SchaetzErgebnis ein professionell formatiertes PDF.
Verwendet reportlab (Platypus) fuer flexibles Layout.

Aufbau des PDFs:
  1. Kopfzeile mit "ReqPOOL"-Schriftzug (Platzhalter-Logo) und Datum
  2. Titel + Erstellungsdatum
  3. Eingabewerte als Tabelle
  4. Projektskizze als Fliesstext
  5. Komplexitaetsfaktor mit Begruendung
  6. Schaetz-Aufschluesselung als Tabelle
  7. Aufschlaege (PM/Tests/Doku)
  8. Gesamt-Schaetzung mit Min/Max-Range (hervorgehoben)
  9. Scope-Beschreibung
"""

from datetime import datetime
from io import BytesIO
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)

from estimator import SchaetzErgebnis, KATEGORIE_LABELS


# ---------------------------------------------------------------------
# Hilfsfunktionen fuer Kopf- und Fusszeile
# ---------------------------------------------------------------------

def _hex_to_color(hex_str: str) -> colors.Color:
    """Wandelt einen Hex-Farbwert wie '#1a2b4a' in ein reportlab-Color um."""
    hex_str = hex_str.lstrip("#")
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return colors.Color(r, g, b)


def _make_header_footer(branding: Dict):
    """Erstellt die Funktion fuer Kopf- und Fusszeile auf jeder Seite.

    Da reportlab die Header-Funktion bei jeder Seite separat aufruft,
    geben wir hier eine Closure zurueck, die das Branding "kennt".
    """
    primaer = _hex_to_color(branding["primaer_farbe"])
    akzent = _hex_to_color(branding["akzent_farbe"])

    def _zeichne(canvas, doc):
        canvas.saveState()
        seitenbreite, seitenhoehe = A4

        # ----- KOPFZEILE -----
        # Farbiger Balken oben
        canvas.setFillColor(primaer)
        canvas.rect(0, seitenhoehe - 2.0 * cm, seitenbreite, 2.0 * cm,
                    stroke=0, fill=1)

        # Logo-Platzhalter (Schriftzug "ReqPOOL")
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 18)
        canvas.drawString(2 * cm, seitenhoehe - 1.3 * cm, branding["firma"])

        # Untertitel "Estimation Manager"
        canvas.setFont("Helvetica", 10)
        canvas.drawString(2 * cm, seitenhoehe - 1.75 * cm, branding["produkt"])

        # Datum oben rechts
        canvas.setFont("Helvetica", 9)
        datum_str = datetime.now().strftime("%d.%m.%Y")
        canvas.drawRightString(seitenbreite - 2 * cm,
                               seitenhoehe - 1.3 * cm, datum_str)

        # ----- FUSSZEILE -----
        canvas.setStrokeColor(akzent)
        canvas.setLineWidth(0.5)
        canvas.line(2 * cm, 1.5 * cm, seitenbreite - 2 * cm, 1.5 * cm)

        canvas.setFillColor(colors.grey)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(2 * cm, 1.0 * cm,
                          f"{branding['firma']} {branding['produkt']}")
        canvas.drawRightString(seitenbreite - 2 * cm, 1.0 * cm,
                               f"Seite {doc.page}")

        canvas.restoreState()

    return _zeichne


# ---------------------------------------------------------------------
# Haupt-Funktion: PDF erzeugen
# ---------------------------------------------------------------------

def erzeuge_pdf(
    ergebnis: SchaetzErgebnis,
    inputs: Dict[str, int],
    skizze: str,
    scope_text: str,
    config: Dict,
    projekt_titel: str = "Projekt-Aufwandsschaetzung",
) -> bytes:
    """Erzeugt das PDF und liefert die Bytes zurueck.

    Diese Bytes koennen direkt in Streamlit als Download angeboten werden.
    """
    branding = config["branding"]
    primaer = _hex_to_color(branding["primaer_farbe"])
    akzent = _hex_to_color(branding["akzent_farbe"])
    hintergrund = _hex_to_color(branding["hintergrund_farbe"])

    # In-Memory-Buffer fuer das PDF
    puffer = BytesIO()

    doc = SimpleDocTemplate(
        puffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=3 * cm,    # Platz fuer Kopfzeile
        bottomMargin=2 * cm, # Platz fuer Fusszeile
        title=projekt_titel,
        author=branding["firma"],
    )

    # ----- Eigene Stile definieren -----
    styles = getSampleStyleSheet()

    style_titel = ParagraphStyle(
        "CustomTitel",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=primaer,
        spaceAfter=6,
        alignment=TA_LEFT,
    )
    style_h2 = ParagraphStyle(
        "CustomH2",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=primaer,
        spaceBefore=14,
        spaceAfter=6,
    )
    style_normal = ParagraphStyle(
        "CustomNormal",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#1f2937"),
        leading=14,
    )
    style_klein = ParagraphStyle(
        "CustomKlein",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
    )
    style_gesamt = ParagraphStyle(
        "CustomGesamt",
        parent=styles["Normal"],
        fontSize=14,
        textColor=akzent,
        leading=18,
    )

    # ----- Inhaltsliste (Story) aufbauen -----
    story = []

    # Titel + Datum
    story.append(Paragraph(projekt_titel, style_titel))
    story.append(Paragraph(
        f"Erstellt am {datetime.now().strftime('%d.%m.%Y, %H:%M Uhr')}",
        style_klein,
    ))
    story.append(Spacer(1, 6 * mm))

    # ----- 1) Eingabewerte als Tabelle -----
    story.append(Paragraph("1. Eingabewerte", style_h2))

    daten = [["Kategorie", "Anzahl", "PT/Einheit", "Summe (PT)"]]
    for kat in ergebnis.kategorien:
        daten.append([
            kat.name,
            str(kat.anzahl),
            f"{kat.pt_pro_einheit:.2f}",
            f"{kat.summe_pt:.2f}",
        ])
    daten.append([
        "Basis-Aufwand", "", "",
        f"{ergebnis.basis_pt:.2f}",
    ])

    tabelle = Table(daten, colWidths=[6 * cm, 3 * cm, 3 * cm, 4 * cm])
    tabelle.setStyle(TableStyle([
        # Kopfzeile
        ("BACKGROUND", (0, 0), (-1, 0), primaer),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        # Datenzeilen
        ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        # Summenzeile hervorheben
        ("BACKGROUND", (0, -1), (-1, -1), hintergrund),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, primaer),
        # Allgemein
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))
    story.append(tabelle)

    # ----- 2) Komplexitaetsfaktor -----
    story.append(Paragraph("2. Komplexitaetsfaktor", style_h2))
    kpx = ergebnis.komplexitaet
    story.append(Paragraph(
        f"<b>Faktor: {kpx.faktor:.2f}</b> "
        f"(angewendet auf den Basis-Aufwand)",
        style_normal,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        f"<i>Begruendung:</i> {kpx.begruendung}",
        style_normal,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        f"<b>Aufwand nach Komplexitaet:</b> "
        f"{ergebnis.pt_nach_komplexitaet:.2f} PT",
        style_normal,
    ))

    # ----- 3) Aufschlaege -----
    story.append(Paragraph("3. Aufschlaege", style_h2))
    daten_a = [["Position", "Prozent", "PT"]]
    for a in ergebnis.aufschlaege:
        daten_a.append([a.name, f"{a.prozent:.0f}%", f"{a.pt:.2f}"])
    daten_a.append([
        "Summe Aufschlaege", "",
        f"{ergebnis.aufschlaege_summe_pt:.2f}",
    ])

    tabelle_a = Table(daten_a, colWidths=[8 * cm, 4 * cm, 4 * cm])
    tabelle_a.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primaer),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("BACKGROUND", (0, -1), (-1, -1), hintergrund),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, primaer),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))
    story.append(tabelle_a)

    # ----- 4) Gesamt-Schaetzung (hervorgehoben) -----
    story.append(Paragraph("4. Gesamt-Schaetzung", style_h2))

    gesamt_daten = [
        ["Erwartet (PT)", "Min (PT)", "Max (PT)"],
        [
            f"{ergebnis.gesamt_pt:.1f}",
            f"{ergebnis.gesamt_pt_min:.1f}",
            f"{ergebnis.gesamt_pt_max:.1f}",
        ],
    ]
    gesamt_tabelle = Table(gesamt_daten, colWidths=[5.6 * cm] * 3)
    gesamt_tabelle.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), akzent),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BACKGROUND", (0, 1), (-1, 1), hintergrund),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 18),
        ("TEXTCOLOR", (0, 1), (-1, 1), primaer),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, primaer),
    ]))
    story.append(gesamt_tabelle)
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        f"<i>Range basiert auf +/- {config.get('range_prozent', 20)}% "
        f"um den erwarteten Wert.</i>",
        style_klein,
    ))

    # ----- 5) Projektskizze -----
    story.append(PageBreak())
    story.append(Paragraph("5. Projektskizze", style_h2))
    skizze_text = skizze.strip() if skizze.strip() else "(keine Beschreibung erfasst)"
    # Zeilenumbrueche fuer reportlab als <br/> umsetzen
    skizze_html = skizze_text.replace("\n", "<br/>")
    story.append(Paragraph(skizze_html, style_normal))

    # ----- 6) Scope-Beschreibung -----
    story.append(Paragraph("6. Scope-Beschreibung", style_h2))
    scope_html = scope_text.replace("\n", "<br/>")
    story.append(Paragraph(scope_html, style_normal))

    # ----- PDF bauen -----
    header_footer = _make_header_footer(branding)
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)

    pdf_bytes = puffer.getvalue()
    puffer.close()
    return pdf_bytes
