import QtQuick 2.11
import QtQuick.Controls 2.4
import "."
import QtQuick.Controls.Material 2.4

Item {
    id: editor
    width: 1280; height: 620
    property string selectedParameter: "feedback"
    property bool midiMapping: false
    signal midiMapRequested(string symbol)
    property int sizeRegion: controls.size.value > .99 ? 2 : controls.size.value < .3333333 ? 0 : 1
    property bool synthActive: controls.active_synth.value > .5
    signal showRouting()
    Rectangle { anchors.fill: parent; color: "#000000"; radius: 14 }
    property var mixColors: ({"feedback": "#42c9c4", "mix": "#efaa45", "reverb": "#dc70b8"})
    readonly property var mixNames: ({"feedback": "Feedback", "mix": "Dry/Wet", "reverb": "Reverb"})
    property var qualityColors: ["#ffffff", "#42c9c4", "#efaa45", "#dc70b8"]
    Column {
        x: 24; y: 24; spacing: 12
        Repeater {
            model: ["feedback", "mix", "reverb"]
            TouchButton {
                id: parameterButton
                width: 150; height: 108; objectName: "select_" + modelData
                checkable: true; checked: editor.selectedParameter === modelData
                highlighted: checked; accent: editor.mixColors[modelData]
                midiMapping: editor.midiMapping; midiParameter: modelData
                onMidiMapRequested: editor.midiMapRequested(symbol)
                contentItem: Column {
                    spacing: 10
                    Label { objectName: "mix_name_" + modelData; width: parent.width; horizontalAlignment: Text.AlignHCenter; text: editor.mixNames[modelData]; color: editor.mixColors[modelData]; font.pixelSize: 18 }
                    Label { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: controls[modelData].value.toFixed(2); color: "#eef3f5"; font.pixelSize: 27 }
                }
                onClicked: editor.selectedParameter = modelData
            }
        }
        TouchButton { objectName: "assignment_button"; width: 150; height: 70; text: "CV\nASSIGNMENT"; onClicked: editor.showRouting() }
        Label {
            objectName: "mala_version_label"; width: 150; height: 20
            text: "v0.1.0-beta.6"; horizontalAlignment: Text.AlignHCenter
            color: "#9caab1"; font.pixelSize: 14
        }
    }
    ParameterSlider { objectName: "mixer_parameter"; x: 190; y: 28; width: 112; height: 444; vertical: true; paramSymbol: editor.selectedParameter; title: editor.mixNames[editor.selectedParameter]; accent: editor.mixColors[editor.selectedParameter]; midiMapping: editor.midiMapping; onMidiMapRequested: editor.midiMapRequested(symbol) }
    Rectangle { x: 320; y: 24; width: 1; height: 444; color: "#38434f" }
    ParameterSlider {
        objectName: "density_parameter"; x: 340; y: 24; width: 908; height: 92; paramSymbol: "density"; accent: "#e5ba78"
        title: "DENSITY"
        midiMapping: editor.midiMapping; onMidiMapRequested: editor.midiMapRequested(symbol)
        leftText: "PERIODIC"
        rightText: "RANDOM"
    }
    Label { x: 340; y: 119; width: 908; horizontalAlignment: Text.AlignHCenter; text: "STOP"; color: "#a8bac6"; font.pixelSize: 12 }
    ParameterSlider { objectName: "time_parameter"; x: 340; y: 149; width: 438; height: 92; paramSymbol: "time"; title: "TIME"; leftText: "RECENT"; rightText: "OLDEST"; midiMapping: editor.midiMapping; onMidiMapRequested: editor.midiMapRequested(symbol) }
    ParameterSlider { objectName: "pitch_parameter"; x: 810; y: 149; width: 438; height: 92; paramSymbol: "pitch"; title: "PITCH · SEMITONES"; leftText: "−24"; rightText: "+24"; midiMapping: editor.midiMapping; onMidiMapRequested: editor.midiMapRequested(symbol) }
    Label { objectName: "size_title"; x: 340; y: 269; width: 438; horizontalAlignment: Text.AlignHCenter; text: "SIZE"; font.pixelSize: 19; color: "#8ebfe8" }
    ParameterSlider { id: sizeSlider; x: 340; y: 284; width: 438; height: 78; paramSymbol: "size"; title: ""; accent: "#8ebfe8"; midiMapping: editor.midiMapping; onMidiMapRequested: editor.midiMapRequested(symbol) }
    Row {
        id: sizeRegions
        x: 340; y: 368; width: 438
        Repeater {
            model: ["REVERSE", "FORWARD", "DELAY"]
            Column {
                width: sizeRegions.width / 3; spacing: 4
                property color regionColor: editor.sizeRegion === index ? "#8ebfe8" : "#a8bac6"
                Label { objectName: "size_symbol_" + index; width: parent.width; height: 43; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; text: ["←", "→", "∞"][index]; color: parent.regionColor; font.pixelSize: 34 }
                Label { objectName: "size_region_" + index; width: parent.width; horizontalAlignment: Text.AlignHCenter; text: modelData; color: parent.regionColor; font.pixelSize: 12 }
            }
        }
    }
    Label { objectName: "shape_title"; x: 810; y: 269; width: 438; horizontalAlignment: Text.AlignHCenter; text: "SHAPE"; font.pixelSize: 19; color: "#8ebfe8" }
    ParameterSlider { id: shapeSlider; x: 810; y: 284; width: 438; height: 78; paramSymbol: "shape"; title: ""; accent: "#8ebfe8"; midiMapping: editor.midiMapping; onMidiMapRequested: editor.midiMapRequested(symbol) }
    Row {
        id: shapes
        x: 810; y: 368; width: 438
        Repeater {
            model: ["RECTANGLE", "DECAY", "BELL", "SLOW ATTACK"]
            Column {
                width: shapes.width / 4; spacing: 4
                Canvas {
                    objectName: "shape_graphic_" + index
                    width: parent.width - 30; height: 43; anchors.horizontalCenter: parent.horizontalCenter
                    onPaint: {
                        var c=getContext("2d"); c.clearRect(0,0,width,height);
                        c.save(); c.scale(width / 104, height / 51);
                        c.strokeStyle="#8ebfe8"; c.lineWidth=2.5; c.beginPath(); c.moveTo(4,46);
                        if (index===0) { c.lineTo(4,6); c.lineTo(99,6); c.lineTo(99,46); }
                        else if (index===1) { c.lineTo(4,6); c.quadraticCurveTo(15,43,99,46); }
                        else if (index===2) { c.bezierCurveTo(19,46,26,6,52,6); c.bezierCurveTo(77,6,83,46,99,46); }
                        else { c.quadraticCurveTo(91,43,99,6); c.lineTo(99,46); }
                        c.stroke(); c.restore();
                    }
                }
                Label { objectName: "shape_region_" + index; width: parent.width; horizontalAlignment: Text.AlignHCenter; text: modelData; color: "#a8bac6"; font.pixelSize: 12 }
            }
        }
    }
    TouchButton {
        id: freezeButton
        objectName: "freeze_button"; x: sizeSlider.x + (sizeSlider.width - width - seedButton.width - latchButton.width - 24)/2; y: 448; width: 164; height: 52
        text: "❄  FREEZE"
        midiMapping: editor.midiMapping; midiParameter: "freeze"; onMidiMapRequested: editor.midiMapRequested(symbol)
        highlighted: controls.active_freeze.value > .5; Material.accent: "#d799c6"
        accent: "#d799c6"
        onClicked: controller.toggleFreeze()
    }
    TouchButton {
        id: seedButton
        objectName: "seed_button"; x: freezeButton.x + freezeButton.width + 12; y: 448; width: 128; height: 52
        text: "✦  SEED"; Material.accent: "#e5ba78"
        midiMapping: editor.midiMapping; midiParameter: "seed"; onMidiMapRequested: editor.midiMapRequested(symbol)
        accent: "#e5ba78"
        onPressed: controller.seedPress()
        onReleased: controller.seedRelease()
        onCanceled: controller.seedRelease()
    }
    TouchButton {
        id: latchButton
        objectName: "latch_button"; x: seedButton.x + seedButton.width + 12; y: 448; width: 120; height: 52
        text: "LATCH"; highlighted: controller.seedLatched
        midiMapping: editor.midiMapping; midiParameter: "seed"; onMidiMapRequested: editor.midiMapRequested(symbol)
        Material.accent: "#e5ba78"; onClicked: controller.toggleLatch()
        accent: "#e5ba78"
    }
    ComboBox {
        id: qualitySelector
        objectName: "quality_selector"; x: shapeSlider.x + (shapeSlider.width - width - monoCheckbox.width - 12)/2; y: 448; width: 230; height: 52
        model: ["Bright digital", "Cold digital", "Sunny tape", "Scorched cassette"]
        currentIndex: controls.quality.value
        property color modeColor: editor.qualityColors[Math.max(0, currentIndex)]
        font.pixelSize: 16; Material.accent: modeColor; Material.foreground: modeColor
        leftPadding: 12; rightPadding: 32
        contentItem: Text {
            objectName: "quality_current_label"
            text: qualitySelector.displayText; font: qualitySelector.font; color: qualitySelector.modeColor
            verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
        }
        // Opaque panels also work with the lab's Qt software renderer.
        background: Rectangle {
            radius: 8; color: "#202e3a"
            border.color: qualitySelector.activeFocus ? qualitySelector.modeColor : "#526273"
        }
        delegate: ItemDelegate {
            id: qualityOption
            objectName: "quality_option_" + index; width: qualitySelector.width - 8; height: 48
            text: modelData; font: qualitySelector.font
            highlighted: qualitySelector.highlightedIndex === index
            contentItem: Text {
                objectName: "quality_option_label_" + index
                text: qualityOption.text; font: qualityOption.font; color: editor.qualityColors[index]
                verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
            }
        }
        popup: Popup {
            y: -height - 6; width: qualitySelector.width; padding: 4
            // Popups live in the window overlay, outside the scaled device surface.
            scale: editor.parent ? editor.parent.scale : 1; transformOrigin: Item.TopLeft
            implicitHeight: contentItem.implicitHeight + topPadding + bottomPadding
            enter: Transition {}
            exit: Transition {}
            contentItem: ListView {
                clip: true; implicitHeight: contentHeight
                model: qualitySelector.delegateModel; currentIndex: qualitySelector.highlightedIndex
                highlightMoveDuration: 0
            }
            background: Rectangle { radius: 8; color: "#24313e"; border.color: "#526273" }
        }
        onActivated: controller.change("quality", currentIndex)
        MouseArea {
            objectName: "midi_target_quality"; anchors.fill: parent; z: 10
            visible: editor.midiMapping; preventStealing: true
            onClicked: editor.midiMapRequested("quality")
        }
    }
    CheckBox {
        id: monoCheckbox
        objectName: "mono_checkbox"; x: qualitySelector.x + qualitySelector.width + 12; y: 448; height: 52
        text: "MONO BUFFER"; checked: controls.mono.value > .5
        font.pixelSize: 16; Material.accent: qualitySelector.modeColor
        onClicked: controller.change("mono", checked ? 1 : 0)
        MouseArea {
            objectName: "midi_target_mono"; anchors.fill: parent; z: 10
            visible: editor.midiMapping; preventStealing: true
            onClicked: editor.midiMapRequested("mono")
        }
    }
    Label { x: sizeSlider.x; y: 503; width: sizeSlider.width; horizontalAlignment: Text.AlignHCenter; text: "Hold Seed 4 s to latch · Seed + Freeze also latches"; color: "#9caab1"; font.pixelSize: 12 }
    Label {
        objectName: "mode_status"; x: shapeSlider.x; y: 503; width: shapeSlider.width; horizontalAlignment: Text.AlignHCenter
        property bool requestedMono: controls.input_stage.value > .5 && controls.audio_connections.value === 0 ? controls.active_mono.value > .5 : controls.mono.value > .5 || (controls.input_stage.value > .5 && controls.audio_connections.value !== 3)
        text: controls.mode_transition.value > .5 ? "SWITCHING…" : editor.synthActive ? "WAVETABLE · 48 kHz · " + ["16-bit", "7-bit", "16-bit osc / 6-bit grains", "4-bit"][controls.active_quality.value] : (controls.quality.value !== controls.active_quality.value || requestedMono !== (controls.active_mono.value > .5) ? "QUEUED · " : "") + controls.buffer_seconds.value.toFixed(2) + " s " + (controls.active_mono.value > .5 ? "MONO" : "STEREO") + " BUFFER"
        font.pixelSize: 12; color: "#9caab1"
    }
    Row {
        x: 24; y: 522; spacing: 16
        Repeater {
            model: ["time", "size", "shape", "pitch"]
            Column {
                width: 295; spacing: 3
                ParameterSlider {
                    width: 290; height: 77; paramSymbol: modelData + "_amount"
                    title: modelData.toUpperCase() + " · ATTENURANDOMIZER"
                    leftText: "PEAKY / RANDOM"; rightText: "UNIFORM / CV"
                    midiMapping: editor.midiMapping; onMidiMapRequested: editor.midiMapRequested(symbol)
                }
                Label {
                    width: parent.width; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 12
                    color: controller.patchedInputs[modelData + "_cv"] ? "#8ce6c7" : "#9caab1"
                    objectName: "cv_meaning_" + modelData
                    text: "CV / RANDOM"
                }
            }
        }
    }
}
