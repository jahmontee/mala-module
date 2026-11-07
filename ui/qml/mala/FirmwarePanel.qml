import QtQuick 2.11
import QtQuick.Controls 2.4

// v2 UI preview: reuse 407's existing parameter/MIDI page and bypass path.
LibraryPanel {
    id: firmwarePanel
    property bool malaFullPanel: true
    midiMappingAvailable: true
    footerLeftInset: 184
    onMidiMapRequested: {
        var kind = controller.midiType(symbol);
        if (!kind.length) return;
        knobs.set_knob_current_effect(effect_id, symbol);
        patchStack.push(Qt.resolvedUrl("../More.qml"), {"current_effect":effect_id,"row_param":symbol,"v_type":kind});
    }
    TouchButton {
        objectName: "mala_firmware_back"
        x: 18; y: 666; width: 148; height: 42
        text: "BACK"
        onClicked: {firmwarePanel.midiMapping=false;patch_single.selected_effect.back_action()}
    }
    TouchButton {
        objectName: "mala_firmware_bypass"
        x: 1095; y: 666; width: 167; height: 42
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
