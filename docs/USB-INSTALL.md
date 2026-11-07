# USB install or update · Mala v2 0.2.0-beta.1 · compat.2

Experimental candidate for Hector 407. Exact-kit physical testing is unperformed.
Read VALIDATION.md, KNOWN-LIMITATIONS.md and COMPATIBILITY.md.

## Prepare on a computer

1. Download mala-hector-0.2.0-beta.1-compat.2-usb-install.zip, the matching
   rollback ZIP and SHA256SUMS from the same release. Compare the archive
   checksum. Checksums detect corruption without providing a publisher signature.
2. Use a dedicated drive with one writable FAT32 partition. An 8 GB drive is
   ample. Back up wanted files before reformatting.
3. Extract the complete install ZIP to the root. You must see debug.sh, mala/
   and READ-ME-FIRST.txt. Keep the folder intact, use one kit per drive and
   safely eject it.

## Install on Hector

1. Save wanted edits, stop playback and power Hector off normally.
2. Insert USB and power on. Firmware407 USB startup runs the kit automatically.
   Do not press the vendor Firmware Update button.
3. Leave power and USB connected. Screen/audio services pause, originals are
   backed up, files are checked/written and Hector requests a normal reboot.
4. Keep USB connected through that reboot. Next startup verifies installed
   files and read-only firmware without installing/rebooting again.
5. Open Mala in Ported and confirm v0.2.0-beta.1.
6. Remove USB after startup. On a computer read MALA-RESULT.txt for
   **INSTALLED AND VERIFIED**. Keep the installer disconnected during normal use.
7. Test controls and your audio path at low monitoring level. A fresh Density
   at noon stops automatic grains. Move it away from center or use Seed.

Recognized public beta.6 updates in place, keeping the same module URI/ports.
Other recognized add-ons remain installed. Unknown versions or edits are
refused before firmware writes, with a reason in the report. Do not remove a
companion to bypass a compatibility refusal. Use coordinated revision2 kits
for subsequent companion changes. Older stock-only/compat.1 tools lack v2 support.

## Problems or interrupted installation

Keep the result, COMMUNITY-LAUNCHER.log and matching rollback ZIP. Recovery data
stays private on Hector at /mnt/hector-community-beta/. Preserve older private
backup folders too. Never delete or share their keys/journals.

After **RECOVERY VERIFIED; NO RETRY**, starting software is restored and the same
USB will not repeat the failed operation. Follow the report to acknowledge with
the opposite matching kit once, then deliberately retry if desired.
**RECOVERY REQUIRED** needs the matching rollback kit and maintainer attention.
Avoid repeated installation attempts. USB recovery requires normal startup;
an unbootable device may need offline SD recovery.
