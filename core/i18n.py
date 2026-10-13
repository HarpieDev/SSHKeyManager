"""French source messages and an English catalog; no key data is translated."""
import json
from pathlib import Path
import re

CATALOG_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'locales' / 'en.json'
ENGLISH = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
_language = 'fr'


class LocalizedText(str):
    def __new__(cls, source: str, values: dict):
        template = ENGLISH.get(source, source) if _language == 'en' else source
        rendered = {key: tr(value) if isinstance(value, LocalizedText) else value for key, value in values.items()}
        value = template.format(**rendered) if values else template
        instance = super().__new__(cls, value)
        instance.source = source
        instance.values = values
        return instance


def language() -> str:
    return _language


def set_language(value: str) -> None:
    global _language
    if value not in ('fr', 'en'):
        raise ValueError('Unsupported language')
    _language = value


def tr(source: str, **values) -> LocalizedText:
    if isinstance(source, LocalizedText):
        return LocalizedText(source.source, source.values)
    return LocalizedText(source, values)


def translate_message(message: str) -> str:
    """Translate an existing diagnostic while preserving inserted names and paths."""
    if isinstance(message, LocalizedText) or message in ENGLISH:
        return tr(message)
    reverse = {value: source for source, value in ENGLISH.items()}
    if message in reverse:
        return tr(reverse[message])
    if '\n' in message:
        return '\n'.join(str(translate_message(line)) for line in message.split('\n'))
    # Exception strings lose their LocalizedText type when returned by str(exc).
    for source, target in ENGLISH.items():
        pattern_source = source if _language == 'en' else target
        if '{p' not in pattern_source:
            continue
        fields = re.findall(r'\{(p\d+)\}', pattern_source)
        pattern = re.escape(pattern_source)
        for name in fields:
            pattern = pattern.replace(re.escape('{' + name + '}'), '(?P<' + name + '>.*?)')
        match = re.fullmatch(pattern, message, re.DOTALL)
        if match:
            return tr(source, **match.groupdict())
    return message
