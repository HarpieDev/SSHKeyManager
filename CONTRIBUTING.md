# Working on Harpie

Harpie is a Windows application distributed with English and French interfaces. Keep changes small, local, and easy to verify. Preserve existing SSH configuration options and recoverable deletion. Do not add telemetry, accounts, or cloud storage.

## Before submitting a change

1. Install pinned dependencies from `requirements.txt` in a virtual environment.
2. Run `python -B -m unittest discover -s tests -v`.
3. Check affected screens in both languages at 920 × 640 and at a larger desktop size, including keyboard navigation. Add messages to `assets/locales/en.json` and preserve formatting parameters.
4. Use disposable keys and `HARPIE_HOME` for diagnostics. Never test mutations against your personal `.ssh` folder.
5. Do not commit keys, passphrases, metadata, logs, virtual environments, or build output.

See the README for setup, screenshot capture, and packaging commands.

## Releasing a version

1. Update `version.py` and add a dated entry to `CHANGELOG.md`.
2. Run `python tools/write_version.py` and the release build script with `-WithInstaller` (Inno Setup 6 is required).
3. Review the source changes, screenshots, and generated package; commit and push to `main`.
4. Wait for the Windows CI checks to pass.
5. Create an annotated tag matching the application version, for example `git tag -a v1.2.0 -m "Harpie 1.2.0"`, then push that tag.
6. The release workflow tests, builds, diagnoses, verifies installation and removal in both languages, and publishes the installer, ZIP, and `SHA256SUMS.txt`. Confirm that the release contains all three assets.

Never move a published version tag. Use a new patch version for corrections. The workflow can also be dispatched manually from an existing version tag.
