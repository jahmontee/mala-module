# Contributing

Fork the repository, make a focused branch, and open a pull request describing
the problem, resulting behavior, and how you checked it. Bug reports and useful
reproduction patches are welcome even when you do not have a code change.

Run the tests and export audit in docs/BUILDING.md. Keep plugin URI, port symbols,
indices, ranges/defaults and saved-state format stable unless a migration is
explicitly designed and reviewed. Separate original upstream code from overlays.
Preserve per-file license notices. Do not submit firmware images, stock DSP
binaries, vendor artwork/fonts, credentials, serials, private transaction records,
owner recordings or full preset collections.

Clearly distinguish native software tests, fixture UI behavior, ARM emulation and
physical Hector evidence. Installer changes need meaningful refusal, interruption
and rollback coverage; never claim a simulated mount/reboot is a device test.
Do not test an installer by running it against your development computer's root.

For a bug, include firmware, Mala version, what you expected, what happened,
reproduction steps and whether it occurs in a minimal patch. Installation issues
can include a redacted MALA-RESULT.txt and the tail of MALA-LAUNCHER.log. Review
logs for personal data before posting; never attach `/mnt/mala-public-beta/`.
