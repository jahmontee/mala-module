# Compatibility and update behavior

This experimental candidate targets Hector firmware 407, AArch64 at 48 kHz.
Admission uses exact public source/file identities. Beebo and unknown firmware
or modified shared files are refused before firmware writes.

| Module | Candidate support |
| --- | --- |
| Stock Hector 407 modules | Retained by the recognized public host compositions |
| Public Mala 0.1.0-beta.6 | In-place update to 0.2.0-beta.1, with or without recognized companions |
| Mala v2 0.2.0-beta.1 | Matching installer verifies existing installation without repeating writes |
| Squelch Box 0.1.0-beta.5 | Optional, coordinated compatibility revision2 kit |
| Network Connection 0.1.0-beta.2 + Ableton Link sync 0.3.0-beta.5 | Optional combined package, coordinated compatibility revision2 kit |
| Echo Field / XL, Orbit / Polyrhythm, 4×4, Cardinal, Oscilloscope | Public USB combinations pending review of exact versions and shared files |
| Sample Box / Legacy, BiPoSeq / external-clock | Public USB combinations pending exact integration review |
| Link audio receiver / sender | Separate from Link sync, public USB combination pending |
| Private lab builds and future versions | Require a reviewed catalog migration before installation |

Software admission/preservation checks do not establish real-time audio
headroom for every combination. Physical acceptance of this exact USB family
remains unperformed.

All three recognized add-ons are optional. The catalog contains eight v2
installed sets and four additional beta.6 upgrade sets. An add-on can be added
or removed independently in any order using coordinated revision2 kits.
The installer composes shared host files for the remaining set and guards
other components' files and metadata.

The same Mala URI and ports remain in place. Updating recognized beta.6 replaces
its existing interface and bridge after backing up originals. Existing patches
still refer to that same Mala. Add Module still creates as many separate patch
instances as the user chooses.

The matching USB rollback kit removes Mala and retains recognized companions.
It does not automatically restore the beta.6 interface. An interrupted upgrade
uses authenticated originals to restore its exact starting software set.
A deliberate completed-version downgrade needs a separately reviewed path.
Software removal preserves saved patches and frozen recordings.

Verified compat.1 inventories can migrate to revision2 only after their HMAC,
device binding, exact installed state and authenticated latest transaction
verify. Finish an older incomplete operation with its original recovery kit.
After migration use revision2 companion kits. Older compat.1 tools refuse the
new catalog. Preserve all private backup folders on Hector.

## Rule for future modules and updates

Every release must review this complete module list and the current project
register. Review shared dispatch, catalogs, routing, clocks, defaults,
parameter controls, saved-state handling and service ownership. Add exact
version identities and compositions, test installation/update/removal order
and interruption recovery, and update this matrix. Preserve stable module URIs
and port/state contracts or provide an explicit migration.

Future compatibility is a continuing release requirement. A changed version
is pending until its actual code and file interactions have been reviewed.
Unknown builds must fail safely rather than overwrite another integration.
