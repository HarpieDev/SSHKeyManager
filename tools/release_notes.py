"""Print the current version's changelog section for GitHub Releases."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from version import __version__


def main():
    text = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    match = re.search(r'^## \[' + re.escape(__version__) + r'\].*?\n(.*?)(?=^## |\Z)', text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f'No changelog entry for {__version__}')
    print(f'# Harpie {__version__}\n')
    print(match.group(1).strip())
    print(f'\n## Download\n\nRun `Harpie-{__version__}-setup-x64.exe` to install Harpie, then open it from the Start menu. The installer and application support English and French. Installation is per user; no administrator rights or Python installation are required.\n')
    print(f'For portable use, extract `Harpie-{__version__}-windows-x64.zip` and run `Harpie.exe`. Windows x64; downloads are currently unsigned.\n')
    print('Verify either download against `SHA256SUMS.txt`. Both packages include documentation and third-party license texts. Uninstalling preserves SSH keys and preferences.\n')
    print('Your keys and metadata stay local and remain compatible with the previous version. Back up important identities independently.\n')


if __name__ == '__main__':
    main()
