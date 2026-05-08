# ReqPOOL Estimation Manager

Eine Streamlit-Webapp zur **Aufwandsschätzung von Software-Projekten in Personentagen (PT)**. Sie kombiniert harte Mengenangaben (Pages, Use Cases, Business Objects, Interfaces, Batches, Languages, Roles, Users) mit einer textuellen Projektskizze und liefert eine transparente, nachvollziehbare Schätzung – inklusive PDF-Export im ReqPOOL-Branding.

---

## ✨ Features

- **Parametrisches Schätzmodell** mit Aufwand pro Einheit, in `config.yaml` und in der UI editierbar
- **Komplexitätsfaktor** wird heuristisch aus der Projektskizze berechnet (Schlüsselwörter wie *komplex*, *Integration*, *Legacy*, *DSGVO* etc.)
- **Aufschläge** für Projektmanagement, Tests und Dokumentation als prozentualer Anteil
- **Min/Max-Range** (± 20 % per Default) zur Darstellung der Schätzunsicherheit
- **Historie**: alle Schätzungen werden lokal in `data/estimations.json` gespeichert
- **PDF-Export** mit professionellem Layout, ReqPOOL-Header, Tabellen, Aufschlüsselung, Scope-Beschreibung
- **Komplett deutschsprachig** (UI, PDF, Kommentare im Code)

---

## 🚀 Installation und Start

### Voraussetzungen
- Python 3.10 oder neuer
- pip

### 1. Repository klonen
```bash
git clone https://github.com/Romain-Ritz/reqpool-estimation-manager.git
cd reqpool-estimation-manager
```

### 2. Virtuelle Umgebung anlegen (empfohlen)
```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

### 3. Abhängigkeiten installieren
```bash
pip install -r requirements.txt
```

### 4. App starten
```bash
streamlit run app.py
```

Im Browser öffnet sich automatisch <http://localhost:8501>.

---

## 🖥️ Bedienung

### UI-Aufbau

**Sidebar (links):**
- Editierbare Schätzwerte (PT pro Einheit) für alle 8 Kategorien
- Button „Auf Defaults zurücksetzen" lädt die Werte aus `config.yaml`
- Anzeige der aktuell eingestellten Aufschläge und Range

**Tab „Neue Schätzung":**
1. Projekttitel eingeben
2. Mengenangaben für die 8 Kategorien (Pages, Use Cases, …) eintragen
3. Projektskizze als Freitext einfügen
4. Auf „Schätzung berechnen" klicken
5. Das Ergebnis wird unten angezeigt:
   - **Gesamtaufwand** in PT mit Min/Max-Range
   - Aufschlüsselung pro Kategorie (Tabelle)
   - Erkannter Komplexitätsfaktor inklusive Begründung (welche Keywords gefunden wurden)
   - Aufschläge separat ausgewiesen
   - Scope-Beschreibung (aufklappbar)
6. Mit „Als PDF herunterladen" wird ein professionell formatiertes PDF generiert

**Tab „Historie":**
- Alle gespeicherten Schätzungen, neueste zuerst
- Aufklappbare Detailansicht inkl. Inputs, Skizze und Ergebniszahlen
- Einzelne Einträge können gelöscht werden

### Beispielhafter Screenshot-Aufbau

```
┌─────────────────────────────────────────────────────────────┐
│ ReqPOOL                                                      │
│ Estimation Manager – Aufwandsschätzung für Softwareprojekte │
├──────────────┬──────────────────────────────────────────────┤
│ ⚙ Schätz-    │  🆕 Neue Schätzung   📚 Historie             │
│   werte      │                                              │
│              │  Projekttitel: [_____________________]       │
│ PT pro Page  │                                              │
│   [ 2.00 ]   │  Pages [10]  Use Cases [5]  ...              │
│ PT pro Use   │                                              │
│   Case [5.0] │  Projektskizze:                              │
│ ...          │  [_______________________________________]   │
│              │                                              │
│              │  [📊 Schätzung berechnen]                    │
│              │                                              │
│              │  ┌───────────────────────────────────┐       │
│              │  │  Geschätzter Aufwand              │       │
│              │  │  ┃ 87.4 PT                        │       │
│              │  │  Range: 69.9 PT – 104.9 PT        │       │
│              │  └───────────────────────────────────┘       │
└──────────────┴──────────────────────────────────────────────┘
```

---

## ⚙️ Konfiguration über `config.yaml`

Die Datei `config.yaml` enthält alle Default-Parameter:

```yaml
aufwand_pro_einheit:
  pages: 2.0              # PT pro Page
  use_cases: 5.0          # PT pro Use Case
  business_objects: 3.0
  interfaces: 4.0
  batches: 3.0
  languages: 1.0
  roles: 0.5
  users: 0.1

aufschlaege_prozent:
  projektmanagement: 15
  tests: 20
  dokumentation: 10

komplexitaet:
  basis_faktor: 1.0
  faktor_min: 0.8
  faktor_max: 1.6
  keywords_erhoehen:
    komplex: 0.10
    integration: 0.08
    legacy: 0.10
    # ... weitere Keywords
  keywords_reduzieren:
    einfach: 0.10
    standard: 0.05
    # ... weitere Keywords

range_prozent: 20
```

### So passt du die Konfiguration an

| Anpassung | Wo? |
|---|---|
| **Aufwand pro Einheit ändern** (z. B. Pages teurer) | In `config.yaml` unter `aufwand_pro_einheit` ODER live in der Sidebar der App |
| **Aufschläge anpassen** (z. B. 25 % Tests statt 20 %) | In `config.yaml` unter `aufschlaege_prozent` |
| **Neue Komplexitäts-Keywords hinzufügen** | In `config.yaml` unter `komplexitaet.keywords_erhoehen` einen Eintrag `mein_keyword: 0.07` ergänzen |
| **Min/Max-Range ändern** (z. B. ± 30 %) | In `config.yaml` den Wert `range_prozent: 30` setzen |
| **Branding-Farben** (PDF + UI) | In `config.yaml` unter `branding` |

> **Hinweis:** Änderungen an `config.yaml` werden beim nächsten Start der App übernommen. Live-Änderungen in der Sidebar wirken nur in der aktuellen Session und werden **nicht** in die Datei zurückgeschrieben.

---

## 🗂️ Projekt-Struktur

```
reqpool-estimation-manager/
├── app.py                # Streamlit-UI (Hauptdatei)
├── estimator.py          # Schätz-Logik (Berechnung, Komplexität)
├── pdf_export.py         # PDF-Generator mit reportlab
├── storage.py            # Persistenz (JSON-basiert)
├── config.yaml           # Alle Schätzparameter
├── requirements.txt      # Python-Dependencies
├── .gitignore
├── data/
│   └── .gitkeep          # estimations.json wird hier zur Laufzeit erzeugt
└── README.md
```

---

## 🧠 Wie funktioniert die Schätzung?

Die Berechnung erfolgt in 5 Schritten:

1. **Basis-Aufwand:** Σ (Anzahl × PT pro Einheit) für alle 8 Kategorien
2. **Komplexitätsfaktor:** Aus der Projektskizze werden Schlüsselwörter extrahiert. Jedes erhöhende Keyword addiert seinen Zuschlag, jedes reduzierende Keyword zieht einen Abzug. Sehr lange Skizzen (> 300 / > 500 Wörter) erhalten einen kleinen Längen-Bonus. Der Faktor wird auf den Bereich `[faktor_min, faktor_max]` begrenzt.
3. **Zwischen-Ergebnis:** Basis-Aufwand × Komplexitätsfaktor
4. **Aufschläge:** Jeweils prozentuale Aufschläge auf das Zwischen-Ergebnis (PM, Tests, Dokumentation)
5. **Gesamt-PT** = Zwischen-Ergebnis + Summe Aufschläge. Min/Max ergeben sich aus ± `range_prozent` %.

> Die Heuristik ist bewusst einfach gehalten und transparent: jeder erkannte Begriff wird in der Begründung sichtbar gemacht.

---

## 📜 Lizenz

Dieses Projekt entstand als Prototyp im Rahmen einer Schulung. Lizenzfragen klären beim Einsatz im Produktivbetrieb.
