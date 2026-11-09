import QtQuick 2.11
import QtQuick.Controls 2.4
import "."
import QtQuick.Controls.Material 2.4

Dialog {
    id: help
    objectName: "mala_mode_help"
    parent: Overlay.overlay
    width: Math.min(1040, parent.width - 32)
    height: Math.min(650, parent.height - 32)
    anchors.centerIn: parent
    modal: true
    enter: Transition {}
    exit: Transition {}
    title: "Mala · mode reference"
    standardButtons: Dialog.Close
    Material.theme: Material.Dark
    Overlay.modal: Rectangle { color: "#b0000000" }
    background: Rectangle { color: "#17212b"; border.color: "#456071"; radius: 10 }
    contentItem: Flickable {
        clip: true
        contentWidth: width
        contentHeight: reference.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}
        Label {
            id: reference
            objectName: "mala_mode_help_text"
            width: parent.width - 24
            wrapMode: Text.WordWrap
            textFormat: Text.RichText
            font.pixelSize: 18
            color: "#e0e8ed"
            text: "<h3>One fixed panel</h3>"
                + "<p>Names and markings stay fixed, like Beads. The processing changes with your patch. Values, connection colors and active-state highlights still update.</p>"
                + "<h3>Granular processing</h3>"
                + "<p>Connect audio and keep Size below its far-right endpoint. Time selects recorded material; Size sets grain duration and forward/reverse playback; Shape sets the envelope; Pitch transposes grains. Feedback recirculates audio. Dry/Wet blends input and grains; Reverb adds ambience.</p>"
                + "<h3>Delay and beat slicing</h3>"
                + "<p>Move Size fully right to the infinity marking. Density sets the base delay timing or subdivisions of a Seed clock/tapped tempo. Its right side can add an unevenly spaced tap. Time selects a delay-time multiple. With Freeze engaged, Time selects a looping slice instead. Shape envelopes the repeats; Pitch shifts the delayed signal. Lower Size to return to granular processing.</p>"
                + "<h3>Wavetable synthesis</h3>"
                + "<p>Unpatch both audio inputs and release Freeze. After ten seconds of quiet output, synthesis starts automatically; audible tails extend the wait. Feedback selects the wavetable bank; Dry/Wet blends the continuous oscillator and grains. Time scans waveforms, Pitch sets the root pitch, Size sets grain duration and Shape sets the grain envelope. Size's printed reverse and infinity markings do not select reverse or delay here. Reverb remains reverb.</p>"
                + "<p>Pitch CV tracks 1 V/oct independently of the Pitch attenurandomizer, which controls grain-pitch randomness. Freeze holds grain envelopes and stops new grains; oscillator phases continue. Reconnecting an audio input returns to recording after Freeze releases.</p>"
                + "<h3>Density, Seed and Latch</h3>"
                + "<p>In granular and synthesis operation, Latch enables continuous grains: Density's left side is periodic, its right side random, and its center stops automatic grains. With Latch on and a Seed signal connected, those sides become clock division and trigger probability. With Latch off, Seed gates a burst; at centered Density, each trigger starts one grain. Delay uses the timing rules above.</p>"
                + "<h3>CV / Random and quality</h3>"
                + "<p>With no parameter CV connected, the amount slider selects peaky or uniform internal randomness. With CV connected, its right side scales direct modulation and its left side scales CV-controlled randomness. Delay uses slow internal modulation. Turquoise CV captions indicate a connected input; grey indicates unpatched. CV Assignment follows the selected mix control's function, including bank and oscillator/grain blend in synthesis.</p>"
                + "<p>The four quality choices select recording character in granular/delay operation and output resolution in synthesis. Recording quality and mono/stereo changes wait while frozen. Freeze and Latch highlights show active states without renaming their buttons.</p>"
                + "<h3>CV input units</h3>"
                + "<p>Module Settings selects how incoming continuous CV is interpreted. Legacy virtual volts preserves older patches. Hector / Poly units converts stock signals by ×5 before Beads modulation: a pitch signal change of 0.2 represents one volt and one octave at full pitch depth. In wavetable synthesis, root pitch CV tracks independently of the pitch amount.</p>"
                + "<p>Only newly added Hector instances select Hector units automatically. Existing patches retain legacy units until you explicitly change this setting; your choice is saved with the patch. The conversion affects Time, Size, Shape, Pitch, Density and assignable CV, while audio, Seed and Freeze gates are unchanged. Physical voltage accuracy still depends on Hector and your pitch source.</p>"
                + "<h3>Assignable CV amounts</h3>"
                + "<p>Feedback, Dry/Wet and Reverb select full-depth CV for one destination. Adjusting its amount changes the selection to Weighted combination and zeros the other two amounts. In Weighted combination, each amount can be adjusted independently.</p>"
                + "<h3>Remembering a frozen recording</h3>"
                + "<p>Enable Remember Frozen Buffer in Module Settings, then keep Freeze active for ten seconds and wait for the recording to be ready. In the Hector/Beebo patch interface, save the patch to retain that recording. Waiting ten seconds alone does not save it to storage; an unsaved recording can be lost when the rack is switched off.</p>"
                + "<p>Loading a saved patch restores its captured recording frozen. Tap Freeze to release the restored hold; a high Freeze input gate continues to hold it. Quality and mono/stereo changes wait until Freeze is fully released. Wavetable voices and reverb tails are not saved. The standalone desktop preview uses its own local session save, separate from Hector patch storage.</p>"
        }
    }
}
