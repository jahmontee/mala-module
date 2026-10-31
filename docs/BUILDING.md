# Build and test

Use a development computer, never Hector's root filesystem, for these commands.
The source subset and LV2 headers are included. The build does not install files
or open an audio device. Requirements: Python 3.8+ for release tooling and a C++17
compiler. The on-device installer itself supports Python 3.5+.

```sh
python3 tools/build.py
python3 -m unittest discover -s tests -v
python3 tools/audit.py
```

The native plugin appears at `build/native/mala.lv2/mala.so`. It is a local
software-test build, not a binary for Hector. To cross-compile with a suitable
AArch64 GNU/Linux compiler and compatible sysroot:

```sh
python3 tools/build.py --compiler aarch64-linux-gnu-g++ --output build/arm64
```

The accepted binary was built with Debian GCC 12.2.0 using ARMv8-A generic tuning;
it requires the previously verified firmware 407 C/C++ ABI. A newer compiler's
successful build alone does not establish that its output can run on Hector.
No system-library update should be added to make an incompatible build run.

Official candidate packaging uses the independently verified accepted binary at
`artifacts/mala.lv2/mala.so`; that ignored file is not in the Git source tree.
Extract it from `mala/payload/usr/lib/lv2/mala.lv2/mala.so` in the same release's
USB install ZIP, or retain it from the maintainer's local build archive. Its SHA-256 is pinned in release.json. The source archive
contains everything needed to rebuild the plugin, but bit-for-bit equality across
different build paths/toolchains is not promised.

```sh
python3 tools/package.py --arm-plugin artifacts/mala.lv2/mala.so
```

This produces USB install/rollback ZIPs, complete source and SHA256SUMS in `dist/`.
Custom binaries are deliberately refused by the official candidate packager;
contributors preparing a forked build should update the version and accepted
binary hash in release.json and the corresponding source hashes in
provenance/accepted-build.json, and review the evidence with their binary change. Never silently reuse an official version/hash.

Changes to the Qt5 editor can be checked with the optional PySide2 preview in
`tools/qt_check.py`. It uses fixture engine state and creates its own window;
this is not a hardware or audio measurement. System Qt5/PySide2 is a developer
requirement, not something the device installer downloads.
