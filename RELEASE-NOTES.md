# Mala 0.3.0-beta.11 for Hector firmware 4.0.7

Community pre-release for Hector. Mala adapts the Mutable Instruments Beads
granular DSP to Hector's patching environment.

## Downloads

- [Signed Mala installer for USB and Poly / View](https://github.com/jahmontee/mala-module/releases/download/v0.3.0-beta.11/Mala-Hector-0.3.0-beta.11-USB.zip)
- [Mala module source](https://github.com/jahmontee/mala-module/releases/download/v0.3.0-beta.11/Mala-Hector-0.3.0-beta.11-Module-Source.zip)
- [Source for the bundled Linux storage repairs](https://github.com/jahmontee/mala-module/releases/download/v0.3.0-beta.11/Hector-Flash-Repair-0.1.0-spi-rx.9-Source.tar)
- [SHA-256 checksums](https://github.com/jahmontee/mala-module/releases/download/v0.3.0-beta.11/SHA256SUMS)

## Known issues

- **Preset load.** Audio can briefly cut out while loading a patch containing
  Mala or in the first few seconds afterward. We reproduced this on Hector
  with the editor closed and the controls untouched.
- **First editor open.** Opening Mala for the first time after a fresh preset
  load can cause another brief cutout, even with the knobs untouched. How
  often this occurs across different patches and devices is still unknown.

## What's new since Mala v2

- Redesigned Module Settings, CV Assignment, and Map MIDI pages. Incoming
  MIDI no longer replaces a value you're typing. MIDI reset uses the same
  defaults as a fresh Mala.
- Fixed saved-value display for MIDI-mapped controls. Density and Pitch
  returned to their saved positions on Hector with the controller connected.
- Reduced unnecessary knob and status redraws and pre-sized the panel artwork.
  The audio engine still receives control changes immediately.
- Reduced DSP work in sample-rate conversion and simplified common delay
  buffer indexing. ARM comparisons for these changes matched the previous
  audio output. Separate Freeze tests matched the saved buffer and restored
  audio. Mala retains the same identity and ordered ports for saved patches.
- One signed ZIP supports standalone USB and Poly / View. Direct USB works
  offline. Its shared runtime includes both the flash-transfer repair and the
  preset-storage read fix. An installation on stock firmware applies the
  repairs first. Already-active compatible repairs are reused.

## Install and update

Save any wanted edits and keep a copy of your presets. The supported target
is Hector firmware 4.0.7. The same ZIP supports fresh installations and
updates from recognized releases, including both previously published
Mala versions.

- **Direct USB.** Extract the entire ZIP to a dedicated FAT32 drive so
  `debug.sh` is at the root. With Hector off, insert the drive and turn it
  on. Allow about 3–4 minutes for the installation, depending on your SD
  card speed. Leave the drive inserted through the final automatic restart,
  even if the normal patch screen appears first. On a stock card, the
  repairs and Mala may require separate restarts. Follow the included
  `READ-ME-FIRST.txt`. This route works with or without Network Connection
  installed.
- **Poly / View.** With a compatible Module Manager, upload the intact ZIP
  in **Module Manager → Release packages**, then choose **Install** or
  **Update**. Follow the restart progress and sign in again after Hector
  returns.

Use **Remove** in a compatible Module Manager to remove Mala. Presets
are preserved, and patches that use Mala need it reinstalled to work.
Recovery from an interrupted update and downgrading a completed installation
are separate operations. The older public rollback ZIPs are for their
matching public releases.

## Validation

The exact signed ZIP passed installation through both Poly / View and
Hector's original USB startup on one spare card. The manual USB trial was a
fresh Mala install on a card with the storage fixes already present. After
restart, all 27 signed module files verified, saved presets and settings
matched the pre-install check, and both storage fixes were active. The
storage check completed 1,056 reads with zero mismatches.

Poly / View Test 28.1 could show the restart dialog before an install
started. Test 28.2 corrects that behavior. The exact beta.11 ZIP was
reinstalled successfully in Firefox and in Safari on iPad, with visible
install progress and an automatic return to sign-in in both browsers.

Local tests covered first-time offline installation from stock with later
manager discovery, both public starting versions, damaged delivery, and
interrupted update recovery.

## Credits and feedback

Original Beads design and DSP by Emilie Gillet / Mutable Instruments.
Hector adaptation, project direction, and physical testing by jahmontee /
Poly Hector, with development, testing, and packaging assistance from
OpenAI Codex. The source archive includes upstream credits and license
notices. This is an independent community project.

When reporting a cutout, include your firmware and Mala versions, the
recording quality, and whether it happened while loading the patch or when
opening the editor. Keep personal presets, backups, and credentials private.
