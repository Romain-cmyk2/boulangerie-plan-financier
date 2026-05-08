"""
Synchronisation GitHub pour la persistance des plans.

Streamlit Community Cloud utilise un filesystem éphémère : les fichiers écrits
en local par l'app sont perdus à chaque redémarrage du conteneur. Pour persister
les plans, on pousse chaque sauvegarde sur le dépôt GitHub via l'API Contents.

Configuration via st.secrets (sur Streamlit Cloud) :
    GITHUB_TOKEN  = "github_pat_xxx"   (fine-grained, scope Contents R/W)
    GITHUB_REPO   = "owner/repo"
    GITHUB_BRANCH = "main"             (optionnel, défaut: main)

En local (sans secrets), is_enabled() renvoie False et toutes les fonctions
sont des no-op silencieux.
"""

import base64
import time

import requests
import streamlit as st


API_BASE = "https://api.github.com"
TIMEOUT = 15
MIN_INTERVAL_SEC = 5.0


def _config():
    """Lit la config depuis st.secrets. Renvoie None si non configuré."""
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo = st.secrets["GITHUB_REPO"]
        branch = st.secrets.get("GITHUB_BRANCH", "main")
        return token, repo, branch
    except (KeyError, FileNotFoundError, AttributeError):
        return None


def is_enabled() -> bool:
    return _config() is not None


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_file(repo: str, branch: str, path: str, token: str) -> tuple:
    """Récupère (content_str, sha) ou (None, None)."""
    url = f"{API_BASE}/repos/{repo}/contents/{path}"
    try:
        r = requests.get(url, headers=_headers(token),
                         params={"ref": branch}, timeout=TIMEOUT)
    except requests.RequestException:
        return None, None
    if r.status_code != 200:
        return None, None
    j = r.json()
    try:
        content = base64.b64decode(j["content"]).decode("utf-8")
        return content, j.get("sha")
    except (KeyError, ValueError):
        return None, None


def push_file(path_in_repo: str, content_str: str,
              commit_message: str) -> tuple[bool, str]:
    """
    Crée ou met à jour un fichier sur GitHub. Idempotent (no-op si contenu
    identique côté serveur). Throttle MIN_INTERVAL_SEC par fichier par session.
    Retry une fois sur 409 avec un SHA frais.
    """
    cfg = _config()
    if cfg is None:
        return False, "GitHub sync non configuré (mode local)"
    token, repo, branch = cfg

    throttle_key = f"_gh_last_push_ts::{path_in_repo}"
    now = time.time()
    last_ts = st.session_state.get(throttle_key, 0)
    if now - last_ts < MIN_INTERVAL_SEC:
        return True, f"Throttle : dernier push il y a {now - last_ts:.1f} s"

    current_content, sha = _get_file(repo, branch, path_in_repo, token)
    if current_content is not None and current_content == content_str:
        st.session_state[throttle_key] = now
        return True, "Déjà à jour sur GitHub"

    payload = {
        "message": commit_message,
        "content": base64.b64encode(content_str.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    url = f"{API_BASE}/repos/{repo}/contents/{path_in_repo}"
    try:
        r = requests.put(url, headers=_headers(token), json=payload, timeout=TIMEOUT)
    except requests.RequestException as e:
        return False, f"Réseau : {e}"

    if r.status_code == 409:
        _, fresh_sha = _get_file(repo, branch, path_in_repo, token)
        if fresh_sha:
            payload["sha"] = fresh_sha
            try:
                r = requests.put(url, headers=_headers(token),
                                 json=payload, timeout=TIMEOUT)
            except requests.RequestException as e:
                return False, f"Réseau (retry) : {e}"

    if r.status_code in (200, 201):
        st.session_state[throttle_key] = time.time()
        return True, "Synchronisé sur GitHub"
    return False, f"GitHub HTTP {r.status_code} : {r.text[:150]}"


def pull_file(path_in_repo: str) -> tuple:
    """Renvoie (content_str, sha) ou (None, None)."""
    cfg = _config()
    if cfg is None:
        return None, None
    token, repo, branch = cfg

    url = f"{API_BASE}/repos/{repo}/contents/{path_in_repo}"
    try:
        r = requests.get(url, headers=_headers(token),
                         params={"ref": branch}, timeout=TIMEOUT)
    except requests.RequestException:
        return None, None
    if r.status_code != 200:
        return None, None
    j = r.json()
    try:
        content = base64.b64decode(j["content"]).decode("utf-8")
    except (KeyError, ValueError):
        return None, None
    return content, j.get("sha")


def list_files(directory: str) -> list | None:
    """Liste les noms (sans extension) des .json dans un répertoire du repo."""
    cfg = _config()
    if cfg is None:
        return None
    token, repo, branch = cfg

    url = f"{API_BASE}/repos/{repo}/contents/{directory}"
    try:
        r = requests.get(url, headers=_headers(token),
                         params={"ref": branch}, timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    items = r.json()
    if not isinstance(items, list):
        return None
    return [item["name"][:-5] for item in items
            if item.get("name", "").endswith(".json")]


def delete_file(path_in_repo: str, commit_message: str) -> tuple[bool, str]:
    cfg = _config()
    if cfg is None:
        return False, "GitHub sync non configuré"
    token, repo, branch = cfg

    _, sha = _get_file(repo, branch, path_in_repo, token)
    if sha is None:
        return True, "Déjà absent sur GitHub"

    url = f"{API_BASE}/repos/{repo}/contents/{path_in_repo}"
    try:
        r = requests.delete(
            url, headers=_headers(token),
            json={"message": commit_message, "sha": sha, "branch": branch},
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        return False, f"Réseau : {e}"
    if r.status_code == 200:
        return True, "Supprimé sur GitHub"
    return False, f"GitHub HTTP {r.status_code} : {r.text[:150]}"


def sync_directory_from_github(local_dir, remote_dir: str) -> int:
    """
    Au démarrage : télécharge tous les .json manquants ou désynchronisés depuis
    GitHub. Renvoie le nombre de fichiers téléchargés.
    """
    cfg = _config()
    if cfg is None:
        return 0
    names = list_files(remote_dir)
    if not names:
        return 0
    count = 0
    for name in names:
        content, _ = pull_file(f"{remote_dir}/{name}.json")
        if content is None:
            continue
        local_path = local_dir / f"{name}.json"
        try:
            existing = local_path.read_text(encoding="utf-8") if local_path.exists() else None
        except OSError:
            existing = None
        if existing != content:
            local_path.write_text(content, encoding="utf-8")
            count += 1
    return count
