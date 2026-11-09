import QtQuick 2.11
import QtQuick.Controls 2.4
import "."
import QtQuick.Controls.Material 2.4
Item {
    id: panel
    property string effect_id
    property var controller: malaHub.bridge(effect_id)
    property var controls: controller.controls
    property bool midiMappingAvailable: false
    property real footerLeftInset: 24
    property bool midiMapping: false
    property string pendingMidiParameter: ""
    signal midiMapRequested(string symbol)
    function requestMidiMapping(symbol) {
        if (!midiMappingAvailable) return;
        midiMapping = false;
        panel.midiMapRequested(symbol);
    }
    onEffect_idChanged: midiMapping = false
    onVisibleChanged: if (!visible) midiMapping = false
    width:1280;height:720
    ModeHelpDialog { id:modeHelp }
    Editor { objectName:"mala_library_editor"; midiMapping: panel.midiMapping; onMidiMapRequested: panel.requestMidiMapping(symbol); onShowRouting: assignment.open() }
    TouchButton {objectName:"mala_settings_button";x:panel.footerLeftInset;y:636;width:250;height:50;text:"MODULE SETTINGS";onClicked:{panel.midiMapping=false;settings.open()}}
    Label {objectName:"mala_footer_status";x:panel.footerLeftInset+276;y:649;width:(panel.midiMappingAvailable ? 764 : 920)-x;elide:Text.ElideRight;color:"#a8bac6";font.pixelSize:15;text:panel.midiMapping ? "Tap a slider or button to map MIDI" : controls.active_synth.value>.5 ? "WAVETABLE SYNTH · LIVE LOCAL ENGINE" : "LIVE LOCAL ENGINE · PATCHBAY INPUTS"}
    TouchButton {
        objectName:"mala_map_midi";x:938;y:636;width:150;height:50;text:"Map Midi"
        visible:panel.midiMappingAvailable;highlighted:panel.midiMapping
        onClicked:panel.midiMapping=!panel.midiMapping
    }
    Dialog {
        id:settings;objectName:"mala_settings_dialog";width:900;height:600;anchors.centerIn:parent;modal:true;title:"Mala settings";standardButtons:Dialog.Close
        Material.theme:Material.Dark
        footer:DialogButtonBox {
            standardButtons:DialogButtonBox.Close
            Button {objectName:"mala_help_button";text:"HELP";DialogButtonBox.buttonRole:DialogButtonBox.ActionRole;onClicked:modeHelp.open()}
            onRejected:settings.close()
        }
        background:Rectangle {color:"#1b2630";border.color:"#456071";radius:10}
        contentItem:Flickable {
            id:settingsScroll;clip:true;contentWidth:width;contentHeight:settingsColumn.implicitHeight
            boundsBehavior:Flickable.StopAtBounds
            ScrollBar.vertical:ScrollBar {}
            Column {
            id:settingsColumn;width:settingsScroll.width;spacing:12
            CheckBox {objectName:"mala_response_checkbox";text:"BEADS KNOB RESPONSE";checked:controls.panel_response.value>.5;onClicked:controller.change("panel_response",checked?1:0)}
            Row {spacing:16
                Label {text:"CV input units";anchors.verticalCenter:parent.verticalCenter;color:"#e0e8ed";font.pixelSize:17}
                ComboBox {
                    objectName:"mala_cv_input_units";width:440
                    model:["Legacy virtual volts","Hector / Poly units (×5)"]
                    currentIndex:controls.cv_input_units.value
                    onActivated:controller.change("cv_input_units",currentIndex)
                }
            }
            CheckBox {text:"REMEMBER FROZEN BUFFER IN PATCH PRESETS";checked:controls.buffer_autosave.value>.5;onClicked:controller.change("buffer_autosave",checked?1:0)}
            CheckBox {objectName:"mala_trigger_checkbox";text:"GRAIN TRIGGERS ON OUT R";checked:controls.grain_triggers.value>.5;onClicked:controller.change("grain_triggers",checked?1:0)}
            CheckBox {text:"BEADS OUTPUT NORMALIZATION";checked:controls.output_normalization.value>.5;onClicked:controller.change("output_normalization",checked?1:0)}
            Row {spacing:16
                CheckBox {text:"AUTOMATIC GAIN";checked:controls.input_gain.value===0;onClicked:controller.autoGain(checked)}
                TouchButton {width:200;height:46;text:"RELEARN GAIN";onClicked:controller.relearnGain()}
                Slider {width:240;from:1;to:255;stepSize:1;enabled:controls.input_gain.value>0;value:controls.input_gain.value||128;onMoved:controller.change("input_gain",value)}
            }
            Label {width:parent.width;wrapMode:Text.WordWrap;font.pixelSize:17;color:"#8ce6c7"
                text:"Connected audio inputs: "+(controls.audio_connections.value&1?"L ":"")+(controls.audio_connections.value&2?"R":"")+" · CV / gates mask: "+controls.connections.value+" · Output mask: "+controls.output_connections.value}
            Label {width:parent.width;wrapMode:Text.WordWrap;font.pixelSize:17;color:"#a8bac6"
                text:controls.buffer_state.value===3?"FROZEN RECORDING READY · Save the patch to retain it.":controls.buffer_state.value===2?"CAPTURING FROZEN RECORDING…":controls.buffer_state.value===1?"FREEZE WAIT · "+controls.buffer_wait_seconds.value.toFixed(1)+" / 10 s":controls.active_synth.value>.5?"WAVETABLE SYNTHESIS":"RECORDING · Quiet no-input wait "+controls.synth_wait_seconds.value.toFixed(1)+" / 10 s"}
            Label {width:parent.width;wrapMode:Text.WordWrap;font.pixelSize:16;color:"#a8bac6";text:"Use the patchbay or Wire to connect inputs and outputs. Empty and connected-silent ports behave differently. Leave OUT R connected in trigger mode to avoid pulses blending into OUT L."}
            }
        }
    }
    Dialog {
        id:assignment;objectName:"mala_assignment_dialog";width:650;height:470;anchors.centerIn:parent;modal:true;title:"Assignable CV";standardButtons:Dialog.Close
        onClosed: {
            if (panel.pendingMidiParameter.length) {
                var symbol=panel.pendingMidiParameter;panel.pendingMidiParameter="";
                panel.requestMidiMapping(symbol);
            }
        }
        Material.theme:Material.Dark
        background:Rectangle {color:"#1b2630";border.color:"#456071";radius:10}
        contentItem:Column {spacing:16
            ComboBox {
                objectName:"mala_assignment_destination"
                width:parent.width;model:["Feedback","Dry/Wet","Reverb","Weighted combination"];currentIndex:controls.assign_destination.value;onActivated:controller.change("assign_destination",currentIndex)
                MouseArea {
                    objectName:"midi_target_assign_destination";anchors.fill:parent;z:10;visible:panel.midiMapping
                    onClicked:{panel.pendingMidiParameter="assign_destination";assignment.close()}
                }
            }
            Repeater {model:["feedback_cv_amount","mix_cv_amount","reverb_cv_amount"]
                ParameterSlider {
                    width:600;height:72;paramSymbol:modelData;assignmentIndex:index
                    enabled:controls.assign_destination.value===3 || controls.assign_destination.value===index || panel.midiMapping
                    leftText:"0";rightText:quickAssignment ? "FULL" : "255 / 256"
                    midiMapping:panel.midiMapping
                    onMidiMapRequested:{panel.pendingMidiParameter=symbol;assignment.close()}
                }
            }
        }
    }
}
