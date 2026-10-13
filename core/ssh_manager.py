from core.i18n import tr
import base64
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import uuid
import copy
from functools import wraps
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core import key_material, metadata_store, ssh_config
from core.storage import atomic_write, private_permission_warning, protect_private

logger = logging.getLogger(__name__)
SSH_DIR = Path(os.environ.get("HARPIE_HOME", Path.home())) / ".ssh"
SSH_CONFIG = SSH_DIR / "config"
LOCK = threading.RLock()
EXCLUDED_FILES = {"known_hosts", "authorized_keys", "config"}
SKIP_SUFFIXES = {".old", ".bak", ".backup", ".ppk"}
NAME_PATTERN = re.compile(r"[a-zA-Z0-9_-]{1,100}\Z")
RESERVED_NAMES = EXCLUDED_FILES | {"con", "prn", "aux", "nul"} | {f"{prefix}{n}" for prefix in ("com", "lpt") for n in range(1, 10)}


@dataclass
class SshKey:
    name: str
    key_type: str
    comment: str
    fingerprint_sha256: str
    created_at: datetime  # conservé pour compatibilité UI ; date de modification
    private_path: Path
    public_path: Path
    public_key_text: str
    warning: str = ""
    tag_id: str = ""
    tag_label: str = ""
    tag_color: str = ""
    encrypted: bool = False
    has_private: bool = True


def get_ssh_dir() -> Path:
    if SSH_DIR.is_symlink():
        raise ValueError(tr('Le dossier .ssh est un lien symbolique : modification automatique refusée.'))
    SSH_DIR.mkdir(parents=True, exist_ok=True)
    return SSH_DIR


def _key_paths(name: str) -> tuple[Path, Path]:
    if not name or Path(name).name != name or any(c in name for c in '/\\:\0\r\n') or name.startswith(".") or name.casefold() in RESERVED_NAMES:
        raise ValueError(tr('Nom de fichier de clé invalide ou réservé.'))
    directory = get_ssh_dir()
    paths = directory / name, directory / f"{name}.pub"
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError(tr('Un lien symbolique ne peut pas être modifié.'))
    return paths


def open_ssh_folder() -> None:
    os.startfile(get_ssh_dir())


def _read_config() -> str:
    get_ssh_dir()
    if SSH_CONFIG.is_symlink():
        raise ValueError(tr('Le fichier config est un lien symbolique.'))
    return SSH_CONFIG.read_text(encoding="utf-8-sig") if SSH_CONFIG.exists() else ""


def _write_config(content: str) -> None:
    if SSH_CONFIG.exists():
        atomic_write(SSH_CONFIG.with_name("config.harpie.bak"), SSH_CONFIG.read_bytes(), private=True)
    atomic_write(SSH_CONFIG, content.encode("utf-8"), private=True)


def get_config_entry(name: str) -> dict[str, str]:
    return ssh_config.connection(_read_config(), name, get_ssh_dir())


def set_config_entry(key_name: str, hostname: str, user: str, port: int = 22) -> tuple[bool, str]:
    try:
        _key_paths(key_name)
        if not re.fullmatch(r"[a-zA-Z0-9._:\[\]-]+", hostname) or hostname.startswith("-"):
            raise ValueError(tr('Adresse du serveur invalide.'))
        if not re.fullmatch(r"[a-zA-Z0-9_.@\\-]+", user) or user.startswith("-"):
            raise ValueError(tr('Utilisateur SSH invalide.'))
        if not 1 <= int(port) <= 65535:
            raise ValueError(tr('Le port doit être compris entre 1 et 65535.'))
        with LOCK:
            _write_config(ssh_config.set_connection(_read_config(), key_name, hostname, user, int(port), get_ssh_dir()))
        return True, ""
    except (OSError, ValueError, UnicodeError) as exc:
        return False, str(exc)


def remove_config_entry(name: str) -> None:
    content = _read_config()
    updated = ssh_config.remove_identity(content, name, get_ssh_dir())
    if updated != content:
        _write_config(updated)


def rename_config_entry(old: str, new: str) -> None:
    content = _read_config()
    updated = ssh_config.replace_identity(content, old, new, get_ssh_dir())
    if updated != content:
        _write_config(updated)


def check_openssh_available() -> tuple[bool, str]:
    return (True, "") if shutil.which("ssh") else (False, tr('OpenSSH est requis pour les connexions et SSH Agent. La gestion des clés reste disponible.'))


def _run(command: str, args: list[str], timeout: int = 15) -> subprocess.CompletedProcess[str]:
    executable = shutil.which(command)
    if not executable:
        raise ValueError(tr('{p0} introuvable. Installez le client OpenSSH Windows.', p0=command))
    try:
        return subprocess.run([executable, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, timeout=timeout,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    except subprocess.TimeoutExpired:
        raise ValueError(tr("{p0} n'a pas répondu après {p1} secondes.", p0=command, p1=timeout)) from None


def scan_keys() -> list[SshKey]:
    with LOCK:
        directory = get_ssh_dir()
        data = metadata_store._load_raw()
        candidates = {}
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.is_symlink() or path.name.startswith(".") or path.suffix.lower() in SKIP_SUFFIXES:
                continue
            if path.name.casefold() in EXCLUDED_FILES or path.name.startswith(("known_hosts", "authorized_keys", "config.")):
                continue
            if path.suffix == ".pub":
                candidates[path.name[:-4]] = True
            else:
                try:
                    with path.open("rb") as stream:
                        header = stream.read(80)
                    if b"PRIVATE KEY-----" in header or (directory / f"{path.name}.pub").exists():
                        candidates[path.name] = True
                except OSError:
                    continue
        keys = []
        for name in sorted(candidates, key=str.casefold):
            private, public = directory / name, directory / f"{name}.pub"
            problems = []
            kind, comment, fingerprint, text = "?", "", "", ""
            encrypted, embedded = False, None
            has_private = private.is_file() and not private.is_symlink()
            if has_private:
                try:
                    embedded, encrypted = key_material.inspect_private(private.read_bytes())
                    permission_warning = private_permission_warning(private)
                    if permission_warning:
                        problems.append(permission_warning)
                    if encrypted and embedded is None:
                        problems.append(tr('Clé PEM chiffrée : correspondance à vérifier avec la passphrase.'))
                except Exception:
                    # Ne jamais inclure les octets de la clé dans une erreur ou un log.
                    problems.append(tr('Clé privée illisible ou format non pris en charge.'))
            else:
                problems.append(tr('Clé privée manquante : clé publique seule.'))
            if public.is_file() and not public.is_symlink():
                try:
                    text = public.read_text(encoding="utf-8-sig").strip()
                    kind, comment, fingerprint = key_material.parse_public(text)
                    if embedded and text.split()[:2] != embedded.decode("ascii").split()[:2]:
                        problems.append(tr('Les clés privée et publique ne correspondent pas.'))
                except (OSError, ValueError, TypeError, UnicodeError):
                    problems.append(tr('Clé publique invalide ou illisible.'))
                    text = ""
            else:
                problems.append(tr('Fichier .pub manquant. Utilisez « Réparer publique ».'))
                if embedded:
                    text = embedded.decode("ascii")
                    kind, comment, fingerprint = key_material.parse_public(text)
            entry = data["keys"].get(name, {})
            tag_id = entry.get("tag_id", "")
            tag = data["tags"].get(tag_id, {})
            try:
                stamp = (private if has_private else public).stat().st_mtime
            except OSError:
                continue
            keys.append(SshKey(name, kind, comment, fingerprint, datetime.fromtimestamp(stamp), private, public, text,
                               "\n".join(problems), tag_id, tag.get("label", ""), tag.get("color", ""), encrypted, has_private))
        return keys


def validate_key_name(name: str, existing_names: set[str] | None = None) -> tuple[bool, str]:
    if not NAME_PATTERN.fullmatch(name) or name.casefold() in RESERVED_NAMES:
        return False, tr('Utilisez 1 à 100 lettres, chiffres, _ ou -. Les noms Windows réservés sont interdits.')
    if existing_names and name.casefold() in {n.casefold() for n in existing_names}:
        return False, tr('Une clé avec ce nom existe déjà.')
    return True, ""


def _ensure_free(name: str) -> tuple[Path, Path]:
    ok, error = validate_key_name(name)
    if not ok:
        raise ValueError(error)
    paths = _key_paths(name)
    existing = {p.name.casefold() for p in get_ssh_dir().iterdir()}
    if any(path.name.casefold() in existing for path in paths):
        raise ValueError(tr("Un fichier avec ce nom existe déjà, même s'il n'est pas listé."))
    return paths


def _clean_comment(comment: str) -> str:
    if any(c in comment for c in "\r\n\0"):
        raise ValueError(tr('Le commentaire doit tenir sur une seule ligne.'))
    return comment.strip()


def _save_pair(name: str, private_data: bytes, public_data: bytes) -> None:
    private, public = _ensure_free(name)
    atomic_write(private, private_data, private=True, exclusive=True)
    try:
        atomic_write(public, public_data.rstrip() + b"\n", exclusive=True)
    except Exception:
        private.unlink()
        raise


def create_key(name: str, comment: str, passphrase: str, key_type: str = "ed25519") -> tuple[bool, str]:
    try:
        with LOCK:
            _ensure_free(name)
            comment = _clean_comment(comment) or name
            private, public = key_material.generate(key_type, passphrase)
            _save_pair(name, private, public + b" " + comment.encode("utf-8"))
        logger.info(tr('Clé créée : %s'), name)
        return True, ""
    except Exception as exc:
        logger.error(tr('Création de clé échouée (%s)'), type(exc).__name__)
        return False, str(exc) if isinstance(exc, (OSError, ValueError)) else tr('Impossible de créer la clé.')


def _snapshot():
    return SSH_CONFIG.read_bytes() if SSH_CONFIG.exists() else None, metadata_store._load_raw()


def _restore_snapshot(snapshot) -> None:
    config, data = snapshot
    if config is None:
        SSH_CONFIG.unlink(missing_ok=True)
    else:
        atomic_write(SSH_CONFIG, config, private=True)
    metadata_store._save_raw(data)


def rename_key(old_name: str, new_name: str) -> tuple[bool, str]:
    moved = []
    snapshot = None
    try:
        with LOCK, metadata_store.LOCK:
            old = _key_paths(old_name)
            if old_name == new_name:
                return True, ""
            new = _ensure_free(new_name)
            if not any(p.exists() for p in old):
                raise ValueError(tr('Clé introuvable.'))
            snapshot = _snapshot()
            for source, target in zip(old, new):
                if source.exists():
                    source.rename(target)
                    moved.append((source, target))
            rename_config_entry(old_name, new_name)
            metadata_store.rename_key_metadata(old_name, new_name)
        logger.info(tr('Clé renommée : %s → %s'), old_name, new_name)
        return True, ""
    except Exception as exc:
        try:
            for source, target in reversed(moved):
                target.rename(source)
            if moved and snapshot:
                _restore_snapshot(snapshot)
        except Exception:
            return False, tr("Renommage interrompu et restauration incomplète. Vérifiez les fichiers dans .ssh ; aucune clé n'a été effacée.")
        return False, tr('Renommage annulé : {p0}', p0=exc)


def update_comment(name: str, comment: str, passphrase: str = "") -> tuple[bool, str]:
    # Le commentaire descriptif est celui du .pub ; aucun déchiffrement nécessaire.
    try:
        with LOCK:
            _, public = _key_paths(name)
            text = public.read_text(encoding="utf-8-sig").strip()
            key_material.parse_public(text)
            updated = " ".join(text.split()[:2]) + (" " + _clean_comment(comment) if comment.strip() else "")
            atomic_write(public, (updated + "\n").encode("utf-8"))
        return True, ""
    except (OSError, ValueError, UnicodeError) as exc:
        return False, str(exc)


def delete_key(name: str) -> tuple[bool, str]:
    """Suppression réversible : clés conservées dans une corbeille privée locale."""
    moved = []
    snapshot = None
    archive = None
    try:
        with LOCK, metadata_store.LOCK:
            paths = _key_paths(name)
            if not any(p.exists() for p in paths):
                raise ValueError(tr('Clé introuvable.'))
            snapshot = _snapshot()
            trash = get_ssh_dir() / ".harpie-trash"
            if trash.is_symlink():
                raise ValueError(tr('La corbeille est un lien symbolique.'))
            trash.mkdir(exist_ok=True)
            protect_private(trash)
            archive = trash / uuid.uuid4().hex
            archive.mkdir()
            protect_private(archive)
            manifest = {"name": name, "deleted_at": datetime.now().isoformat(), "metadata": snapshot[1]["keys"].get(name, {}),
                        "config": _read_config(), "config_after": ssh_config.remove_identity(_read_config(), name, get_ssh_dir())}
            atomic_write(archive / "manifest.json", json.dumps(manifest, ensure_ascii=False).encode("utf-8"), private=True)
            for path, label in zip(paths, ("private", "public")):
                if path.exists():
                    target = archive / label
                    path.rename(target)
                    moved.append((path, target))
            remove_config_entry(name)
            metadata_store.delete_key_metadata(name)
        return True, ""
    except Exception as exc:
        try:
            for source, target in reversed(moved):
                target.rename(source)
            if moved and snapshot:
                _restore_snapshot(snapshot)
            if archive:
                (archive / "manifest.json").unlink(missing_ok=True)
                archive.rmdir()
        except Exception:
            return False, tr('Suppression interrompue. Les fichiers sont conservés dans .ssh ou .harpie-trash.')
        return False, tr('Suppression annulée : {p0}', p0=exc)


def list_deleted_keys() -> list[dict]:
    trash = get_ssh_dir() / ".harpie-trash"
    if not trash.exists() or trash.is_symlink():
        return []
    items = []
    for folder in trash.iterdir():
        if not folder.is_dir() or folder.is_symlink():
            continue
        try:
            data = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
            items.append({"id": folder.name, "name": data["name"], "deleted_at": data["deleted_at"]})
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return sorted(items, key=lambda item: item["deleted_at"], reverse=True)


def restore_deleted_key(archive_id: str) -> tuple[bool, str]:
    moved = []
    snapshot = None
    try:
        with LOCK, metadata_store.LOCK:
            if not re.fullmatch(r"[0-9a-f]{32}", archive_id):
                raise ValueError(tr('Archive invalide.'))
            archive = get_ssh_dir() / ".harpie-trash" / archive_id
            if archive.is_symlink() or not archive.resolve().is_relative_to(get_ssh_dir().resolve()):
                raise ValueError(tr('Archive invalide.'))
            manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
            private, public = _key_paths(manifest["name"])
            if private.exists() or public.exists():
                raise ValueError(tr('Ce nom est déjà utilisé. Renommez la clé existante avant de restaurer.'))
            snapshot = _snapshot()
            for label, target in (("private", private), ("public", public)):
                source = archive / label
                if source.is_symlink():
                    raise ValueError(tr('Archive invalide.'))
                if source.exists():
                    source.rename(target)
                    moved.append((source, target))
            if not moved:
                raise ValueError(tr('Archive vide.'))
            data = copy.deepcopy(snapshot[1])
            tag_id = manifest.get("metadata", {}).get("tag_id", "")
            if tag_id in data["tags"]:
                data["keys"][manifest["name"]] = {"tag_id": tag_id}
                metadata_store._save_raw(data)
            # Ne pas écraser les modifications de config intervenues depuis la suppression.
            if _read_config() == manifest.get("config_after"):
                _write_config(manifest["config"])
            else:
                updated = ssh_config.restore_identities(_read_config(), manifest.get("config", ""), manifest["name"], get_ssh_dir())
                if updated != _read_config():
                    _write_config(updated)
            (archive / "manifest.json").unlink()
            archive.rmdir()
        return True, ""
    except Exception as exc:
        try:
            for source, target in reversed(moved):
                target.rename(source)
            if moved and snapshot:
                _restore_snapshot(snapshot)
        except Exception:
            return False, tr('Restauration interrompue. Vérifiez .ssh et la corbeille Harpie.')
        return False, tr('Restauration annulée : {p0}', p0=exc)


def read_public_key(name: str) -> tuple[str, str]:
    try:
        _, public = _key_paths(name)
        text = public.read_text(encoding="utf-8-sig").strip()
        key_material.parse_public(text)
        return text, ""
    except (OSError, ValueError, UnicodeError) as exc:
        return "", str(exc)


def repair_public_key(name: str, passphrase: str = "") -> tuple[bool, str]:
    try:
        with LOCK:
            private, public = _key_paths(name)
            key = key_material.load_private(private.read_bytes(), passphrase)
            if public.exists():
                raise ValueError(tr('Le fichier .pub existe déjà. Il ne sera pas écrasé.'))
            atomic_write(public, key_material.public_bytes(key) + b" " + name.encode("utf-8") + b"\n", exclusive=True)
        return True, ""
    except Exception as exc:
        return False, str(exc) if isinstance(exc, (ValueError, OSError)) else tr('Format de clé non pris en charge.')


def validate_key(name: str, passphrase: str = "") -> tuple[bool, str]:
    try:
        private, public = _key_paths(name)
        key = key_material.load_private(private.read_bytes(), passphrase)
        text = public.read_text(encoding="utf-8-sig").strip()
        key_material.parse_public(text)
        if text.split()[:2] != key_material.public_bytes(key).decode("ascii").split()[:2]:
            raise ValueError(tr('Les clés privée et publique ne correspondent pas.'))
        return True, ""
    except Exception as exc:
        return False, str(exc) if isinstance(exc, (ValueError, OSError)) else tr('Format de clé non pris en charge.')


def change_passphrase(name: str, old_passphrase: str, new_passphrase: str) -> tuple[bool, str]:
    try:
        private, _ = _key_paths(name)
        key = key_material.load_private(private.read_bytes(), old_passphrase)
        atomic_write(private, key_material.serialize_private(key, new_passphrase), private=True)
        return True, ""
    except Exception as exc:
        return False, str(exc) if isinstance(exc, (ValueError, OSError)) else tr('Impossible de changer la passphrase.')


def import_key(source: Path, name: str, passphrase: str = "") -> tuple[bool, str]:
    try:
        with LOCK:
            _ensure_free(name)
            raw = source.read_bytes()
            if raw.startswith(b"PuTTY-User-Key-File"):
                raise ValueError("Convertissez d'abord le .ppk en OpenSSH avec PuTTYgen.")
            key = key_material.load_private(raw, passphrase)
            public = key_material.public_bytes(key)
            companion = source.with_name(source.name + ".pub")
            if companion.is_file():
                text = companion.read_text(encoding="utf-8-sig").strip()
                key_material.parse_public(text)
                if text.split()[:2] != public.decode("ascii").split()[:2]:
                    raise ValueError(tr('Le .pub importé ne correspond pas à la clé privée.'))
                public = text.encode("utf-8")
            _save_pair(name, raw, public)
        return True, ""
    except Exception as exc:
        return False, str(exc) if isinstance(exc, (OSError, ValueError)) else tr('Format de clé non pris en charge.')


def export_key(name: str, destination: Path, private: bool = False) -> tuple[bool, str]:
    try:
        source = _key_paths(name)[0 if private else 1]
        if destination.resolve() == source.resolve():
            raise ValueError(tr('Choisissez un autre emplacement.'))
        atomic_write(destination, source.read_bytes(), private=private, exclusive=True)
        return True, ""
    except (OSError, ValueError) as exc:
        return False, str(exc)


def fix_permissions(name: str) -> tuple[bool, str]:
    try:
        private, _ = _key_paths(name)
        protect_private(private)
        return True, ""
    except (OSError, ValueError) as exc:
        return False, str(exc)


def agent_keys() -> tuple[str, str]:
    try:
        result = _run("ssh-add", ["-l"])
        if result.returncode not in (0, 1):
            return "", "SSH Agent indisponible. Activez le service Windows « OpenSSH Authentication Agent »."
        return result.stdout.strip() or tr('Aucune clé chargée.'), ""
    except (OSError, ValueError) as exc:
        return "", str(exc)


def remove_from_agent(name: str) -> tuple[bool, str]:
    try:
        _, public = _key_paths(name)
        result = _run("ssh-add", ["-d", str(public)])
        return result.returncode == 0, "" if result.returncode == 0 else tr("Impossible de retirer la clé de l'agent.")
    except (OSError, ValueError) as exc:
        return False, str(exc)


def _interactive(command: str, args: list[str]) -> None:
    executable = shutil.which(command)
    if not executable:
        raise ValueError(f"{command} introuvable.")
    # La passphrase est saisie directement dans le terminal OpenSSH.
    script = "& " + " ".join("'" + value.replace("'", "''") + "'" for value in [executable, *args])
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    subprocess.Popen(["powershell.exe", "-NoProfile", "-NoExit", "-EncodedCommand", encoded],
                     creationflags=subprocess.CREATE_NEW_CONSOLE)


def add_to_agent(name: str) -> None:
    private, _ = _key_paths(name)
    if not private.is_file():
        raise ValueError(tr('Clé privée manquante.'))
    _interactive("ssh-add", [str(private)])


def connect(name: str) -> None:
    entry = get_config_entry(name)
    if not entry:
        raise ValueError(tr("Configurez d'abord la connexion de cette clé."))
    _interactive("ssh", ["-F", str(SSH_CONFIG), "--", entry["alias"]])


def _synchronized(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        # Garder les verrous jusque pendant le retour arrière d'une opération.
        with LOCK, metadata_store.LOCK:
            return function(*args, **kwargs)
    return wrapped


for _name in ("rename_key", "delete_key", "restore_deleted_key", "import_key", "create_key", "repair_public_key",
              "update_comment", "export_key", "fix_permissions", "remove_config_entry", "rename_config_entry", "get_config_entry", "validate_key", "change_passphrase"):
    globals()[_name] = _synchronized(globals()[_name])
