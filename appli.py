import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import plotly.express as px

st.set_page_config(
    page_title="Analyse de Relevé Bancaire",
    page_icon="💳",
    layout="wide"
)

# --- CSS moderne pour titres et métriques ---
st.markdown("""
    <style>
    .big-metric { font-size: 2rem; font-weight: 700; }
    .sub { color: #888; font-size: 1rem; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("<h1 style='margin-bottom:0;'>Analyse automatique de votre relevé bancaire</h1>", unsafe_allow_html=True)
st.markdown("<div class='sub'>Importez un relevé PDF pour visualiser vos transactions, dépenses par catégorie et suivre votre solde.</div>", unsafe_allow_html=True)

# --- UPLOAD ---
with st.sidebar:
    st.header("🗂 Import du relevé")
    uploaded_file = st.file_uploader("Choisissez un relevé de compte (PDF)", type=["pdf"])
    st.info("L'analyse fonctionne sur la plupart des relevés PDF français classiques.")

@st.cache_data(show_spinner=False)
def parse_pdf(file_bytes):
    try:
        pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        return None, f"Erreur lors de la lecture du PDF: {e}"
    transactions = []
    for page_index in range(pdf_doc.page_count):
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

def classify_transaction(type_text, desc_text, amount):
    text = f"{type_text} {desc_text}".lower()
    categ = "Autre"
    if any(word in text for word in ["restaur", "pizza", "caf", "bar", "supermarch", "carrefour", "intermarch", "u express"]):
        categ = "Alimentation"
    elif any(word in text for word in ["station", "essence", "fuel", "gaz", "carburant", "engen", "total", "avia", "bus", "transport", "uber", "taxi"]):
        categ = "Transport"
    elif any(word in text for word in ["cin", "cinema", "netflix", "spotify", "loisir", "loisirs", "jeu", "steam", "concert", "voyage", "vacance"]):
        categ = "Loisirs"
    elif any(word in text for word in ["exécution d'ordre", "savings plan", "achat", "etf", "bourse", "invest"]):
        categ = "Investissement"
    elif any(word in text for word in ["virement", "transf", "transfer"]):
        categ = "Transfert"
    elif amount > 0 and any(word in text for word in ["intérêt", "interest", "remboursement", "salaire", "revenu", "crédit"]):
        categ = "Revenu"
    elif amount > 0 and categ == "Autre":
        categ = "Revenu"
    return categ

# ----------- MAIN APP UI ----------------

if uploaded_file:
    with st.spinner("Analyse en cours..."):
        file_bytes = uploaded_file.read()
        df, err = parse_pdf(file_bytes)
    if err or df is None or df.empty:
        st.error(err or "Aucune transaction trouvée. Format PDF non supporté.")
        st.stop()
    # Format dates
    if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df = df.dropna(subset=["Date"])
    df["Catégorie"] = df.apply(lambda row: classify_transaction(row["Type"], row["Description"], row["Montant"]), axis=1)
    df = df.sort_values(by="Date").reset_index(drop=True)

    # ------ Filtres classiques ------
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtres rapides")
    min_date, max_date = df["Date"].min(), df["Date"].max()
    date_range = st.sidebar.date_input(
        "Période",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    categories = sorted(df["Catégorie"].unique())
    selected_cats = st.sidebar.multiselect("Catégories", categories, default=categories)
    search_txt = st.sidebar.text_input("Recherche dans description", "")

    mask = (
        (df["Date"] >= pd.to_datetime(date_range[0])) &
        (df["Date"] <= pd.to_datetime(date_range[1])) &
        (df["Catégorie"].isin(selected_cats)) &
        (df["Description"].str.lower().str.contains(search_txt.lower()))
    )
    df_filtered = df[mask].copy().reset_index(drop=True)

    # --------- Onglets principaux ---------
    tab1, tab2, tab3 = st.tabs(
        ["🏠 Aperçu général", "💳 Transactions", "📊 Visualisations"]
    )

    # ----- 1. Aperçu général -----
    with tab1:
        st.subheader("Synthèse de la période")
        col1, col2, col3 = st.columns(3)
        total_dep = df_filtered[df_filtered["Montant"] < 0]["Montant"].sum()
        total_rev = df_filtered[df_filtered["Montant"] > 0]["Montant"].sum()
        solde_fin = (
            df_filtered["Solde"].dropna().iloc[-1]
            if df_filtered["Solde"].notna().any()
            else df_filtered["Montant"].cumsum().iloc[-1]
        )
        with col1:
            st.metric("Total dépenses", f"{abs(total_dep):,.2f} €", delta=None)
        with col2:
            st.metric("Total revenus", f"{total_rev:,.2f} €", delta=None)
        with col3:
            st.metric("Solde final", f"{solde_fin:,.2f} €", delta=None)

        # Résumé par catégorie (tableau compact)
        st.markdown("**Dépenses par catégorie**")
        resume = (
            df_filtered[df_filtered["Montant"] < 0]
            .groupby("Catégorie")["Montant"]
            .sum()
            .abs()
            .sort_values(ascending=False)
            .reset_index()
        )
        st.dataframe(resume, use_container_width=True, height=180)

    # ----- 2. Transactions -----
    with tab2:
        st.subheader("Liste détaillée des transactions filtrées")
        st.caption("Vous pouvez trier les colonnes et faire défiler le tableau.")
        st.dataframe(
            df_filtered[["Date", "Type", "Description", "Montant", "Solde", "Catégorie"]],
            use_container_width=True,
            height=430
        )

    # ----- 3. Visualisations -----
    with tab3:
        st.subheader("Répartition des dépenses par catégorie")
        depenses = df_filtered[df_filtered["Montant"] < 0].copy()
        if depenses.empty:
            st.warning("Aucune dépense détectée sur la période.")
        else:
            fig = px.pie(
                depenses,
                names="Catégorie",
                values=abs(depenses["Montant"]),
                title="Dépenses par catégorie",
                hole=0.4
            )
            fig.update_traces(textinfo="percent+label", pull=[0.05]*len(depenses["Catégorie"].unique()))
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Évolution du solde du compte")
        df_solde = df_filtered.copy()
        df_solde = df_solde.sort_values("Date").dropna(subset=["Solde"])
        if not df_solde.empty:
            fig2 = px.line(
                df_solde, x="Date", y="Solde", markers=True,
                title="Solde du compte (€)",
                template="plotly_white"
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Solde non disponible sur ce relevé.")

    st.markdown(
        "<div style='text-align:right;font-size:0.95rem;color:#888;'>Thème clair/sombre auto selon vos préférences système (voir Paramètres Streamlit).</div>",
        unsafe_allow_html=True
    )

else:
    st.info("Veuillez importer un relevé bancaire au format PDF pour démarrer l’analyse.")
