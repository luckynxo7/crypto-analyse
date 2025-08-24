import io
import base64
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Krypto Analyse – Regeln & Legenden", layout="wide")

# -----------------------------
# Legenden (Sektion 5)
# -----------------------------
LEG_MACD_POSITION = [
    (8, "Sehr weit über 0"),
    (7, "Weit über 0"),
    (6, "Leicht über 0"),
    (5, "Knapp über 0"),
    (4, "Knapp unter 0"),
    (3, "Leicht unter 0"),
    (2, "Weit unter 0"),
    (1, "Sehr weit unter 0"),
]

LEG_MACD_SIGLINE = [
    ("a", "Bullisch gekreuzt"),
    ("b", "Knapp bullisch gekreuzt"),
    ("c", "Unmittelbar vor bullischer Kreuzung"),
    ("d", "Kurz vor bullischer Kreuzung"),
    ("e", "Parallel, Abstand weit"),
    ("f", "Parallel, Abstand moderat"),
    ("g", "Kurz vor bärischer Kreuzung"),
    ("h", "Unmittelbar vor bärischer Kreuzung"),
    ("i", "Knapp bärisch gekreuzt"),
    ("j", "Bärisch gekreuzt"),
]

LEG_MACD_HIST = [
    ("!", "Stark steigend, positiv"),
    ("„", "Leicht steigend, positiv"),
    ("§", "Leicht sinkend, positiv"),
    ("$", "Stark sinkend, positiv"),
    ("%", "Stark steigend, negativ"),
    ("&", "Leicht steigend, negativ"),
    ("/", "Leicht sinkend, negativ"),
    ("(", "Stark sinkend, negativ"),
    (")", "Stark steigend, fast bei 0"),
    ("?", "Leicht steigend, fast bei 0"),
    (";", "Leicht sinkend, fast bei 0"),
    ("#", "Stark sinkend, fast bei 0"),
]

BOLLINGER_STATES = [
    "überverkauft",
    "leicht überverkauft",
    "neutral",
    "leicht überkauft",
    "überkauft",
]

DIVERGENZ_STATES = [
    "stark bullisch",
    "bullisch",
    "leicht bullisch",
    "neutral",
    "leicht bärisch",
    "bärisch",
    "stark bärisch",
]

POS_LABELS = {k: v for k, v in LEG_MACD_POSITION}
SIG_LABELS = {k: v for k, v in LEG_MACD_SIGLINE}
HIST_LABELS = {k: v for k, v in LEG_MACD_HIST}

# -----------------------------
# Utility
# -----------------------------
def to_excel_bytes(sheets: dict) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return output.getvalue()

def normalize_hist_code(code: str) -> str:
    if code is None:
        return ""
    code = str(code).strip()
    if code == '"':
        return "„"
    return code

# -----------------------------
# State
# -----------------------------
if "rows" not in st.session_state:
    st.session_state.rows = []

# -----------------------------
# Tabs (Sektionen)
# -----------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Sektion 1 – Eingabe",
    "Sektion 2 – Übersicht",
    "Sektion 3 – Handlungsempfehlungen",
    "Sektion 4 – Regeln",
    "Sektion 5 – Legenden",
])

# -----------------------------
# Sektion 1
# -----------------------------
with tab1:
    st.subheader("Eingabemaske")
    with st.form("eingabe"):
        c1, c2, c3 = st.columns(3)
        with c1:
            asset = st.text_input("Asset")
            kurs_usd = st.number_input("Kurs USD", min_value=0.0, step=0.01)
            rsi = st.number_input("RSI", min_value=0.0, max_value=100.0, step=0.1)
            timeframe = st.selectbox("Timeframe", ["1H", "4H", "1D", "1W"], index=1)
        with c2:
            macd_pos = st.selectbox("MACD Position", [p for p, _ in LEG_MACD_POSITION], format_func=lambda x: f"{x} – {POS_LABELS[x]}")
            macd_sig = st.selectbox("MACD zu Signallinie", [s for s, _ in LEG_MACD_SIGLINE], format_func=lambda x: f"{x} – {SIG_LABELS[x]}")
            macd_hist = st.selectbox("MACD Histogramm", [h for h, _ in LEG_MACD_HIST], format_func=lambda x: f"{x} – {HIST_LABELS[x]}")
            bollinger = st.selectbox("Bollinger Bänder", BOLLINGER_STATES)
        with c3:
            divergenz = st.selectbox("Divergenz RSI/Kurs", DIVERGENZ_STATES)
            bew_zeit = st.text_input("Bewertungszeit", value=datetime.now().strftime("%Y-%m-%d %H:%M"))
            kommentar = st.text_input("Kommentar", value="")
        submitted = st.form_submit_button("➕ Datensatz hinzufügen")
        if submitted and asset.strip():
            st.session_state.rows.append({
                "Asset": asset.strip(),
                "Kurs_USD": kurs_usd,
                "RSI": rsi,
                "MACD_Position": macd_pos,
                "MACD_zu_Signallinie": macd_sig,
                "MACD_Histogramm": normalize_hist_code(macd_hist),
                "Bollinger": bollinger,
                "Divergenz": divergenz,
                "Timeframe": timeframe,
                "Bewertungszeit": bew_zeit,
                "Kommentar": kommentar,
            })
            st.success(f"Eintrag für {asset} hinzugefügt")

# -----------------------------
# Sektion 2
# -----------------------------
with tab2:
    st.subheader("Übersicht")
    if st.session_state.rows:
        df = pd.DataFrame(st.session_state.rows)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Export als XLSX", to_excel_bytes({"Daten": df}), "daten.xlsx")
    else:
        st.info("Noch keine Einträge vorhanden.")

# -----------------------------
# Regeln Funktion
# -----------------------------
def evaluate_row(row):
    rsi = row["RSI"]; mp = row["MACD_Position"]; sig = row["MACD_zu_Signallinie"]; hist = row["MACD_Histogramm"]; boll = row["Bollinger"]; div = row["Divergenz"]
    if rsi < 40 and mp < 3 and sig in {"a","b","c","d"} and hist in {"(","/",";"} and boll=="überverkauft" and div in {"leicht bullisch","bullisch","stark bullisch"}:
        return "Kaufen"
    if 40 <= rsi <= 45 and mp == 3 and sig in {"a","b","c","d"} and hist in {"(","/",";"} and boll in {"überverkauft","leicht überverkauft"} and div=="leicht bullisch":
        return "Kauf in Erwägung ziehen"
    if 65 <= rsi <= 70 and mp == 6 and sig in {"g","h","i","j"} and hist in {"$","§"} and boll in {"leicht überkauft","überkauft"} and div=="leicht bärisch":
        return "Verkauf in Erwägung ziehen"
    if rsi > 70 and mp > 6 and sig in {"g","h","i","j"} and hist in {"$","§"} and boll=="überkauft" and div in {"leicht bärisch","bärisch","stark bärisch"}:
        return "Verkaufen"
    return "Keine Handlung"

# -----------------------------
# Sektion 3
# -----------------------------
with tab3:
    st.subheader("Handlungsempfehlungen")
    if st.session_state.rows:
        df = pd.DataFrame(st.session_state.rows)
        df["Empfehlung"] = df.apply(evaluate_row, axis=1)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Export Empfehlungen", to_excel_bytes({"Empfehlungen": df}), "empfehlungen.xlsx")
    else:
        st.info("Noch keine Daten.")

# -----------------------------
# Sektion 4
# -----------------------------
with tab4:
    st.subheader("Regeln")
    st.markdown("""
1. **Kaufen**: RSI < 40, MACD Pos < 3, Sig ∈ {a,b,c,d}, Hist ∈ {(,/,;}, Bollinger=überverkauft, Divergenz bullisch  
2. **Kauf erwägen**: RSI 40–45, MACD Pos=3, Sig ∈ {a,b,c,d}, Hist ∈ {(,/,;}, Bollinger ∈ {überverkauft, leicht überverkauft}, Divergenz=leicht bullisch  
3. **Verkauf erwägen**: RSI 65–70, MACD Pos=6, Sig ∈ {g,h,i,j}, Hist ∈ {$,§}, Bollinger ∈ {leicht überkauft, überkauft}, Divergenz=leicht bärisch  
4. **Verkaufen**: RSI > 70, MACD Pos > 6, Sig ∈ {g,h,i,j}, Hist ∈ {$,§}, Bollinger=überkauft, Divergenz bärisch  
5. **Keine Handlung**, wenn keine zutrifft
""")

# -----------------------------
# Sektion 5
# -----------------------------
with tab5:
    st.subheader("Legenden")
    c1, c2, c3 = st.columns(3)
    with c1: st.table(pd.DataFrame(LEG_MACD_POSITION, columns=["Wert","Bedeutung"]))
    with c2: st.table(pd.DataFrame(LEG_MACD_SIGLINE, columns=["Code","Bedeutung"]))
    with c3: st.table(pd.DataFrame(LEG_MACD_HIST, columns=["Code","Bedeutung"]))
