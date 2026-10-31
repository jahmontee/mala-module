# USB installation — Mala 0.1.0-beta.6

For Hector, unmodified firmware 407. Beebo and other firmware versions are not
supported by this installer. This is a beta candidate; read KNOWN-LIMITATIONS.md.
Installation, automatic post-reboot verification and rollback passed on one
Hector using a pre-Mala407 SD backup with existing internal settings/presets.
This was not a fresh vendor-download flash; see VALIDATION.md for the test scope.

The kit starts automatically when its USB drive mounts. Save wanted patch edits
and finish playing before inserting it. Installation pauses the screen and audio
and normally reboots Hector once. Network access and SSH are not needed.

**When to remove the USB:** keep it inserted through the automatic reboot. Once
the normal interface has returned and Mala opens, remove the installer drive.
Leave it disconnected during normal use. No additional reboot is required.

## Prepare the thumb drive on your computer

1. Use a dedicated thumb drive with one FAT32 partition. Back up anything on it
   before changing its format or files. No particular drive label is required.
2. Download the **USB install ZIP** and its release SHA256SUMS from the same release.
   Compare the archive checksum using your computer's checksum tool. Checksums
   detect a damaged download; they are not a publisher signature.
3. Extract the ZIP **directly to the root** of the drive. Its top level must contain:

   ```text
   debug.sh
   mala/
   READ-ME-FIRST.txt
   ```

   Keep the `mala` folder intact. Do not leave an extra outer ZIP folder, another
   `debug.sh`, or another update kit on the drive. Safely eject it.

## Install on Hector

1. Save your patch and shut Hector down normally. Insert the prepared drive.
2. Start Hector. The existing USB startup service runs the kit automatically.
   **Do not press Firmware Update.** This is a community startup-script kit,
   not a vendor firmware-update archive.
3. Leave power and the thumb drive connected. The screen/audio services pause;
   after file verification, Hector requests its own normal reboot.
4. Keep the drive inserted through that reboot. The next startup verifies the
   installed files and read-only firmware without installing or rebooting again.
5. When the normal interface returns, check the Ported browser for Mala and open
   it. Confirm the editor shows `v0.1.0-beta.6`.
6. **Remove the installer drive now that startup is complete and Mala opens.**
   On a computer, read `MALA-RESULT.txt` at its root. The final success status is
   **INSTALLED AND VERIFIED**. Keep the installer disconnected during normal use.
7. Check Back, Bypass, Freeze/Seed and your intended audio path at a low monitoring
   level. There is no need to reconnect the installer or reboot again for these checks.

If the module is already installed, the drive performs verification only. It
never silently upgrades a different beta or replaces a conflicting community UI.
If admission fails, it leaves firmware unchanged and writes the reason to
`MALA-RESULT.txt`; the normal interface can continue.

## Recovery and removal

Keep the matching USB rollback ZIP. Your originals and metadata are stored on
Hector at `/mnt/mala-public-beta/`, not solely on the removable drive. Do not
remove or share that private directory: it can contain original vendor UI files
and a device-specific backup identity.

If a file changes during install, the worker attempts verified restoration and a
normal reboot. A report saying **RECOVERY REQUIRED** needs attention; it is not a
successful install. Do not repeatedly rerun the install drive or cycle power.
Follow USB-ROLLBACK.md. If Hector cannot complete a normal boot, USB rollback is
not guaranteed; offline SD recovery or help from the maintainer may be needed.

Presets, recordings, calibration, network configuration, boot firmware and the
package database are not installation targets. Patches saved using Mala still
need Mala to produce its sound after removal. Back up wanted patches separately.
