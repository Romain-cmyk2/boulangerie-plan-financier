"""
Export HTML autonome du plan financier.

Génère un fichier HTML self-contained (Plotly via CDN) avec :
  - Hero photo + en-tête
  - 5 KPIs synthèse
  - Trajectoire 5 ans (bar + lignes)
  - Mix CA An 5 + saisonnalité An 1
  - Cascade P&L An 5 (waterfall)
  - Structure des charges sur 60 mois (stacked area)
  - Cash cumulé + service de la dette
  - Tableaux KPIs annuels + P&L par entité
  - Footer SConseil + date génération

L'output est une string HTML de ~500 ko (Plotly chargé depuis CDN cdn.plot.ly).
"""

import base64
from datetime import datetime, date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from core.calculs import projection_complete
from core.indicateurs import kpi_annuels, kpi_par_entite, synthese_globale
from core.style import (
    appliquer_theme, format_eur, format_eur_compact, format_pct,
    COULEUR_PRIMAIRE, COULEUR_FONCEE, COULEUR_SECONDAIRE, COULEUR_DOREE,
    COULEUR_POSITIF, COULEUR_NEGATIF, COULEUR_TOTAL, COULEUR_FOND, COULEUR_CREME,
    COULEUR_ACT, COULEUR_IMMO, COULEUR_EXPLOIT,
)


ASSETS = Path(__file__).resolve().parent.parent / "assets"


# ─── CSS ────────────────────────────────────────────────────────────────────

def _css() -> str:
    return f"""
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 0;
    font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    color: #2B1810;
    background: {COULEUR_CREME};
    line-height: 1.5;
  }}
  .container {{
    max-width: 1180px;
    margin: 0 auto;
    padding: 0 24px 80px;
    background: {COULEUR_FOND};
  }}
  header.hero {{
    margin: 0 -24px;
    padding: 0;
    position: relative;
  }}
  .hero-img {{
    width: 100%;
    height: 280px;
    background-size: cover;
    background-position: center;
    border-bottom: 4px solid {COULEUR_PRIMAIRE};
  }}
  .hero-text {{
    padding: 32px 24px 16px;
    text-align: left;
  }}
  h1 {{
    font-family: Georgia, serif;
    color: {COULEUR_FONCEE};
    margin: 0 0 6px;
    font-size: 2.4rem;
    letter-spacing: -0.02em;
  }}
  h2 {{
    font-family: Georgia, serif;
    color: {COULEUR_FONCEE};
    margin: 36px 0 12px;
    font-size: 1.5rem;
    border-bottom: 2px solid {COULEUR_DOREE};
    padding-bottom: 6px;
  }}
  h3 {{
    font-family: Georgia, serif;
    color: {COULEUR_FONCEE};
    margin: 18px 0 8px;
    font-size: 1.15rem;
  }}
  .subtitle {{
    color: #6B4423;
    font-style: italic;
    font-size: 1.1rem;
    margin: 0 0 4px;
  }}
  .meta {{
    color: #888;
    font-size: 0.95rem;
    margin: 0;
  }}
  section {{
    margin: 28px 0;
  }}
  .kpis {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 14px;
    margin: 24px 0;
  }}
  .kpi {{
    background: white;
    border: 1px solid #E8DCC4;
    border-radius: 10px;
    padding: 16px 14px;
    box-shadow: 0 1px 3px rgba(92, 46, 15, 0.06);
  }}
  .kpi-label {{
    font-size: 0.82rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
  }}
  .kpi-value {{
    font-family: Georgia, serif;
    font-size: 1.65rem;
    font-weight: bold;
    color: {COULEUR_FONCEE};
    line-height: 1.1;
  }}
  .row-2 {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0;
    background: white;
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(92, 46, 15, 0.05);
  }}
  th {{
    background: {COULEUR_PRIMAIRE};
    color: white;
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 0.92rem;
  }}
  td {{
    padding: 9px 12px;
    border-bottom: 1px solid #F0E6D0;
    font-size: 0.95rem;
    text-align: right;
  }}
  td:first-child {{ text-align: left; font-weight: 600; color: {COULEUR_FONCEE}; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:nth-child(even) td {{ background: #FBF7EE; }}
  .chart {{
    background: {COULEUR_FOND};
    border-radius: 8px;
    padding: 8px;
    margin: 6px 0;
  }}
  footer {{
    margin: 60px -24px -80px;
    padding: 24px;
    background: {COULEUR_FONCEE};
    color: {COULEUR_CREME};
    text-align: center;
    font-size: 0.9rem;
  }}
  footer strong {{ color: {COULEUR_DOREE}; }}
  .badge {{
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.78rem;
    background: {COULEUR_DOREE};
    color: {COULEUR_FONCEE};
    font-weight: 600;
  }}
  @media (max-width: 800px) {{
    .kpis {{ grid-template-columns: repeat(2, 1fr); }}
    .row-2 {{ grid-template-columns: 1fr; }}
    h1 {{ font-size: 1.8rem; }}
  }}
</style>
"""


# ─── Helpers HTML ───────────────────────────────────────────────────────────

def _image_b64(chemin: Path) -> str:
    if not chemin.exists():
        return ""
    return base64.b64encode(chemin.read_bytes()).decode("ascii")


def _fig_to_div(fig: go.Figure, div_id: str) -> str:
    """Convertit une figure Plotly en <div> autonome (le JS Plotly est inclus
    une seule fois en haut via CDN)."""
    return fig.to_html(
        include_plotlyjs=False, full_html=False,
        div_id=div_id,
        config={"displayModeBar": False, "responsive": True},
    )


def _df_to_table(df: pd.DataFrame, formatter=None) -> str:
    """Génère une table HTML stylée à partir d'un DataFrame."""
    df_disp = df.copy()
    if formatter is not None:
        for c in df_disp.columns:
            df_disp[c] = df_disp[c].map(formatter)
    return df_disp.to_html(classes="data-table", border=0)


# ─── Sections ──────────────────────────────────────────────────────────────

def _section_hero(params: dict, hero_b64: str) -> str:
    nom = params.get("nom_entreprise", "—")
    nom_plan = params.get("nom_plan", "Plan")
    ville = params.get("ville", "")
    date_ouv = params.get("date_ouverture", "")
    if isinstance(date_ouv, date):
        date_ouv = date_ouv.isoformat()
    nb_mois = params.get("nb_mois_projection", 0)

    img_html = (f'<div class="hero-img" style="background-image:'
                f'url(\'data:image/jpeg;base64,{hero_b64}\');"></div>'
                if hero_b64 else "")
    return f"""
<header class="hero">
  {img_html}
  <div class="hero-text">
    <span class="badge">PLAN FINANCIER · {nom_plan}</span>
    <h1>{nom}</h1>
    <p class="subtitle">Boulangerie-pâtisserie haut de gamme · {ville}</p>
    <p class="meta">Ouverture {date_ouv} · Projection {nb_mois} mois ·
       Structure SRL Immobilière + SRL Exploitation</p>
  </div>
</header>
"""


def _section_kpis(synth: dict) -> str:
    cards = [
        ("CA An 1", format_eur_compact(synth["ca_an1"])),
        ("CA An 5", format_eur_compact(synth["ca_an5"])),
        ("EBITDA An 5", format_eur_compact(synth["ebitda_an5"])),
        ("Résultat net cumulé", format_eur_compact(synth["resultat_net_cumule"])),
        ("Cash fin de période", format_eur_compact(synth["cash_fin_periode"])),
    ]
    inner = "".join(
        f'<div class="kpi"><div class="kpi-label">{lbl}</div>'
        f'<div class="kpi-value">{val}</div></div>'
        for lbl, val in cards
    )
    return f'<section><h2>📊 Indicateurs clés</h2><div class="kpis">{inner}</div></section>'


def _section_trajectoire(proj: dict) -> str:
    kpi = kpi_annuels(proj)
    annees = [f"An {y}" for y in kpi.index]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=annees, y=kpi["CA"], name="CA",
        marker_color=COULEUR_PRIMAIRE, opacity=0.85,
        text=[format_eur_compact(v) for v in kpi["CA"]],
        textposition="outside",
        textfont={"size": 12, "color": COULEUR_FONCEE},
    ))
    fig.add_trace(go.Scatter(
        x=annees, y=kpi["EBITDA"], name="EBITDA",
        mode="lines+markers+text",
        line={"color": COULEUR_DOREE, "width": 4},
        marker={"size": 11, "color": COULEUR_DOREE,
                "line": {"color": COULEUR_FONCEE, "width": 1.5}},
        text=[format_eur_compact(v) for v in kpi["EBITDA"]],
        textposition="top center",
        textfont={"size": 12, "color": COULEUR_FONCEE},
    ))
    fig.add_trace(go.Scatter(
        x=annees, y=kpi["Résultat net"], name="Résultat net",
        mode="lines+markers",
        line={"color": COULEUR_FONCEE, "width": 3, "dash": "dot"},
        marker={"size": 9, "color": COULEUR_FONCEE},
    ))
    fig.update_yaxes(tickformat=",.0f", ticksuffix=" €")
    appliquer_theme(fig, hauteur=400)
    return f"""
<section>
  <h2>📈 Trajectoire sur 5 ans</h2>
  <div class="chart">{_fig_to_div(fig, 'chart-trajectoire')}</div>
</section>"""


def _section_mix_saisonnalite(proj: dict) -> str:
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

    fig_donut = go.Figure(go.Pie(
        labels=labels, values=valeurs, hole=0.55,
        marker={"colors": couleurs, "line": {"color": "white", "width": 2}},
        textinfo="label+percent",
        textfont={"size": 13, "color": COULEUR_FONCEE},
    ))
    fig_donut.update_layout(annotations=[{
        "text": f"<b>{format_eur_compact(sum(valeurs))}</b><br>CA An 5",
        "x": 0.5, "y": 0.5, "showarrow": False,
        "font": {"size": 17, "family": "Georgia, serif", "color": COULEUR_FONCEE},
    }])
    appliquer_theme(fig_donut, hauteur=360, titre="Répartition CA An 5", legende=False)

    # Saisonnalité An 1
    an1 = idx["annee_exploit"] == 1
    mois_lbls = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
                 "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]
    df_an1 = pd.DataFrame({
        "mois_cal": idx.loc[an1, "mois_calendrier"].values,
        "Boulangerie": ventes.loc[an1, "ventes_boulangerie"].values,
        "Pâtisserie": ventes.loc[an1, "ventes_patisserie"].values,
        "Traiteur B2B": ventes.loc[an1, "ventes_traiteur_b2b"].values,
    }).groupby("mois_cal").sum().reindex(range(1, 13), fill_value=0)

    fig_sais = go.Figure()
    for col, c in zip(["Boulangerie", "Pâtisserie", "Traiteur B2B"], couleurs):
        fig_sais.add_trace(go.Bar(
            x=mois_lbls, y=df_an1[col].values, name=col, marker_color=c,
        ))
    fig_sais.update_layout(barmode="stack")
    fig_sais.update_yaxes(tickformat=",.0f", ticksuffix=" €")
    appliquer_theme(fig_sais, hauteur=360, titre="Saisonnalité — CA mensuel An 1")

    return f"""
<section>
  <h2>🥐 Mix d'activités &amp; saisonnalité</h2>
  <div class="row-2">
    <div class="chart">{_fig_to_div(fig_donut, 'chart-donut')}</div>
    <div class="chart">{_fig_to_div(fig_sais, 'chart-sais')}</div>
  </div>
</section>"""


def _section_cascade(proj: dict) -> str:
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
        connector={"line": {"color": "#D0C5B0", "width": 1, "dash": "dot"}},
        increasing={"marker": {"color": COULEUR_POSITIF}},
        decreasing={"marker": {"color": COULEUR_NEGATIF}},
        totals={"marker": {"color": COULEUR_TOTAL}},
    ))
    fig.update_yaxes(tickformat=",.0f", ticksuffix=" €")
    appliquer_theme(fig, hauteur=440, legende=False)
    return f"""
<section>
  <h2>💰 Cascade P&amp;L — Année 5 (consolidé)</h2>
  <div class="chart">{_fig_to_div(fig, 'chart-cascade')}</div>
</section>"""


def _section_structure_couts(proj: dict) -> str:
    idx = proj["index"]
    cv = proj["charges_var"]["cv_total"]
    perso_prod = proj["personnel"]["perso_prod_pl"]
    perso_admin = proj["personnel"]["perso_admin_pl"]
    cf = proj["charges_fixes"]["cf_total"]
    amort = proj["amortissements"]["amort_exploit"] + proj["amortissements"]["amort_immo"]
    ints = proj["prets"]["mensuel"]["interets_exploit"] + proj["prets"]["mensuel"]["interets_immo"]
    dates = idx["date"].astype(str).values

    fig = go.Figure()
    series = [
        ("Matières & emballages", cv.values, COULEUR_ACT["boulangerie"]),
        ("Personnel production", perso_prod.values, COULEUR_PRIMAIRE),
        ("Personnel admin.", perso_admin.values, COULEUR_DOREE),
        ("Charges fixes", cf.values, COULEUR_SECONDAIRE),
        ("Amortissements", amort.values, "#A89A7E"),
        ("Intérêts financiers", ints.values, COULEUR_NEGATIF),
    ]
    for nom, valeurs, couleur in series:
        fig.add_trace(go.Scatter(
            x=dates, y=valeurs, name=nom,
            mode="lines", stackgroup="charges",
            line={"width": 0.5, "color": couleur},
            fillcolor=couleur,
        ))
    fig.update_yaxes(tickformat=",.0f", ticksuffix=" €")
    appliquer_theme(fig, hauteur=400)
    return f"""
<section>
  <h2>🔍 Structure des charges sur 60 mois</h2>
  <div class="chart">{_fig_to_div(fig, 'chart-structure')}</div>
</section>"""


def _section_cash_dette(proj: dict) -> str:
    idx = proj["index"]
    dates = idx["date"].astype(str).values
    cash_e = proj["cash_exploit"]["cash_cumule"].values
    cash_i = proj["cash_immo"]["cash_cumule"].values
    cash_c = cash_e + cash_i

    fig_cash = go.Figure()
    fig_cash.add_trace(go.Scatter(x=dates, y=cash_e, name="SRL Exploitation",
        mode="lines", line={"color": COULEUR_EXPLOIT, "width": 3}))
    fig_cash.add_trace(go.Scatter(x=dates, y=cash_i, name="SRL Immobilière",
        mode="lines", line={"color": COULEUR_IMMO, "width": 3}))
    fig_cash.add_trace(go.Scatter(x=dates, y=cash_c, name="Consolidé",
        mode="lines", line={"color": COULEUR_FONCEE, "width": 4, "dash": "dash"}))
    fig_cash.add_hline(y=0, line_dash="dot", line_color=COULEUR_NEGATIF, line_width=1)
    fig_cash.update_yaxes(tickformat=",.0f", ticksuffix=" €")
    appliquer_theme(fig_cash, hauteur=360, titre="Cash cumulé par entité")

    # Service de la dette annuel
    prets_m = proj["prets"]["mensuel"]
    df_dette = pd.DataFrame({
        "annee_exploit": idx["annee_exploit"].values,
        "int_immo": prets_m["interets_immo"].values,
        "cap_immo": prets_m["capital_immo"].values,
        "int_exploit": prets_m["interets_exploit"].values,
        "cap_exploit": prets_m["capital_exploit"].values,
    }).groupby("annee_exploit").sum()
    annees = [f"An {y}" for y in df_dette.index]
    fig_dette = go.Figure()
    fig_dette.add_trace(go.Bar(x=annees, y=df_dette["cap_immo"], name="Capital — Immo",
        marker_color=COULEUR_IMMO, opacity=0.95))
    fig_dette.add_trace(go.Bar(x=annees, y=df_dette["int_immo"], name="Intérêts — Immo",
        marker_color=COULEUR_IMMO, opacity=0.55))
    fig_dette.add_trace(go.Bar(x=annees, y=df_dette["cap_exploit"], name="Capital — Exploit",
        marker_color=COULEUR_EXPLOIT, opacity=0.95))
    fig_dette.add_trace(go.Bar(x=annees, y=df_dette["int_exploit"], name="Intérêts — Exploit",
        marker_color=COULEUR_EXPLOIT, opacity=0.55))
    fig_dette.update_layout(barmode="stack")
    fig_dette.update_yaxes(tickformat=",.0f", ticksuffix=" €")
    appliquer_theme(fig_dette, hauteur=360, titre="Service de la dette par an")

    return f"""
<section>
  <h2>💵 Cash &amp; dette</h2>
  <div class="row-2">
    <div class="chart">{_fig_to_div(fig_cash, 'chart-cash')}</div>
    <div class="chart">{_fig_to_div(fig_dette, 'chart-dette')}</div>
  </div>
</section>"""


def _section_tableaux(proj: dict) -> str:
    kpi = kpi_annuels(proj)
    par_ent = kpi_par_entite(proj)

    # KPIs annuels (table principale)
    kpi_disp = kpi.copy()
    cols_eur = ["CA", "Marge brute", "EBITDA", "EBIT",
                "Résultat avant impôt", "ISOC", "Résultat net",
                "CAF", "Cash cumulé fin année"]
    for c in cols_eur:
        if c in kpi_disp.columns:
            kpi_disp[c] = kpi_disp[c].map(format_eur)
    kpi_disp.index = [f"Année {y}" for y in kpi_disp.index]
    kpi_disp.index.name = ""

    df_e = par_ent["Exploitation"].copy()
    df_e_fmt = df_e.map(format_eur)
    df_e_fmt.index = [f"An {y}" for y in df_e.index]
    df_e_fmt.index.name = ""

    df_i = par_ent["Immobilière"].copy()
    df_i_fmt = df_i.map(format_eur)
    df_i_fmt.index = [f"An {y}" for y in df_i.index]
    df_i_fmt.index.name = ""

    return f"""
<section>
  <h2>📋 Tableaux récapitulatifs</h2>

  <h3>KPIs annuels — consolidé</h3>
  {kpi_disp.to_html(border=0)}

  <h3>Résultats par entité</h3>
  <div class="row-2">
    <div>
      <p><strong style="color:#C19A6B;">🥖 SRL Exploitation</strong></p>
      {df_e_fmt.to_html(border=0)}
    </div>
    <div>
      <p><strong style="color:#6B4423;">🏛️ SRL Immobilière</strong></p>
      {df_i_fmt.to_html(border=0)}
    </div>
  </div>
</section>"""


def _section_methodologie() -> str:
    return f"""
<section>
  <h2>📚 Méthodologie SConseil</h2>
  <p>Ce plan financier reproduit fidèlement la <strong>structure 2 entités</strong> belge :</p>
  <ul>
    <li><strong>SRL Immobilière</strong> détient le bien immobilier, perçoit un loyer
        mensuel de la SRL Exploitation, supporte le précompte immobilier et le
        prêt hypothécaire.</li>
    <li><strong>SRL Exploitation</strong> opère l'activité commerciale, paie le loyer
        à la SRL Immobilière, et supporte les charges d'exploitation.</li>
  </ul>
  <p>Le modèle intègre les spécificités belges : <strong>pécule de vacances</strong>
  versé en juillet, <strong>13e mois</strong> en décembre, <strong>TVA trimestrielle</strong>
  payée le mois suivant clôture (avril, juillet, octobre, janvier),
  <strong>ISOC PME</strong> à 20 % jusqu'à 100 k€ puis 25 %, paiement en juin N+1.</p>
  <p>P&amp;L lissé (masse salariale annuelle / 12) ; cash flow réel suivant le prorata
  effectif des paiements. Mensualité constante pour les prêts. Amortissements linéaires.</p>
</section>"""


# ─── Orchestrateur ──────────────────────────────────────────────────────────

def generer_html(params: dict) -> str:
    """
    Génère la string HTML complète. À sauvegarder en .html ou à servir via
    st.download_button.
    """
    proj = projection_complete(params)
    synth = synthese_globale(proj)
    hero_b64 = _image_b64(ASSETS / "hero_vitrine.jpg")
    date_gen = datetime.now().strftime("%d/%m/%Y à %H:%M")

    body = (
        _section_hero(params, hero_b64)
        + _section_kpis(synth)
        + _section_trajectoire(proj)
        + _section_mix_saisonnalite(proj)
        + _section_cascade(proj)
        + _section_structure_couts(proj)
        + _section_cash_dette(proj)
        + _section_tableaux(proj)
        + _section_methodologie()
    )

    footer = f"""
<footer>
  <p><strong>Plan financier</strong> · {params.get('nom_entreprise', '')} ·
     généré le {date_gen}</p>
  <p>Document de démonstration — <strong>SConseil</strong> — Méthodologie de plan
     financier 2 entités</p>
</footer>
"""

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Plan financier — {params.get('nom_entreprise', 'Plan')}</title>
  <script src="https://cdn.plot.ly/plotly-2.35.0.min.js" charset="utf-8"></script>
  {_css()}
</head>
<body>
  <div class="container">
    {body}
  </div>
  {footer}
</body>
</html>
"""
