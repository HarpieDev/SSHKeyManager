"""Package only the executable, documentation, and original license texts."""
import hashlib
from importlib import metadata
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from version import __version__


def main():
    executable = ROOT / 'dist' / 'Harpie.exe'
    if not executable.is_file():
        raise FileNotFoundError('Build dist/Harpie.exe first')
    output = ROOT / 'dist' / 'release'
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f'Harpie-{__version__}-windows-x64.zip'
    distributions = ('PySide6', 'PySide6_Addons', 'PySide6_Essentials', 'shiboken6',
                     'cryptography', 'bcrypt', 'cffi', 'pycparser', 'pyinstaller')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as package:
        package.write(executable, 'Harpie.exe')
        for filename in ('README.md', 'CHANGELOG.md', 'CONTRIBUTING.md', 'THIRD_PARTY_NOTICES.md', 'SECURITY.md'):
            package.write(ROOT / filename, filename)
        for path in (ROOT / 'docs' / 'screenshots').glob('*.png'):
            package.write(path, path.relative_to(ROOT).as_posix())
        package.write(ROOT / 'assets' / 'icons' / 'harpie.png', 'assets/icons/harpie.png')
        package.write(ROOT / 'assets' / 'fonts' / 'OFL.txt', 'licenses/Inter/OFL.txt')
        for filename in ('LGPL-3.0.txt', 'GPL-3.0.txt'):
            package.write(ROOT / 'assets' / 'licenses' / filename, f'licenses/Qt/{filename}')
        for name in distributions:
            distribution = metadata.distribution(name)
            found = 0
            for entry in distribution.files or []:
                lower = entry.as_posix().lower()
                if '.dist-info/' in lower and ('/licenses/' in lower or entry.name.lower().startswith(('license', 'copying', 'notice'))):
                    source = Path(distribution.locate_file(entry))
                    if source.is_file():
                        suffix = entry.as_posix().split('.dist-info/', 1)[1]
                        package.write(source, f'licenses/{name}/{suffix}')
                        found += 1
            if not found:
                raise RuntimeError(f'No license text found for {name}')
        python_license = Path(sys.base_prefix) / 'LICENSE.txt'
        if not python_license.is_file():
            raise FileNotFoundError('CPython LICENSE.txt is missing')
        package.write(python_license, 'licenses/Python/LICENSE.txt')
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    (output / 'SHA256SUMS.txt').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    print(f'{archive.name} ({archive.stat().st_size:,} bytes)')
    print(f'SHA256: {digest}')


if __name__ == '__main__':
    main()
