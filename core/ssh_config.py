"""Édition ciblée du config OpenSSH, en conservant les options personnelles."""
from core.i18n import tr
import re
from pathlib import Path

DIRECTIVE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9]*)\s*(?:=\s*|\s+)(.*?)\s*$")


def parse_line(line: str) -> tuple[str, list[str]]:
    quoted = False
    for i, char in enumerate(line):
        if char == '"':
            quoted = not quoted
        elif char == "#" and not quoted:
            line = line[:i]
            break
    match = DIRECTIVE.match(line)
    if not match:
        return "", []
    return match[1].lower(), [word.strip('"') for word in re.findall(r'"[^"]*"|[^\s]+', match[2])]


def blocks(lines: list[str]):
    starts = [i for i, line in enumerate(lines) if parse_line(line)[0] in {"host", "match"}]
    for index, start in enumerate(starts):
        yield start, starts[index + 1] if index + 1 < len(starts) else len(lines)


def is_identity(value: str, key_name: str, ssh_dir: Path) -> bool:
    normalized = value.replace("\\", "/").casefold()
    return normalized in {
        f"~/.ssh/{key_name}".casefold(),
        (ssh_dir / key_name).as_posix().casefold(),
        f"%d/.ssh/{key_name}".casefold(),
    }


def replace_identity(content: str, old: str, new: str, ssh_dir: Path) -> str:
    result = []
    for line in content.splitlines(keepends=True):
        keyword, values = parse_line(line)
        if keyword == "identityfile" and len(values) == 1 and is_identity(values[0], old, ssh_dir):
            # Remplacer seulement la valeur, pas les commentaires ni l'alias Host.
            value = values[0]
            replacement = value.replace("\\", "/").rsplit("/", 1)[0] + "/" + new
            line = line.replace(value, replacement, 1)
        result.append(line)
    return "".join(result)


def remove_identity(content: str, name: str, ssh_dir: Path) -> str:
    return "".join(line for line in content.splitlines(keepends=True)
                   if not (parse_line(line)[0] == "identityfile" and len(parse_line(line)[1]) == 1
                           and is_identity(parse_line(line)[1][0], name, ssh_dir)))


def connection(content: str, name: str, ssh_dir: Path) -> dict[str, str]:
    lines = content.splitlines(keepends=True)
    for start, end in blocks(lines):
        keyword, aliases = parse_line(lines[start])
        if keyword != "host":
            continue
        entries = [parse_line(line) for line in lines[start + 1:end]]
        if not any(k == "identityfile" and len(v) == 1 and is_identity(v[0], name, ssh_dir) for k, v in entries):
            continue
        values = {k: v[0] for k, v in reversed(entries) if v}
        return {"alias": aliases[0] if aliases else name, "hostname": values.get("hostname", ""),
                "user": values.get("user", ""), "port": values.get("port", "22")}
    return {}


def set_connection(content: str, name: str, host: str, user: str, port: int, ssh_dir: Path) -> str:
    lines = content.splitlines(keepends=True)
    associated = connection(content, name, ssh_dir)
    alias = associated.get("alias", name)
    matches = [(start, end) for start, end in blocks(lines)
               if parse_line(lines[start])[0] == "host" and alias in parse_line(lines[start])[1]]
    if len(matches) > 1:
        raise ValueError(tr('Plusieurs blocs Host portent cet alias. Modifiez le config manuellement.'))
    updates = {"hostname": host, "user": user, "port": str(port), "identityfile": f"~/.ssh/{name}"}
    labels = {"hostname": "HostName", "user": "User", "port": tr('Port'), "identityfile": "IdentityFile"}
    if matches:
        start, end = matches[0]
        aliases = parse_line(lines[start])[1]
        if len(aliases) != 1 or any(c in aliases[0] for c in "*?!"):
            raise ValueError(tr('Ce bloc Host est partagé ou utilise un motif. Modification automatique refusée.'))
        if not associated and any(parse_line(line)[0] == "identityfile" for line in lines[start + 1:end]):
            raise ValueError(tr('Cet alias Host utilise déjà une autre clé. Choisissez un autre nom de clé ou modifiez le config manuellement.'))
        replacement = [lines[start]]
        seen = set()
        for line in lines[start + 1:end]:
            key, vals = parse_line(line)
            if key in updates:
                if key == "identityfile" and (len(vals) != 1 or not is_identity(vals[0], name, ssh_dir)):
                    replacement.append(line)
                    continue
                if key not in seen:
                    replacement.append(f"    {labels[key]} {updates[key]}\n")
                    seen.add(key)
            else:
                replacement.append(line)
        for key in updates:
            if key in seen:
                continue
            if replacement and not replacement[-1].endswith("\n"):
                replacement[-1] += "\n"
            replacement.append(f"    {labels[key]} {updates[key]}\n")
        lines[start:end] = replacement
        return "".join(lines)
    block = f"Host {name}\n" + "".join(f"    {labels[k]} {v}\n" for k, v in updates.items())
    # Les valeurs spécifiques précèdent les valeurs par défaut. Host * préserve
    # la portée des directives globales déjà présentes en tête de fichier.
    return block + ("\nHost *\n" + content if content else "")


def restore_identities(content: str, previous: str, name: str, ssh_dir: Path) -> str:
    """Réinsère les références supprimées sans écraser les options modifiées depuis."""
    old_lines = previous.splitlines(keepends=True)
    sections = list(blocks(old_lines))
    if not sections or sections[0][0] > 0:
        sections.insert(0, (0, sections[0][0] if sections else len(old_lines)))
    for start, end in sections:
        identity_lines = [line for line in old_lines[start:end] if parse_line(line)[0] == "identityfile"
                          and len(parse_line(line)[1]) == 1 and is_identity(parse_line(line)[1][0], name, ssh_dir)]
        if not identity_lines:
            continue
        lines = content.splitlines(keepends=True)
        keyword, values = parse_line(old_lines[start])
        if keyword in {"host", "match"}:
            matches = [(a, b) for a, b in blocks(lines) if parse_line(lines[a]) == (keyword, values)]
            if len(matches) > 1:
                raise ValueError(tr('Plusieurs blocs de configuration identiques : restauration automatique impossible.'))
            if matches:
                a, b = matches[0]
                if any(parse_line(line)[0] == "identityfile" and len(parse_line(line)[1]) == 1
                       and is_identity(parse_line(line)[1][0], name, ssh_dir) for line in lines[a + 1:b]):
                    continue
                lines[a + 1:a + 1] = identity_lines
                content = "".join(lines)
            elif keyword == "host":
                block = "".join(old_lines[start:end]).rstrip() + "\n"
                content = block + ("\nHost *\n" + content if content else "")
            else:
                raise ValueError(tr("Le bloc Match d'origine a changé. Restaurez sa référence à la clé manuellement."))
        else:
            # Directives globales : conserver leur portée, en tête du fichier.
            content = "".join(identity_lines) + content
    return content
