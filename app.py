"""
ReqPOOL Estimation Manager - Streamlit-App
===========================================
Webbasierte Oberflaeche fuer die Aufwandsschaetzung von Software-Projekten.

Struktur:
- Sidebar: Schaetzwerte (PT pro Einheit) editierbar + Historie
- Tab 1 "Neue Schaetzung": Eingabeformular + Ergebnis + PDF-Download
- Tab 2 "Historie": gespeicherte Schaetzungen anzeigen / loeschen

Start:
    streamlit run app.py
"""

from datetime import datetime
from pathlib import Path

import streamlit as st
import yaml

from estimator import (
    KATEGORIE_LABELS,
    berechne_schaetzung,
    erzeuge_scope_beschreibung,
)
from pdf_export import erzeuge_pdf
from storage import (
    ist_persistent,
    lade_alle_schaetzungen,
    loesche_schaetzung,
    speichere_schaetzung,
)


# ---------------------------------------------------------------------
# Konfiguration laden
# ---------------------------------------------------------------------
CONFIG_PFAD = Path(__file__).parent / "config.yaml"


@st.cache_data
def lade_config() -> dict:
    """Laedt config.yaml. Wird von Streamlit gecacht."""
    with CONFIG_PFAD.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------
# Streamlit-Seite konfigurieren
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="ReqPOOL Estimation Manager",
    page_icon="📊",
    layout="wide",
)

config = lade_config()
branding = config["branding"]

# CSS fuer das ReqPOOL-Branding
st.markdown(
    f"""
    <style>
    .reqpool-header {{
        background-color: {branding['primaer_farbe']};
        color: white;
        padding: 18px 24px;
        border-radius: 8px;
        margin-bottom: 20px;
    }}
    .reqpool-header h1 {{
        margin: 0;
        font-size: 28px;
        font-weight: 700;
    }}
    .reqpool-header p {{
        margin: 4px 0 0 0;
        font-size: 14px;
        opacity: 0.9;
    }}
    .gesamt-box {{
        background-color: {branding['hintergrund_farbe']};
        border-left: 5px solid {branding['akzent_farbe']};
        padding: 16px 20px;
        border-radius: 4px;
        margin: 12px 0;
    }}
    </style>
    <div class="reqpool-header">
        <h1>{branding['firma']}</h1>
        <p>{branding['produkt']} – Aufwandsschaetzung fuer Software-Projekte</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# Persistenz-Hinweis: Wenn wir nur Session-State haben (z.B. Streamlit
# Cloud), zeigen wir einen freundlichen Hinweis an.
# ---------------------------------------------------------------------
if not ist_persistent():
    st.info(
        "ℹ️ **Demo-Modus:** Die Schaetzungs-Historie wird nur in deiner "
        "aktuellen Browser-Session gespeichert. Nach dem Schliessen des "
        "Tabs oder einem Neustart der App sind die Eintraege weg. "
        "Wichtige Schaetzungen also bitte als PDF herunterladen!"
    )


# ---------------------------------------------------------------------
# Sidebar: Schaetzwerte einstellen
# ---------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Schaetzwerte (PT pro Einheit)")
    st.caption(
        "Diese Werte werden fuer die Berechnung verwendet. "
        "Defaults stammen aus `config.yaml`."
    )

    # Wir merken uns die Werte im Session-State, damit sie ueber
    # Reruns hinweg erhalten bleiben.
    if "aufwand_overrides" not in st.session_state:
        st.session_state.aufwand_overrides = dict(config["aufwand_pro_einheit"])

    aufwand_overrides = {}
    for key, label in KATEGORIE_LABELS.items():
        default_wert = float(st.session_state.aufwand_overrides.get(
            key, config["aufwand_pro_einheit"][key]
        ))
        aufwand_overrides[key] = st.number_input(
            f"PT pro {label}",
            min_value=0.0,
            value=default_wert,
            step=0.1,
            format="%.2f",
            key=f"aufwand_{key}",
        )
    st.session_state.aufwand_overrides = aufwand_overrides

    if st.button("🔄 Auf Defaults zuruecksetzen"):
        # Werte aus Config zurueckholen und Session-State leeren
        for key in KATEGORIE_LABELS:
            st.session_state[f"aufwand_{key}"] = float(
                config["aufwand_pro_einheit"][key]
            )
        st.session_state.aufwand_overrides = dict(config["aufwand_pro_einheit"])
        st.rerun()

    st.divider()
    st.caption(
        f"**Aufschlaege:** PM "
        f"{config['aufschlaege_prozent']['projektmanagement']}%, "
        f"Tests {config['aufschlaege_prozent']['tests']}%, "
        f"Doku {config['aufschlaege_prozent']['dokumentation']}%"
    )
    st.caption(f"**Range:** ± {config['range_prozent']}%")


# ---------------------------------------------------------------------
# Tabs: Neue Schaetzung / Historie
# ---------------------------------------------------------------------
tab_neu, tab_historie = st.tabs(["🆕 Neue Schaetzung", "📚 Historie"])


# =====================================================================
# TAB 1: Neue Schaetzung
# =====================================================================
with tab_neu:
    st.subheader("Projekt-Eingaben")

    # Projekttitel
    titel = st.text_input(
        "Projekttitel",
        value="",
        placeholder="z.B. ERP-Ablöse Phase 1",
    )

    # Mengen-Eingabefelder in 2x4-Grid
    spalten = st.columns(4)
    inputs = {}
    keys = list(KATEGORIE_LABELS.keys())
    for i, key in enumerate(keys):
        with spalten[i % 4]:
            inputs[key] = st.number_input(
                KATEGORIE_LABELS[key],
                min_value=0,
                value=0,
                step=1,
                key=f"input_{key}",
            )

    # Projektskizze
    skizze = st.text_area(
        "Projektskizze (Freitext)",
        height=180,
        placeholder=(
            "Beschreiben Sie das Projekt in eigenen Worten. "
            "Begriffe wie 'komplex', 'Integration', 'Legacy', 'Migration', "
            "'Echtzeit', 'Sicherheit', 'DSGVO' etc. erhoehen den "
            "Komplexitaetsfaktor automatisch."
        ),
    )

    # Berechnungs-Button
    knopf = st.button("📊 Schaetzung berechnen", type="primary")

    # Ergebnis-Anzeige (nur wenn berechnet wurde)
    if knopf:
        if sum(inputs.values()) == 0 and not skizze.strip():
            st.warning(
                "Bitte mindestens eine Mengenangabe machen oder eine "
                "Skizze eingeben."
            )
        else:
            ergebnis = berechne_schaetzung(
                inputs=inputs,
                skizze=skizze,
                config=config,
                aufwand_pro_einheit_override=st.session_state.aufwand_overrides,
            )
            scope_text = erzeuge_scope_beschreibung(inputs, skizze)

            # Ergebnis im Session-State speichern, damit es nach
            # einem Rerun (z.B. durch Download-Button) noch da ist.
            st.session_state.letztes_ergebnis = {
                "ergebnis": ergebnis,
                "inputs": inputs,
                "skizze": skizze,
                "scope_text": scope_text,
                "titel": titel or "Unbenannte Schaetzung",
            }

            # Automatisch speichern
            speicher_id = speichere_schaetzung(
                titel=titel or "Unbenannte Schaetzung",
                inputs=inputs,
                skizze=skizze,
                ergebnis=ergebnis,
            )
            st.toast(f"✅ Schaetzung gespeichert (ID: {speicher_id[:8]}...)")

    # Falls eine Schaetzung im Session-State liegt, anzeigen
    if "letztes_ergebnis" in st.session_state:
        daten = st.session_state.letztes_ergebnis
        ergebnis = daten["ergebnis"]
        scope_text = daten["scope_text"]

        st.divider()
        st.subheader("📈 Ergebnis")

        # --- Gesamt-Box ---
        st.markdown(
            f"""
            <div class="gesamt-box">
                <div style="font-size:14px;color:#555;">Geschaetzter Aufwand</div>
                <div style="font-size:36px;font-weight:700;
                            color:{branding['primaer_farbe']};">
                    {ergebnis.gesamt_pt:.1f} PT
                </div>
                <div style="font-size:14px;color:#555;">
                    Range: <b>{ergebnis.gesamt_pt_min:.1f} PT</b> –
                    <b>{ergebnis.gesamt_pt_max:.1f} PT</b>
                    (± {config['range_prozent']}%)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- Aufschluesselung in Spalten ---
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Aufschluesselung pro Kategorie**")
            tabellen_daten = [
                {
                    "Kategorie": k.name,
                    "Anzahl": k.anzahl,
                    "PT/Einheit": f"{k.pt_pro_einheit:.2f}",
                    "Summe (PT)": f"{k.summe_pt:.2f}",
                }
                for k in ergebnis.kategorien
            ]
            st.dataframe(tabellen_daten, hide_index=True, use_container_width=True)
            st.metric("Basis-Aufwand", f"{ergebnis.basis_pt:.2f} PT")

        with col2:
            st.markdown("**Komplexitaet & Aufschlaege**")
            st.metric(
                "Komplexitaetsfaktor",
                f"{ergebnis.komplexitaet.faktor:.2f}",
            )
            st.caption(ergebnis.komplexitaet.begruendung)
            st.metric(
                "Aufwand nach Komplexitaet",
                f"{ergebnis.pt_nach_komplexitaet:.2f} PT",
            )

            aufschlaege_daten = [
                {"Position": a.name, "Prozent": f"{a.prozent:.0f}%",
                 "PT": f"{a.pt:.2f}"}
                for a in ergebnis.aufschlaege
            ]
            st.dataframe(
                aufschlaege_daten, hide_index=True,
                use_container_width=True,
            )
            st.metric(
                "Summe Aufschlaege",
                f"{ergebnis.aufschlaege_summe_pt:.2f} PT",
            )

        # --- Scope-Beschreibung ---
        with st.expander("📄 Scope-Beschreibung"):
            st.text(scope_text)

        # --- PDF-Download ---
        st.divider()
        pdf_bytes = erzeuge_pdf(
            ergebnis=ergebnis,
            inputs=daten["inputs"],
            skizze=daten["skizze"],
            scope_text=scope_text,
            config=config,
            projekt_titel=daten["titel"],
        )
        datei_name = (
            f"reqpool_schaetzung_"
            f"{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        )
        st.download_button(
            label="📥 Als PDF herunterladen",
            data=pdf_bytes,
            file_name=datei_name,
            mime="application/pdf",
            type="primary",
        )


# =====================================================================
# TAB 2: Historie
# =====================================================================
with tab_historie:
    st.subheader("Gespeicherte Schaetzungen")

    eintraege = lade_alle_schaetzungen()
    if not eintraege:
        st.info("Noch keine Schaetzungen vorhanden. Lege im Tab "
                "'Neue Schaetzung' eine an.")
    else:
        st.caption(f"{len(eintraege)} Eintraege - neueste zuerst")
        for eintrag in eintraege:
            ts = eintrag.get("timestamp", "")
            titel_str = eintrag.get("titel", "Unbenannt")
            erg = eintrag.get("ergebnis", {})
            with st.expander(
                f"📋 {titel_str} – {ts} – "
                f"{erg.get('gesamt_pt', 0):.1f} PT"
            ):
                col1, col2, col3 = st.columns(3)
                col1.metric("Gesamt", f"{erg.get('gesamt_pt', 0):.1f} PT")
                col2.metric(
                    "Range",
                    f"{erg.get('gesamt_pt_min', 0):.0f} – "
                    f"{erg.get('gesamt_pt_max', 0):.0f}",
                )
                col3.metric(
                    "Komplexitaet",
                    f"{erg.get('komplexitaet_faktor', 1.0):.2f}",
                )

                st.markdown("**Inputs:**")
                st.json(eintrag.get("inputs", {}), expanded=False)

                st.markdown("**Skizze:**")
                st.text(eintrag.get("skizze", "") or "(leer)")

                if st.button(
                    "🗑️ Loeschen",
                    key=f"loesch_{eintrag['id']}",
                ):
                    loesche_schaetzung(eintrag["id"])
                    st.rerun()
