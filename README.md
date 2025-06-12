# test2

This repository contains a Streamlit application.

## Requirements

Install the required packages:

```bash
pip install -r requirements.txt
```

This installs `streamlit`, `pandas`, `pymupdf` and `plotly`.

## Run locally

Launch the application with:

```bash
streamlit run appli.py
```

The application automatically filters transactions whose type contains the word
"carte" (case insensitive) to display card expenses only.

In the **Aperçu général** tab, the summary table now includes an additional
column showing the average amount per transaction. This value is left blank
when there is only a single transaction for a given description.

## Visualisation des dépenses

L'onglet **Visualisation** propose désormais deux modes :

- **Évolution cumulée** des dépenses au fil du temps
- **Dépenses par jour** pour voir les montants quotidiens

Un menu déroulant dans l'application permet de choisir la vue désirée.

## Deploy on share.streamlit.io

On share.streamlit.io, create a new deployment and set **appli.py** as the entry point. The platform will read `requirements.txt` to install the dependencies automatically.
