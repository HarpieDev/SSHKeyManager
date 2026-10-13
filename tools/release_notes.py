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
    print(f'\n## Download\n\nExtract `Harpie-{__version__}-windows-x64.zip` and run `Harpie.exe`. No Python installation is required. Windows x64; application interface in French. The executable is unsigned.\n')
    print('Verify the ZIP against `SHA256SUMS.txt`. The archive includes documentation and third-party license texts.\n')
    print('Your keys and metadata stay local and remain compatible with the previous version. Back up important identities independently.\n')


if __name__ == '__main__':
    main()
