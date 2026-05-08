"""
Dashboard de visualisation — La Maison Verheyden.

Sections :
  1. Hero KPIs
  2. Trajectoire (CA, EBITDA, Résultat net annuels)
  3. Mix CA par activité + saisonnalité An 1
  4. Cascade P&L An 5 (waterfall)
  5. Structure des coûts mensuelle (stacked area)
  6. Cash cumulé + service de la dette
  7. P&L par entité
  8. Détails dans expanders
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from core.calculs import projection_complete
from core.indicateurs import kpi_annuels, synthese_globale
from core.style import (
    appliquer_theme, format_eur, format_eur_compact, format_pct,
    COULEUR_PRIMAIRE, COULEUR_FONCEE, COULEUR_SECONDAIRE, COULEUR_DOREE,
    COULEUR_POSITIF, COULEUR_NEGATIF, COULEUR_TOTAL,
    COULEUR_ACT, COULEUR_IMMO, COULEUR_EXPLOIT,
)


# ─── Entrée principale ──────────────────────────────────────────────────────

def render_dashboard(params: dict):
    with st.spinner("Calcul de la projection..."):
        proj = projection_complete(params)

    _bandeau_exports(params)
    _section_kpis_hero(proj)
    st.divider()
    _section_trajectoire(proj)
    st.divider()
    _section_mix_saisonnalite(proj, params)
    st.divider()
    _section_cascade_pl_an5(proj)
    st.divider()
    _section_structure_couts(proj)
    st.divider()
    _section_cash_dette(proj, params)
    st.divider()
    _section_par_entite(proj)
    st.divider()
    _section_details(proj, params)


# ─── Bandeau exports ───────────────────────────────────────────────────────

def _bandeau_exports(params: dict):
    """Bandeau de boutons d'export en haut du dashboard."""
    from datetime import datetime
    from exports.html import generer_html

    nom_plan = params.get("nom_plan", "Plan")
    horodatage = datetime.now().strftime("%Y%m%d_%H%M")
    nom_fichier_base = f"{nom_plan}_{horodatage}".replace(" ", "_")

    col_html, col_pdf, col_pptx, col_xlsx, col_spacer = st.columns([2, 2, 2, 2, 4])

    with col_html:
        if st.button("📄 Préparer export HTML", width='stretch'):
            with st.spinner("Génération HTML..."):
                html = generer_html(params)
                st.session_state["_html_export"] = html
                st.session_state["_html_export_filename"] = f"{nom_fichier_base}.html"

    if st.session_state.get("_html_export"):
        with col_html:
            st.download_button(
                label="⬇️ Télécharger HTML",
                data=st.session_state["_html_export"],
                file_name=st.session_state.get(
                    "_html_export_filename", "plan_financier.html"
                ),
                mime="text/html",
                width='stretch',
                type="primary",
            )

    with col_pdf:
        st.button("📕 PDF", width='stretch', disabled=True,
                  help="Phase 4b — à venir")
    with col_pptx:
        st.button("📊 PowerPoint", width='stretch', disabled=True,
                  help="Phase 4b — à venir")
    with col_xlsx:
        st.button("📗 Excel", width='stretch', disabled=True,
                  help="Phase 4b — à venir")


# ─── 1. Hero KPIs ───────────────────────────────────────────────────────────

def _section_kpis_hero(proj: dict):
    synth = synthese_globale(proj)
    st.markdown(
        "<h3 style='font-family: Georgia, serif; color:#5C2E0F; "
        "margin-bottom:0.2rem;'>Indicateurs clés</h3>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("CA An 1", format_eur_compact(synth["ca_an1"]))
    c2.metric("CA An 5", format_eur_compact(synth["ca_an5"]),
              delta=f"+{(synth['ca_an5'] / synth['ca_an1'] - 1) * 100:.0f} %"
              if synth["ca_an1"] else None)
    c3.metric("EBITDA An 5", format_eur_compact(synth["ebitda_an5"]),
              delta=f"+{(synth['ebitda_an5'] / synth['ebitda_an1'] - 1) * 100:.0f} %"
              if synth["ebitda_an1"] else None)
    c4.metric("Résultat net cumulé", format_eur_compact(synth["resultat_net_cumule"]))
    c5.metric("Cash fin de période", format_eur_compact(synth["cash_fin_periode"]))


# ─── 2. Trajectoire annuelle ────────────────────────────────────────────────

def _section_trajectoire(proj: dict):
    st.markdown(
        "<h3 style='font-family: Georgia, serif; color:#5C2E0F;'>"
        "📈 Trajectoire sur 5 ans</h3>",
        unsafe_allow_html=True,
    )
    kpi = kpi_annuels(proj)
    annees = [f"An {y}" for y in kpi.index]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=annees, y=kpi["CA"], name="Chiffre d'affaires",
        marker_color=COULEUR_PRIMAIRE, opacity=0.85,
        text=[format_eur_compact(v) for v in kpi["CA"]],
        textposition="outside",
        textfont={"size": 13, "color": COULEUR_FONCEE, "family": "system-ui"},
    ))
    fig.add_trace(go.Scatter(
        x=annees, y=kpi["EBITDA"], name="EBITDA",
        mode="lines+markers+text",
        line={"color": COULEUR_DOREE, "width": 4},
        marker={"size": 12, "color": COULEUR_DOREE,
                "line": {"color": COULEUR_FONCEE, "width": 1.5}},
        text=[format_eur_compact(v) for v in kpi["EBITDA"]],
        textposition="top center",
        textfont={"size": 13, "color": COULEUR_FONCEE, "family": "system-ui"},
    ))
    fig.add_trace(go.Scatter(
        x=annees, y=kpi["Résultat net"], name="Résultat net",
        mode="lines+markers",
        line={"color": COULEUR_FONCEE, "width": 3, "dash": "dot"},
        marker={"size": 10, "color": COULEUR_FONCEE},
    ))
    fig.update_yaxes(tickformat=",.0f", ticksuffix=" €")
    appliquer_theme(fig, hauteur=420, titre=None)
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


# ─── 3. Mix CA par activité + saisonnalité ─────────────────────────────────

def _section_mix_saisonnalite(proj: dict, params: dict):
    st.markdown(
        "<h3 style='font-family: Georgia, serif; color:#5C2E0F;'>"
        "🥐 Mix d'activités &amp; saisonnalité</h3>",
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2, gap="large")

    # ── Donut : répartition CA An 5 par activité ────────────────────────
    with col1:
        idx = proj["index"]
        ventes = proj["ventes"]
        mask_an5 = idx["annee_exploit"] == idx["annee_exploit"].max()
        valeurs = [
            ventes.loc[mask_an5, "ventes_boulangerie"].sum(),
            ventes.loc[mask_an5, "ventes_patisserie"].sum(),
            ventes.loc[mask_an5, "ventes_traiteur_b2b"].sum(),
        ]
        labels = ["Boulangerie", "Pâtisserie", "Traiteur B2B"]
        couleurs = [COULEUR_ACT["boulangerie"], COULEUR_ACT["patisserie"],
                    COULEUR_ACT["traiteur_b2b"]]

        fig = go.Figure(go.Pie(
            labels=labels, values=valeurs, hole=0.55,
            marker={"colors": couleurs, "line": {"color": "white", "width": 2}},
            textinfo="label+percent",
            textfont={"size": 14, "family": "system-ui", "color": COULEUR_FONCEE},
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} €<br>%{percent}<extra></extra>",
        ))
        # Annotation centre
        fig.update_layout(
            annotations=[{
                "text": f"<b>{format_eur_compact(sum(valeurs))}</b><br>"
                        f"<span style='font-size:13px;'>CA An 5</span>",
                "x": 0.5, "y": 0.5,
                "font": {"size": 18, "family": "Georgia, serif", "color": COULEUR_FONCEE},
                "showarrow": False,
            }]
        )
        appliquer_theme(fig, hauteur=380, titre="Répartition du CA An 5",
                        legende=False)
        st.plotly_chart(fig, width='stretch',
                        config={"displayModeBar": False})

    # ── Bars : saisonnalité CA An 1 par mois ────────────────────────────
    with col2:
        idx = proj["index"]
        ventes = proj["ventes"]
        an1 = idx["annee_exploit"] == 1
        mois_labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
                       "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]

        df_an1 = pd.DataFrame({
            "mois_cal": idx.loc[an1, "mois_calendrier"].values,
            "Boulangerie": ventes.loc[an1, "ventes_boulangerie"].values,
            "Pâtisserie": ventes.loc[an1, "ventes_patisserie"].values,
            "Traiteur B2B": ventes.loc[an1, "ventes_traiteur_b2b"].values,
        }).groupby("mois_cal").sum().reindex(range(1, 13), fill_value=0)

        fig = go.Figure()
        for col, c in zip(["Boulangerie", "Pâtisserie", "Traiteur B2B"],
                          [COULEUR_ACT["boulangerie"], COULEUR_ACT["patisserie"],
                           COULEUR_ACT["traiteur_b2b"]]):
            fig.add_trace(go.Bar(
                x=mois_labels, y=df_an1[col].values,
                name=col, marker_color=c,
                hovertemplate=f"<b>{col}</b><br>%{{x}} : %{{y:,.0f}} €<extra></extra>",
            ))
        fig.update_layout(barmode="stack")
        fig.update_yaxes(tickformat=",.0f", ticksuffix=" €")
        appliquer_theme(fig, hauteur=380, titre="Saisonnalité — CA mensuel An 1")
        st.plotly_chart(fig, width='stretch',
                        config={"displayModeBar": False})


# ─── 4. Cascade P&L An 5 (Waterfall) ────────────────────────────────────────

def _section_cascade_pl_an5(proj: dict):
    st.markdown(
        "<h3 style='font-family: Georgia, serif; color:#5C2E0F;'>"
        "💰 Cascade P&amp;L — Année 5 (consolidé)</h3>",
        unsafe_allow_html=True,
    )
    pl = proj["pl_consolide"]
    idx = proj["index"]
    mask = idx["annee_exploit"] == idx["annee_exploit"].max()
    pl_an = pl.loc[mask].sum()

    labels = [
        "CA", "Charges variables", "Marge brute",
        "Personnel prod.", "Personnel admin.", "Charges fixes",
        "EBITDA", "Amortissements", "EBIT",
        "Intérêts", "ISOC", "Résultat net",
    ]
    valeurs = [
        pl_an["ca"], pl_an["charges_variables"], 0,
        pl_an["personnel_production"], pl_an["personnel_admin"],
        pl_an["charges_fixes"], 0,
        pl_an["amortissements"], 0,
        pl_an["interets"], pl_an["isoc"], 0,
    ]
    mesures = [
        "absolute", "relative", "total",
        "relative", "relative", "relative", "total",
        "relative", "total",
        "relative", "relative", "total",
    ]

    fig = go.Figure(go.Waterfall(
        x=labels, y=valeurs, measure=mesures,
        text=[format_eur_compact(v) if v != 0 else "" for v in valeurs],
        textposition="outside",
        textfont={"size": 12, "color": COULEUR_FONCEE},
        connector={"line": {"color": "#D0C5B0", "width": 1, "dash": "dot"}},
        increasing={"marker": {"color": COULEUR_POSITIF}},
        decreasing={"marker": {"color": COULEUR_NEGATIF}},
        totals={"marker": {"color": COULEUR_TOTAL}},
        hovertemplate="<b>%{x}</b><br>%{y:,.0f} €<extra></extra>",
    ))
    fig.update_yaxes(tickformat=",.0f", ticksuffix=" €")
    appliquer_theme(fig, hauteur=460, legende=False)
    st.plotly_chart(fig, width='stretch',
                    config={"displayModeBar": False})


# ─── 5. Structure des coûts mensuelle (stacked area) ───────────────────────

def _section_structure_couts(proj: dict):
    st.markdown(
        "<h3 style='font-family: Georgia, serif; color:#5C2E0F;'>"
        "🔍 Structure des charges sur 60 mois</h3>",
        unsafe_allow_html=True,
    )
    idx = proj["index"]
    cv = proj["charges_var"]["cv_total"]
    perso_prod = proj["personnel"]["perso_prod_pl"]
    perso_admin = proj["personnel"]["perso_admin_pl"]
    cf = proj["charges_fixes"]["cf_total"]
    amort_e = proj["amortissements"]["amort_exploit"]
    amort_i = proj["amortissements"]["amort_immo"]
    int_e = proj["prets"]["mensuel"]["interets_exploit"]
    int_i = proj["prets"]["mensuel"]["interets_immo"]

    dates = idx["date"].astype(str).values

    fig = go.Figure()
    series = [
        ("Matières & emballages", cv.values, COULEUR_ACT["boulangerie"]),
        ("Personnel production", perso_prod.values, COULEUR_PRIMAIRE),
        ("Personnel admin.", perso_admin.values, COULEUR_DOREE),
        ("Charges fixes", cf.values, COULEUR_SECONDAIRE),
        ("Amortissements", (amort_e + amort_i).values, "#A89A7E"),
        ("Intérêts financiers", (int_e + int_i).values, COULEUR_NEGATIF),
    ]
    for nom, valeurs, couleur in series:
        fig.add_trace(go.Scatter(
            x=dates, y=valeurs, name=nom,
            mode="lines", stackgroup="charges",
            line={"width": 0.5, "color": couleur},
            fillcolor=couleur,
            hovertemplate=f"<b>{nom}</b><br>%{{x|%b %Y}} : %{{y:,.0f}} €<extra></extra>",
        ))
    fig.update_yaxes(tickformat=",.0f", ticksuffix=" €")
    appliquer_theme(fig, hauteur=420)
    st.plotly_chart(fig, width='stretch',
                    config={"displayModeBar": False})


# ─── 6. Cash cumulé + service de la dette ──────────────────────────────────

def _section_cash_dette(proj: dict, params: dict):
    st.markdown(
        "<h3 style='font-family: Georgia, serif; color:#5C2E0F;'>"
        "💵 Cash &amp; dette</h3>",
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2, gap="large")

    # ── Cash cumulé par entité + consolidé ──────────────────────────────
    with col1:
        idx = proj["index"]
        dates = idx["date"].astype(str).values
        cash_e = proj["cash_exploit"]["cash_cumule"].values
        cash_i = proj["cash_immo"]["cash_cumule"].values
        cash_c = cash_e + cash_i

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=cash_e, name="SRL Exploitation",
            mode="lines", line={"color": COULEUR_EXPLOIT, "width": 3},
            hovertemplate="SRL Exploit %{x|%b %Y} : %{y:,.0f} €<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=dates, y=cash_i, name="SRL Immobilière",
            mode="lines", line={"color": COULEUR_IMMO, "width": 3},
            hovertemplate="SRL Immo %{x|%b %Y} : %{y:,.0f} €<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=dates, y=cash_c, name="Consolidé",
            mode="lines", line={"color": COULEUR_FONCEE, "width": 4, "dash": "dash"},
            hovertemplate="Consolidé %{x|%b %Y} : %{y:,.0f} €<extra></extra>",
        ))
        # Ligne zéro
        fig.add_hline(y=0, line_dash="dot", line_color=COULEUR_NEGATIF, line_width=1)
        fig.update_yaxes(tickformat=",.0f", ticksuffix=" €")
        appliquer_theme(fig, hauteur=380, titre="Cash cumulé par entité")
        st.plotly_chart(fig, width='stretch',
                        config={"displayModeBar": False})

    # ── Service de la dette annuel (intérêts + capital) par entité ─────
    with col2:
        idx = proj["index"]
        prets_m = proj["prets"]["mensuel"]
        df = pd.DataFrame({
            "annee_exploit": idx["annee_exploit"].values,
            "int_immo": prets_m["interets_immo"].values,
            "cap_immo": prets_m["capital_immo"].values,
            "int_exploit": prets_m["interets_exploit"].values,
            "cap_exploit": prets_m["capital_exploit"].values,
        }).groupby("annee_exploit").sum()

        annees = [f"An {y}" for y in df.index]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=annees, y=df["cap_immo"], name="Capital — Immo",
            marker_color=COULEUR_IMMO, opacity=0.95,
        ))
        fig.add_trace(go.Bar(
            x=annees, y=df["int_immo"], name="Intérêts — Immo",
            marker_color=COULEUR_IMMO, opacity=0.55,
        ))
        fig.add_trace(go.Bar(
            x=annees, y=df["cap_exploit"], name="Capital — Exploit",
            marker_color=COULEUR_EXPLOIT, opacity=0.95,
        ))
        fig.add_trace(go.Bar(
            x=annees, y=df["int_exploit"], name="Intérêts — Exploit",
            marker_color=COULEUR_EXPLOIT, opacity=0.55,
        ))
        fig.update_layout(barmode="stack")
        fig.update_yaxes(tickformat=",.0f", ticksuffix=" €")
        appliquer_theme(fig, hauteur=380, titre="Service de la dette par an")
        st.plotly_chart(fig, width='stretch',
                        config={"displayModeBar": False})


# ─── 7. P&L par entité (mini cards) ─────────────────────────────────────────

def _section_par_entite(proj: dict):
    from core.indicateurs import kpi_par_entite
    st.markdown(
        "<h3 style='font-family: Georgia, serif; color:#5C2E0F;'>"
        "🏢 Résultats par entité</h3>",
        unsafe_allow_html=True,
    )
    par_ent = kpi_par_entite(proj)
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown(
            "<h4 style='color:#C19A6B; margin-bottom:0.3rem;'>"
            "🥖 SRL Exploitation</h4>",
            unsafe_allow_html=True,
        )
        df_e = par_ent["Exploitation"].copy()
        df_e_fmt = df_e.map(lambda v: format_eur(v))
        df_e_fmt.index = [f"An {y}" for y in df_e.index]
        st.dataframe(df_e_fmt, width='stretch')

    with col2:
        st.markdown(
            "<h4 style='color:#6B4423; margin-bottom:0.3rem;'>"
            "🏛️ SRL Immobilière</h4>",
            unsafe_allow_html=True,
        )
        df_i = par_ent["Immobilière"].copy()
        df_i_fmt = df_i.map(lambda v: format_eur(v))
        df_i_fmt.index = [f"An {y}" for y in df_i.index]
        st.dataframe(df_i_fmt, width='stretch')


# ─── 8. Détails dans expanders ──────────────────────────────────────────────

def _section_details(proj: dict, params: dict):
    st.markdown(
        "<h3 style='font-family: Georgia, serif; color:#5C2E0F;'>"
        "🔬 Détails</h3>",
        unsafe_allow_html=True,
    )

    with st.expander("📋 KPIs annuels consolidés (tableau complet)"):
        st.dataframe(kpi_annuels(proj), width='stretch')

    with st.expander("📅 P&L mensuel consolidé (60 mois)"):
        st.dataframe(proj["pl_consolide"].round(0), width='stretch')

    with st.expander("💸 Cash flow mensuel par entité"):
        c1, c2 = st.columns(2)
        with c1:
            st.caption("**SRL Exploitation**")
            st.dataframe(proj["cash_exploit"].round(0), width='stretch')
        with c2:
            st.caption("**SRL Immobilière**")
            st.dataframe(proj["cash_immo"].round(0), width='stretch')

    with st.expander("🏦 Tableaux d'amortissement des prêts"):
        for pret in params.get("prets", []):
            pid = pret["id"]
            st.markdown(
                f"**{pret['libelle']}** — {format_eur(pret['montant'])} sur "
                f"{pret['duree_annees']} ans à {pret['taux_annuel'] * 100:.2f} % "
                f"(entité : {pret['entite']})"
            )
            tab = proj["prets"]["tableaux"].get(pid, [])
            if tab:
                df_tab = pd.DataFrame(tab)
                df_tab_fmt = df_tab.copy()
                for c in ["mensualite", "interets", "capital_rembourse", "capital_restant"]:
                    df_tab_fmt[c] = df_tab[c].apply(lambda v: format_eur(v, 2))
                st.dataframe(df_tab_fmt, width='stretch', height=300)
            st.divider()
