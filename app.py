"""
Plan Financier — La Maison Verheyden (boulangerie-pâtisserie Liège).

Router Streamlit minimal. La logique métier vit dans core/.
"""

import base64
from pathlib import Path
import streamlit as st

from core import github_sync
from core.schema import params_defaut, valider_params
from core.persistence import (
    lister_plans, charger_plan, sauvegarder_plan,
    dupliquer_plan, supprimer_plan, sync_initial,
)
from views.accueil import render_accueil

ASSETS = Path(__file__).resolve().parent / "assets"


def _bandeau_image(chemin: Path, hauteur_px: int = 140):
    if not chemin.exists():
        return
    data = base64.b64encode(chemin.read_bytes()).decode("ascii")
    st.markdown(
        f"""<div style="width:100%; height:{hauteur_px}px;
            background-image:url('data:image/jpeg;base64,{data}');
            background-size:cover; background-position:center;
            border-radius:8px; margin-bottom:0.8rem;"></div>""",
        unsafe_allow_html=True,
    )


# ─── Configuration page ─────────────────────────────────────────────────────

st.set_page_config(
    page_title="Plan Financier — La Maison Verheyden",
    page_icon="🥐",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _code_edition() -> str:
    """Code d'édition lu depuis st.secrets, fallback dev = 'mpl2026'."""
    try:
        return st.secrets["CODE_EDITION"]
    except Exception:
        return "mpl2026"


# ─── État de session ────────────────────────────────────────────────────────

def _init_session():
    defaults = {
        "auth_edition": False,
        "plan_actif": None,
        "params_actifs": None,
        "mode_consultation": "Visualisation",
        "page": "accueil",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_session()
sync_initial()  # Pull plans depuis GitHub si configuré (idempotent)


# ─── Sidebar : auth + navigation + status sync ──────────────────────────────

def _sidebar():
    with st.sidebar:
        st.markdown("### 🥐 La Maison Verheyden")
        st.caption("Plan financier de démonstration — SConseil")

        # Status sync GitHub
        if github_sync.is_enabled():
            st.markdown(
                "<div style='font-size:0.82rem; color:#4A7C59;'>"
                "🟢 Sync GitHub active</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='font-size:0.82rem; color:#888;'>"
                "⚪ Mode local (pas de sync)</div>",
                unsafe_allow_html=True,
            )
        st.divider()

        # Auth
        if st.session_state["auth_edition"]:
            st.success("Mode édition actif")
            if st.button("Quitter le mode édition", width='stretch'):
                st.session_state["auth_edition"] = False
                st.rerun()
        else:
            with st.expander("🔐 Activer l'édition"):
                code = st.text_input("Code d'accès", type="password",
                                      key="code_input")
                if st.button("Connexion", width='stretch'):
                    if code == _code_edition():
                        st.session_state["auth_edition"] = True
                        st.rerun()
                    else:
                        st.error("Code incorrect")

        st.divider()

        # Navigation
        if st.session_state["plan_actif"]:
            st.markdown(f"**Plan actif** : `{st.session_state['plan_actif']}`")
            mode = st.radio(
                "Mode",
                options=["Visualisation", "Hypothèses"],
                index=0 if st.session_state["mode_consultation"] == "Visualisation" else 1,
                disabled=not st.session_state["auth_edition"]
                          and st.session_state["mode_consultation"] != "Hypothèses",
                help=("Le mode Hypothèses nécessite l'activation de l'édition."
                      if not st.session_state["auth_edition"] else None),
            )
            if mode == "Hypothèses" and not st.session_state["auth_edition"]:
                st.warning("Activez l'édition pour modifier les hypothèses.")
                mode = "Visualisation"
            st.session_state["mode_consultation"] = mode
            if st.button("← Retour à l'accueil", width='stretch'):
                st.session_state["page"] = "accueil"
                st.session_state["plan_actif"] = None
                st.session_state["params_actifs"] = None
                st.rerun()
        else:
            st.info("Aucun plan ouvert. Sélectionnez-en un dans la liste.")

        # Footer sidebar
        st.divider()
        st.markdown(
            "<div style='font-size:0.78rem; color:#888; text-align:center;'>"
            "Démo SConseil<br>romain@sconseil.be</div>",
            unsafe_allow_html=True,
        )


# ─── Page : plan ouvert ────────────────────────────────────────────────────

def render_plan_ouvert():
    p = st.session_state["params_actifs"]
    mode = st.session_state["mode_consultation"]

    nav_l, nav_r = st.columns([1, 5])
    with nav_l:
        if st.button("← Retour aux plans", width='stretch'):
            st.session_state["page"] = "accueil"
            st.session_state["plan_actif"] = None
            st.session_state["params_actifs"] = None
            st.rerun()
    with nav_r:
        st.markdown(
            f"<div style='text-align:right; color:#888; padding-top:0.4rem;'>"
            f"Mode : <strong style='color:#5C2E0F;'>{mode}</strong></div>",
            unsafe_allow_html=True,
        )

    _bandeau_image(ASSETS / "macarons.jpg", hauteur_px=140)

    st.markdown(
        f"<h1 style='font-family: Georgia, serif; color:#5C2E0F; "
        f"margin-top:0.5rem; margin-bottom:0;'>{p.get('nom_plan', 'Plan')}</h1>",
        unsafe_allow_html=True,
    )
    st.caption(f"{p.get('nom_entreprise')} · {p.get('ville')} · "
               f"Ouverture {p.get('date_ouverture')} · "
               f"Projection {p.get('nb_mois_projection')} mois")

    if mode == "Visualisation":
        from views.visualisation import render_dashboard
        render_dashboard(p)
    else:
        from views.hypotheses import render_hypotheses
        render_hypotheses(
            p,
            on_save_auto=_sauver_plan_local,
            on_save_explicit=_sauver_plan_complet,
        )


def _sauver_plan_local(params: dict):
    """Auto-save : local uniquement, ne push pas GitHub (évite le spam)."""
    nom = st.session_state["plan_actif"]
    if not nom:
        return
    sauvegarder_plan(nom, params, local_only=True)
    st.session_state["params_actifs"] = params


def _sauver_plan_complet(params: dict):
    """Sauvegarde explicite : local + push GitHub si configuré."""
    nom = st.session_state["plan_actif"]
    if not nom:
        return
    sauvegarder_plan(nom, params, local_only=False)
    st.session_state["params_actifs"] = params


# ─── Routeur principal ──────────────────────────────────────────────────────

def main():
    _sidebar()
    if st.session_state["page"] == "accueil" or not st.session_state["plan_actif"]:
        render_accueil(
            auth_edition=st.session_state["auth_edition"],
            on_open_plan=_ouvrir_plan,
            on_create_plan=_creer_plan,
            on_duplicate_plan=_dupliquer,
            on_delete_plan=_supprimer,
        )
    else:
        render_plan_ouvert()


def _ouvrir_plan(nom: str):
    p = charger_plan(nom)
    erreurs = valider_params(p)
    if erreurs:
        st.error("Plan invalide : " + " ; ".join(erreurs))
        return
    st.session_state["plan_actif"] = nom
    st.session_state["params_actifs"] = p
    st.session_state["page"] = "plan"
    st.rerun()


def _creer_plan(nouveau_nom: str):
    p = params_defaut()
    p["nom_plan"] = nouveau_nom
    sauvegarder_plan(nouveau_nom, p)
    _ouvrir_plan(nouveau_nom)


def _dupliquer(source: str, nouveau_nom: str):
    dupliquer_plan(source, nouveau_nom)
    st.toast(f"Plan dupliqué : {nouveau_nom}", icon="✅")
    st.rerun()


def _supprimer(nom: str):
    supprimer_plan(nom)
    st.toast(f"Plan supprimé : {nom}", icon="🗑️")
    st.rerun()


if __name__ == "__main__":
    main()
