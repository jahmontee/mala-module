# USB rollback — Mala 0.1.0-beta.6

This kit restores the exact files and metadata saved by this public beta's
installer on this Hector. It removes only unchanged additions recorded by that
transaction. No SSH, network connection or SD-card removal is required when the
normal USB startup service is still working.

1. Save wanted patch edits. On a computer, prepare a dedicated single-partition
   FAT32 thumb drive using `mala-hector-0.1.0-beta.6-usb-rollback.zip`.
2. Extract it directly to the drive root: `debug.sh`, `mala/`, and
   `READ-ME-FIRST.txt`. Remove the install kit from this drive first; the two
   `debug.sh` files perform different actions. Safely eject the drive.
3. Shut Hector down normally, insert the rollback drive, and start it.
4. The kit checks this Hector's backup and current file hashes, pauses screen/audio,
   restores the originals, verifies them, and requests one normal reboot.
5. Keep the drive inserted through reboot. The final USB `MALA-RESULT.txt` status
   should be **ROLLBACK VERIFIED**. Remove the drive after the normal screen returns.

**Leave the rollback drive disconnected during normal use.** Rebooting again
with the drive inserted is a release-validation test, not a required removal step.

The rollback drive does not repeat a completed removal. An interrupted publication
or restoration can be resumed from the authenticated transaction when its files
still match known original or candidate states. A stale reservation is retired
only if its worker is inactive. A still-running worker is never interrupted.

Unknown file edits, altered metadata, missing/corrupt backups, a different device,
or a different beta cause refusal before restoration writes. Keep the report and
get help; do not delete transaction files or force removal. Other files you add
to Mala's directories are preserved.

Removal preserves saved patches and frozen-buffer assets. Patches containing Mala
will reference a missing plugin until Mala is installed again; retain a pre-beta
patch for use without it. The normal interface and existing DSP files are restored.

The USB path depends on enough of firmware 407 starting to mount the drive and
run its debug startup service. It cannot promise recovery from a damaged SD card,
a power interruption, or a system that cannot reach that service. Existing SD
backups/offline recovery remain the fallback. Public-kit rollback and its
automatic post-reboot verification passed on the one407 backup-card trial
described in VALIDATION.md. Physical power-loss and unbootable-device recovery
remain unvalidated.
