# Mala 0.1.0-beta.6 — Hector firmware 407

Community beta for willing testers. Based on the open-source Beads DSP
by Emilie Gillet / Mutable Instruments, adapted for Hector's patching environment.

Includes four recording qualities, Freeze and Seed, CV modulation, wavetable
synthesis, frozen-buffer patch storage, MIDI mapping, and the new footer: Back
left of Module Settings, module Bypass on the right.

Download the **USB install ZIP**, extract it to a dedicated FAT32 thumb drive,
and follow READ-ME-FIRST.txt. No SSH or network setup is required. Use the separate
**USB rollback ZIP** to restore your Hector's saved pre-installation files. This
uses automatic USB startup support; do not press the vendor Firmware Update button.
Keep the installer inserted through the automatic reboot. Once startup completes
and Mala opens, **remove the installer USB and leave it disconnected for normal
use**. No additional reboot is required. Check its `MALA-RESULT.txt` on a computer
for **INSTALLED AND VERIFIED**.

This initial installer accepts unmodified Hector firmware407. Beebo, other firmware,
older private Mala installs and other community UI modifications are refused.
Read the full known limitations and retain pre-beta patches.

The DSP binary and 58-port preset contract match the accepted private beta.5.
Native source/DSP, Qt5 UI, filesystem transaction and simulated USB-worker checks
pass. Public USB installation, automatic post-reboot verification, rollback and
both additional startup checks passed on one Hector, with owner-confirmed audio
and editor controls and normal stock audio after removal. That trial used a
pre-Mala firmware407 SD backup and existing internal preset/settings storage,
not a fresh vendor-download flash or factory reset. External MIDI/CV and detailed
frozen-buffer save/reload were not separately repeated in this public-kit trial.
Physical power-loss recovery and broad reliability/calibration claims are not
established. See docs/VALIDATION.md for the exact evidence and remaining coverage.

Report reproducible issues using the repository's bug-report template. Source,
credits, license texts, build instructions and contribution guidance are included.
This is an independent community project, not an official vendor release.

Original Beads design and DSP: **Emilie Gillet / Mutable Instruments**. Hector
adaptation and project direction: **jahmontee / Poly Hector**, with **OpenAI Codex**
acknowledged for AI development assistance with implementation, testing tools,
documentation and packaging. Full upstream acknowledgments are in CREDITS.md.
