"""
Paramètres par défaut du plan financier — La Maison Verheyden (Liège, BE).

Boulangerie-pâtisserie haut de gamme avec 3 activités :
  1. Boulangerie (pain, viennoiserie)
  2. Pâtisserie (gâteaux, desserts)
  3. Traiteur B2B (cafés, hôtels, bureaux)

Structure : SRL Immobilière (détient l'immeuble) + SRL Exploitation.
Horizon : 60 mois (5 ans).
"""

from datetime import date


def params_defaut() -> dict:
    return {
        # ─── Méta ──────────────────────────────────────────────────────────
        "nom_plan": "Démo Maison Verheyden",
        "nom_entreprise": "La Maison Verheyden",
        "ville": "Liège",
        "date_ouverture": date(2027, 1, 1),
        "nb_mois_projection": 60,
        "devise": "EUR",

        # ─── Activité 1 : Boulangerie ──────────────────────────────────────
        "boulangerie": {
            "tickets_jour_an1": 250,
            "panier_moyen_an1": 7.50,
            "jours_ouverture_semaine": 6,
            # Croissance volumes par année (an 1 → 5)
            "croissance_volumes": [0.0, 0.04, 0.04, 0.03, 0.02],
            # Hausse prix annuelle
            "hausse_prix": [0.0, 0.025, 0.025, 0.025, 0.025],
            # Saisonnalité (jan→déc), pondère le volume mensuel
            "saisonnalite": [1.00, 0.95, 1.00, 1.05, 1.05, 0.95,
                             0.85, 0.85, 1.00, 1.05, 1.05, 1.20],
            # TVA moyenne (6% emporter alim. — quasi tout en boulangerie)
            "tva_taux": 0.06,
        },

        # ─── Activité 2 : Pâtisserie ──────────────────────────────────────
        "patisserie": {
            "tickets_jour_an1": 80,
            "panier_moyen_an1": 22.00,
            "jours_ouverture_semaine": 6,
            "croissance_volumes": [0.0, 0.05, 0.05, 0.04, 0.03],
            "hausse_prix": [0.0, 0.025, 0.025, 0.025, 0.025],
            # Pic décembre (Noël), Pâques (mars/avril), Saint-Valentin (fév),
            # fête des mères (mai). Creux été.
            "saisonnalite": [0.90, 1.30, 1.10, 1.40, 1.30, 1.00,
                             0.80, 0.80, 0.95, 1.05, 1.10, 1.80],
            "tva_taux": 0.06,
        },

        # ─── Activité 3 : Traiteur B2B ────────────────────────────────────
        "traiteur_b2b": {
            "nb_clients_an1": 8,         # clients réguliers
            "panier_mensuel_an1": 600,   # CA HT par client / mois
            # Croissance par acquisition de clients (nb absolu ajouté/an)
            "nouveaux_clients_par_an": [0, 3, 4, 3, 2],
            "hausse_prix": [0.0, 0.020, 0.020, 0.020, 0.020],
            "saisonnalite": [0.95, 0.95, 1.00, 1.00, 1.00, 0.95,
                             0.70, 0.75, 1.05, 1.05, 1.10, 1.30],
            "tva_taux": 0.06,
        },

        # ─── Charges variables (% CA HT par activité) ──────────────────────
        "charges_variables": {
            "boulangerie": {
                "matieres_premieres": 0.32,
                "emballages": 0.020,
                "energie_cuisson": 0.030,
            },
            "patisserie": {
                "matieres_premieres": 0.28,
                "emballages": 0.030,
                "energie_cuisson": 0.030,
            },
            "traiteur_b2b": {
                "matieres_premieres": 0.33,
                "emballages": 0.020,
                "livraison": 0.050,
            },
        },

        # ─── Personnel production (charges fixes directes) ─────────────────
        # Salaires bruts mensuels en EUR. ONSS patronal ajouté via belge.py.
        # Pécule juillet + 13e mois décembre (règles BE).
        "personnel_production": [
            {"poste": "Chef boulanger", "brut_mensuel": 4500, "nb": 1, "mois_embauche": 1},
            {"poste": "Boulanger",      "brut_mensuel": 3200, "nb": 2, "mois_embauche": 1},
            {"poste": "Apprenti boulangerie", "brut_mensuel": 2000, "nb": 1, "mois_embauche": 1},
            {"poste": "Chef pâtissier", "brut_mensuel": 4500, "nb": 1, "mois_embauche": 1},
            {"poste": "Pâtissier",      "brut_mensuel": 3000, "nb": 1, "mois_embauche": 1},
            {"poste": "Aide pâtissier", "brut_mensuel": 2400, "nb": 1, "mois_embauche": 4},
            {"poste": "Livreur traiteur", "brut_mensuel": 2500, "nb": 1, "mois_embauche": 1},
        ],

        # ─── Personnel administration & vente (charges fixes indirectes) ───
        "personnel_admin": [
            {"poste": "Gérant",                   "brut_mensuel": 5000, "nb": 1, "mois_embauche": 1},
            {"poste": "Vendeuse temps plein",     "brut_mensuel": 2500, "nb": 2, "mois_embauche": 1},
            {"poste": "Vendeuse temps partiel",   "brut_mensuel": 1500, "nb": 1, "mois_embauche": 1},
        ],

        # Taux ONSS patronal moyen (Belgique, hors réductions structurelles)
        "onss_patronal": 0.25,

        # ─── Charges fixes indirectes mensuelles (HT) ──────────────────────
        "charges_fixes_indirectes": {
            "loyer_inter_societes": 7500,   # SRL Immo facture SRL Exploit
            "energie_part_fixe": 1200,
            "eau": 200,
            "telecom_internet": 150,
            "marketing": 500,
            "assurances": 600,
            "comptable": 800,
            "honoraires_divers": 300,
            "entretien_maintenance": 400,
            "fournitures_bureau": 100,
        },

        # Inflation des charges fixes (par an)
        "inflation_charges": 0.02,

        # ─── Investissements (CAPEX) ───────────────────────────────────────
        "investissements_immo": [
            # SRL Immobilière : acquisition + travaux
            {"poste": "Terrain (non amortissable)", "montant": 150_000, "amort_annees": 0, "entite": "immo"},
            {"poste": "Bâtiment commercial",        "montant": 700_000, "amort_annees": 33, "entite": "immo"},
            {"poste": "Travaux d'aménagement immeuble", "montant": 50_000, "amort_annees": 10, "entite": "immo"},
        ],
        "investissements_exploit": [
            # SRL Exploitation
            {"poste": "Aménagement boutique + atelier", "montant": 120_000, "amort_annees": 10, "entite": "exploit"},
            {"poste": "Four à pain professionnel",      "montant": 45_000,  "amort_annees": 7,  "entite": "exploit"},
            {"poste": "Pétrin / façonneuse",            "montant": 25_000,  "amort_annees": 7,  "entite": "exploit"},
            {"poste": "Chambres de pousse + froide",    "montant": 30_000,  "amort_annees": 7,  "entite": "exploit"},
            {"poste": "Matériel pâtisserie",            "montant": 35_000,  "amort_annees": 7,  "entite": "exploit"},
            {"poste": "Vitrine réfrigérée",             "montant": 18_000,  "amort_annees": 10, "entite": "exploit"},
            {"poste": "Mobilier de vente",              "montant": 15_000,  "amort_annees": 10, "entite": "exploit"},
            {"poste": "Caisse + informatique",          "montant": 8_000,   "amort_annees": 5,  "entite": "exploit"},
            {"poste": "Véhicule traiteur frigorifique", "montant": 28_000,  "amort_annees": 5,  "entite": "exploit"},
        ],

        # ─── Financement ───────────────────────────────────────────────────
        "apports": {
            "immo":    200_000,
            "exploit": 80_000,
        },
        "prets": [
            {
                "id": 0,
                "entite": "immo",
                "libelle": "Prêt hypothécaire bâtiment",
                "montant": 700_000,
                "duree_annees": 20,
                "taux_annuel": 0.040,
                "type": "mensualite_constante",
                "mois_debut": 1,   # mois d'exploitation où démarre l'amort.
            },
            {
                "id": 1,
                "entite": "exploit",
                "libelle": "Prêt investissement matériel",
                "montant": 250_000,
                "duree_annees": 7,
                "taux_annuel": 0.050,
                "type": "mensualite_constante",
                "mois_debut": 1,
            },
        ],

        # ─── Fiscalité (Belgique) ──────────────────────────────────────────
        "fiscalite": {
            # ISOC : taux PME 20% sur 1ère tranche 100k€, 25% au-delà
            "isoc_taux_pme": 0.20,
            "isoc_seuil_pme": 100_000,
            "isoc_taux_standard": 0.25,
            # TVA payée le mois suivant clôture trimestre
            # (avril, juillet, octobre, janvier)
            "tva_periodicite": "trimestrielle",
            # Précompte immobilier annuel (SRL Immo)
            "precompte_immobilier_annuel": 4_500,
        },

        # ─── BFR / délais paiement (en jours) ──────────────────────────────
        "bfr": {
            "delai_clients_b2c": 0,        # boulangerie/pâtisserie : cash
            "delai_clients_b2b": 30,       # traiteur B2B
            "delai_fournisseurs": 30,
            "delai_personnel": 0,          # paie en fin de mois
            "stock_jours": 5,              # stock matières
        },
    }


# ─── Validation simple ───────────────────────────────────────────────────────

def valider_params(p: dict) -> list[str]:
    """Retourne la liste des erreurs détectées (vide si OK)."""
    erreurs = []
    if p.get("nb_mois_projection", 0) <= 0:
        erreurs.append("nb_mois_projection doit être > 0")
    for act in ("boulangerie", "patisserie", "traiteur_b2b"):
        if act not in p:
            erreurs.append(f"Section '{act}' manquante")
    if not p.get("prets"):
        erreurs.append("Aucun prêt défini")
    if not p.get("investissements_immo") and not p.get("investissements_exploit"):
        erreurs.append("Aucun investissement défini")
    return erreurs
