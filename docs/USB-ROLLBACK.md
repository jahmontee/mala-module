# USB rollback and recovery · Mala v2 0.2.0-beta.1 · compat.2

Experimental candidate. This exact rollback kit has no physical trial.
Read COMPATIBILITY.md and back up wanted patches before removal.

## Remove Mala

1. Download mala-hector-0.2.0-beta.1-compat.2-usb-rollback.zip and compare its
   SHA256SUMS entry from the same release.
2. Extract the complete ZIP onto a dedicated, single-partition FAT32 drive.
   debug.sh, mala/ and READ-ME-FIRST.txt must be at the root. Use one kit per
   drive. Safely eject it.
3. Save wanted edits, stop playback, power off, insert USB and power on.
   Do not press the vendor Firmware Update button.
4. Keep power/USB connected through the normal automatic reboot and subsequent
   verification. If Mala is already absent, verification needs no write/reboot.
5. Confirm Mala is absent from the browser, remove USB after startup and read
   MALA-RESULT.txt on a computer for **ROLLBACK VERIFIED**.

Removal retains recognized Squelch Box and Network/Link components and composes
the shared UI for that remaining set. Presets, frozen recordings and network
profiles remain user data. Patches containing Mala still need Mala for its sound.

**Rollback removes Mala.** It does not return a completed v2 update to the
beta.6 interface. A completed-version downgrade needs a separately reviewed
path. No such downgrade kit is included in this release.

## Recover an interrupted operation

For an incomplete Mala transaction, the matching rollback kit restores exact
starting software from authenticated originals. An interrupted beta.6 upgrade
can therefore recover beta.6. Backups stay on that Hector in
/mnt/hector-community-beta/. Never move, delete or publish them.
Finish older compat.1 interruptions with the original matching kit first.

After **RECOVERY VERIFIED; NO RETRY**, the same action stays blocked from
repeating automatically. Follow the result to acknowledge once with the
opposite kit, then deliberately choose your next action. Unknown later edits
stop recovery rather than being overwritten. **RECOVERY REQUIRED** needs
maintainer attention. USB recovery of an unbootable device is unqualified.
