"""
Manuel d'utilisation — version courte pour démo client.

Page accessible via le bouton « 📖 Manuel » dans la sidebar.
"""

import streamlit as st


def render_manuel(on_retour):
    # Header
    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Retour", width='stretch'):
            on_retour()

    st.markdown(
        "<h1 style='font-family: Georgia, serif; color:#5C2E0F; "
        "margin-top:0.5rem; margin-bottom:0;'>📖 Manuel d'utilisation</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='font-size:1.05rem; color:#6B4423; font-style:italic; "
        "margin-top:0.2rem;'>Prise en main en 5 minutes</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── 1. À quoi sert l'application ────────────────────────────────────────
    st.markdown(
        "<h2 style='font-family: Georgia, serif; color:#5C2E0F;'>"
        "🎯 À quoi ça sert</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Cette application modélise le **plan financier sur 5 ans** d'une "
        "boulangerie-pâtisserie fictive (La Maison Verheyden, Liège), "
        "structurée en deux SRL belges : une **SRL Immobilière** qui détient "
        "l'immeuble et une **SRL Exploitation** qui opère les 3 activités "
        "(boulangerie · pâtisserie · traiteur B2B).\n\n"
        "Vous pouvez **modifier n'importe quelle hypothèse** (prix de vente, "
        "volumes, salaires, prêts, loyer…) et voir **immédiatement l'impact** "
        "sur le compte de résultat, la trésorerie et les ratios."
    )

    # ── 2. Ouvrir un plan ────────────────────────────────────────────────────
    st.markdown(
        "<h2 style='font-family: Georgia, serif; color:#5C2E0F;'>"
        "📂 Ouvrir un plan</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Sur la **page d'accueil**, choisissez un plan dans la liste et "
        "cliquez sur **Ouvrir**. Vous arrivez en mode **Visualisation** : "
        "dashboard, graphiques P&L, trésorerie cumulée, ratios par année."
    )

    # ── 3. Modifier une hypothèse ────────────────────────────────────────────
    st.markdown(
        "<h2 style='font-family: Georgia, serif; color:#5C2E0F;'>"
        "✏️ Modifier une hypothèse</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "1. Dans la **sidebar (à gauche)**, dépliez « 🔐 Activer l'édition » "
        "et entrez le code d'accès.\n"
        "2. Le mode **Hypothèses** devient disponible — basculez-y via le "
        "sélecteur de la sidebar.\n"
        "3. Modifiez la valeur souhaitée (chiffre d'affaires, masse salariale, "
        "prêt, etc.). L'**auto-save local** se déclenche à chaque changement.\n"
        "4. Repassez en mode **Visualisation** pour voir l'impact sur les "
        "graphiques et indicateurs."
    )
    st.info(
        "💡 Pour une démo : un seul changement bien choisi (ex. +10 % de prix "
        "de vente pâtisserie) suffit à illustrer la réactivité du modèle.",
        icon="💡",
    )

    # ── 4. Exporter ──────────────────────────────────────────────────────────
    st.markdown(
        "<h2 style='font-family: Georgia, serif; color:#5C2E0F;'>"
        "📤 Exporter</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Dans le dashboard, le bouton **Télécharger HTML** génère un rapport "
        "complet, autonome, partageable par mail. Pas besoin d'installer "
        "quoi que ce soit côté destinataire : il suffit d'ouvrir le fichier "
        "dans un navigateur."
    )

    st.divider()
    st.markdown(
        "<p style='text-align:center; color:#888; font-size:0.9rem;'>"
        "Une question ? <strong>romain@sconseil.be</strong></p>",
        unsafe_allow_html=True,
    )
