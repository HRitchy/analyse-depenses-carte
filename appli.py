import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import plotly.express as px

st.set_page_config(
    page_title="Analyse de Relevé Bancaire Carte",
    page_icon="💳",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .big-metric { font-size: 2rem; font-weight: 700; }
    .sub { color: #888; font-size: 1rem; }
    .step-title { font-size: 1.1rem; font-weight: 600; margin-top:1rem; }
    @media (max-width: 600px) {
        .big-metric { font-size: 1.5rem; }
        .sub { font-size: 0.9rem; }
        .step-title { font-size: 1rem; }
        h1 { font-size: 1.4rem !important; }
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='margin-bottom:0;'>Analyse de vos dépenses carte bancaire</h1>", unsafe_allow_html=True)
st.markdown(
    "<div class='sub'>Suivez vos dépenses en quelques étapes : importez un PDF puis explorez les résultats.</div>",
    unsafe_allow_html=True,
)

# --- UPLOAD ---
with st.sidebar:
    st.header("🗂 Import du relevé")
    st.info("Seules les transactions dont le type contient 'carte' seront conservées.")

st.markdown("<div class='step-title'>1️⃣ Importez un relevé PDF</div>", unsafe_allow_html=True)
uploaded_file = st.file_uploader("Choisissez un relevé de compte (PDF)", type=["pdf"])

# ----------- PARSE PDF (version corrigée) ----------------

@st.cache_data(show_spinner=False)
def parse_pdf(file_bytes):
    try:
        pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        return None, f"Erreur lors de la lecture du PDF: {e}"
    transactions = []
    total_pages = pdf_doc.page_count
    for page_index in range(total_pages):
        page = pdf_doc.load_page(page_index)
        words = page.get_text("words")
        day_indices = []
        for i, w in enumerate(words):
            x0, y0, x1, y1, text, *_ = w
            if 45 <= x0 <= 55 and text.isdigit():
                try:
                    num = int(text)
                except:
                    continue
                if 1 <= num <= 31:
                    day_indices.append(i)
        for idx_pos, start_idx in enumerate(day_indices):
            end_idx = day_indices[idx_pos + 1] if idx_pos < len(day_indices) - 1 else len(words)
            trans_words = words[start_idx:end_idx]
            if len(trans_words) >= 3:
                day = trans_words[0][4]
                month = trans_words[1][4]
                year = trans_words[2][4]
            else:
                continue
            month_names = {
                'janvier': 1, 'février': 2, 'fevrier': 2, 'mars': 3, 'avril': 4, 'mai': 5,
                'juin': 6, 'juillet': 7, 'aout': 8, 'août': 8, 'septembre': 9, 'octobre': 10,
                'novembre': 11, 'décembre': 12, 'decembre': 12
            }
            month_lower = month.lower().strip(".")
            month_num = month_names.get(month_lower)
            try:
                day_num = int(day)
                year_num = int(year)
            except:
                day_num = year_num = None
            date_obj = None
            date_str = ""
            if day_num and month_num and year_num:
                try:
                    date_obj = pd.to_datetime(f"{year_num}-{month_num:02d}-{day_num:02d}")
                    date_str = date_obj.strftime("%Y-%m-%d")
                except:
                    date_str = f"{day} {month} {year}"
            else:
                date_str = f"{day} {month} {year}"
            type_text = ""
            desc_text = ""
            credit_val = 0.0
            debit_val = 0.0
            balance_val = None
            for w in trans_words[3:]:
                x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
                if text.lower().startswith("page ") or text.lower().startswith("généré"):
                    continue
                if 80 <= x0 < 170:
                    type_text += text + " "
                elif 170 <= x0 < 429:
                    desc_text += text + " "
                elif 429 <= x0 < 470:
                    if text.strip().endswith("€"):
                        text = text.replace("€", "")
                    try:
                        credit_val = float(text.replace('\u202f', '').replace('\u00a0', '').replace(',', '.'))
                    except:
                        pass
                elif 470 <= x0 < 510:
                    if text.strip().endswith("€"):
                        text = text.replace("€", "")
                    try:
                        debit_val = float(text.replace('\u202f', '').replace('\u00a0', '').replace(',', '.'))
                    except:
                        pass
                elif x0 >= 510:
                    if text.strip().endswith("€"):
                        text = text.replace("€", "")
                    try:
                        balance_val = float(text.replace('\u202f', '').replace('\u00a0', '').replace(',', '.'))
                    except:
                        pass
            type_text = type_text.strip()
            desc_text = desc_text.strip()
            amount_val = credit_val if credit_val != 0.0 else -debit_val if debit_val != 0.0 else 0.0
            transactions.append({
                "Date": date_obj if date_obj is not None else date_str,
                "Type": type_text,
                "Description": desc_text,
                "Montant": amount_val,
                "Solde": balance_val
            })
    df = pd.DataFrame(transactions)
    return df, None

# ----------- MAIN APP UI ----------------

if uploaded_file:
    progress_bar = st.progress(0)
    with st.spinner("Analyse en cours..."):
        file_bytes = uploaded_file.read()
        df, err = parse_pdf(file_bytes)
    progress_bar.empty()
    st.markdown("<div class='step-title'>2️⃣ Résultats de l'analyse</div>", unsafe_allow_html=True)
    if err or df is None or df.empty:
        st.error(err or "Aucune transaction trouvée. Format PDF non supporté.")
        st.stop()
    # Format dates
    if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df = df.dropna(subset=["Date"])

    # --- FILTRAGE : Transactions carte ---
    df = df[df["Type"].str.contains("carte", case=False, na=False)].copy()
    if df.empty:
        st.warning("Aucune transaction par carte trouvée sur ce relevé.")
        st.stop()

    df = df.sort_values(by="Date").reset_index(drop=True)

    # ------ Filtres classiques (date, recherche description) ------
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtres")
    min_date, max_date = df["Date"].min(), df["Date"].max()
    date_range = st.sidebar.date_input(
        "Période",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    search_txt = st.sidebar.text_input("Recherche dans description", "")

    mask = (
        (df["Date"] >= pd.to_datetime(date_range[0])) &
        (df["Date"] <= pd.to_datetime(date_range[1])) &
        (df["Description"].str.lower().str.contains(search_txt.lower()))
    )
    df_filtered = df[mask].copy().reset_index(drop=True)

    # --------- Onglets principaux ---------
    tab1, tab2, tab3 = st.tabs([
        "🏠 Aperçu général",
        "💳 Transactions",
        "📊 Visualisation",
    ])

    # ----- 1. Aperçu général -----
    with tab1:

        if df_filtered.empty:
            st.warning("Aucune transaction ne correspond aux filtres sélectionnés.")
            st.stop()

        total_dep = df_filtered[df_filtered["Montant"] < 0]["Montant"].sum()
        st.metric("Total dépenses carte", f"{abs(total_dep):,.2f} €", delta=None)

        # Dépenses par description (tableau compact)
        st.markdown("**Dépenses par carte (par description)**")
        resume = (
            df_filtered[df_filtered["Montant"] < 0]
            .groupby("Description")["Montant"]
            .sum()
            .abs()
            .sort_values(ascending=False)
            .reset_index()
        )

        # Ajout d'une colonne indiquant la part de chaque description
        total_depenses = resume["Montant"].sum()
        if total_depenses != 0:
            resume["Pourcentage"] = (resume["Montant"] / total_depenses * 100).round(1)

        resume.index += 1
        format_dict = {"Montant": "{:,.2f} €"}
        if "Pourcentage" in resume.columns:
            format_dict["Pourcentage"] = "{:.1f}%"
        formatted_resume = resume.style.format(format_dict)
        st.dataframe(
            formatted_resume,
            use_container_width=True,
            height=200,
        )

    # ----- 2. Transactions -----
    with tab2:
        depenses_par_carte = df_filtered[df_filtered["Montant"] < 0].copy()
        depenses_par_carte = depenses_par_carte.sort_values("Date")
        # Format de la date sans l'heure pour l'affichage
        if pd.api.types.is_datetime64_any_dtype(depenses_par_carte["Date"]):
            depenses_par_carte["Date"] = depenses_par_carte["Date"].dt.strftime("%d/%m/%Y")
        total_depenses_carte = abs(depenses_par_carte["Montant"].sum())
        st.markdown(f"**Total des dépenses par carte : {total_depenses_carte:,.2f} €**")
        moyenne_journaliere = total_depenses_carte / 30.44
        st.markdown(
            f"<div class='sub'>Dépense moyenne quotidienne : {moyenne_journaliere:,.2f} €</div>",
            unsafe_allow_html=True,
        )
        # Style montant column: red for negatives, green for positives
        def color_montant(val):
            color = "red" if val < 0 else "green"
            return f"color: {color}"

        depenses_par_carte = depenses_par_carte.reset_index(drop=True)
        depenses_par_carte.index += 1
        styled_df = (
            depenses_par_carte[["Date", "Description", "Montant"]]
            .style.applymap(color_montant, subset=["Montant"])
            .format({"Montant": "{:+,.2f} €"})
        )
        st.dataframe(styled_df, use_container_width=True, height=460)

    # ----- 3. Visualisation -----
    with tab3:
        if df_filtered.empty:
            st.warning("Aucune transaction ne correspond aux filtres sélectionnés.")
        else:
            evolution = (
                df_filtered[df_filtered["Montant"] < 0]
                .groupby(df_filtered["Date"].dt.date)["Montant"]
                .sum()
                .abs()
                .reset_index()
            )
            evolution["Montant cumulé"] = evolution["Montant"].cumsum()
            fig = px.line(
                evolution,
                x="Date",
                y="Montant cumulé",
                markers=True,
                title="Évolution cumulée des dépenses dans le temps",
            )
            fig.update_layout(xaxis_title="Date", yaxis_title="Montant cumulé (€)")
            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Importez un relevé bancaire PDF pour démarrer l’analyse (étape 1).")
