"""
Charte graphique unique du dashboard.

Couleurs terre/boulangerie. Toutes les figures Plotly passent par
appliquer_theme() pour rester cohérentes (gras 14px min, fonds neutres).
"""

import plotly.graph_objects as go


# ─── Palette ────────────────────────────────────────────────────────────────

COULEUR_PRIMAIRE = "#8B4513"      # Brun moyen — primary brand
COULEUR_FONCEE = "#5C2E0F"        # Brun foncé — titres
COULEUR_SECONDAIRE = "#D2691E"    # Orange chocolat — accents
COULEUR_DOREE = "#DAA520"         # Doré — highlights
COULEUR_CREME = "#F2E8D5"         # Beige clair — fond
COULEUR_FOND = "#FAF6F0"          # Fond carte
COULEUR_NEUTRE = "#888888"        # Texte secondaire

# Couleurs par activité (cohérent dans tous les graphes)
COULEUR_ACT = {
    "boulangerie": "#C19A6B",      # Croûte de pain dorée
    "patisserie": "#D4748E",       # Rose macaron
    "traiteur_b2b": "#5C2E0F",     # Chocolat foncé
}

# Couleurs P&L (cascade)
COULEUR_POSITIF = "#4A7C59"        # Vert sapin (sobre)
COULEUR_NEGATIF = "#A23B3B"        # Rouge brique
COULEUR_TOTAL = "#5C2E0F"          # Brun foncé pour totaux

# Couleurs entités
COULEUR_IMMO = "#6B4423"           # Brun terreux
COULEUR_EXPLOIT = "#C19A6B"        # Croûte dorée


# ─── Thème Plotly ───────────────────────────────────────────────────────────

def appliquer_theme(fig: go.Figure, hauteur: int = 380,
                     titre: str | None = None,
                     legende: bool = True) -> go.Figure:
    """
    Applique la charte graphique à une figure Plotly :
      - typo Georgia/serif pour titre, system-ui pour data
      - taille de texte ≥ 14px, gras sur titres
      - fond beige clair
      - pas de gridlines verticales
      - légende horizontale en bas
    """
    fig.update_layout(
        title={
            "text": (f"<b>{titre}</b>" if titre else None),
            "font": {"family": "Georgia, serif", "size": 18, "color": COULEUR_FONCEE},
            "x": 0.0, "xanchor": "left",
            "pad": {"b": 10},
        },
        height=hauteur,
        paper_bgcolor=COULEUR_FOND,
        plot_bgcolor=COULEUR_FOND,
        font={"family": "system-ui, sans-serif", "size": 14, "color": "#2B1810"},
        margin={"l": 50, "r": 30, "t": 60 if titre else 30, "b": 60},
        legend={
            "orientation": "h",
            "yanchor": "bottom", "y": -0.25,
            "xanchor": "left", "x": 0,
            "font": {"size": 13},
        } if legende else {},
        showlegend=legende,
        hoverlabel={
            "bgcolor": "white",
            "font": {"family": "system-ui, sans-serif", "size": 13},
            "bordercolor": COULEUR_PRIMAIRE,
        },
    )
    fig.update_xaxes(
        showgrid=False,
        showline=True, linewidth=1, linecolor="#D0C5B0",
        tickfont={"size": 13},
    )
    fig.update_yaxes(
        showgrid=True, gridwidth=1, gridcolor="#E8DCC4",
        zerolinecolor="#D0C5B0",
        tickfont={"size": 13},
    )
    return fig


def format_eur(montant: float, decimales: int = 0) -> str:
    """Formate un montant EUR avec séparateurs de milliers en espace."""
    if montant is None:
        return "—"
    formatted = f"{montant:,.{decimales}f}".replace(",", " ")
    return f"{formatted} €"


def format_eur_compact(montant: float) -> str:
    """Format compact : 1 234 567 → 1.23 M€"""
    if montant is None:
        return "—"
    if abs(montant) >= 1_000_000:
        return f"{montant / 1_000_000:.2f} M€"
    if abs(montant) >= 1_000:
        return f"{montant / 1_000:.0f} k€"
    return f"{montant:.0f} €"


def format_pct(valeur: float, decimales: int = 1) -> str:
    return f"{valeur:.{decimales}f} %"
