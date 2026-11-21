# Mala 0.3.0-beta.11 module source

This archive contains the module DSP source, the editor files from the signed
release, the module description and port metadata, and the upstream notices.
For installation on Hector use the separate signed USB ZIP.

Run `sh build-dsp.sh` to build the AArch64 module. The release used
`aarch64-linux-gnu-g++-12 (Debian 12.2.0-14) 12.2.0` from Debian and the flags in the script.
The source is included locally. The build does not download dependencies.

SHA-256 of the released `module.so`:

`6b921ab31333f55cfff4883c21ff415c8e4aa50bc37274b6f00127cd50939993`

The upstream lock records the origin of the vendored files. The release builds
the updated source in this archive, including the delay-line indexing change.
See `LICENSE`, `COPYING`, `LICENSES/`, and `CREDITS.md`.
