import QtQuick 2.11
import QtQuick.Controls 2.4

// Device shell: retain the approved editor and reuse 407's parameter/MIDI page.
LibraryPanel {
    id: firmwarePanel
    property bool malaFullPanel: true
    midiMappingAvailable: true
    footerLeftInset: 186
    onMidiMapRequested: {
        var kind = controller.midiType(symbol);
        if (!kind.length) return;
        knobs.set_knob_current_effect(effect_id, symbol);
        patchStack.push(Qt.resolvedUrl("../More.qml"), {"current_effect":effect_id,"row_param":symbol,"v_type":kind});
    }
    Rectangle {
        id: cpuMeter
        objectName: "mala_cpu_meter"
        x: 776; y: 636; width: 150; height: 50
        radius: 11; color: "#202c38"; border.color: "#3c4b59"; border.width: 1.5
        // Same whole-engine reading/allowance as 407's stock DSP meter.
        readonly property real load: typeof dspLoad === "undefined" || dspLoad === null ? -1 : dspLoad.value
        readonly property bool hasReading: isFinite(load) && load >= 0
        readonly property color loadColor: !hasReading ? "#9caab1" : load > .97 ? "#ef7777" : load > .60 ? "#e5ba78" : "#8ce6c7"
        Label {
            x: 12; y: 8; width: 74
            text: "CPU · PATCH"; color: "#a8bac6"; font.pixelSize: 12
        }
        Label {
            objectName: "mala_cpu_percent"
            x: 86; y: 4; width: 52; height: 25
            text: cpuMeter.hasReading ? (cpuMeter.load * 100).toFixed(0) + "%" : "—"
            horizontalAlignment: Text.AlignRight; color: cpuMeter.loadColor; font.pixelSize: 18
        }
        Rectangle {
            objectName: "mala_cpu_track"
            x: 12; y: 34; width: 126; height: 6; radius: 3; color: "#111921"
            Rectangle {
                objectName: "mala_cpu_fill"
                width: parent.width * (cpuMeter.hasReading ? Math.min(1, cpuMeter.load) : 0)
                height: parent.height; radius: 3; color: cpuMeter.loadColor
            }
        }
    }
    TouchButton {
        objectName: "mala_firmware_back"
        x: 24; y: 636; width: 150; height: 50
        text: "BACK"
        onClicked: {firmwarePanel.midiMapping=false;patch_single.selected_effect.back_action()}
    }
    TouchButton {
        objectName: "mala_firmware_bypass"
        x: 1100; y: 636; width: 150; height: 50
        text: "BYPASS"
        enabled: !!currentEffects[firmwarePanel.effect_id]
        highlighted: enabled && !currentEffects[firmwarePanel.effect_id]["enabled"].value
        onClicked: {
            if (currentEffects[firmwarePanel.effect_id]) {
                knobs.set_bypass(firmwarePanel.effect_id, !currentEffects[firmwarePanel.effect_id]["enabled"].value);
            }
        }
    }
    Component.onDestruction: malaHub.release(controller)
}
