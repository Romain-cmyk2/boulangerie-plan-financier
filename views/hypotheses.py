"""
Page d'hypothèses : édition de tous les paramètres avec aperçu KPIs temps réel.

Structure :
  - Bandeau KPIs en haut (recalculé à chaque interaction)
  - 5 onglets : Ventes / Charges / Personnel / Investissements / Financement
  - Auto-save sur chaque modification (debounced via hash)
"""

import hashlib
import json
from typing import Callable

import pandas as pd
import streamlit as st

from core.calculs import projection_complete
from core.indicateurs import synthese_globale
from core.style import format_eur, format_eur_compact, COULEUR_FONCEE, COULEUR_PRIMAIRE


# ─── Aperçu KPIs en haut ────────────────────────────────────────────────────

def _apercu_kpis(params: dict):
    """Bandeau KPI sticky en haut de la page."""
    try:
        proj = projection_complete(params)
        synth = synthese_globale(proj)
    except Exception as e:
        st.error(f"Erreur de calcul : {e}")
        return

    st.markdown(
        "<h4 style='font-family: Georgia, serif; color:#5C2E0F; "
        "margin-top:0; margin-bottom:0.4rem;'>📊 Aperçu en temps réel</h4>",
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("CA An 1", format_eur_compact(synth["ca_an1"]))
    c2.metric("CA An 5", format_eur_compact(synth["ca_an5"]))
    c3.metric("EBITDA An 5", format_eur_compact(synth["ebitda_an5"]))
    c4.metric("Résultat net cumulé", format_eur_compact(synth["resultat_net_cumule"]))
    c5.metric("Cash fin de période", format_eur_compact(synth["cash_fin_periode"]))


# ─── Helpers ────────────────────────────────────────────────────────────────

def _hash_params(p: dict) -> str:
    """Empreinte stable du dict params (pour détecter les modifs)."""
    s = json.dumps(p, default=str, sort_keys=True)
    return hashlib.md5(s.encode()).hexdigest()


def _slider_pct(label: str, valeur: float, min_v: float = -10.0,
                 max_v: float = 30.0, step: float = 0.5,
                 key: str = None) -> float:
    """Slider qui édite un pourcentage (entrée et sortie en décimal)."""
    pct = st.slider(label, min_value=min_v, max_value=max_v,
                     value=round(valeur * 100, 1), step=step,
                     key=key, format="%.1f %%")
    return pct / 100


# ─── Onglet 1 : Ventes ──────────────────────────────────────────────────────

def _editeur_ventes(params: dict):
    """3 colonnes pour les 3 activités + saisonnalité en expander."""
    st.caption("Modifiez les leviers de chiffre d'affaires par activité. "
               "Les variations se voient instantanément dans l'aperçu en haut.")

    col_b, col_p, col_t = st.columns(3, gap="medium")

    # ── Boulangerie ────────────────────────────────────────────────────────
    with col_b:
        st.markdown("##### 🥖 Boulangerie")
        b = params["boulangerie"]
        b["tickets_jour_an1"] = st.number_input(
            "Tickets / jour (An 1)", min_value=0, max_value=2000,
            value=int(b["tickets_jour_an1"]), step=10,
            key="b_tickets",
        )
        b["panier_moyen_an1"] = st.number_input(
            "Panier moyen (€)", min_value=0.0, max_value=100.0,
            value=float(b["panier_moyen_an1"]), step=0.5, format="%.2f",
            key="b_panier",
        )
        b["jours_ouverture_semaine"] = st.number_input(
            "Jours d'ouverture / semaine", min_value=1, max_value=7,
            value=int(b["jours_ouverture_semaine"]), step=1,
            key="b_jours",
        )
        # Croissance & hausse prix : un seul curseur appliqué à An 2-5
        croiss_b = _slider_pct("Croissance volumes / an (An 2-5)",
                                b["croissance_volumes"][1], 0.0, 15.0, 0.5,
                                key="b_croiss")
        b["croissance_volumes"] = [0.0] + [croiss_b] * 4
        hausse_b = _slider_pct("Hausse prix / an", b["hausse_prix"][1],
                                0.0, 10.0, 0.25, key="b_hausse")
        b["hausse_prix"] = [0.0] + [hausse_b] * 4

    # ── Pâtisserie ────────────────────────────────────────────────────────
    with col_p:
        st.markdown("##### 🧁 Pâtisserie")
        pa = params["patisserie"]
        pa["tickets_jour_an1"] = st.number_input(
            "Tickets / jour (An 1)", min_value=0, max_value=500,
            value=int(pa["tickets_jour_an1"]), step=5,
            key="p_tickets",
        )
        pa["panier_moyen_an1"] = st.number_input(
            "Panier moyen (€)", min_value=0.0, max_value=200.0,
            value=float(pa["panier_moyen_an1"]), step=1.0, format="%.2f",
            key="p_panier",
        )
        pa["jours_ouverture_semaine"] = st.number_input(
            "Jours d'ouverture / semaine", min_value=1, max_value=7,
            value=int(pa["jours_ouverture_semaine"]), step=1,
            key="p_jours",
        )
        croiss_p = _slider_pct("Croissance volumes / an (An 2-5)",
                                pa["croissance_volumes"][1], 0.0, 15.0, 0.5,
                                key="p_croiss")
        pa["croissance_volumes"] = [0.0] + [croiss_p] * 4
        hausse_p = _slider_pct("Hausse prix / an", pa["hausse_prix"][1],
                                0.0, 10.0, 0.25, key="p_hausse")
        pa["hausse_prix"] = [0.0] + [hausse_p] * 4

    # ── Traiteur B2B ──────────────────────────────────────────────────────
    with col_t:
        st.markdown("##### 🚚 Traiteur B2B")
        t = params["traiteur_b2b"]
        t["nb_clients_an1"] = st.number_input(
            "Nb clients réguliers (An 1)", min_value=0, max_value=200,
            value=int(t["nb_clients_an1"]), step=1,
            key="t_clients",
        )
        t["panier_mensuel_an1"] = st.number_input(
            "Panier mensuel / client (€)", min_value=0, max_value=10_000,
            value=int(t["panier_mensuel_an1"]), step=50,
            key="t_panier",
        )
        st.caption("Acquisition de nouveaux clients par an :")
        cols = st.columns(5)
        nouveaux = list(t["nouveaux_clients_par_an"])
        for i, c in enumerate(cols):
            with c:
                nouveaux[i] = st.number_input(
                    f"An {i + 1}", min_value=0, max_value=50,
                    value=int(nouveaux[i]) if i < len(nouveaux) else 0,
                    step=1, key=f"t_nouv_{i}", label_visibility="visible",
                )
        t["nouveaux_clients_par_an"] = nouveaux
        hausse_t = _slider_pct("Hausse prix / an", t["hausse_prix"][1],
                                0.0, 10.0, 0.25, key="t_hausse")
        t["hausse_prix"] = [0.0] + [hausse_t] * 4

    # ── Saisonnalité (expander) ───────────────────────────────────────────
    with st.expander("📅 Saisonnalité mensuelle (avancé)"):
        st.caption("Coefficient appliqué chaque mois (1.00 = neutre, 1.50 = +50 %, "
                   "0.80 = -20 %).")
        mois_lbls = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
                     "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]
        df_sais = pd.DataFrame({
            "Mois": mois_lbls,
            "Boulangerie": params["boulangerie"]["saisonnalite"],
            "Pâtisserie": params["patisserie"]["saisonnalite"],
            "Traiteur B2B": params["traiteur_b2b"]["saisonnalite"],
        })
        edited = st.data_editor(
            df_sais, width='stretch', hide_index=True,
            key="sais_editor",
            disabled=["Mois"],
            column_config={
                "Boulangerie": st.column_config.NumberColumn(
                    format="%.2f", min_value=0.0, max_value=3.0, step=0.05),
                "Pâtisserie": st.column_config.NumberColumn(
                    format="%.2f", min_value=0.0, max_value=3.0, step=0.05),
                "Traiteur B2B": st.column_config.NumberColumn(
                    format="%.2f", min_value=0.0, max_value=3.0, step=0.05),
            },
        )
        params["boulangerie"]["saisonnalite"] = edited["Boulangerie"].tolist()
        params["patisserie"]["saisonnalite"] = edited["Pâtisserie"].tolist()
        params["traiteur_b2b"]["saisonnalite"] = edited["Traiteur B2B"].tolist()


# ─── Onglet 2 : Charges ────────────────────────────────────────────────────

def _editeur_charges(params: dict):
    st.caption("Charges variables (en % du CA HT par activité) et charges fixes "
               "indirectes (montants mensuels).")

    # ── Charges variables ─────────────────────────────────────────────────
    st.markdown("##### Charges variables — % du CA")
    cv = params["charges_variables"]
    col_b, col_p, col_t = st.columns(3, gap="medium")
    for col, (act_key, titre) in zip(
        [col_b, col_p, col_t],
        [("boulangerie", "🥖 Boulangerie"),
         ("patisserie", "🧁 Pâtisserie"),
         ("traiteur_b2b", "🚚 Traiteur B2B")]
    ):
        with col:
            st.markdown(f"**{titre}**")
            for poste in list(cv[act_key].keys()):
                cv[act_key][poste] = _slider_pct(
                    poste.replace("_", " ").capitalize(),
                    cv[act_key][poste], 0.0, 60.0, 0.5,
                    key=f"cv_{act_key}_{poste}",
                )
            total = sum(cv[act_key].values()) * 100
            st.caption(f"**Total CV : {total:.1f} % du CA**")

    st.divider()

    # ── Charges fixes indirectes ──────────────────────────────────────────
    st.markdown("##### Charges fixes indirectes — montants mensuels HT")
    cfi = params["charges_fixes_indirectes"]
    cols = st.columns(3, gap="medium")
    keys = list(cfi.keys())
    for i, key in enumerate(keys):
        with cols[i % 3]:
            cfi[key] = st.number_input(
                key.replace("_", " ").capitalize(),
                min_value=0, max_value=100_000,
                value=int(cfi[key]), step=50,
                key=f"cfi_{key}",
            )
    st.divider()
    params["inflation_charges"] = _slider_pct(
        "Inflation annuelle des charges fixes",
        params["inflation_charges"], 0.0, 10.0, 0.25,
        key="inflation",
    )


# ─── Onglet 3 : Personnel ──────────────────────────────────────────────────

def _editeur_personnel(params: dict):
    st.caption("Personnel chargé — règles belges : pécule de vacances en juillet "
               "(92 % du brut) + 13e mois en décembre, charges patronales ONSS.")

    params["onss_patronal"] = _slider_pct(
        "Taux ONSS patronal moyen", params["onss_patronal"],
        15.0, 35.0, 0.5, key="onss",
    )

    st.divider()
    st.markdown("##### Personnel de production (charges fixes directes)")

    col_cfg = {
        "poste": st.column_config.TextColumn("Poste", required=True),
        "brut_mensuel": st.column_config.NumberColumn(
            "Brut mensuel (€)", format="%d", min_value=0, max_value=20_000, step=100),
        "nb": st.column_config.NumberColumn(
            "Nb personnes", format="%d", min_value=0, max_value=20, step=1),
        "mois_embauche": st.column_config.NumberColumn(
            "Mois d'embauche", format="%d", min_value=1, max_value=60, step=1,
            help="Mois de la projection (1 = mois 1, 12 = mois 12, etc.)"),
    }

    df_prod = pd.DataFrame(params["personnel_production"])
    edited_prod = st.data_editor(
        df_prod, width='stretch', hide_index=True, num_rows="dynamic",
        column_config=col_cfg, key="perso_prod_editor",
    )
    params["personnel_production"] = edited_prod.to_dict("records")

    st.divider()
    st.markdown("##### Personnel administration & vente (charges fixes indirectes)")
    df_admin = pd.DataFrame(params["personnel_admin"])
    edited_admin = st.data_editor(
        df_admin, width='stretch', hide_index=True, num_rows="dynamic",
        column_config=col_cfg, key="perso_admin_editor",
    )
    params["personnel_admin"] = edited_admin.to_dict("records")


# ─── Onglet 4 : Investissements ────────────────────────────────────────────

def _editeur_invest(params: dict):
    st.caption("Investissements répartis entre la SRL Immobilière (bâtiment) et "
               "la SRL Exploitation (matériel & aménagement). "
               "Amortissement linéaire sur la durée fiscale indiquée.")

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        params["apports"]["immo"] = st.number_input(
            "Apport en capital — SRL Immobilière (€)",
            min_value=0, max_value=5_000_000,
            value=int(params["apports"]["immo"]), step=10_000,
            key="apport_immo",
        )
    with col2:
        params["apports"]["exploit"] = st.number_input(
            "Apport en capital — SRL Exploitation (€)",
            min_value=0, max_value=5_000_000,
            value=int(params["apports"]["exploit"]), step=5_000,
            key="apport_exploit",
        )

    st.divider()

    col_cfg_inv = {
        "poste": st.column_config.TextColumn("Poste"),
        "montant": st.column_config.NumberColumn(
            "Montant (€)", format="%d", min_value=0),
        "amort_annees": st.column_config.NumberColumn(
            "Amort. (années)", format="%d", min_value=0, max_value=50, step=1,
            help="0 = non amortissable (ex. terrain)"),
        "entite": st.column_config.SelectboxColumn(
            "Entité", options=["immo", "exploit"]),
    }

    st.markdown("##### 🏛️ Investissements SRL Immobilière")
    df_immo = pd.DataFrame(params["investissements_immo"])
    edited_immo = st.data_editor(
        df_immo, width='stretch', hide_index=True, num_rows="dynamic",
        column_config=col_cfg_inv, key="inv_immo_editor",
    )
    # Forcer l'entité
    records = edited_immo.to_dict("records")
    for r in records:
        r["entite"] = "immo"
    params["investissements_immo"] = records

    st.markdown("##### 🥖 Investissements SRL Exploitation")
    df_exp = pd.DataFrame(params["investissements_exploit"])
    edited_exp = st.data_editor(
        df_exp, width='stretch', hide_index=True, num_rows="dynamic",
        column_config=col_cfg_inv, key="inv_exp_editor",
    )
    records = edited_exp.to_dict("records")
    for r in records:
        r["entite"] = "exploit"
    params["investissements_exploit"] = records


# ─── Onglet 5 : Financement ────────────────────────────────────────────────

def _editeur_financement(params: dict):
    st.caption("Prêts en mensualité constante. La clé `id` est fixe et ne doit "
               "pas être modifiée (évite les doublons).")

    col_cfg = {
        "id": st.column_config.NumberColumn("ID", format="%d", disabled=True),
        "entite": st.column_config.SelectboxColumn(
            "Entité", options=["immo", "exploit"]),
        "libelle": st.column_config.TextColumn("Libellé"),
        "montant": st.column_config.NumberColumn(
            "Montant (€)", format="%d", min_value=0),
        "duree_annees": st.column_config.NumberColumn(
            "Durée (ans)", format="%d", min_value=1, max_value=40, step=1),
        "taux_annuel": st.column_config.NumberColumn(
            "Taux annuel", format="%.3f", min_value=0.0, max_value=0.20, step=0.001,
            help="Décimal : 0.040 = 4 %"),
        "type": st.column_config.SelectboxColumn(
            "Type", options=["mensualite_constante"]),
        "mois_debut": st.column_config.NumberColumn(
            "Mois début", format="%d", min_value=1, max_value=60, step=1),
    }

    df = pd.DataFrame(params["prets"])
    edited = st.data_editor(
        df, width='stretch', hide_index=True, num_rows="dynamic",
        column_config=col_cfg, key="prets_editor",
    )
    # Réattribuer un id stable et incrémental
    records = edited.to_dict("records")
    for i, r in enumerate(records):
        r["id"] = i
        if "type" not in r or not r["type"]:
            r["type"] = "mensualite_constante"
    params["prets"] = records

    st.divider()
    st.markdown("##### 🇧🇪 Fiscalité (Belgique)")
    fisc = params["fiscalite"]
    cols = st.columns(3, gap="medium")
    with cols[0]:
        fisc["isoc_taux_pme"] = _slider_pct(
            "Taux ISOC PME (1ère tranche)", fisc["isoc_taux_pme"],
            10.0, 35.0, 0.5, key="isoc_pme",
        )
    with cols[1]:
        fisc["isoc_seuil_pme"] = st.number_input(
            "Seuil tranche PME (€)", min_value=0, max_value=500_000,
            value=int(fisc["isoc_seuil_pme"]), step=10_000,
            key="isoc_seuil",
        )
    with cols[2]:
        fisc["isoc_taux_standard"] = _slider_pct(
            "Taux ISOC standard", fisc["isoc_taux_standard"],
            10.0, 40.0, 0.5, key="isoc_std",
        )

    fisc["precompte_immobilier_annuel"] = st.number_input(
        "Précompte immobilier annuel (SRL Immo, €)",
        min_value=0, max_value=100_000,
        value=int(fisc["precompte_immobilier_annuel"]), step=100,
        key="precompte",
    )


# ─── Entrée principale ─────────────────────────────────────────────────────

def render_hypotheses(params: dict,
                       on_save_auto: Callable[[dict], None],
                       on_save_explicit: Callable[[dict], None]):
    """
    Affiche la page d'hypothèses avec aperçu KPIs en haut + 5 tabs.

    on_save_auto      : appelé après chaque interaction (local-only,
                        évite de spammer GitHub).
    on_save_explicit  : appelé sur clic du bouton « Sauvegarder »
                        (force la sync GitHub si activée).
    """
    # ── Aperçu KPIs ────────────────────────────────────────────────────────
    _apercu_kpis(params)
    st.divider()

    # ── Snapshot avant édition pour détecter changements ───────────────────
    hash_avant = _hash_params(params)

    # ── Tabs d'édition ─────────────────────────────────────────────────────
    tabs = st.tabs([
        "🛒 Ventes", "💸 Charges", "👥 Personnel",
        "🏗️ Investissements", "🏦 Financement",
    ])
    with tabs[0]:
        _editeur_ventes(params)
    with tabs[1]:
        _editeur_charges(params)
    with tabs[2]:
        _editeur_personnel(params)
    with tabs[3]:
        _editeur_invest(params)
    with tabs[4]:
        _editeur_financement(params)

    # ── Auto-save local si modification détectée ──────────────────────────
    hash_apres = _hash_params(params)
    if hash_avant != hash_apres:
        try:
            on_save_auto(params)
            st.toast("Sauvegarde automatique ✓", icon="💾")
        except Exception as e:
            st.error(f"Échec sauvegarde : {e}")

    # ── Bandeau actions en bas ────────────────────────────────────────────
    st.divider()
    col_l, col_m, col_r = st.columns([2, 2, 6])
    with col_l:
        if st.button("💾 Sauvegarder + Sync", type="primary", width='stretch',
                     help="Sauvegarde locale + push GitHub si configuré"):
            try:
                on_save_explicit(params)
                st.toast("Plan sauvegardé ✓", icon="✅")
            except Exception as e:
                st.error(f"Échec : {e}")
    with col_m:
        if st.button("🔄 Réinitialiser", width='stretch',
                     help="Restaure les hypothèses par défaut"):
            from core.schema import params_defaut
            defaut = params_defaut()
            defaut["nom_plan"] = params["nom_plan"]
            for k, v in defaut.items():
                params[k] = v
            on_save_explicit(params)
            st.toast("Hypothèses réinitialisées", icon="🔄")
            st.rerun()
