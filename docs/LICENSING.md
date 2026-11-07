# Licensing and source provenance

The repository is intentionally mixed-license. Do not replace all notices with
one MIT header or describe the complete Hector UI as MIT.

| Component | Distribution terms and source |
|---|---|
| Authored Mala adapter, new panel/Python helpers, installer and tools | MIT; LICENSES/MIT-Mala.txt |
| Vendored Beads/stmlib | Original MIT notices in each file; locked commits in provenance/source-lock.json |
| LV2 headers | Original per-file permissive licenses; headers are included under vendor/lv2-headers |
| digit_ui files and Mala modifications | GPL; upstream README specifies GPL without a version; this combined UI distribution uses GPL version 3, with full text in COPYING |
| Material Slider-derived wrapper | Qt's GPL-2.0-or-later alternative, used under GPL version 3; full original notice remains in ui/qml/mala/Slider.qml |
| Potential compiler runtime code | GCC runtime library exception and package copyright in LICENSES/GCC-Runtime.txt |

The selected upstream GPL statement is preserved verbatim in
LICENSES/digit-ui-statement.txt. Choosing GPL version 3 for this combined UI does
not claim that upstream originally specified GPL-3.0-only. Existing upstream
notices and the Qt alternative-license notice remain intact.

The USB ZIPs include their complete corresponding project source under
`mala/source/`, including the modified UI source, original selected public 407
preimages, exact integration patch, locked portable Beads/stmlib sources, build
overlays and build scripts. The separate source archive contains the same program source and runtime
assets, plus the finished documentation screenshot omitted from the USB kits.
The retained ARM binary is the accepted Mala DSP. The v2 release changes the
interface, fresh-add initialization and coordinated compatibility packaging. No network fetch is required to compile the source.

Source locks identify original bytes and upstream URLs. Build overlays explicitly
isolate RNG storage per thread, guard an unused zero-weight wavetable read,
provide a type-only codec shim and extract the portable PotChannel class. Original
vendor source files are kept unchanged. Portable source and waveform resources
are included under their source notices; STM32 hardware drivers are not compiled.

The public export excludes private lab history, device-specific manifests,
transaction keys/records, credentials, owner presets and recordings, firmware
images, proprietary binaries, third-party runtime libraries and SD/NOR dumps.
Device-local backups necessarily retain that tester's own pre-installation files;
they are private recovery data and must not be posted in issues.
