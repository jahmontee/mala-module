# Build and package Mala v2

The complete locked Beads/stmlib, adapter and modified public host source are
included. No network fetch is required to compile. Use a fresh output folder.

```sh
python3 -B tools/build.py --output build/native --compiler g++
python3 -B -m unittest discover -s tests -v
python3 -B tools/audit.py
# Put the accepted ARM mala.so in artifacts/mala.lv2/.
python3 -B tools/package.py --output dist/v2-review
python3 -B tools/verify_archives.py --folder dist/v2-review
```

The accepted ARM binary SHA256 is pinned in release.json and its compiled
sources in provenance/accepted-build.json. Extract that binary from the
matching install kit's content-addressed blobs, using the catalog hash for
usr/lib/lv2/mala.lv2/mala.so. Native builds are for computer checks. An ARM build
requires the Hector-compatible C/C++ ABI, with ARMv8-A generic tuning. Updating
system libraries to accommodate another compiler is outside this installer.

integration/hosts contains all exact shared host compositions. The historical
integration/firmware407.patch describes the earlier Mala-only integration.
provenance/component-catalog.json is the current compatibility contract.
Changed payloads require a new reviewed version/catalog. update_catalog.py is
review-time tooling for this release identity, not an automatic future merger.

For Qt5 checks use Python3.10/PySide2 5.15 or an equivalent development runtime,
then run tools/qt_check.py --fresh --v2 with an offscreen software backend.
These development dependencies are not installed on Hector by the USB kit.
