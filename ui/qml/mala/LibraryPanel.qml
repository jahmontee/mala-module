import QtQuick 2.11
import QtQuick.Controls 2.4
import "."
import QtQuick.Controls.Material 2.4
Item {
    id: panel
    Material.theme: Material.Light
    Material.foreground: "#303932"
    Material.accent: "#008f98"
    Image { objectName: "mala_silver_panel_art"; anchors.fill: parent; source: "assets/silver-panel.png"; sourceSize.width: 1280; sourceSize.height: 720; cache: true; smooth: true }
    Rectangle { x: 0; y: 656; width: parent.width; height: 1; color: "#9d9792" }
    Rectangle { x: 0; y: 657; width: parent.width; height: 1; color: "#fffdf7" }
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
    TouchButton {objectName:"mala_settings_button";x:panel.footerLeftInset;y:666;width:222;height:42;text:"MODULE SETTINGS";onClicked:{panel.midiMapping=false;settings.open()}}
    Label {objectName:"mala_footer_status";x:425;y:677;width:458;height:24;horizontalAlignment:Text.AlignHCenter;elide:Text.ElideRight;color:"#29231f";font.pixelSize:13;font.italic:true;text:panel.midiMapping ? "Tap a knob or button to map MIDI" : "Based on Beads · Emilie Gillet / Mutable Instruments"}
    TouchButton {
        objectName:"mala_map_midi";x:897;y:666;width:176;height:42;text:"MAP MIDI"
        visible:panel.midiMappingAvailable;highlighted:panel.midiMapping
        onClicked:panel.midiMapping=!panel.midiMapping
    }
    Dialog {
        id:settings;objectName:"mala_settings_dialog";width:900;height:600;anchors.centerIn:parent;modal:true;title:"Mala settings";standardButtons:Dialog.Close
        Material.theme:Material.Light
        footer:DialogButtonBox {
            standardButtons:DialogButtonBox.Close
            Button {objectName:"mala_help_button";text:"HELP";DialogButtonBox.buttonRole:DialogButtonBox.ActionRole;onClicked:modeHelp.open()}
            onRejected:settings.close()
        }
        background:Rectangle {color:"#f1eee5";border.color:"#91968a";radius:10}
        contentItem:Flickable {
            id:settingsScroll;clip:true;contentWidth:width;contentHeight:settingsColumn.implicitHeight
            boundsBehavior:Flickable.StopAtBounds
            ScrollBar.vertical:ScrollBar {}
            Column {
            id:settingsColumn;width:settingsScroll.width;spacing:12
    Rectangle {
        id: cpuMeter
        objectName: "mala_cpu_meter"
        width: 220; height: 50
        radius: 11; color: "#f2efe5"; border.color: "#969b90"; border.width: 1.5
        // Same whole-engine reading/allowance as 407's stock DSP meter.
        readonly property real load: typeof dspLoad === "undefined" || dspLoad === null ? -1 : dspLoad.value
        readonly property bool hasReading: isFinite(load) && load >= 0
        readonly property color loadColor: !hasReading ? "#697265" : load > .97 ? "#bb3131" : load > .60 ? "#9d6900" : "#008b80"
        Label {
            x: 12; y: 8; width: 74
            text: "CPU · PATCH"; color: "#596157"; font.pixelSize: 12
        }
        Label {
            objectName: "mala_cpu_percent"
            x: 150; y: 4; width: 52; height: 25
            text: cpuMeter.hasReading ? (cpuMeter.load * 100).toFixed(0) + "%" : "—"
            horizontalAlignment: Text.AlignRight; color: cpuMeter.loadColor; font.pixelSize: 18
        }
        Rectangle {
            objectName: "mala_cpu_track"
            x: 12; y: 34; width: 196; height: 6; radius: 3; color: "#d0d4c9"
            Rectangle {
                objectName: "mala_cpu_fill"
                width: parent.width * (cpuMeter.hasReading ? Math.min(1, cpuMeter.load) : 0)
                height: parent.height; radius: 3; color: cpuMeter.loadColor
            }
        }
    }

            Label { text: "BUFFER · " + controls.buffer_seconds.value.toFixed(2) + " s · " + (controls.active_mono.value > .5 ? "MONO" : "STEREO"); font.pixelSize:17; color:"#303932" }
            CheckBox {objectName:"mala_response_checkbox";text:"BEADS KNOB RESPONSE";checked:controls.panel_response.value>.5;onClicked:controller.change("panel_response",checked?1:0)}
            Row {spacing:16
                Label {text:"CV input units";anchors.verticalCenter:parent.verticalCenter;color:"#303932";font.pixelSize:17}
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
            Label {width:parent.width;wrapMode:Text.WordWrap;font.pixelSize:17;color:"#007b83"
                text:"Connected audio inputs: "+(controls.audio_connections.value&1?"L ":"")+(controls.audio_connections.value&2?"R":"")+" · CV / gates mask: "+controls.connections.value+" · Output mask: "+controls.output_connections.value}
            Label {width:parent.width;wrapMode:Text.WordWrap;font.pixelSize:17;color:"#596157"
                text:controls.buffer_state.value===3?"FROZEN RECORDING READY · Save the patch to retain it.":controls.buffer_state.value===2?"CAPTURING FROZEN RECORDING…":controls.buffer_state.value===1?"FREEZE WAIT · "+controls.buffer_wait_seconds.value.toFixed(1)+" / 10 s":controls.active_synth.value>.5?"WAVETABLE SYNTHESIS":"RECORDING · Quiet no-input wait "+controls.synth_wait_seconds.value.toFixed(1)+" / 10 s"}
            Label {width:parent.width;wrapMode:Text.WordWrap;font.pixelSize:16;color:"#596157";text:"Use the patchbay or Wire to connect inputs and outputs. Empty and connected-silent ports behave differently. Leave OUT R connected in trigger mode to avoid pulses blending into OUT L."}
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
        Material.theme:Material.Light
        background:Rectangle {color:"#f1eee5";border.color:"#91968a";radius:10}
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
