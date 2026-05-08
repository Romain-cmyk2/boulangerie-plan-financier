"""
Règles spécifiques Belgique :
  - Personnel : pécule de vacances (juillet) + 13e mois (décembre) au prorata
  - TVA : paiement le mois suivant la clôture du trimestre
  - ISOC : charge en décembre, paiement en juin N+1, taux PME 20%/25%
  - Amortissements : linéaires sur durée fiscale
  - Prêts : mensualité constante (formule belge classique)
"""

from datetime import date
from dateutil.relativedelta import relativedelta
import calendar


# ─── Personnel : masse salariale chargée et cash ────────────────────────────

def cout_charge_mensuel(brut_mensuel: float, onss_patronal: float) -> float:
    """Coût mensuel chargé hors pécule/13e (12 mois de salaire)."""
    return brut_mensuel * (1 + onss_patronal)


def masse_annuelle_chargee(brut_mensuel: float, onss_patronal: float) -> float:
    """
    Masse salariale annuelle chargée incluant :
      - 12 salaires bruts
      - 1 pécule de vacances (≈ 92% du brut)
      - 1 13e mois (≈ 100% du brut)
    le tout chargé d'ONSS patronal.
    """
    base_annuelle = brut_mensuel * 12
    pecule = brut_mensuel * 0.92
    treizieme = brut_mensuel * 1.00
    return (base_annuelle + pecule + treizieme) * (1 + onss_patronal)


def cout_pl_mensuel(brut_mensuel: float, onss_patronal: float) -> float:
    """Coût lissé en P&L : masse annuelle / 12."""
    return masse_annuelle_chargee(brut_mensuel, onss_patronal) / 12


def cash_personnel_mois(
    brut_mensuel: float,
    onss_patronal: float,
    mois_de_lannee: int,
    mois_actif: bool,
    mois_actif_jul_dec: tuple[bool, bool] = (True, True),
) -> float:
    """
    Sortie cash réelle sur un mois donné :
      - chaque mois actif : brut * (1+ONSS)
      - juillet : + pécule (0.92 * brut * (1+ONSS)) si actif en juillet
      - décembre : + 13e mois (brut * (1+ONSS)) si actif en décembre
    """
    if not mois_actif:
        return 0.0
    cash = brut_mensuel * (1 + onss_patronal)
    actif_jul, actif_dec = mois_actif_jul_dec
    if mois_de_lannee == 7 and actif_jul:
        cash += brut_mensuel * 0.92 * (1 + onss_patronal)
    if mois_de_lannee == 12 and actif_dec:
        cash += brut_mensuel * 1.00 * (1 + onss_patronal)
    return cash


# ─── TVA ────────────────────────────────────────────────────────────────────

def trimestre_de_mois(mois_de_lannee: int) -> int:
    """Retourne 1, 2, 3 ou 4 selon le mois (1-12)."""
    return (mois_de_lannee - 1) // 3 + 1


def est_mois_paiement_tva(mois_de_lannee: int) -> bool:
    """
    Mois où la TVA du trimestre précédent est payée :
      - avril (T1), juillet (T2), octobre (T3), janvier (T4)
    """
    return mois_de_lannee in (1, 4, 7, 10)


def mois_paiement_tva_pour_trimestre(annee: int, trimestre: int) -> tuple[int, int]:
    """Retourne (annee, mois) du paiement TVA pour un trimestre donné."""
    mapping = {1: (annee, 4), 2: (annee, 7), 3: (annee, 10), 4: (annee + 1, 1)}
    return mapping[trimestre]


# ─── ISOC ───────────────────────────────────────────────────────────────────

def calc_isoc(resultat_imposable: float, taux_pme: float, seuil_pme: float,
              taux_standard: float) -> float:
    """
    Calcul ISOC PME : 20% jusqu'au seuil, 25% au-delà.
    Si résultat négatif ou nul, ISOC = 0 (pas de remboursement, report).
    """
    if resultat_imposable <= 0:
        return 0.0
    if resultat_imposable <= seuil_pme:
        return resultat_imposable * taux_pme
    return seuil_pme * taux_pme + (resultat_imposable - seuil_pme) * taux_standard


# ─── Amortissements linéaires ───────────────────────────────────────────────

def amortissement_mensuel(montant: float, annees: int) -> float:
    """Amortissement mensuel linéaire. Si annees=0, pas d'amortissement (terrain)."""
    if annees <= 0:
        return 0.0
    return montant / (annees * 12)


def vnc_a_la_fin_du_mois(montant: float, annees: int, mois_ecoules: int) -> float:
    """Valeur nette comptable après N mois d'amortissement."""
    if annees <= 0:
        return montant
    nb_mois_total = annees * 12
    if mois_ecoules >= nb_mois_total:
        return 0.0
    cumul_amort = amortissement_mensuel(montant, annees) * mois_ecoules
    return max(0.0, montant - cumul_amort)


# ─── Prêts à mensualité constante ───────────────────────────────────────────

def mensualite_constante(montant: float, taux_annuel: float, duree_annees: int) -> float:
    """Formule de la mensualité constante (capital + intérêts)."""
    n = duree_annees * 12
    if taux_annuel == 0:
        return montant / n
    i = taux_annuel / 12
    return montant * i / (1 - (1 + i) ** (-n))


def tableau_amortissement(montant: float, taux_annuel: float,
                           duree_annees: int) -> list[dict]:
    """
    Retourne le tableau d'amortissement mensuel :
    [{mois, mensualite, interets, capital_rembourse, capital_restant}, ...]
    """
    n = duree_annees * 12
    i = taux_annuel / 12
    M = mensualite_constante(montant, taux_annuel, duree_annees)
    capital_restant = montant
    lignes = []
    for k in range(1, n + 1):
        interets = capital_restant * i
        capital = M - interets
        capital_restant = max(0.0, capital_restant - capital)
        lignes.append({
            "mois": k,
            "mensualite": M,
            "interets": interets,
            "capital_rembourse": capital,
            "capital_restant": capital_restant,
        })
    return lignes


# ─── Helpers dates ──────────────────────────────────────────────────────────

def mois_range(date_debut: date, nb_mois: int) -> list[date]:
    """Liste des 1ers du mois sur nb_mois à partir de date_debut."""
    return [date_debut + relativedelta(months=k) for k in range(nb_mois)]


def jours_dans_mois(d: date) -> int:
    return calendar.monthrange(d.year, d.month)[1]
