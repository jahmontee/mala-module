# Changelog

## 0.1.0-beta.6 — public beta candidate

- Back moved left of Module Settings; module Bypass occupies its former position
  and reflects the host's acknowledged enabled state.
- Generic, offline USB install/rollback kits for unmodified Hector firmware407.
- Per-device original backups, metadata restoration, refusal checks, durable
  journal and transient worker; no owner-specific connection or identity pins.
- Complete portable source, build scripts, credits, license notices, known limits,
  contribution instructions and GitHub issue/PR templates.
- Accepted beta.5 ARM DSP binary, plugin URI, 58 ports, CV behavior and state format
  retained. The main editor version annotation now distinguishes this candidate.
- Public USB install, post-reboot verification, rollback and both repeat-startup
  checks passed on one Hector using a pre-Mala 407 SD backup with existing
  internal settings/presets. Fresh vendor-flash and physical power-loss recovery
  remain unvalidated; see docs/VALIDATION.md.
