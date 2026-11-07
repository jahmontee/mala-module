# Mala v2 interface and controls

Mala is a granular texture processor for Hector firmware 407. Read
USB-INSTALL.md, COMPATIBILITY.md and VALIDATION.md before installation.

## Knobs

Drag upward to increase and downward to decrease. Touching a knob does not
jump its value. Horizontal movement does not adjust it. A 160-pixel vertical
drag covers its full panel range, in one-percent position steps.
Double-tap resets to the minimum. For Pitch this is the lowest pitch setting;
for an attenurandomizer it is the negative endpoint. MIDI mapping suppresses
that gesture. Numerical knob readouts are hidden in this interface.

The Beads response lookup maps panel position into native pitch and modulation
ranges. The DSP, URI, 58 ports and saved-state format are retained. Loading
an existing patch preserves its values.

## Fresh instances

Feedback and Reverb start at 0%. Dry/Wet, Time, Density, Pitch, Size, Shape and
all four attenurandomizers start at noon. Initialization happens once after
Add Module. Opening the editor or restoring a patch does not reset values.
Pitch at noon is zero semitones and the attenurandomizers are neutral.
Density at noon stops automatic grains. Move it away from center or use Seed
to generate grains.

## Panel controls

Freeze, Seed and Latch have separate yellow indications. Latch holds Seed
active. A short Seed press clears latch; holding Seed for four seconds engages
it. The quality button below Density opens its four-mode menu. See
[V2-QUALITY.md](V2-QUALITY.md) and [V2-PANEL-CONTROLS.md](V2-PANEL-CONTROLS.md).

Mono Buffer and its status are below CV Assignment. Back is at the lower left,
Module Settings beside it, Map MIDI and Bypass at the right. The existing
whole-patch CPU reading is in Module Settings. Bypass follows host acknowledgement.

Runtime graphics are the panel texture, knob body and button face under
ui/qml/mala/assets. Pointers, guides, symbols, labels and the Shape envelope
are drawn by the interface. The current screenshot is available on GitHub.
USB kits omit documentation images while retaining runtime graphics and source.
