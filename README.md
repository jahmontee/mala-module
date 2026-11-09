# Mala for Hector — public beta

Mala is a community granular texture processor for **Hector running firmware 407**,
based on the open-source Beads algorithms by Emilie Gillet / Mutable Instruments.
It includes four recording qualities, Freeze and Seed, CV modulation, wavetable
synthesis, frozen-buffer preset storage, MIDI mapping, and a touchscreen editor.

**0.1.0-beta.6** includes Back to the left of Module Settings and a dedicated
module Bypass on the right. The plugin URI and 58-port parameter contract are
unchanged from the private beta.5.

![Mala beta.6 touchscreen editor](docs/images/mala-beta6.png)

## Install with a USB thumb drive

No SSH, terminal, network connection, or SD-card removal is required for normal
installation or rollback. Use a dedicated, single-partition FAT32 thumb drive.

1. Download `mala-hector-0.1.0-beta.6-usb-install.zip` from this repository's Releases.
2. Follow the [USB installation instructions](docs/USB-INSTALL.md): extract the
   kit directly onto the thumb drive, save your patch, and start Hector with it inserted.
3. The kit checks compatibility, retains originals on Hector, applies Mala and
   requests an ordinary reboot. Keep the drive inserted through that reboot for
   verification.
4. Find **Mala** in the Ported module browser. The editor displays `v0.1.0-beta.6`.
5. **Remove the installer thumb drive once startup is complete and Mala opens.**
   Leave it disconnected during normal use; no extra reboot is required. On your
   computer, check its `MALA-RESULT.txt` for **INSTALLED AND VERIFIED**.

The kit uses firmware 407's existing **USB startup-script support**. It runs when
the thumb drive mounts; it does not use the touchscreen's vendor Firmware Update
button. Use the separate [USB rollback kit](docs/USB-ROLLBACK.md) to restore your
own pre-installation files.

The initial public installer accepts **unmodified stock 407**. It refuses older
private Mala installs, other community UI modifications, Beebo, and unknown files
rather than overwriting them. See [compatibility and limitations](docs/KNOWN-LIMITATIONS.md).

## Beta validation status

The same ARM DSP binary has prior Hector use and ARM emulation evidence. The
footer has been installed and physically confirmed by the owner on Hector.
The public USB kits passed installation, automatic post-reboot verification,
rollback and both additional startup checks on one Hector. The owner confirmed
the beta.6 editor, audio, Back, Bypass and module controls, followed by normal
stock audio after removal. The test used a pre-Mala firmware407 SD backup with
existing internal preset/settings storage, not a fresh vendor-download flash or
factory reset. External MIDI/CV and detailed frozen-buffer save/reload were not
separately repeated in this public-kit trial. Read [validation](docs/VALIDATION.md)
and [known limitations](docs/KNOWN-LIMITATIONS.md) before testing.

## Community development

Forks, pull requests and issue reports are welcome. Please read
[Contributing](CONTRIBUTING.md) and use the supplied bug-report template. Start
with [Build from source](docs/BUILDING.md) and the [technical design](docs/INSTALLER-DESIGN.md).

Mala is an independent community project, not an official Poly Effects or Mutable
Instruments release. Original design and DSP credit belong to Emilie Gillet and
the upstream contributors. See [credits](CREDITS.md) and [licensing](docs/LICENSING.md).

The Hector adaptation was developed by jahmontee / Poly Hector with AI development
assistance from OpenAI Codex.
