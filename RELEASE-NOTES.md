# Mala v2 · 0.2.0-beta.1 · compact USB packaging

For Hector firmware 407. Packaging revision slim.1 provides smaller install
and rollback downloads while retaining the same Mala DSP, interface, module
identity, 58 ports, defaults and saved-state format. Existing 0.2.0-beta.1 users
need no reinstallation for this packaging-only change.

Use the matching compat.2-slim.1 USB install and rollback ZIPs with SHA256SUMS.
Keep USB connected through the automatic normal reboot, then remove it after
startup and check MALA-RESULT.txt. Follow [USB installation](docs/USB-INSTALL.md)
and [rollback/recovery](docs/USB-ROLLBACK.md).

Program source, runtime artwork and notices remain in the USB kits. The finished
screenshot remains on GitHub. Read [compatibility](docs/COMPATIBILITY.md),
[validation](docs/VALIDATION.md) and [limitations](docs/KNOWN-LIMITATIONS.md).
These exact USB kits have computer-only validation and no physical Hector trial.

Original Beads by Emilie Gillet / Mutable Instruments and credited upstream
contributors. Hector adaptation/testing by jahmontee / Poly Hector, with
AI development assistance from OpenAI Codex. Independent community project.
