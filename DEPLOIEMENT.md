# Déploiement — Plan Financier La Maison Verheyden

## Prérequis

- Compte GitHub
- Compte Streamlit Community Cloud (https://streamlit.io/cloud, connecté à GitHub)

---

## 1) Créer le repo GitHub

```bash
cd C:\Users\Iziboard2\boulangerie_plan_financier
git init
git add .
git commit -m "Initial commit : plan financier La Maison Verheyden"
```

Crée un repo public sur https://github.com/new (suggestion : `Romain-cmyk2/boulangerie-plan-financier`), puis :

```bash
git branch -M main
git remote add origin https://github.com/Romain-cmyk2/boulangerie-plan-financier.git
git push -u origin main
```

---

## 2) Créer un fine-grained token GitHub

1. Va sur https://github.com/settings/personal-access-tokens/new
2. **Repository access** : « Only select repositories » → choisis le repo créé
3. **Permissions** : Repository → Contents → **Read and write**
4. Nom : `boulangerie-plan-financier-sync`, expiration : 90j ou 1 an
5. Copie le token (commence par `github_pat_…`)

---

## 3) Déployer sur Streamlit Cloud

1. Va sur https://share.streamlit.io
2. Clique « New app »
3. Repo : `Romain-cmyk2/boulangerie-plan-financier`, branche : `main`, fichier : `app.py`
4. Avant le déploiement, clique **« Advanced settings »** → onglet **Secrets** et colle :

```toml
CODE_EDITION = "mpl2026"

GITHUB_TOKEN  = "github_pat_xxxxxxxxxxxxxxxxxxx"
GITHUB_REPO   = "Romain-cmyk2/boulangerie-plan-financier"
GITHUB_BRANCH = "main"
```

5. Clique « Deploy ». Le 1er build prend 2-3 minutes.

---

## 4) Vérification post-déploiement

- Page d'accueil : tu vois le plan « Démo Maison Verheyden »
- Sidebar : badge **🟢 Sync GitHub active**
- Active l'édition (`mpl2026`) → modifie une hypothèse → clique « 💾 Sauvegarder + Sync »
- Va sur GitHub → le fichier `plans/Démo Maison Verheyden.json` doit avoir un commit récent

---

## Maintenance

- **Mettre à jour le code** : commits sur `main` → Streamlit Cloud redéploie automatiquement.
- **Renouveler le token GitHub** : si tu mets une expiration, pense à régénérer et mettre à jour les secrets sur Streamlit Cloud avant l'expiration.
- **Voir les logs** : sur Streamlit Cloud, bouton « Manage app » → onglet « Logs ».

---

## Mode local (sans GitHub)

L'app fonctionne sans secrets.toml :
- `CODE_EDITION` → fallback `mpl2026`
- Pas de sync GitHub : les plans sont stockés dans `plans/` sur ton disque

Pour lancer :
```
streamlit run app.py
```

Ou double-clic sur `lancer.bat`.
