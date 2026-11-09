# Credits

**Original Beads design and DSP:** Emilie Gillet / Mutable Instruments. Mala is
built from the published Beads and stmlib source, not a firmware binary port.
Their original copyright and MIT notices are retained in every vendored source.

**Additional upstream Beads contributors:** Frédéric Meslin / Fred's Lab and
Oliver Rockstedt / sourcebox.de, as identified in the gain-control sources.

**Hector/Beebo UI and platform integration:** Poly Effects and the digit_ui
contributors. The integration uses public digit_ui commit
`9d83f1a3105de182d83af0580e4cb1afec00f978`, matched to the selected firmware 407
source files. Only the required source modifications are included; no firmware
image, stock DSP binaries, fonts, icons, factory presets or runtime libraries are
redistributed here.

**Mala host adapter, touchscreen editor, CV handling, frozen-buffer integration,
and release tooling:** Beebo / Hector Lab contributors, 2026.

**Project direction, feature decisions and physical Hector testing:** jahmontee /
Poly Hector.

**AI development assistance:** OpenAI Codex assisted with the Hector adaptation,
touchscreen implementation, testing tools, documentation and release packaging.

**Slider placement:** The Qt Company, Qt Quick Controls 2 Material Slider; its
complete notice and applicable GPL/LGPL texts are included. Other Qt classes are
used from Hector's existing installation; Qt libraries are not shipped.

**LV2 interface headers:** their upstream authors, including David Robillard and
other contributors credited in the included headers. Their original notices are
retained. **Compiler runtime:** GCC contributors; the runtime exception/copyright
notice accompanies the accepted ARM build. No compiler or system libraries ship.

This is an independent community beta. Poly Effects and Mutable Instruments
have not been represented as sponsors, endorsers, or support providers for Mala.
