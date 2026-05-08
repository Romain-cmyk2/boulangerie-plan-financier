"""
Moteur de projection financière — La Maison Verheyden.

Sortie principale : projection_complete(params) → dict de DataFrames mensuels
  - 'ventes'        : CA HT par activité, par mois
  - 'charges_var'   : charges variables par activité, par mois
  - 'personnel'     : coûts P&L et cash, par catégorie, par mois
  - 'pl_exploit'    : P&L SRL Exploitation
  - 'pl_immo'       : P&L SRL Immobilière
  - 'pl_consolide'  : P&L consolidé
  - 'cash_exploit'  : cash flow SRL Exploit
  - 'cash_immo'     : cash flow SRL Immo
  - 'amortissements': détail par investissement
  - 'prets'         : tableau d'amortissement par prêt
  - 'tva'           : collectée / déductible / à payer par mois
  - 'index'         : DataFrame de référence (date, mois_calendrier, annee_exploit)

Pas de Streamlit ici : moteur pur, testable.
"""

from datetime import date
import pandas as pd
import numpy as np

from .belge import (
    cout_charge_mensuel, cout_pl_mensuel, cash_personnel_mois,
    masse_annuelle_chargee, est_mois_paiement_tva, trimestre_de_mois,
    amortissement_mensuel, mensualite_constante, tableau_amortissement,
    calc_isoc, mois_range,
)


# ─── Index temporel ──────────────────────────────────────────────────────────

def construire_index(p: dict) -> pd.DataFrame:
    """DataFrame avec une ligne par mois : date, mois_calendrier, annee_exploit."""
    nb = p["nb_mois_projection"]
    d0 = p["date_ouverture"]
    if isinstance(d0, str):
        d0 = date.fromisoformat(d0)
    dates = mois_range(d0, nb)
    return pd.DataFrame({
        "mois_idx": list(range(1, nb + 1)),
        "date": dates,
        "annee_calendrier": [d.year for d in dates],
        "mois_calendrier": [d.month for d in dates],
        "annee_exploit": [(k - 1) // 12 + 1 for k in range(1, nb + 1)],
    })


# ─── Ventes par activité ────────────────────────────────────────────────────

def _ventes_b2c(p_act: dict, idx: pd.DataFrame) -> pd.Series:
    """Ventes mensuelles d'une activité B2C (boulangerie ou pâtisserie)."""
    tickets_an1 = p_act["tickets_jour_an1"]
    panier_an1 = p_act["panier_moyen_an1"]
    jours_sem = p_act["jours_ouverture_semaine"]
    croiss = p_act["croissance_volumes"]
    hausse = p_act["hausse_prix"]
    saison = p_act["saisonnalite"]

    out = []
    for _, r in idx.iterrows():
        ae = int(r["annee_exploit"])
        i = min(ae, len(croiss)) - 1
        # Volumes annuels cumulés
        vol_factor = 1.0
        for k in range(i + 1):
            vol_factor *= (1 + croiss[k])
        prix_factor = 1.0
        for k in range(i + 1):
            prix_factor *= (1 + hausse[k])
        tickets = tickets_an1 * vol_factor
        panier = panier_an1 * prix_factor
        # Nombre de jours ouvrés du mois (approx = jours_sem * 4.33)
        jours_mois = jours_sem * 4.33
        # Saisonnalité
        saison_factor = saison[int(r["mois_calendrier"]) - 1]
        ca = tickets * panier * jours_mois * saison_factor
        out.append(ca)
    return pd.Series(out, index=idx.index)


def _ventes_b2b(p_act: dict, idx: pd.DataFrame) -> pd.Series:
    """Ventes mensuelles traiteur B2B."""
    nb_clients_an1 = p_act["nb_clients_an1"]
    panier_an1 = p_act["panier_mensuel_an1"]
    nouveaux = p_act["nouveaux_clients_par_an"]
    hausse = p_act["hausse_prix"]
    saison = p_act["saisonnalite"]

    out = []
    for _, r in idx.iterrows():
        ae = int(r["annee_exploit"])
        i = min(ae, len(nouveaux)) - 1
        # Stock de clients cumulé en fin d'année courante
        nb_clients = nb_clients_an1 + sum(nouveaux[1:i + 1]) if i >= 1 else nb_clients_an1
        prix_factor = 1.0
        for k in range(i + 1):
            prix_factor *= (1 + hausse[k])
        panier = panier_an1 * prix_factor
        saison_factor = saison[int(r["mois_calendrier"]) - 1]
        ca = nb_clients * panier * saison_factor
        out.append(ca)
    return pd.Series(out, index=idx.index)


def calc_ventes(p: dict, idx: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame(index=idx.index)
    df["ventes_boulangerie"] = _ventes_b2c(p["boulangerie"], idx)
    df["ventes_patisserie"] = _ventes_b2c(p["patisserie"], idx)
    df["ventes_traiteur_b2b"] = _ventes_b2b(p["traiteur_b2b"], idx)
    df["ventes_total"] = df.sum(axis=1)
    return df


# ─── Charges variables ──────────────────────────────────────────────────────

def calc_charges_variables(p: dict, df_ventes: pd.DataFrame) -> pd.DataFrame:
    cv = p["charges_variables"]
    df = pd.DataFrame(index=df_ventes.index)
    for act_key, ca_col in [
        ("boulangerie", "ventes_boulangerie"),
        ("patisserie", "ventes_patisserie"),
        ("traiteur_b2b", "ventes_traiteur_b2b"),
    ]:
        total_pct = sum(cv[act_key].values())
        df[f"cv_{act_key}"] = df_ventes[ca_col] * total_pct
    df["cv_total"] = df.filter(like="cv_").sum(axis=1)
    return df


# ─── Personnel : P&L lissé + cash réel ──────────────────────────────────────

def _personnel_lignes(postes: list[dict], idx: pd.DataFrame,
                       onss: float, label: str) -> pd.DataFrame:
    """
    Génère deux colonnes : '{label}_pl' (lissé) et '{label}_cash' (réel BE).
    Un poste démarre au 'mois_embauche' (1-indexed sur la projection).
    """
    pl = np.zeros(len(idx))
    cash = np.zeros(len(idx))
    for poste in postes:
        brut = poste["brut_mensuel"]
        nb = poste["nb"]
        debut = poste["mois_embauche"]
        cout_pl = cout_pl_mensuel(brut, onss) * nb
        for i, r in idx.iterrows():
            mois_idx = int(r["mois_idx"])
            if mois_idx < debut:
                continue
            pl[i] += cout_pl
            mois_cal = int(r["mois_calendrier"])
            cash[i] += cash_personnel_mois(
                brut, onss, mois_cal, mois_actif=True
            ) * nb
    return pd.DataFrame({f"{label}_pl": pl, f"{label}_cash": cash}, index=idx.index)


def calc_personnel(p: dict, idx: pd.DataFrame) -> pd.DataFrame:
    onss = p["onss_patronal"]
    df_prod = _personnel_lignes(p["personnel_production"], idx, onss, "perso_prod")
    df_admin = _personnel_lignes(p["personnel_admin"], idx, onss, "perso_admin")
    return pd.concat([df_prod, df_admin], axis=1)


# ─── Charges fixes indirectes ───────────────────────────────────────────────

def calc_charges_fixes(p: dict, idx: pd.DataFrame) -> pd.DataFrame:
    cfi = p["charges_fixes_indirectes"]
    inflation = p["inflation_charges"]
    df = pd.DataFrame(index=idx.index)
    for poste, montant in cfi.items():
        col = []
        for _, r in idx.iterrows():
            ae = int(r["annee_exploit"])
            facteur_inflation = (1 + inflation) ** (ae - 1)
            col.append(montant * facteur_inflation)
        df[f"cf_{poste}"] = col
    df["cf_total"] = df.filter(like="cf_").sum(axis=1)
    return df


# ─── Investissements & amortissements ──────────────────────────────────────

def calc_amortissements(p: dict, idx: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Retourne {'amort_immo': DF mensuel, 'amort_exploit': DF mensuel,
              'detail': DF par poste}.
    """
    out = {}
    for cle_invest, label in [("investissements_immo", "amort_immo"),
                               ("investissements_exploit", "amort_exploit")]:
        col = np.zeros(len(idx))
        for inv in p.get(cle_invest, []):
            am = amortissement_mensuel(inv["montant"], inv["amort_annees"])
            for i, _ in idx.iterrows():
                col[i] += am
        out[label] = pd.Series(col, index=idx.index)
    return out


# ─── Prêts ──────────────────────────────────────────────────────────────────

def calc_prets(p: dict, idx: pd.DataFrame) -> dict:
    """
    Retourne :
      - 'tableaux'     : {pret_id: list[dict]} tableau d'amortissement
      - 'mensuel'      : DF avec interets/capital/mensualite par entité par mois
      - 'capital_restant_initial' : {pret_id: capital initial}
    """
    nb = len(idx)
    cols = {
        "interets_immo": np.zeros(nb), "capital_immo": np.zeros(nb), "mens_immo": np.zeros(nb),
        "interets_exploit": np.zeros(nb), "capital_exploit": np.zeros(nb), "mens_exploit": np.zeros(nb),
    }
    tableaux = {}
    capital_restants = {}
    for pret in p.get("prets", []):
        pid = pret["id"]
        entite = pret["entite"]
        debut = pret["mois_debut"]
        tab = tableau_amortissement(
            pret["montant"], pret["taux_annuel"], pret["duree_annees"]
        )
        tableaux[pid] = tab
        capital_restants[pid] = pret["montant"]
        for k, ligne in enumerate(tab):
            mois_proj = debut + k
            if mois_proj < 1 or mois_proj > nb:
                continue
            i = mois_proj - 1
            cols[f"interets_{entite}"][i] += ligne["interets"]
            cols[f"capital_{entite}"][i] += ligne["capital_rembourse"]
            cols[f"mens_{entite}"][i] += ligne["mensualite"]
    df = pd.DataFrame(cols, index=idx.index)
    return {"tableaux": tableaux, "mensuel": df, "capital_initial": capital_restants}


# ─── P&L par entité ─────────────────────────────────────────────────────────

def calc_pl(p: dict, idx: pd.DataFrame, ventes: pd.DataFrame, cv: pd.DataFrame,
            personnel: pd.DataFrame, cf: pd.DataFrame,
            amort: dict, prets: dict) -> dict[str, pd.DataFrame]:
    """
    P&L mensuel SRL Exploit, SRL Immo, et consolidé.
    Le loyer inter-sociétés est PRODUIT chez immo et CHARGE chez exploit
    → s'élimine au consolidé.
    """
    nb = len(idx)
    # ── SRL Exploitation ───────────────────────────────────────────────────
    pl_e = pd.DataFrame(index=idx.index)
    pl_e["ca"] = ventes["ventes_total"]
    pl_e["charges_variables"] = -cv["cv_total"]
    pl_e["marge_brute"] = pl_e["ca"] + pl_e["charges_variables"]

    pl_e["personnel_production"] = -personnel["perso_prod_pl"]
    pl_e["personnel_admin"] = -personnel["perso_admin_pl"]

    # Charges fixes indirectes — toutes vont à exploit
    cf_total = cf["cf_total"]
    pl_e["charges_fixes"] = -cf_total
    pl_e["ebitda"] = (pl_e["marge_brute"]
                      + pl_e["personnel_production"]
                      + pl_e["personnel_admin"]
                      + pl_e["charges_fixes"])
    pl_e["amortissements"] = -amort["amort_exploit"]
    pl_e["ebit"] = pl_e["ebitda"] + pl_e["amortissements"]
    pl_e["interets"] = -prets["mensuel"]["interets_exploit"]
    pl_e["resultat_avant_impot"] = pl_e["ebit"] + pl_e["interets"]

    # ISOC : charge en décembre sur résultat annuel imposable
    fisc = p["fiscalite"]
    isoc_mensuel = np.zeros(nb)
    for annee_calc in idx["annee_exploit"].unique():
        mask = idx["annee_exploit"] == annee_calc
        ri_annuel = pl_e.loc[mask, "resultat_avant_impot"].sum()
        impot = calc_isoc(ri_annuel, fisc["isoc_taux_pme"],
                          fisc["isoc_seuil_pme"], fisc["isoc_taux_standard"])
        # on inscrit l'ISOC dans le dernier mois de l'année d'exploitation
        last_mois = idx.loc[mask, "mois_idx"].max()
        if last_mois is not None:
            isoc_mensuel[int(last_mois) - 1] = -impot
    pl_e["isoc"] = isoc_mensuel
    pl_e["resultat_net"] = pl_e["resultat_avant_impot"] + pl_e["isoc"]

    # ── SRL Immobilière ────────────────────────────────────────────────────
    pl_i = pd.DataFrame(index=idx.index)
    loyer_mensuel = p["charges_fixes_indirectes"]["loyer_inter_societes"]
    inflation = p["inflation_charges"]
    loyers = []
    for _, r in idx.iterrows():
        ae = int(r["annee_exploit"])
        loyers.append(loyer_mensuel * (1 + inflation) ** (ae - 1))
    pl_i["ca"] = pd.Series(loyers, index=idx.index)
    # Précompte immobilier annuel — réparti sur 12 mois pour P&L
    pi = fisc["precompte_immobilier_annuel"]
    pl_i["precompte_immobilier"] = -pi / 12
    pl_i["amortissements"] = -amort["amort_immo"]
    pl_i["ebit"] = pl_i["ca"] + pl_i["precompte_immobilier"] + pl_i["amortissements"]
    pl_i["interets"] = -prets["mensuel"]["interets_immo"]
    pl_i["resultat_avant_impot"] = pl_i["ebit"] + pl_i["interets"]
    isoc_immo = np.zeros(nb)
    for annee_calc in idx["annee_exploit"].unique():
        mask = idx["annee_exploit"] == annee_calc
        ri_annuel = pl_i.loc[mask, "resultat_avant_impot"].sum()
        impot = calc_isoc(ri_annuel, fisc["isoc_taux_pme"],
                          fisc["isoc_seuil_pme"], fisc["isoc_taux_standard"])
        last_mois = idx.loc[mask, "mois_idx"].max()
        if last_mois is not None:
            isoc_immo[int(last_mois) - 1] = -impot
    pl_i["isoc"] = isoc_immo
    pl_i["resultat_net"] = pl_i["resultat_avant_impot"] + pl_i["isoc"]

    # ── Consolidé ─────────────────────────────────────────────────────────
    # Le loyer inter-sociétés s'élimine : il est dans cf_loyer côté exploit
    # (négatif) et dans pl_i["ca"] (positif). Au consolidé on les ajoute
    # tels quels — ils s'annulent naturellement.
    pl_c = pd.DataFrame(index=idx.index)
    pl_c["ca"] = pl_e["ca"]   # loyer immo n'est pas du CA pour le groupe
    pl_c["charges_variables"] = pl_e["charges_variables"]
    pl_c["marge_brute"] = pl_e["marge_brute"]
    pl_c["personnel_production"] = pl_e["personnel_production"]
    pl_c["personnel_admin"] = pl_e["personnel_admin"]
    # Charges fixes consolidées : cf_total exploit moins le loyer inter-sociétés
    cf_hors_loyer = cf_total - cf["cf_loyer_inter_societes"]
    pl_c["charges_fixes"] = -cf_hors_loyer + pl_i["precompte_immobilier"]
    pl_c["ebitda"] = (pl_c["marge_brute"] + pl_c["personnel_production"]
                      + pl_c["personnel_admin"] + pl_c["charges_fixes"])
    pl_c["amortissements"] = pl_e["amortissements"] + pl_i["amortissements"]
    pl_c["ebit"] = pl_c["ebitda"] + pl_c["amortissements"]
    pl_c["interets"] = pl_e["interets"] + pl_i["interets"]
    pl_c["resultat_avant_impot"] = pl_c["ebit"] + pl_c["interets"]
    pl_c["isoc"] = pl_e["isoc"] + pl_i["isoc"]
    pl_c["resultat_net"] = pl_c["resultat_avant_impot"] + pl_c["isoc"]

    return {"exploit": pl_e, "immo": pl_i, "consolide": pl_c}


# ─── Cash flow simple (Phase 1) ─────────────────────────────────────────────

def calc_cash(p: dict, idx: pd.DataFrame, pl: dict, amort: dict, prets: dict,
              ventes: pd.DataFrame, cv: pd.DataFrame, personnel: pd.DataFrame,
              cf: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Cash flow mensuel par entité. En Phase 1 :
      - On part du résultat net
      - On rajoute amortissements (non-cash)
      - On corrige la TVA (collectée - déductible) avec décalage trimestriel
      - On corrige le décalage personnel (P&L lissé vs cash réel BE)
      - On corrige l'ISOC (charge décembre, paiement juin N+1)
      - On retire le remboursement de capital des prêts
      - Le BFR détaillé est repoussé en Phase 2 (modèle simple ici)
    """
    fisc = p["fiscalite"]
    nb = len(idx)

    # ── Personnel : décalage P&L vs cash ──────────────────────────────────
    delta_perso_prod = personnel["perso_prod_cash"] - personnel["perso_prod_pl"]
    delta_perso_admin = personnel["perso_admin_cash"] - personnel["perso_admin_pl"]

    # ── TVA : collectée moins déductible, payée le mois suivant clôture ──
    # Approximation : TVA moyenne 6% sur ventes, 21% sur charges déductibles
    tva_coll = (ventes["ventes_boulangerie"] * p["boulangerie"]["tva_taux"]
                + ventes["ventes_patisserie"] * p["patisserie"]["tva_taux"]
                + ventes["ventes_traiteur_b2b"] * p["traiteur_b2b"]["tva_taux"])
    # TVA déductible : sur cv (matières) à 6% pour alim, sur cf à 21%
    tva_ded_cv = cv["cv_total"] * 0.06
    tva_ded_cf = cf["cf_total"] * 0.21 * 0.5  # ~50% des charges fixes sont avec TVA déductible
    tva_due_mois = tva_coll - tva_ded_cv - tva_ded_cf

    # Cash flow TVA : exploit collecte/paie, étalé par trimestre
    cash_tva_exploit = np.zeros(nb)
    # Accumulation par trimestre
    by_trim = {}
    for i, r in idx.iterrows():
        annee = int(r["annee_calendrier"])
        mc = int(r["mois_calendrier"])
        trim = trimestre_de_mois(mc)
        cle = (annee, trim)
        by_trim[cle] = by_trim.get(cle, 0.0) + tva_due_mois.iloc[i]
    # Paiement trimestre N → mois suivant clôture
    for (annee, trim), montant in by_trim.items():
        # paiement = mois 4, 7, 10 ou 1 (annee+1 pour T4)
        if trim == 1:
            pay_y, pay_m = annee, 4
        elif trim == 2:
            pay_y, pay_m = annee, 7
        elif trim == 3:
            pay_y, pay_m = annee, 10
        else:
            pay_y, pay_m = annee + 1, 1
        match = idx[(idx["annee_calendrier"] == pay_y) & (idx["mois_calendrier"] == pay_m)]
        if len(match) == 1:
            i_pay = int(match["mois_idx"].iloc[0]) - 1
            cash_tva_exploit[i_pay] -= montant
    # Pendant le mois courant, la TVA collectée est encaissée et la déductible est décaissée
    # Comme on travaille en HT, on ajoute juste le solde de trésorerie TVA
    # (encaissements TTC - décaissements TTC + paiement trim. négatif quand il a lieu)
    cash_tva_exploit_courant = tva_due_mois.values  # encaissée mensuelle (solde positif si TVA due)
    cash_tva_net = cash_tva_exploit_courant + cash_tva_exploit

    # ── ISOC : charge en déc, paiement en juin N+1 ───────────────────────
    cash_isoc_exploit = np.zeros(nb)
    cash_isoc_immo = np.zeros(nb)
    for annee_calc in idx["annee_exploit"].unique():
        mask = idx["annee_exploit"] == annee_calc
        last = idx.loc[mask, "mois_idx"].max()
        if last is None:
            continue
        i_charge = int(last) - 1
        # Paiement en juin de l'année calendaire suivante
        annee_paye = int(idx.iloc[i_charge]["annee_calendrier"]) + 1
        match = idx[(idx["annee_calendrier"] == annee_paye)
                    & (idx["mois_calendrier"] == 6)]
        if len(match) == 1:
            i_pay = int(match["mois_idx"].iloc[0]) - 1
            cash_isoc_exploit[i_pay] = pl["exploit"].iloc[i_charge]["isoc"]
            cash_isoc_immo[i_pay] = pl["immo"].iloc[i_charge]["isoc"]

    # ── SRL Exploitation ──────────────────────────────────────────────────
    cash_e = pd.DataFrame(index=idx.index)
    cash_e["resultat_net"] = pl["exploit"]["resultat_net"]
    cash_e["amort_add_back"] = -pl["exploit"]["amortissements"]  # non-cash → repris
    cash_e["isoc_neutralise"] = -pl["exploit"]["isoc"]            # neutralise charge mensuelle
    cash_e["isoc_paye"] = cash_isoc_exploit                       # paiement réel
    cash_e["delta_personnel"] = -(delta_perso_prod + delta_perso_admin)  # P&L>cash en N-juillet/déc
    # Actually: cash > P&L when paying pécule/13e — so "delta" > 0 means MORE cash out than P&L
    # Correction : cash personnel = perso_cash, P&L = perso_pl. CFG = -pertes cash réelle
    # On a déjà retiré perso_pl dans le résultat net (via P&L). Il faut substituer cash réel.
    # Donc on AJOUTE perso_pl et on RETIRE perso_cash → impact = -(cash - pl) = pl - cash
    cash_e["delta_personnel"] = (personnel["perso_prod_pl"] + personnel["perso_admin_pl"]
                                  - personnel["perso_prod_cash"] - personnel["perso_admin_cash"])
    cash_e["solde_tva"] = cash_tva_net
    cash_e["remboursement_capital"] = -prets["mensuel"]["capital_exploit"]
    cash_e["cash_net_mois"] = cash_e[
        ["resultat_net", "amort_add_back", "isoc_neutralise", "isoc_paye",
         "delta_personnel", "solde_tva", "remboursement_capital"]
    ].sum(axis=1)
    # Apport initial au mois 1
    cash_e["apport_initial"] = 0.0
    cash_e.iloc[0, cash_e.columns.get_loc("apport_initial")] = p["apports"]["exploit"]
    # CAPEX investi au mois 1 (simplification Phase 1)
    capex_e = sum(inv["montant"] for inv in p.get("investissements_exploit", []))
    cash_e["capex"] = 0.0
    cash_e.iloc[0, cash_e.columns.get_loc("capex")] = -capex_e
    # Tirage prêt au mois de début (mois 1 par défaut)
    cash_e["tirage_pret"] = 0.0
    for pret in p.get("prets", []):
        if pret["entite"] != "exploit":
            continue
        i_tirage = pret["mois_debut"] - 1
        if 0 <= i_tirage < nb:
            cash_e.iloc[i_tirage, cash_e.columns.get_loc("tirage_pret")] += pret["montant"]
    cash_e["cash_total_mois"] = (cash_e["cash_net_mois"] + cash_e["apport_initial"]
                                  + cash_e["capex"] + cash_e["tirage_pret"])
    cash_e["cash_cumule"] = cash_e["cash_total_mois"].cumsum()

    # ── SRL Immobilière ───────────────────────────────────────────────────
    cash_i = pd.DataFrame(index=idx.index)
    cash_i["resultat_net"] = pl["immo"]["resultat_net"]
    cash_i["amort_add_back"] = -pl["immo"]["amortissements"]
    cash_i["isoc_neutralise"] = -pl["immo"]["isoc"]
    cash_i["isoc_paye"] = cash_isoc_immo
    cash_i["remboursement_capital"] = -prets["mensuel"]["capital_immo"]
    # Précompte immobilier : payé en une fois (octobre, simplification)
    pi_paye = np.zeros(nb)
    for ae in idx["annee_exploit"].unique():
        mask = (idx["annee_exploit"] == ae) & (idx["mois_calendrier"] == 10)
        if mask.any():
            i = int(idx.loc[mask, "mois_idx"].iloc[0]) - 1
            pi_paye[i] = -fisc["precompte_immobilier_annuel"]
    cash_i["precompte_paye"] = pi_paye
    cash_i["precompte_neutralise"] = -pl["immo"]["precompte_immobilier"]
    cash_i["cash_net_mois"] = cash_i[
        ["resultat_net", "amort_add_back", "isoc_neutralise", "isoc_paye",
         "remboursement_capital", "precompte_paye", "precompte_neutralise"]
    ].sum(axis=1)
    cash_i["apport_initial"] = 0.0
    cash_i.iloc[0, cash_i.columns.get_loc("apport_initial")] = p["apports"]["immo"]
    capex_i = sum(inv["montant"] for inv in p.get("investissements_immo", []))
    cash_i["capex"] = 0.0
    cash_i.iloc[0, cash_i.columns.get_loc("capex")] = -capex_i
    cash_i["tirage_pret"] = 0.0
    for pret in p.get("prets", []):
        if pret["entite"] != "immo":
            continue
        i_tirage = pret["mois_debut"] - 1
        if 0 <= i_tirage < nb:
            cash_i.iloc[i_tirage, cash_i.columns.get_loc("tirage_pret")] += pret["montant"]
    cash_i["cash_total_mois"] = (cash_i["cash_net_mois"] + cash_i["apport_initial"]
                                  + cash_i["capex"] + cash_i["tirage_pret"])
    cash_i["cash_cumule"] = cash_i["cash_total_mois"].cumsum()

    return {"exploit": cash_e, "immo": cash_i}


# ─── Orchestrateur principal ────────────────────────────────────────────────

def projection_complete(p: dict) -> dict:
    """
    Calcule la projection complète et retourne un dict de DataFrames.
    """
    idx = construire_index(p)
    ventes = calc_ventes(p, idx)
    cv = calc_charges_variables(p, ventes)
    personnel = calc_personnel(p, idx)
    cf = calc_charges_fixes(p, idx)
    amort = calc_amortissements(p, idx)
    prets = calc_prets(p, idx)
    pl = calc_pl(p, idx, ventes, cv, personnel, cf, amort, prets)
    cash = calc_cash(p, idx, pl, amort, prets, ventes, cv, personnel, cf)

    return {
        "index": idx,
        "ventes": ventes,
        "charges_var": cv,
        "personnel": personnel,
        "charges_fixes": cf,
        "amortissements": amort,
        "prets": prets,
        "pl_exploit": pl["exploit"],
        "pl_immo": pl["immo"],
        "pl_consolide": pl["consolide"],
        "cash_exploit": cash["exploit"],
        "cash_immo": cash["immo"],
    }
