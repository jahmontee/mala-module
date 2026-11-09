# Compatibility and known limitations

- **Hector, stock firmware 407, AArch64, 48 kHz only.** Beebo has not been validated
  for this release and is deliberately refused. Other versions, prior private
  Mala installations and shared community modifications need a separate migration.
- **One public-kit hardware trial.** USB install, verification, rollback and both
  additional startup checks passed on one Hector using a pre-Mala407 SD backup
  and existing internal preset/settings storage. This is not a fresh vendor-flash
  or factory-reset qualification. Required stock-file admission checks passed;
  complete firmware-tree equivalence to the vendor download was not established.
  Disposable tests provide additional evidence with simulated mounts/services.
- USB installation uses existing automatic `debug.sh` startup, not the vendor
  Firmware Update button. Use one writable FAT32 partition, retain the folder
  layout, and leave power/USB connected through the normal reboot.
- Normal Hector use and UI operation have owner confirmation. Extended CPU/xrun,
  long-run reliability, absolute CV/pitch/gate/output calibration, and exhaustive
  physical MIDI/controller coverage have not been established.
- The public-kit trial covered basic audio and editor controls. External MIDI/CV
  and detailed frozen-buffer save/reload were not separately repeated in that
  trial; earlier DSP/ARM/private-install checks remain inherited evidence.
- Whole-engine CPU is shown by the existing stock meter; it is not a Mala-only
  measurement. Available headroom depends on the rest of the patch.
- Freeze protects the current quality/mono recording mode. A pending quality or
  mono choice is applied after Freeze releases. Quality changes include a short
  transition; recording capacity varies by quality and mono/stereo.
- Remember Frozen Buffer needs continuous Freeze for ten seconds and a ready
  status, followed by saving the patch. Waiting alone does not persist an unsaved
  patch. Restoring a missing or invalid saved buffer cannot recreate the recording.
- Fresh Hector instances use Hector / Poly CV units (×5). Older saved parameter
  sets use legacy virtual volts unless explicitly changed in Module Settings.
  INPUT LEVEL and physical calibration remain the operator's settings.
- The plugin URI deliberately remains `urn:beebo-hector-lab:mala-preview` for preset
  continuity. Its historical name does not imply a second plugin should be installed.
- Preset downgrades to old binaries/port schemas are not promised. Keep pre-beta
  patches. USB rollback restores software; it does not rewrite saved patches.
- Atomic files and authenticated local backups support ordinary errors and
  interrupted filesystem transactions. Physical power-loss durability, offline
  restoration and unbootable-device USB recovery are not certified.
- The installer downloads nothing, installs no system dependencies, and changes no
  network, calibration, NOR, bootloader, existing DSP plugins, or preset files.
