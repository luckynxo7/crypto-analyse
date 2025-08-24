
import io
import re
import json
import base64
import pandas as pd
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Krypto-Indikator Signale", layout="wide")

# -----------------------------
# Helpers
# -----------------------------

def norm_col(name: str) -> str:
    name = str(name)
    name = re.sub(r"\s+", "_", name.strip())
    name = re.sub(r"[^0-9a-zA-Z_]", "_", name)
    if re.match(r"^\d", name):
        name = "_" + name
    return name

def df_with_norm_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {c: norm_col(c) for c in df.columns}
    df2 = df.copy()
    df2.columns = [mapping[c] for c in df.columns]
    return df2, mapping

def to_excel_bytes(sheets: dict) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return output.getvalue()

def download_link(binary: bytes, filename: str, label: str):
    b64 = base64.b64encode(binary).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)

def try_to_numeric(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == "object":
            out[c] = pd.to_numeric(out[c], errors="ignore")
    return out

# -----------------------------
# Sidebar: File upload
# -----------------------------

st.title("📈 Krypto-Indikator Signale - regelbasierte Empfehlungen")

with st.sidebar:
    st.header("🔧 Datenquelle")
    uploaded = st.file_uploader("ODS/XLSX-Datei hochladen (mit Sheets: Daten, Legenden, Regeln)", type=["ods", "xlsx"])
    st.caption("Tipp: Deine bestehende Datei mit den Sheets Daten, Legenden und Regeln hochladen.")

    st.markdown(
        "**Regeln-Format (Beispiel):**  \n"
        "- Spalten: Regel (boolescher Ausdruck), Empfehlung, optional Prioritaet (Zahl, kleiner = wichtiger), Begruendung  \n"
        "- Ausdruecke referenzieren Spaltennamen aus 'Daten' (nach Normalisierung - Leerzeichen werden durch '_' ersetzt).  \n"
        "- Operatoren: and, or, >, >=, <, <=, ==, !=  \n"
        "- Beispiel: RSI < 30 and MACD_Histogramm > 0 and Preis <= Bollinger_Unteres_Band"
    )

# -----------------------------
# Load sheets
# -----------------------------

if "state" not in st.session_state:
    st.session_state.state = {}

sheets = {}
if uploaded is not None:
    try:
        if uploaded.name.lower().endswith(".ods"):
            df_all = pd.read_excel(uploaded, sheet_name=None, engine="odf")
        else:
            df_all = pd.read_excel(uploaded, sheet_name=None)
        sheets = df_all
    except Exception as e:
        st.error(f"Fehler beim Einlesen: {e}")

# Initialize placeholders if missing
if sheets == {}:
    st.info("Noch keine Datei geladen. Du kannst ohne Upload loslegen - wir erzeugen leere Sheets.")
    sheets = {
        "Daten": pd.DataFrame(columns=["Asset", "Timeframe", "Bewertungszeit", "RSI", "MACD_Line", "MACD_Signal", "MACD_Histogramm", "Preis"]),
        "Legenden": pd.DataFrame(columns=["Indikator", "Label", "Von", "Bis", "Farbe"]),
        "Regeln": pd.DataFrame(columns=["Regel", "Empfehlung", "Prioritaet", "Begruendung"]),
    }

for k, v in list(sheets.items()):
    if not isinstance(v, pd.DataFrame):
        try:
            sheets[k] = pd.DataFrame(v)
        except Exception:
            pass

daten_df = sheets.get("Daten", pd.DataFrame()).copy()
legenden_df = sheets.get("Legenden", pd.DataFrame()).copy()
regeln_df = sheets.get("Regeln", pd.DataFrame()).copy()

daten_df = try_to_numeric(daten_df)
legenden_df = try_to_numeric(legenden_df)
regeln_df = try_to_numeric(regeln_df)

daten_norm, daten_map = df_with_norm_columns(daten_df)
regeln_norm, regeln_map = df_with_norm_columns(regeln_df)

tab1, tab2, tab3, tab4 = st.tabs(["🔎 Übersicht", "🧭 Legenden", "📝 Bewertung erfassen", "✅ Empfehlungen"])

with tab1:
    st.subheader("Struktur & Vorschau")
    cols = st.columns(3)
    with cols[0]:
        st.metric("Zeilen (Daten)", len(daten_df))
    with cols[1]:
        st.metric("Zeilen (Legenden)", len(legenden_df))
    with cols[2]:
        st.metric("Zeilen (Regeln)", len(regeln_df))

    st.markdown("**Spalten in 'Daten' (Original -> Normalisiert):**")
    if len(daten_df.columns) == 0:
        st.write("Keine Spalten vorhanden.")
    else:
        map_df = pd.DataFrame({"Original": list(daten_map.keys()), "Normalisiert": list(daten_map.values())})
        st.dataframe(map_df, use_container_width=True)

    st.markdown("**Vorschau 'Daten'**")
    st.dataframe(daten_df.head(25), use_container_width=True)

    st.markdown("**Vorschau 'Regeln'**")
    st.dataframe(regeln_df.head(25), use_container_width=True)

with tab2:
    st.subheader("Legenden / Bewertungs-Referenzen")
    if len(legenden_df) == 0:
        st.info("Keine Legenden vorhanden. Optional: Spalten wie 'Indikator | Label | Von | Bis | Farbe'.")
    else:
        st.dataframe(legenden_df, use_container_width=True)

with tab3:
    st.subheader("Neue Bewertung eintragen")
    base_cols = ["Asset", "Timeframe", "Bewertungszeit"]
    numeric_candidates = [c for c in daten_df.columns if c not in base_cols]

    with st.form("bewertung_form"):
        left, right = st.columns(2)
        with left:
            asset = st.text_input("Asset", value=(daten_df["Asset"].dropna().iloc[0] if "Asset" in daten_df.columns and len(daten_df["Asset"].dropna()) else ""))
            timeframe = st.text_input("Timeframe (z. B. 1H, 4H, 1D)", value=(daten_df["Timeframe"].dropna().iloc[0] if "Timeframe" in daten_df.columns and len(daten_df["Timeframe"].dropna()) else ""))
        with right:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            bew_zeit = st.text_input("Bewertungszeit (YYYY-MM-DD HH:MM)", value=now_str)

        st.markdown("---")
        st.markdown("**Indikator-Werte**")
        new_row = {}
        for c in numeric_candidates:
            val = st.text_input(f"{c}", value="")
            new_row[c] = val

        submitted = st.form_submit_button("➕ Eintrag hinzufügen")
        if submitted:
            row = {}
            for c in daten_df.columns:
                if c == "Asset":
                    row[c] = asset
                elif c == "Timeframe":
                    row[c] = timeframe
                elif c == "Bewertungszeit":
                    row[c] = bew_zeit
                else:
                    row[c] = new_row.get(c, None)
            daten_df = pd.concat([daten_df, pd.DataFrame([row])], ignore_index=True)
            st.success("Eintrag hinzugefügt (nur in dieser Sitzung).")
            st.session_state["added_rows"] = st.session_state.get("added_rows", 0) + 1

    st.markdown("**Aktuelle Daten (inkl. neu erfasster Einträge in dieser Sitzung):**")
    st.dataframe(daten_df, use_container_width=True)

    upd = {"Daten": daten_df, "Legenden": legenden_df, "Regeln": regeln_df}
    xlsx_bytes = to_excel_bytes(upd)
    download_link(xlsx_bytes, "krypto_indikator_daten.xlsx", "📥 Aktualisierte Datei herunterladen (XLSX)")

with tab4:
    st.subheader("Regelbasierte Handlungsempfehlungen")
    daten_norm, daten_map = df_with_norm_columns(daten_df)

    f1, f2, f3 = st.columns(3)
    asset_choices = sorted([x for x in daten_df.get("Asset", pd.Series(dtype=str)).dropna().unique()]) if "Asset" in daten_df.columns else []
    timeframe_choices = sorted([x for x in daten_df.get("Timeframe", pd.Series(dtype=str)).dropna().unique()]) if "Timeframe" in daten_df.columns else []
    with f1:
        asset_sel = st.multiselect("Asset-Filter", options=asset_choices, default=asset_choices)
    with f2:
        tf_sel = st.multiselect("Timeframe-Filter", options=timeframe_choices, default=timeframe_choices)
    with f3:
        latest_only = st.checkbox("Nur jüngste Bewertung je Asset/Timeframe", value=True)

    rules = []
    if len(regeln_df) > 0 and "Regel" in regeln_df.columns and "Empfehlung" in regeln_df.columns:
        for _, r in regeln_df.iterrows():
            expr = str(r.get("Regel", "")).strip()
            emp = str(r.get("Empfehlung", "")).strip()
            prio = r.get("Prioritaet", None)
            try:
                prio = float(prio) if pd.notna(prio) else 9999.0
            except Exception:
                prio = 9999.0
            begr = str(r.get("Begruendung", "")).strip()
            if expr and emp:
                rules.append({"expr": expr, "empfehlung": emp, "prio": prio, "begruendung": begr})

    result_rows = []
    if len(daten_norm) > 0 and len(rules) > 0:
        work = daten_df.copy()
        if "Asset" in work.columns and asset_sel:
            work = work[work["Asset"].isin(asset_sel)]
        if "Timeframe" in work.columns and tf_sel:
            work = work[work["Timeframe"].isin(tf_sel)]
        if latest_only and set(["Asset","Timeframe","Bewertungszeit"]).issubset(work.columns):
            tmp = work.copy()
            tmp["_parsed_dt"] = pd.to_datetime(tmp["Bewertungszeit"], errors="coerce")
            tmp = tmp.sort_values(["Asset","Timeframe","_parsed_dt"], ascending=[True, True, False])
            work = tmp.groupby(["Asset","Timeframe"], as_index=False).head(1).drop(columns=["_parsed_dt"])

        work_norm, mapping = df_with_norm_columns(work)
        work_norm = try_to_numeric(work_norm)

        for idx, row in work_norm.iterrows():
            best = None
            locals_dict = {col: row[col] for col in work_norm.columns}
            for rule in rules:
                expr = rule["expr"]
                expr_norm = expr
                for orig, normed in mapping.items():
                    if orig != normed and orig in expr_norm:
                        expr_norm = re.sub(rf"\b{re.escape(orig)}\b", normed, expr_norm)

                try:
                    ok = eval(expr_norm, {"__builtins__": {}}, locals_dict)
                except Exception:
                    ok = False

                if ok:
                    if (best is None) or (rule["prio"] < best["prio"]):
                        best = rule

            result_rows.append({
                "Asset": row.get(mapping.get("Asset","Asset"), ""),
                "Timeframe": row.get(mapping.get("Timeframe","Timeframe"), ""),
                "Bewertungszeit": row.get(mapping.get("Bewertungszeit","Bewertungszeit"), ""),
                "Empfehlung": best["empfehlung"] if best else "",
                "Regel_trigger": best["expr"] if best else "",
                "Begruendung": best["begruendung"] if best else "",
                "Prioritaet": best["prio"] if best else None
            })

    results_df = pd.DataFrame(result_rows)
    if len(results_df) == 0:
        st.warning("Keine Empfehlungen berechnet. Pruefe, ob Regeln vorhanden sind und die Spaltennamen in den Ausdruecken stimmen.")
    else:
        st.dataframe(results_df, use_container_width=True)
        csv = results_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Ergebnisse als CSV herunterladen", data=csv, file_name="empfehlungen.csv", mime="text/csv")
        xlsx_bytes = to_excel_bytes({"Empfehlungen": results_df, "Daten": daten_df, "Regeln": regeln_df, "Legenden": legenden_df})
        st.download_button("📥 Ergebnisse als XLSX herunterladen", data=xlsx_bytes, file_name="empfehlungen.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.caption("Hinweis: Spaltennamen werden intern normalisiert (Leerzeichen -> '_'). Passe deine Regelausdruecke entsprechend an oder nutze die Originalnamen - die App versucht eine automatische Abbildung.")
