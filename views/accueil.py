"""
Page d'accueil : liste des plans avec actions ouvrir / créer / dupliquer / supprimer.
"""

import base64
from pathlib import Path
import streamlit as st
from typing import Callable

from core.persistence import lister_plans, charger_plan

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def _bandeau_image(chemin: Path, hauteur_px: int = 220):
    """Affiche une image en banner avec hauteur contrôlée (object-fit: cover)."""
    if not chemin.exists():
        return
    data = base64.b64encode(chemin.read_bytes()).decode("ascii")
    st.markdown(
        f"""
        <div style="
            width: 100%;
            height: {hauteur_px}px;
            background-image: url('data:image/jpeg;base64,{data}');
            background-size: cover;
            background-position: center;
            border-radius: 8px;
            margin-bottom: 1rem;
        "></div>
        """,
        unsafe_allow_html=True,
    )


def render_accueil(
    auth_edition: bool,
    on_open_plan: Callable[[str], None],
    on_create_plan: Callable[[str], None],
    on_duplicate_plan: Callable[[str, str], None],
    on_delete_plan: Callable[[str], None],
):
    # ── Hero image (bandeau hauteur contrôlée) ─────────────────────────────
    _bandeau_image(ASSETS / "hero_vitrine.jpg", hauteur_px=220)

    # ── Header ─────────────────────────────────────────────────────────────
    st.markdown(
        "<h1 style='font-family: Georgia, serif; color: #5C2E0F; "
        "margin-top: 0.5rem; margin-bottom: 0;'>La Maison Verheyden</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='font-size: 1.15rem; color: #6B4423; font-style: italic; "
        "margin-top: 0.2rem;'>Plan financier — Boulangerie-pâtisserie haut de gamme · Liège</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color: #555;'>Démonstration SConseil : modélisation d'une "
        "structure <strong>SRL Immobilière + SRL Exploitation</strong>, "
        "3 activités (boulangerie · pâtisserie · traiteur B2B), "
        "projection sur 5 ans.</p>",
        unsafe_allow_html=True,
    )

    # ── Galerie des 3 activités ────────────────────────────────────────────
    photos_galerie = [
        ("pain.jpg", "Boulangerie", "Pain artisanal et viennoiserie"),
        ("patisserie.jpg", "Pâtisserie", "Créations sur mesure"),
        ("atelier.jpg", "Traiteur B2B", "Cafés, hôtels et bureaux"),
    ]
    cols = st.columns(3)
    for col, (img, titre, sous_titre) in zip(cols, photos_galerie):
        with col:
            chemin = ASSETS / img
            if chemin.exists():
                st.image(str(chemin), width='stretch')
            st.markdown(
                f"<p style='text-align:center; margin-top:0.3rem;'>"
                f"<strong style='color:#5C2E0F;'>{titre}</strong><br>"
                f"<span style='color:#888; font-size:0.9rem;'>{sous_titre}</span></p>",
                unsafe_allow_html=True,
            )
    st.divider()

    # ── Liste des plans ────────────────────────────────────────────────────
    plans = lister_plans()

    col_main, col_actions = st.columns([3, 2], gap="large")

    with col_main:
        st.subheader("📂 Plans disponibles")
        if not plans:
            st.info("Aucun plan enregistré pour le moment. "
                    "Créez-en un pour démarrer.")
        else:
            for nom in plans:
                _render_carte_plan(nom, auth_edition, on_open_plan,
                                    on_duplicate_plan, on_delete_plan)

    with col_actions:
        if auth_edition:
            st.subheader("➕ Créer un nouveau plan")
            nouveau_nom = st.text_input("Nom du plan", key="creer_nom",
                                         placeholder="Ex. Scénario optimiste")
            if st.button("Créer", type="primary", width='stretch',
                         disabled=not nouveau_nom):
                if nouveau_nom in plans:
                    st.error("Un plan portant ce nom existe déjà.")
                else:
                    on_create_plan(nouveau_nom)
        else:
            st.info(
                "🔐 Activez le mode édition (sidebar) pour créer ou modifier "
                "des plans.\n\nEn mode lecture, vous pouvez ouvrir un plan "
                "existant pour visualiser sa projection."
            )


def _render_carte_plan(nom: str, auth_edition: bool,
                        on_open: Callable, on_dup: Callable, on_del: Callable):
    """Affiche une carte par plan avec ses méta + boutons d'action."""
    try:
        p = charger_plan(nom)
        meta_line = (f"{p.get('nom_entreprise', '?')} · "
                     f"{p.get('ville', '?')} · "
                     f"{p.get('nb_mois_projection', 0)} mois")
    except Exception as e:
        meta_line = f"⚠️ Erreur de lecture : {e}"
        p = None

    with st.container(border=True):
        c1, c2 = st.columns([4, 2])
        with c1:
            st.markdown(f"**{nom}**")
            st.caption(meta_line)
        with c2:
            if st.button("Ouvrir", key=f"open_{nom}", width='stretch'):
                on_open(nom)
            if auth_edition:
                with st.popover("Plus", width='stretch'):
                    nouveau = st.text_input("Dupliquer en :", key=f"dup_{nom}",
                                             value=f"{nom} (copie)")
                    if st.button("Dupliquer", key=f"dupbtn_{nom}",
                                  width='stretch'):
                        on_dup(nom, nouveau)
                    st.divider()
                    if st.button("🗑️ Supprimer", key=f"del_{nom}",
                                  width='stretch', type="secondary"):
                        on_del(nom)
