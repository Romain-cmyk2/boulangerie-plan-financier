"""
Indicateurs annuels et ratios de synthèse.

Travaille sur le dict retourné par calculs.projection_complete().
"""

import pandas as pd


def _agreger_par_annee(df: pd.DataFrame, idx: pd.DataFrame,
                       cols_sum: list[str] = None) -> pd.DataFrame:
    """Agrège un DataFrame mensuel par annee_exploit (somme de toutes les colonnes
    numériques sauf si cols_sum spécifié)."""
    df_with_year = df.copy()
    df_with_year["annee_exploit"] = idx["annee_exploit"].values
    if cols_sum is None:
        cols_sum = [c for c in df.columns if df[c].dtype.kind in "fi"]
    grouped = df_with_year.groupby("annee_exploit")[cols_sum].sum()
    return grouped


def kpi_annuels(projection: dict) -> pd.DataFrame:
    """
    Retourne un DataFrame indexé par annee_exploit avec les KPIs principaux,
    consolidés.
    """
    idx = projection["index"]
    pl_c = projection["pl_consolide"]
    cash_e = projection["cash_exploit"]
    cash_i = projection["cash_immo"]

    pl_an = _agreger_par_annee(pl_c, idx)
    cash_e_an = _agreger_par_annee(cash_e, idx)
    cash_i_an = _agreger_par_annee(cash_i, idx)

    out = pd.DataFrame(index=pl_an.index)
    out["CA"] = pl_an["ca"]
    out["Marge brute"] = pl_an["marge_brute"]
    out["Taux marge brute %"] = (pl_an["marge_brute"] / pl_an["ca"] * 100).round(1)
    out["EBITDA"] = pl_an["ebitda"]
    out["Taux EBITDA %"] = (pl_an["ebitda"] / pl_an["ca"] * 100).round(1)
    out["EBIT"] = pl_an["ebit"]
    out["Résultat avant impôt"] = pl_an["resultat_avant_impot"]
    out["ISOC"] = pl_an["isoc"]
    out["Résultat net"] = pl_an["resultat_net"]
    out["Taux marge nette %"] = (pl_an["resultat_net"] / pl_an["ca"] * 100).round(1)

    # CAF approximée : résultat net + amortissements
    out["CAF"] = pl_an["resultat_net"] + (-pl_an["amortissements"])

    # Cash cumulé fin d'année (consolidé)
    cash_cum_consol = (cash_e["cash_cumule"] + cash_i["cash_cumule"])
    cash_cum_consol = pd.DataFrame({"cash_cumule": cash_cum_consol.values},
                                   index=cash_e.index)
    cash_cum_consol["annee_exploit"] = idx["annee_exploit"].values
    out["Cash cumulé fin année"] = cash_cum_consol.groupby("annee_exploit")["cash_cumule"].last()

    return out.round(0)


def kpi_par_entite(projection: dict) -> dict[str, pd.DataFrame]:
    """KPIs annuels séparés pour SRL Exploit et SRL Immo."""
    idx = projection["index"]
    out = {}
    for label, df_pl in [("Exploitation", projection["pl_exploit"]),
                         ("Immobilière", projection["pl_immo"])]:
        an = _agreger_par_annee(df_pl, idx)
        kpi = pd.DataFrame(index=an.index)
        kpi["CA"] = an["ca"]
        if "ebitda" in an.columns:
            kpi["EBITDA"] = an["ebitda"]
        kpi["EBIT"] = an["ebit"]
        kpi["Résultat net"] = an["resultat_net"]
        out[label] = kpi.round(0)
    return out


def synthese_globale(projection: dict) -> dict:
    """Synthèse en un coup d'œil pour la page d'accueil / hero du dashboard."""
    kpi = kpi_annuels(projection)
    return {
        "ca_an1": int(kpi["CA"].iloc[0]) if len(kpi) > 0 else 0,
        "ca_an5": int(kpi["CA"].iloc[-1]) if len(kpi) > 0 else 0,
        "ebitda_an1": int(kpi["EBITDA"].iloc[0]) if len(kpi) > 0 else 0,
        "ebitda_an5": int(kpi["EBITDA"].iloc[-1]) if len(kpi) > 0 else 0,
        "resultat_net_cumule": int(kpi["Résultat net"].sum()),
        "cash_fin_periode": int(kpi["Cash cumulé fin année"].iloc[-1]) if len(kpi) > 0 else 0,
    }
