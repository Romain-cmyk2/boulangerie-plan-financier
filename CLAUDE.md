# Plan Financier - La Maison Verheyden (boulangerie-pâtisserie Liège)

## Objectif
Application de démonstration SConseil. Sert à :
- Faire des démos en clientèle (5 minutes : prospect modifie une hypothèse, voit l'impact, télécharge HTML)
- Captures d'écran et vidéos LinkedIn pour expliquer la méthodologie

## Entreprise fictive
- **Nom** : La Maison Verheyden
- **Localisation** : Liège, Belgique
- **Structure** : 2 entités belges
  - SRL Immobilière Verheyden (détient l'immeuble, perçoit loyer)
  - SRL La Maison Verheyden (exploitation)
- **3 activités** : Boulangerie / Pâtisserie / Traiteur B2B
- **Horizon de projection** : 5 ans (60 mois)

## Règles métier critiques (Belgique)
- **SRL** (et non SARL — on est en Belgique)
- **Personnel** : pécule de vacances (juillet) + 13e mois (décembre) au prorata
- **Cash vs P&L** : P&L lissé (masse/12), cash suit le prorata réel
- **TVA** : 6% (alimentaire emporter), 12% (consommation sur place), 21% (boissons alcool/non-alimentaire) — paiement le mois suivant clôture trimestre (avril, juillet, octobre, janvier)
- **Modèle en HT** : ajouter TVA nette au cash flow mensuel
- **ISOC** : charge en décembre, paiement en juin N+1. Taux PME 20% sur 1ère tranche, 25% au-delà
- **Loyer inter-sociétés** : SRL Immo facture mensuellement à SRL Exploit
- **Prêts** : clé par index (pas par nom) pour éviter doublons
- **Termes** : "mensualité constante" (pas "annuité constante")

## Stack technique
- Framework : Streamlit (Python)
- Calculs : pandas, numpy
- Graphiques : Plotly (texte gras, taille ≥ 14px, couleurs contrastées)
- Stockage : JSON dans `/plans/`
- Exports : HTML (priorité démo), PDF (fpdf2), PPTX (python-pptx), Excel (openpyxl)
- Auth : `CODE_EDITION` lu depuis `st.secrets`, fallback `mpl2026` en mode local
- Sync GitHub : `core/github_sync.py`, token via `st.secrets["GITHUB_TOKEN"]`. Sans secrets, mode 100% local.
- Déploiement : Streamlit Community Cloud, repo `boulangerie-plan-financier` (voir DEPLOIEMENT.md)
- Auto-save hypothèses : `local_only=True` (n'utilise pas GitHub) — la sync GitHub se fait sur clic explicite « Sauvegarder + Sync »

## Architecture (verrouillée)
- 1 fichier = 1 responsabilité, max 500 lignes
- `app.py` = router uniquement (~200 lignes max)
- `core/` = moteur pur (sans Streamlit)
- `views/` = UI Streamlit (renommé pour éviter le multipage auto-discovery de Streamlit)
- `exports/` = générateurs de fichiers

## Approche projet
- TOUJOURS proposer plan AVANT de coder
- Auto-save local à chaque section critique, push GitHub uniquement sur bouton
- Charte graphique unique (un seul module style.py si besoin)
- Ne pas itérer 10x sur le CSS : 2-3 options et validation
- Paramètres communs : verrouillés par défaut, bouton Modifier pour éditer
- Tableau d'amortissement par prêt dans un expander

## Phases
1. ✅ Phase 1 — Fondations : schéma + moteur + 1 plan exemple + page accueil
2. ⏳ Phase 2 — Pages d'hypothèses (5 sections)
3. ⏳ Phase 3 — Visualisation (dashboard + graphes)
4. ⏳ Phase 4 — Exports (HTML d'abord, puis PDF/PPT/Excel)
5. ⏳ Phase 5 — Polish (auth, GitHub sync, photos, charte)
