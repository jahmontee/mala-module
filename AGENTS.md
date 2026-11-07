# Public Mala release source

Read docs/COMPATIBILITY.md before changing or packaging a module. Review the
Mala compatibility rules and shared integration files for every update. Keep
module identity, port/state contracts and existing saved values stable unless
an explicit migration is supplied. Preserve unrelated file bytes, metadata, services and user data. Validate install, in-place update, removal, postboot idempotence and recovery for exact recognized files. Unknown
versions must be refused before target writes. Update the compatibility matrix
and validation scope honestly. Preparation does not authorize hardware access.

Keep public beta.6 tags/downloads immutable. New bytes need a distinct version.
Include complete corresponding source and upstream notices. Never export
private device bindings, backups, keys, presets or lab history.
