# Changelog

## [1.2.0] — 2026-10-13

### Added

- Complete English and French interfaces in a single application, with a live language selector and a remembered preference.
- Automatic first-launch language selection from the Windows locale, with English as the fallback.
- Localized dialogs, key diagnostics, accessibility labels, native Qt buttons, and tag management without translating user names or comments.
- Bilingual per-user Windows installer with Start menu shortcut, optional desktop shortcut, and an uninstaller that preserves SSH identities and settings.
- Installer and portable ZIP assets with individual SHA256 checksums.
- CI verification of English and French installation, installed application startup, uninstallation, and preservation of user data.

### Changed

- Prepared the application and documentation for distribution to other Windows users.
- Added regression coverage for language switching, preservation of unsaved tag drafts, and translation template integrity.

No key or metadata migration is required.

## [1.1.0] — 2026-10-13

### Changed

- Redesigned the complete desktop workspace with charcoal surfaces, restrained blue, purple, orange, and pink accents, clearer typography, and consistent rounded controls.
- Refined the key library, summary cards, search, colored filters, sidebar, and empty state with direct create/import actions.
- Rebuilt the selection inspector with scrollable details and permanently accessible public-key and management actions.
- Harmonized identity creation, key details, connection settings, security actions, passphrase changes, and tag management.
- Replaced generic SSH Agent and trash popups with dedicated dialogs.
- Improved form accessibility with field names and label buddies.

### Added

- English README with actual screenshots, download instructions, storage details, development commands, and build documentation.
- Shared application version and generated Windows executable metadata.
- Windows CI for Python 3.12 and 3.14 and automated tag-triggered releases.
- Verified portable Windows package, third-party license bundle, and SHA256 checksum.
- Contribution guidance, security reporting guidance, issue forms, and a pull-request template.
- Disposable-key screenshot capture utility.

Existing key storage and metadata remain compatible. No migration is required.

## [1.0.0] — 2026-10-09

Initial application snapshot: local key creation, import/export, passphrase management, permissions checks, SSH configuration preservation, tags, agent integration, and recoverable deletion. This snapshot was not tagged as a GitHub release.
