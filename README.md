# Mala v2 for Hector · experimental public beta

Granular textures based on Beads by Emilie Gillet / Mutable Instruments, for
**Poly Effects Hector firmware 407**. The approved silver v2 interface adds
vertical knob gestures, a four-mode quality menu and live Shape envelope guide.

![Mala v2, rendered from its actual Qt5 source](docs/images/mala-v2.png)

**0.2.0-beta.1 · USB compatibility revision2 is an experimental candidate.**
The UI was privately deployed and visually approved on Hector. These exact USB
kits have computer-only testing and no physical USB trial. Read
[validation](docs/VALIDATION.md) and [limitations](docs/KNOWN-LIMITATIONS.md).

## Install or update by USB

Download the matching install ZIP, rollback ZIP and SHA256SUMS from this
version's GitHub prerelease. Use one kit per dedicated FAT32 thumb drive.
An 8 GB drive is ample. Normal installation needs no SSH or internet access.

1. Follow [USB installation](docs/USB-INSTALL.md). Extract at the drive root,
   so debug.sh and mala/ are directly visible.
2. Save your patch, power off, insert USB and power on. Leave USB and power
   connected through the automatic normal reboot.
3. Open Mala from Ported and confirm v0.2.0-beta.1. Remove the USB after startup.
4. On a computer read MALA-RESULT.txt for **INSTALLED AND VERIFIED**. Keep the
   installer disconnected during normal use.

Public Mala beta.6 updates **in place**, with its same URI and 58 ports.
Replaced files are backed up before writing. Existing patches refer to the same
module. The [rollback kit](docs/USB-ROLLBACK.md) removes Mala and retains
the recognized shared UI state. Returning to the old interface after a completed update
is a separate downgrade operation.

## Compatibility

For Hector firmware407, with an exact guarded update path from public Mala
0.1.0-beta.6. The installer checks recognized firmware/UI files and preserves
saved data. Unknown source modifications are refused before firmware writes.
Read [compatibility and update behavior](docs/COMPATIBILITY.md).

This release contains only Mala. Install, removal and future updates must retain
its module identity and saved-patch contract, with explicit migrations for
changed file layouts or versions.

## Fresh defaults and controls

New instances start with Feedback/Reverb at 0%, Dry/Wet at 50%, and the remaining
knobs at noon. Existing loaded patches retain their values. Density at noon
stops automatic grains. Move Density away from center or use Seed for grains.

Freeze protects the current recording mode, so quality/mono changes wait until
it releases. Latch holds Seed active. Short Seed presses clear latch and a
four-second hold engages it. See [panel controls](docs/V2-PANEL-CONTROLS.md),
[quality](docs/V2-QUALITY.md) and [interface notes](docs/V2-UI.md).

## Credits and community

Original Beads design and DSP by **Emilie Gillet / Mutable Instruments**, with
Frédéric Meslin and Oliver Rockstedt credited upstream. Hector adaptation,
direction and physical testing by **jahmontee / Poly Hector**, with **AI
development assistance from OpenAI Codex**. Full [credits](CREDITS.md) and
[licenses](docs/LICENSING.md) accompany both USB kits and the source.
This is an independent community project.

Forks, pull requests and [issues](https://github.com/poly-hector/mala-module/issues)
are welcome. Include firmware/module versions, steps and USB result text. Keep
personal presets and private recovery backups out of public reports. Read
[contributing](CONTRIBUTING.md) and [building](docs/BUILDING.md).

The [published beta.6](https://github.com/poly-hector/mala-module/releases/tag/v0.1.0-beta.6)
remains available as its own historical release.
