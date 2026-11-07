# Known limitations

- Experimental Hector 407, AArch64, 48 kHz candidate. Beebo, other firmware and
  unknown shared-source modifications are refused before target writes.
- These exact v2 USB kits have no physical trial. Earlier beta.6 USB testing and
  private v2 UI use are separate evidence. GitHub CI is pending on final source.
- COMPATIBILITY.md lists recognized versions. Echo Field/XL, Orbit/Polyrhythm,
  4×4, Cardinal, Oscilloscope and Link audio receiver/sender public combinations
  remain pending. Future versions require catalog review.
- Public beta.6 updates in place. Successful USB rollback removes Mala.
  Downgrading a completed update to beta.6 needs a separate reviewed procedure.
- Fresh Density starts at noon, stopping automatic grains. Move it away from
  center or use Seed. Existing saved values are retained.
- Numerical knob readouts and four lower color badges are hidden. Double-tap
  resets to minimum, including Pitch and attenurandomizers.
- Freeze defers quality/mono changes until released. Latch holds Seed active.
  Short Seed presses clear latch; four-second holds engage it.
- Remember Frozen Buffer requires ten seconds continuously frozen, ready status
  and saving the patch. Missing recordings cannot be reconstructed. Removed
  software leaves user recordings/presets, but Mala patches need Mala installed.
- Long-run audio, physical MIDI/CV calibration, broad recall and mixed-patch CPU
  headroom remain unqualified. The CPU display covers the whole engine.
- Atomic per-file writes and authenticated backups support recovery. Multi-file
  transactions are not filesystem snapshots. Physical power-cut durability and
  USB recovery of an unbootable device are unqualified.
- Checksums detect corruption without being a publisher signature. Keep private
  backups, keys, device bindings, presets and recordings out of public reports.
