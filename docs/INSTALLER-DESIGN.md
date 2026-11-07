# Coordinated USB revision2 design

Firmware407 runs debug.sh through existing USB startup support. No download or
system dependency installation is required.

The exact catalog has eight optional v2 installed sets and four additional
beta.6 upgrade sets. Transitions enumerate allowed targets, guard unchanged
component files and metadata, validate content-addressed payloads and capture
a complete worker before pausing services. Workers recheck device/boot/USB,
saved data, preimages and guards before writing.

Authenticated original bytes/metadata are durable before publication. Services
pause, firmware becomes writable, per-file atomic writes publish the change,
then exact installed state verifies. Firmware closes read-only or remains
paused for normal reboot closeout. Next startup verifies bytes, metadata and
read-only firmware. Repeated matching USB use is verification-only.

The shared inventory and outcomes are HMAC/device-bound. Migration admits only
the explicit prior catalog digest, its exact mapped state, known component
identities and matching authenticated latest transaction. Older unfinished
operations require the original recovery kit. Old backups remain private.

Mala updates retain the URI and ports. Independent removal composes shared UI
for remaining recognized modules. Interrupted recovery restores exact originals.
Completed-version downgrade is separate. Recovery blocks automatic retry until
acknowledgement with the opposite matching kit. Unknown edits/metadata, links,
overlay shadows, wrong mounts and corrupt payloads are refused.

Computer tests simulate mounts/services/reboot. Physical durability and
unbootable-device recovery remain unqualified.
