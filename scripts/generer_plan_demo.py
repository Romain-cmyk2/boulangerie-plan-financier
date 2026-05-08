"""
Script utilitaire : génère le plan de démo par défaut + smoke-test du moteur.

Usage : python scripts/generer_plan_demo.py
"""

import sys
from pathlib import Path

# Permettre l'import depuis la racine du projet
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.schema import params_defaut, valider_params
from core.persistence import sauvegarder_plan
from core.calculs import projection_complete
from core.indicateurs import kpi_annuels, synthese_globale


def main():
    p = params_defaut()
    erreurs = valider_params(p)
    if erreurs:
        print("[ERREUR] Validation :")
        for e in erreurs:
            print(f"   - {e}")
        return 1

    nom = p["nom_plan"]
    chemin = sauvegarder_plan(nom, p)
    print(f"[OK] Plan sauvegarde : {chemin}")

    print("\n[Smoke test moteur de projection]")
    proj = projection_complete(p)

    print(f"   - Index                   : {len(proj['index'])} mois")
    print(f"   - Ventes total mois 1     : {proj['ventes']['ventes_total'].iloc[0]:>12,.0f} EUR")
    print(f"   - Ventes total mois 12    : {proj['ventes']['ventes_total'].iloc[11]:>12,.0f} EUR")
    print(f"   - EBITDA consolide mois 1 : {proj['pl_consolide']['ebitda'].iloc[0]:>12,.0f} EUR")
    print(f"   - EBITDA consolide mois 60: {proj['pl_consolide']['ebitda'].iloc[59]:>12,.0f} EUR")

    print("\n[KPIs annuels (consolide)]")
    kpi = kpi_annuels(proj)
    txt = kpi[["CA", "EBITDA", "Taux EBITDA %", "Résultat net",
                "Cash cumulé fin année"]].to_string()
    # Pour console Windows cp1252, on translittere les accents.
    for src, dst in [("é", "e"), ("è", "e"), ("ê", "e"), ("É", "E"),
                     ("à", "a"), ("â", "a"), ("ô", "o"), ("ù", "u")]:
        txt = txt.replace(src, dst)
    print(txt)

    print("\n[Synthese globale]")
    synth = synthese_globale(proj)
    for k, v in synth.items():
        print(f"   - {k:<25} : {v:>12,.0f} EUR")

    return 0


if __name__ == "__main__":
    sys.exit(main())
