from core.i18n import tr
import json
import logging
import uuid
import re
import threading
import os
from datetime import datetime
from pathlib import Path

from core.storage import atomic_write

logger = logging.getLogger(__name__)

METADATA_DIR = ((Path(os.environ["HARPIE_HOME"]) / "AppData" / "Roaming") if os.environ.get("HARPIE_HOME")
                else Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))) / "HarpieSSH"
METADATA_FILE = METADATA_DIR / "metadata.json"
LOCK = threading.RLock()
LAST_WARNING = ""

LEGACY_COLORS = {
    "teal": "#14B8A6",
    "indigo": "#6366F1",
    "blue": "#3B82F6",
    "green": "#22C55E",
    "orange": "#F97316",
    "purple": "#8B5CF6",
    "red": "#EF4444",
    "amber": "#F59E0B",
}


def _ensure_dir() -> None:
    METADATA_DIR.mkdir(parents=True, exist_ok=True)


def _empty_data() -> dict:
    return {"version": 2, "tags": {}, "keys": {}}


def _load_raw() -> dict:
    global LAST_WARNING
    _ensure_dir()
    if not METADATA_FILE.exists():
        return _empty_data()
    try:
        data = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError):
        data = None

    if isinstance(data, dict) and "version" in data and data["version"] != 2:
        raise ValueError(tr("Version des métadonnées non prise en charge. Le fichier n'a pas été modifié."))

    if not isinstance(data, dict) or (data.get("version") == 2 and (
        not isinstance(data.get("tags", {}), dict) or not isinstance(data.get("keys", {}), dict)
        or any(not isinstance(v, dict) for v in data.get("tags", {}).values())
        or any(not isinstance(v, dict) for v in data.get("keys", {}).values())
        or any(not isinstance(v.get("tag_id", ""), str) for v in data.get("keys", {}).values() if isinstance(v, dict))
    )):
        backup = METADATA_FILE.with_name(f"metadata.invalid-{datetime.now():%Y%m%d-%H%M%S-%f}.json")
        atomic_write(backup, METADATA_FILE.read_bytes(), private=True, exclusive=True)
        LAST_WARNING = tr('Les tags endommagés ont été sauvegardés dans {p0}.', p0=backup.name)
        logger.warning(LAST_WARNING)
        _save_raw(_empty_data())
        return _empty_data()

    if "version" in data and data.get("version") == 2:
        data.setdefault("tags", {})
        data.setdefault("keys", {})
        for tag in data["tags"].values():
            tag["label"] = str(tag.get("label", ""))
            color = tag.get("color", "#64748B")
            tag["color"] = color if isinstance(color, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", color) else "#64748B"
        return data

    return _migrate_legacy(data)


def _migrate_legacy(old: dict) -> dict:
    data = _empty_data()
    for key_name, entry in old.items():
        if not isinstance(entry, dict):
            continue
        tag_id = str(entry.get("tag_id", "none"))
        tag_label = str(entry.get("tag_label", "")).strip()
        if tag_id == "none" and not tag_label:
            continue
        label = tag_label or tag_id
        color = LEGACY_COLORS.get(tag_id, "#64748B")
        new_id = next((tid for tid, tag in data["tags"].items() if tag == {"label": label, "color": color}), uuid.uuid4().hex)
        data["tags"][new_id] = {"label": label, "color": color}
        data["keys"][key_name] = {"tag_id": new_id}
    _save_raw(data)
    logger.info(tr('metadata.json migré vers le format v2'))
    return data


def _save_raw(data: dict) -> None:
    _ensure_dir()
    atomic_write(METADATA_FILE, json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"), private=True)


def list_tags() -> list[dict]:
    data = _load_raw()
    result = []
    for tag_id, tag in data["tags"].items():
        result.append({
            "id": tag_id,
            "label": tag.get("label", ""),
            "color": tag.get("color", "#64748B"),
        })
    return sorted(result, key=lambda t: t["label"].lower())


def get_tag(tag_id: str) -> dict | None:
    if not tag_id or tag_id == "none":
        return None
    tag = _load_raw()["tags"].get(tag_id)
    if not tag:
        return None
    return {"id": tag_id, "label": tag.get("label", ""), "color": tag.get("color", "#64748B")}


def create_tag(label: str, color: str) -> str:
    label = label.strip()
    if not label:
        raise ValueError(tr('Le nom du tag est obligatoire.'))
    data = _load_raw()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise ValueError(tr('Couleur de tag invalide.'))
    if any(tag.get("label", "").casefold() == label.casefold() for tag in data["tags"].values()):
        raise ValueError(tr('Un tag avec ce nom existe déjà.'))
    tag_id = uuid.uuid4().hex
    data["tags"][tag_id] = {"label": label, "color": color}
    _save_raw(data)
    logger.info(tr('Tag créé : %s (%s)'), label, tag_id)
    return tag_id


def delete_tag(tag_id: str) -> None:
    data = _load_raw()
    data["tags"].pop(tag_id, None)
    for key_name, entry in list(data["keys"].items()):
        if entry.get("tag_id") == tag_id:
            del data["keys"][key_name]
    _save_raw(data)


def update_tag(tag_id: str, label: str, color: str) -> None:
    """Renomme/recolore un tag sans changer son identité ni ses associations."""
    label = label.strip()
    if not label:
        raise ValueError(tr('Le nom du tag est obligatoire.'))
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise ValueError(tr('Couleur de tag invalide.'))
    data = _load_raw()
    if tag_id not in data["tags"]:
        raise ValueError(tr('Tag introuvable.'))
    if any(tid != tag_id and tag.get("label", "").casefold() == label.casefold()
           for tid, tag in data["tags"].items()):
        raise ValueError(tr('Un tag avec ce nom existe déjà.'))
    data["tags"][tag_id] = {"label": label, "color": color}
    _save_raw(data)


def get_key_tag(key_name: str) -> tuple[str, str, str]:
    """Retourne (tag_id, label, color). Vide si aucun tag."""
    data = _load_raw()
    entry = data["keys"].get(key_name, {})
    tag_id = entry.get("tag_id", "")
    if not tag_id:
        return "", "", ""
    tag = data["tags"].get(tag_id)
    if not tag:
        return "", "", ""
    return tag_id, tag.get("label", ""), tag.get("color", "#64748B")


def set_key_tag(key_name: str, tag_id: str) -> None:
    data = _load_raw()
    if not tag_id or tag_id == "none":
        data["keys"].pop(key_name, None)
    else:
        if tag_id not in data["tags"]:
            raise ValueError(tr('Tag introuvable.'))
        data["keys"][key_name] = {"tag_id": tag_id}
    _save_raw(data)
    logger.info(tr('Tag assigné à %s : %s'), key_name, tag_id or "aucun")


def clear_key_tag(key_name: str) -> None:
    set_key_tag(key_name, "")


def rename_key_metadata(old_name: str, new_name: str) -> None:
    data = _load_raw()
    if old_name in data["keys"]:
        data["keys"][new_name] = data["keys"].pop(old_name)
        _save_raw(data)


def delete_key_metadata(key_name: str) -> None:
    data = _load_raw()
    if key_name in data["keys"]:
        del data["keys"][key_name]
        _save_raw(data)


# Lecture/modification/écriture sont protégées ensemble, y compris avec les tâches Qt.
def _synchronized(function):
    from functools import wraps
    @wraps(function)
    def wrapped(*args, **kwargs):
        with LOCK:
            return function(*args, **kwargs)
    return wrapped


for _name in ("_load_raw", "_save_raw", "list_tags", "get_tag", "create_tag", "update_tag", "delete_tag",
              "get_key_tag", "set_key_tag", "clear_key_tag", "rename_key_metadata", "delete_key_metadata"):
    globals()[_name] = _synchronized(globals()[_name])
