# Publishing on GitHub

The public repository is [poly-hector/mala-module](https://github.com/poly-hector/mala-module),
with source, forks, pull requests and issue reports. Use GitHub Releases for the
USB downloads and mark beta releases as prereleases. The local source directory
and download prefix remain `mala-hector`.

1. Review this standalone source tree. Its history must start here; do not import
   the private lab repository/history, ignored build directories or device records.
2. Keep Issues enabled and include the source, existing license, credits,
   CONTRIBUTING, issue/PR templates and CI workflow.
   Contributors can fork and propose PRs; they do not need direct write access.
3. Let CI build native DSP and run the disposable tests/audit. Review all logs
   before publishing the release downloads. Require a successful GitHub Actions
   run for the exact release source commit; local checks do not replace that run.
4. Review the completed one-unit USB install/reboot/rollback evidence and the
   remaining coverage in VALIDATION.md. State the actual pre-Mala407 backup-card
   baseline and its limits in the prerelease; do not call it a fresh vendor-flash
   qualification or treat simulated recovery as physical power-loss testing.
5. Tag the reviewed source commit `v0.1.0-beta.6`. Build the archives from that exact
   clean source state; verify SHA256SUMS and complete source with tools/verify_archives.py.
6. Create a draft GitHub prerelease for that tag, using RELEASE-NOTES.md, and attach
   the install ZIP, rollback ZIP, source archive and SHA256SUMS together. Review the
   concrete draft and publish only when approved. Do not label it a stable release.

Keep installed-user reports separate from emulation/fixture results. Future beta
versions need explicit source/binary/manifest updates and a reviewed migration;
never replace the bytes behind an already published release or tag.
