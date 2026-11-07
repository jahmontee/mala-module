# Mala compatibility and update behavior

This experimental candidate targets Hector firmware 407, AArch64 at 48 kHz.
Beebo, other firmware and unknown modified target files are refused before
firmware writes. Exact file identities are checked, rather than relying only
on a displayed version number.

## Install and update

The USB install kit installs Mala on the recognized407 baseline and updates
recognized public Mala 0.1.0-beta.6 to 0.2.0-beta.1 in place. Its URI, 58 ports and
saved-state format are retained. Existing patches still refer to the same
Mala. A matching installed v2 is verified without another write or reboot.

Replaced files and metadata are backed up before changes. The installer writes
Mala and only the shared UI integration required for the recognized starting
state. Unchanged files are guards. Presets, frozen recordings and settings
remain user data. Unknown shared-source changes require review before updating.

## Removal and recovery

The matching USB rollback removes Mala and restores the appropriate recognized
shared UI state. It does not restore the beta.6 interface after a completed v2
update. A deliberate completed-version downgrade needs a separate reviewed
procedure, which this release does not provide.

Interrupted-operation recovery restores exact starting files from the device's
authenticated originals. An interrupted beta.6 upgrade can therefore recover
beta.6. Finish an older incomplete operation with its original matching kit
before using this release. Preserve private backup folders and journals.

## Future Mala updates

An update must keep the module identity and saved-patch contract, or include an
explicit migration. Review shared UI integration, routing, clocks, parameter
controls, metadata, defaults and state restoration. Validate update, removal,
postboot verification and interruption recovery for exact recognized files.
Unknown future versions remain pending until reviewed. Source and checksums
must match the exact release commit.

The exact v2 USB kit has computer-only validation. Earlier private UI use and
public beta.6 USB testing are separate evidence. Physical exact-kit testing,
long-run audio/touch/MIDI/CV and loaded-patch headroom remain unqualified.
