# Installer design and review boundaries

The FAT32 kit's `debug.sh` uses firmware 407's existing debug startup service. It
checks the two executable Python sources against hashes embedded in the launcher,
then starts the USB entrypoint. The entrypoint refuses desktops and Beebo, enters
PID1's mount namespace, and verifies board, model, firmware-source hashes, visible
and persistent files, overlay layout, package ownership, USB mount and free space.
There is no default password, SSH identity, network setup or embedded unit serial.

Admission is followed by a root-owned capture under `/mnt/mala-public-beta/` and
a transient systemd worker independent of the USB debug service and frontend.
Only that captured worker can pause screen/audio services and remount the lower
firmware tree. Temporary RAM service drop-ins prevent automatic consumer restarts;
they disappear during the ordinary reboot. No persistent startup service is added.

Before a target write, the worker stores all actual originals and their metadata,
a device binding, transaction ID, and an HMAC-authenticated durable journal. It
verifies those backups before publication. Target changes are atomic per file,
with fsync and recorded intent; the complete 34-file update is not a filesystem-wide
atomic operation. Exceptions attempt restoration of known states; unknown file
edits or metadata changes refuse restoration. Added directories are removed only
when recorded and empty. Presets and unrelated files are never deletion targets.

After verifying the installed/restored lower tree, the worker syncs and attempts
read-only closeout. The known stock407 synced-EBUSY remount condition is recorded
as requiring normal reboot, with consumers still paused. It never treats another
mount error as success. The next USB boot verifies read-only state and visible
files, without repeating a committed install or completed rollback.

A root-owned reservation prevents concurrent workers. Rollback can retire a
stale reservation only after verifying its service is inactive/failed. A running
worker is not interrupted. Backups are retained after rollback. A deliberate
later installation can create a fresh transaction after matching stock preimages.

Cryptographic checks protect package integrity and local journal consistency;
they are not a publisher signature or protection from an attacker with root on
Hector. USB reports omit the device binding, key and saved preimages. There is
no automatic power-loss recovery service. See KNOWN-LIMITATIONS.md.
