"""
Persistance des plans en JSON.

Local : fichiers dans /plans/. Sur Streamlit Cloud (filesystem éphémère),
synchronisation transparente avec GitHub via core.github_sync.

Comportement :
  - Au 1er run de la session : pull de tous les .json depuis GitHub si sync activée.
  - sauvegarder_plan : écrit en local + push GitHub (sauf local_only=True).
  - supprimer_plan : suppression locale + suppression GitHub.
  - L'app reste fonctionnelle si GitHub sync est inactive (mode dev).
"""

from datetime import date
from pathlib import Path
import copy
import hashlib
import json

import streamlit as st

from . import github_sync


PLANS_DIR = Path(__file__).resolve().parent.parent / "plans"
PLANS_DIR.mkdir(exist_ok=True)
REMOTE_DIR = "plans"


# ─── Sync GitHub au démarrage ────────────────────────────────────────────────

def sync_initial():
    """
    Au 1er run de la session, pull les plans depuis GitHub. Idempotent.
    Indexe aussi les hashs locaux pour éviter les pushs vides ultérieurs.
    """
    if st.session_state.get("_plans_synced", False):
        return
    if github_sync.is_enabled():
        try:
            github_sync.sync_directory_from_github(PLANS_DIR, REMOTE_DIR)
        except Exception:
            pass
        for f in PLANS_DIR.glob("*.json"):
            try:
                contenu = f.read_text(encoding="utf-8")
                st.session_state[f"_last_pushed_hash::{f.stem}"] = (
                    hashlib.md5(contenu.encode("utf-8")).hexdigest()
                )
            except OSError:
                pass
    st.session_state["_plans_synced"] = True


# ─── Sérialisation ──────────────────────────────────────────────────────────

def _serialiser(p: dict) -> dict:
    out = copy.deepcopy(p)
    for k, v in out.items():
        if isinstance(v, date):
            out[k] = v.isoformat()
    return out


def _deserialiser(d: dict) -> dict:
    if "date_ouverture" in d and isinstance(d["date_ouverture"], str):
        d["date_ouverture"] = date.fromisoformat(d["date_ouverture"])
    return d


# ─── API publique ───────────────────────────────────────────────────────────

def lister_plans() -> list[str]:
    return sorted(f.stem for f in PLANS_DIR.glob("*.json"))


def charger_plan(nom: str) -> dict:
    fichier = PLANS_DIR / f"{nom}.json"
    if not fichier.exists():
        raise FileNotFoundError(f"Plan introuvable : {nom}")
    with open(fichier, encoding="utf-8") as f:
        return _deserialiser(json.load(f))


def sauvegarder_plan(nom: str, params: dict, local_only: bool = False,
                      commit_message: str | None = None) -> Path:
    """
    Sauvegarde locale + push GitHub si activé.

    local_only=True : skip GitHub (utile pour les auto-saves très fréquents
    pendant l'édition d'hypothèses, pour ne pas spammer le repo).
    """
    fichier = PLANS_DIR / f"{nom}.json"
    contenu = json.dumps(_serialiser(params), ensure_ascii=False, indent=2)
    fichier.write_text(contenu, encoding="utf-8")

    if local_only or not github_sync.is_enabled():
        return fichier

    new_hash = hashlib.md5(contenu.encode("utf-8")).hexdigest()
    hash_key = f"_last_pushed_hash::{nom}"
    if st.session_state.get(hash_key) == new_hash:
        return fichier

    msg = commit_message or f"Sauvegarde plan : {nom}"
    ok, info = github_sync.push_file(f"{REMOTE_DIR}/{nom}.json", contenu, msg)
    if ok:
        st.session_state[hash_key] = new_hash
    else:
        try:
            st.toast(f"Sauvegarde locale OK, GitHub KO : {info}", icon="⚠️")
        except Exception:
            pass
    return fichier


def dupliquer_plan(nom_source: str, nouveau_nom: str) -> Path:
    p = charger_plan(nom_source)
    p["nom_plan"] = nouveau_nom
    return sauvegarder_plan(nouveau_nom, p)


def supprimer_plan(nom: str) -> bool:
    fichier = PLANS_DIR / f"{nom}.json"
    deleted = False
    if fichier.exists():
        fichier.unlink()
        deleted = True
    if github_sync.is_enabled():
        github_sync.delete_file(f"{REMOTE_DIR}/{nom}.json",
                                f"Suppression plan : {nom}")
    return deleted


def renommer_plan(ancien_nom: str, nouveau_nom: str) -> Path:
    p = charger_plan(ancien_nom)
    p["nom_plan"] = nouveau_nom
    nouveau_chemin = sauvegarder_plan(nouveau_nom, p)
    if ancien_nom != nouveau_nom:
        supprimer_plan(ancien_nom)
    return nouveau_chemin
