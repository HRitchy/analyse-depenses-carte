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

## Visualisation des dépenses

Un onglet **Visualisation** affiche l'évolution cumulée des dépenses par carte
dans le temps à l'aide d'un graphique interactif.

## Deploy on share.streamlit.io

On share.streamlit.io, create a new deployment and set **appli.py** as the entry point. The platform will read `requirements.txt` to install the dependencies automatically.
