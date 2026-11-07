// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.11
import QtQuick.Controls 2.4
import QtQuick.Controls.Material 2.4
import "."

Item {
    id: editor
    width: 1280; height: 656
    property bool midiMapping: false
    // Temporary appearance switches; all parameter values and controls are retained.
    property bool showKnobValues: false
    property bool showLowerBadges: false
    readonly property int switchColumnX: 1075
    readonly property real sideRowCenterY: 158.5
    readonly property int sideRowSpacing: 116
    readonly property int grainSectionOffsetY: 18
    readonly property int sizeRegion: controls.size.value > .99 ? 2 : controls.size.value < .3333333 ? 0 : 1
    readonly property bool synthActive: controls.active_synth.value > .5
    readonly property var qualityColors: ["#fffdf4", "#379cf1", "#f5a03c", "#e45a9e"]
    readonly property var qualityNames: ["Bright digital", "Cold digital", "Sunny tape", "Scorched cassette"]
    readonly property int activeQuality: Math.max(0, Math.min(3, Math.round(controls.active_quality.value)))
    readonly property bool qualityPending: controls.quality.value !== controls.active_quality.value
    signal midiMapRequested(string symbol)
    signal showRouting()
    Material.theme: Material.Light

    Label { x: 435; y: 0; text: "MALA"; font.pixelSize: 41; font.letterSpacing: 7; font.weight: Font.Light; color: "#181716" }
    Label { x: 610; y: 12; text: "texture synthesizer"; font.pixelSize: 27; font.weight: Font.Light; color: "#252321" }
    Label { objectName: "mala_version_label"; x: 1095; y: 17; width: 160; text: "v0.2.0-beta.1"; color: "#292725"; font.pixelSize: 15; horizontalAlignment: Text.AlignRight }
    Canvas {
        x: 0; y: 51; width: parent.width; height: 17
        onPaint: {
            var c=getContext("2d");c.clearRect(0,0,width,height);c.save();c.strokeStyle="#a6a19d";c.lineWidth=.85;
            c.beginPath();c.moveTo(0,1);c.lineTo(width,1);c.moveTo(0,16);c.lineTo(width,16);c.stroke();
            for(var x=-10;x<width;x+=19) {
                c.beginPath();c.moveTo(x+9,3);c.lineTo(x+3,8.5);c.lineTo(x+9,14);c.lineTo(x+15,8.5);c.closePath();c.stroke();
                c.beginPath();c.moveTo(x+3,3);c.lineTo(x-3,8.5);c.lineTo(x+3,14);c.moveTo(x+15,3);c.lineTo(x+21,8.5);c.lineTo(x+15,14);c.stroke();
            }
            c.restore();
        }
    }
    Repeater {
        model: ["feedback", "mix", "reverb"]
        BeadsKnob {
            showValue: editor.showKnobValues
            objectName: modelData + "_parameter"
            x: 24; y: editor.sideRowCenterY + index * editor.sideRowSpacing - diameter / 2
            width: 230; height: 91; diameter: 79; compact: true
            faceX: 40; labelX: 133; labelY: centeredSideLabelY; titleSize: 20; valueSize: 25
            paramSymbol: modelData; title: ["FEEDBACK", "DRY / WET", "REVERB"][index]
            badgeSymbol: ["feedback", "cloud", "cube"][index]
            accent: ["#00b6c0", "#ffce08", "#df1472"][index]
            midiMapping: editor.midiMapping; onMidiMapRequested: editor.midiMapRequested(symbol)
        }
    }
    BeadsKnob { showValue: editor.showKnobValues; objectName: "time_parameter"; x: 298; y: 118 + editor.grainSectionOffsetY; width: 178; height: 207; diameter: 154; paramSymbol: "time"; title: "TIME"; caption: "RECENT · OLDEST"; midiMapping: editor.midiMapping; onMidiMapRequested: editor.midiMapRequested(symbol) }
    BeadsKnob { showValue: editor.showKnobValues; objectName: "density_parameter"; x: 528; y: 72 + editor.grainSectionOffsetY; width: 222; height: 237; diameter: 186; scaleRing: true; paramSymbol: "density"; title: "DENSITY"; caption: "PERIODIC · STOP · RANDOM"; midiMapping: editor.midiMapping; onMidiMapRequested: editor.midiMapRequested(symbol) }
    BeadsKnob { showValue: editor.showKnobValues; objectName: "pitch_parameter"; x: 809; y: 118 + editor.grainSectionOffsetY; width: 178; height: 207; diameter: 156; paramSymbol: "pitch"; title: "PITCH"; caption: "−24 · SEMITONES · +24"; midiMapping: editor.midiMapping; onMidiMapRequested: editor.midiMapRequested(symbol) }
    BeadsKnob { showValue: editor.showKnobValues; objectName: "size_parameter"; x: 387; y: 311 + editor.grainSectionOffsetY; width: 196; height: 190; diameter: 130; titleSize: 20; valueSize: 18; paramSymbol: "size"; title: "SIZE"; caption: "Reverse grains · Forward grains · Delay at the far-right end"; midiMapping: editor.midiMapping; onMidiMapRequested: editor.midiMapRequested(symbol) }
    BeadsKnob { showValue: editor.showKnobValues; objectName: "shape_parameter"; x: 692; y: 311 + editor.grainSectionOffsetY; width: 196; height: 190; diameter: 130; titleSize: 20; valueSize: 18; paramSymbol: "shape"; title: "SHAPE"; caption: "Square · Decay · Bell · Rising envelope"; midiMapping: editor.midiMapping; onMidiMapRequested: editor.midiMapRequested(symbol) }
    Canvas {
        x: 310; y: 251 + editor.grainSectionOffsetY; width: 665; height: 124
        onPaint: {
            var c=getContext("2d");c.clearRect(0,0,width,height);c.save();c.fillStyle="#282522";
            function dots(a,b,d,e,f,g,h,j) {
                for(var i=0;i<=28;i++) {
                    var t=i/28,u=1-t;var x=u*u*u*a+3*u*u*t*d+3*u*t*t*f+t*t*t*h;var y=u*u*u*b+3*u*u*t*e+3*u*t*t*g+t*t*t*j;
                    c.beginPath();c.arc(x,y,1.15,0,Math.PI*2);c.fill();
                }
            }
            dots(19,8,-7,81,28,103,105,124);dots(647,8,671,81,635,103,557,124);
            c.restore();
        }
    }
    Rectangle {
        id: qualityLed
        objectName: "quality_led"
        x: 582; y: 331 + editor.grainSectionOffsetY; width: 19; height: 19; radius: width / 2; antialiasing: true
        readonly property color modeColor: editor.qualityColors[editor.activeQuality]
        readonly property string modeName: editor.qualityNames[editor.activeQuality]
        color: modeColor; border.width: 1.2; border.color: "#6b5d52"
        gradient: Gradient {
            GradientStop { position: 0; color: Qt.lighter(qualityLed.modeColor, 1.2) }
            GradientStop { position: 1; color: Qt.darker(qualityLed.modeColor, 1.08) }
        }
        Rectangle { x: 4; y: 3; width: 6; height: 3; radius: 2; color: "#aaffffff"; antialiasing: true }
        Accessible.role: Accessible.StaticText
        Accessible.name: "Active quality: " + modeName
    }
    ComboBox {
        id: qualitySelector
        objectName: "quality_selector"; x: 612; y: 316 + editor.grainSectionOffsetY; width: 48; height: 48
        model: editor.qualityNames
        currentIndex: controls.quality.value
        Accessible.name: "Recording quality"
        Accessible.description: "Active: " + qualityLed.modeName + (editor.qualityPending ? "; " + displayText + " queued" : "")
        font.pixelSize: 19; padding: 0
        indicator: Item {}
        contentItem: Item {}
        background: Item {
            anchors.fill: parent
            Rectangle { x: 11; y: 13; width: 28; height: 28; radius: 14; color: "#22000000"; antialiasing: true }
            Rectangle {
                x: 10; y: 10; width: 28; height: 28; radius: 14; antialiasing: true
                border.width: 1.7; border.color: qualitySelector.down || qualitySelector.visualFocus ? "#008f98" : "#57504a"
                gradient: Gradient {
                    GradientStop { position: 0; color: qualitySelector.down ? "#24211f" : "#4a4743" }
                    GradientStop { position: 1; color: "#151311" }
                }
            }
        }
        delegate: ItemDelegate {
            id: option
            objectName: "quality_option_" + index
            width: qualitySelector.popup.width - 12; height: 50
            text: modelData; font: qualitySelector.font
            highlighted: qualitySelector.highlightedIndex === index
            contentItem: Item {
                implicitHeight: 34
                Rectangle {
                    x: 5; y: (parent.height - height) / 2; width: 17; height: 17; radius: 9
                    color: editor.qualityColors[index]; border.color: "#76675d"; antialiasing: true
                }
                Text { x: 35; height: parent.height; width: parent.width - 62; text: option.text; font: option.font; color: "#211c18"; verticalAlignment: Text.AlignVCenter }
                Text { x: parent.width - 24; height: parent.height; width: 24; text: qualitySelector.currentIndex === index ? "✓" : ""; color: "#007f85"; font.pixelSize: 21; verticalAlignment: Text.AlignVCenter }
            }
            background: Rectangle { color: option.highlighted ? "#dce8df" : "#faf5ed"; radius: 5 }
        }
        popup: Popup {
            objectName: "quality_popup"
            modal: true; dim: false
            x: (qualitySelector.width - width) / 2; y: qualitySelector.height + 6
            width: 284; padding: 6
            scale: editor.parent ? editor.parent.scale : 1; transformOrigin: Item.TopLeft
            implicitHeight: contentItem.implicitHeight + topPadding + bottomPadding
            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
            enter: Transition {}
            exit: Transition {}
            contentItem: ListView {
                clip: true; implicitHeight: contentHeight
                model: qualitySelector.delegateModel; currentIndex: qualitySelector.highlightedIndex; highlightMoveDuration: 0
            }
            background: Rectangle { radius: 8; color: "#faf5ed"; border.color: "#74665a" }
        }
        onActivated: controller.change("quality", currentIndex)
        ToolTip.visible: hovered && !popup.visible && !editor.midiMapping
        ToolTip.delay: 650
        ToolTip.text: qualityLed.modeName + (editor.qualityPending ? " · " + displayText + " queued" : "")
        MouseArea { objectName: "midi_target_quality"; anchors.fill: parent; z: 10; visible: editor.midiMapping; preventStealing: true; onClicked: editor.midiMapRequested("quality") }
    }
    Label { x: 601; y: 366 + editor.grainSectionOffsetY; width: 70; text: "QUALITY"; horizontalAlignment: Text.AlignHCenter; color: "#4b423b"; font.pixelSize: 11 }
    // Printed mode-color key; the round LED on the left shows the active DSP mode.
    Repeater {
        model: editor.qualityColors
        Rectangle {
            objectName: "quality_key_" + index
            x: 667; y: 324 + index*8 + editor.grainSectionOffsetY; width: [12,20,32,45][index]; height: 5; radius: 2.5
            color: modelData; border.width: index === 0 ? 1 : 0; border.color: "#9d8e7a"
        }
    }
    Canvas {
        x: 525; y: 264 + editor.grainSectionOffsetY; width: 228; height: 17
        onPaint: {
            var c=getContext("2d");c.clearRect(0,0,width,height);c.save();c.strokeStyle="#49433e";c.lineWidth=1.2;
            [0,208].forEach(function(x){for(var i=0;i<5;i++){c.beginPath();c.moveTo(x+i*4,3);c.lineTo(x+i*4,13);c.stroke();}});c.restore();
        }
    }
    // Fixed panel markings follow the knob's existing 270-degree value sweep.
    Repeater {
        model: [0,1,2]
        Label {
            objectName: "size_symbol_" + index
            x: [403,535,535][index]; y: [424,292,424][index] + editor.grainSectionOffsetY; width: 38; height: 29
            text: ["↶","→","∞"][index]; font.pixelSize: 29
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
            color: !editor.synthActive && editor.sizeRegion === index ? "#00858a" : "#403a34"
        }
    }
    Label {
        objectName: "size_mode_caption"; x: 407; y: 477 + editor.grainSectionOffsetY; width: 156; height: 14
        text: editor.synthActive ? "GRAIN DURATION" : ["REVERSE","FORWARD","∞  DELAY"][editor.sizeRegion]
        font.pixelSize: 11; color: "#62574d"; horizontalAlignment: Text.AlignHCenter
    }
    Repeater {
        model: [0,1/3,2/3,1]
        EnvelopeGraphic {
            objectName: "shape_mark_" + index
            x: [712,712,832,842][index]; y: [432,301,302,432][index] + editor.grainSectionOffsetY
            width: 28; height: 18; shapeValue: modelData; strokeWidth: 1.4
        }
    }
    Label { x: 908; y: 357 + editor.grainSectionOffsetY; width: 160; text: "ENVELOPE SHAPE"; font.pixelSize: 11; color: "#62574d"; horizontalAlignment: Text.AlignHCenter }
    EnvelopeGraphic {
        objectName: "shape_envelope_preview"
        x: 921; y: 379 + editor.grainSectionOffsetY; width: 134; height: 48; strokeWidth: 2
        shapeValue: controls.shape.value
    }
    BeadsSwitch {
        objectName: "freeze_button"; x: editor.switchColumnX; y: editor.sideRowCenterY - height / 2
        width: 200; height: 76; diameter: 67; text: "FREEZE"
        highlighted: controls.active_freeze.value > .5; accent: "#dba51b"
        midiMapping: editor.midiMapping; midiParameter: "freeze"
        onMidiMapRequested: editor.midiMapRequested(symbol); onClicked: controller.toggleFreeze()
    }
    BeadsSwitch {
        objectName: "seed_button"; x: editor.switchColumnX; y: editor.sideRowCenterY + editor.sideRowSpacing - height / 2
        width: 200; height: 76; diameter: 67; text: "SEED"
        accent: "#dba51b"; highlighted: controls.seed.value === 1
        midiMapping: editor.midiMapping; midiParameter: "seed"; onMidiMapRequested: editor.midiMapRequested(symbol)
        onPressed: controller.seedPress(); onReleased: controller.seedRelease(); onCanceled: controller.seedRelease()
    }
    BeadsSwitch {
        objectName: "latch_button"; x: editor.switchColumnX; y: editor.sideRowCenterY + 2 * editor.sideRowSpacing - height / 2
        width: 200; height: 76; diameter: 67; text: "LATCH"
        highlighted: controller.seedLatched; accent: "#c99b0a"
        midiMapping: editor.midiMapping; midiParameter: "seed"
        onMidiMapRequested: editor.midiMapRequested(symbol); onClicked: controller.toggleLatch()
    }
    TouchButton { id: assignmentButton; objectName: "assignment_button"; x: 28; y: 455; width: 158; height: 51; text: "CV\nASSIGNMENT"; font.pixelSize: 16; font.bold: true; onClicked: editor.showRouting() }
    CheckBox {
        id: monoCheckbox
        objectName: "mono_checkbox"
        x: assignmentButton.x; y: assignmentButton.y + assignmentButton.height + 21
        width: assignmentButton.width; height: 36
        text: "MONO BUFFER"; checked: controls.mono.value > .5; font.pixelSize: 16; padding: 0
        indicator: Rectangle { objectName: "mono_indicator"; x: 4; width: 23; height: 23; y: (monoCheckbox.height - height) / 2; radius: 2; color: "transparent"; border.width: 2; border.color: "#25221f"; Text { anchors.centerIn: parent; text: monoCheckbox.checked ? "✓" : ""; font.pixelSize: 20; color: "#25221f" } }
        contentItem: Text { objectName: "mono_label"; text: monoCheckbox.text; font: monoCheckbox.font; leftPadding: 35; color: "#151412"; verticalAlignment: Text.AlignVCenter }
        Material.foreground: "#303532"; Material.accent: "#008f98"
        onClicked: controller.change("mono", checked ? 1 : 0)
        MouseArea { objectName: "midi_target_mono"; anchors.fill: parent; z: 10; visible: editor.midiMapping; preventStealing: true; onClicked: editor.midiMapRequested("mono") }
    }
    Label {
        objectName: "mode_status"
        x: monoCheckbox.x + 4; y: monoCheckbox.y + monoCheckbox.height + 6
        width: monoCheckbox.width - 8
        visible: controls.mode_transition.value > .5 || editor.synthActive || controls.quality.value !== controls.active_quality.value || requestedMono !== (controls.active_mono.value > .5)
        horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: "#665446"; font.pixelSize: 13
        readonly property bool requestedMono: controls.input_stage.value > .5 && controls.audio_connections.value === 0 ? controls.active_mono.value > .5 : controls.mono.value > .5 || (controls.input_stage.value > .5 && controls.audio_connections.value !== 3)
        text: controls.mode_transition.value > .5 ? "SWITCHING…" : editor.synthActive ? "WAVETABLE\n48 kHz · " + ["16-bit", "7-bit", "16-bit osc / 6-bit grains", "4-bit"][controls.active_quality.value] : (editor.qualityPending ? "QUEUED · " + editor.qualityNames[controls.quality.value] + " · " : requestedMono !== (controls.active_mono.value > .5) ? "QUEUED · " : "") + controls.buffer_seconds.value.toFixed(2) + " s " + (controls.active_mono.value > .5 ? "MONO" : "STEREO") + " BUFFER"
    }
    Label { x: 518; y: 515; width: 260; text: "ATTENURANDOMIZERS"; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 20; font.bold: true; color: "#171513" }
    Canvas {
        x: 0; y: 0; width: parent.width; height: parent.height
        onPaint: {
            var c=getContext("2d");c.clearRect(0,0,width,height);c.save();c.fillStyle="#4e4741";
            for(var x=199;x<506;x+=6){c.beginPath();c.arc(x,527,1.05,0,Math.PI*2);c.fill();}
            for(var x=781;x<1115;x+=6){c.beginPath();c.arc(x,527,1.05,0,Math.PI*2);c.fill();}
            [376,634,892].forEach(function(x){for(var y=566;y<641;y+=6){c.beginPath();c.arc(x,y,.85,0,Math.PI*2);c.fill();}});
            c.restore();
        }
    }
    Repeater {
        model: ["time", "size", "shape", "pitch"]
        BeadsKnob {
            showValue: editor.showKnobValues
            x: [151, 395, 653, 925][index]; y: 541; width: 220; height: 113; diameter: 79; labelPlacement: "above"; showAccent: editor.showLowerBadges
            faceY: 28; titleSize: 17; valueSize: 15; valueOnTouch: true
            objectName: modelData + "_amount_parameter"
            paramSymbol: modelData + "_amount"; title: modelData.toUpperCase()
            badgeSymbol: ["random", "dice", "wave", "cube"][index]
            connected: controller.patchedInputs[modelData + "_cv"]
            caption: connected ? "RANDOM − · + CV" : "PEAKY − · + UNIFORM"
            accent: ["#00b7bf", "#ffcf0a", "#ff8b0b", "#df1472"][index]
            midiMapping: editor.midiMapping; onMidiMapRequested: editor.midiMapRequested(symbol)
        }
    }
}
