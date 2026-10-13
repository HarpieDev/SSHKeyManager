# Third-party notices

Harpie uses the following third-party software. Each component retains its own copyright and license terms; the original license texts are included in release archives under `licenses/`.

| Component | Use | License family |
| --- | --- | --- |
| CPython | Bundled runtime | Python Software Foundation License |
| PySide6, Shiboken6, Qt | Desktop interface | LGPL/GPL/commercial terms; see distributed notices |
| cryptography | SSH key generation and cryptographic operations | Apache-2.0 / BSD-3-Clause |
| bcrypt | Encrypted OpenSSH key support | Apache-2.0 |
| cffi, pycparser | Cryptographic runtime dependencies | MIT-0 / BSD-3-Clause |
| Inter | Bundled interface font | SIL Open Font License 1.1 |
| PyInstaller | Executable packaging and bootloader | GPL with a bootloader exception; see distributed license |

Qt and cryptography wheels may contain additional third-party notices. Those notices are copied from the installed distributions without alteration. Harpie's source and build instructions are available in this repository.

The LGPL 3.0 and GPL 3.0 texts in `assets/licenses/` are reproduced from [GNU's official license collection](https://www.gnu.org/licenses/). PySide6 is used under its LGPL 3.0 option. Upstream source is available from [Qt for Python](https://code.qt.io/cgit/pyside/pyside-setup.git/) and [Qt](https://code.qt.io/cgit/qt/); match the version recorded in `requirements.txt` to the corresponding upstream release. Release archives include these license texts in addition to the notices included with the wheels. You can rebuild Harpie from this repository with compatible replacement libraries; no signature or activation check restricts that build.
