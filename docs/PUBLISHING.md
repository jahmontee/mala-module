# GitHub preparation

Target repository is poly-hector/mala-module. This candidate is prepared locally.

1. Review clean source, screenshot, credits, compatibility matrix and final
   receipts. Exclude private lab history, presets, keys and device backups.
2. Upload source on a v2 review branch and run CI on the exact commit.
3. Create a draft prerelease tagged v0.2.0-beta.1-compat.2. Attach matching
   install, rollback, complete source and SHA256SUMS. Preserve beta.6 assets.
4. Attach only Mala install, rollback, source, screenshot and checksums.
   Review exact version identities and keep the physical-test limits visible.
5. If publishing without a physical exact-kit trial, retain the experimental
   label and missing-trial statement in README and release notes. The owner
   requested computer-only preparation. Publishing follows concrete review.

Each future release must review Mala compatibility in COMPATIBILITY.md and
provide an explicit exact-version catalog migration. New bytes need a new tag.
