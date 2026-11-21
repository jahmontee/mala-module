// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.11
import "MidiLabels.js" as MidiLabels

Item {
    id: page
    objectName: "midi_assignment_page"
    width: 1280; height: 720
    property bool malaFullPanel: true
    property string current_effect: ""
    property string row_param: ""
    property string v_type: "float"
    readonly property var theme: ({text:"#292725",muted:"#625d55",border:"#9d9792"})
    readonly property var screenTheme: ({background:"#f1eee5",surface:"#faf7ef",border:"#b1aaa0",text:"#292725",muted:"#746d62",primary:"#008f98"})
    readonly property var midiBackend: typeof polyViewNativeHub!=="undefined" ? polyViewNativeHub.backend(current_effect,"mala") : null
    readonly property var effect: typeof currentEffects!=="undefined" ? currentEffects[current_effect] : null
    readonly property var target: effect && effect.controls ? effect.controls[row_param] : null
    readonly property bool available: !!target && effect.effect_type==="mala" && !!midiBackend && midiBackend.midiType(row_param)===v_type
    readonly property real actualValue: available ? target.value : 0
    readonly property int midiCC: available ? target.cc : -1
    readonly property bool assigned: midiCC>=0
    readonly property real minimum: available ? target.rmin : 0
    readonly property real maximum: available ? target.rmax : 1
    readonly property bool inSpotlight: {
        var entries=typeof knobs!=="undefined"?knobs.spotlight_entries:[]
        for(var i=0;i<entries.length;++i)
            if(entries[i][0]===current_effect && entries[i][1]===row_param)return true
        return false
    }
    property bool learning: false
    property bool freshEntry: true
    property string draft: formatValue(actualValue)
    readonly property bool validValue: available && /^-?\d+(\.\d*)?$/.test(draft) &&
        isFinite(Number(draft)) && Number(draft)>=minimum && Number(draft)<=maximum &&
        (v_type!=="int" || Math.round(Number(draft))===Number(draft))

    function formatValue(value) { return String(Math.round(Number(value)*10000)/10000) }
    function followValue() { draft=formatValue(actualValue);freshEntry=true }
    function learnOrForget() {
        if(!available || (learning&&!assigned))return
        learning=!assigned
        knobs.midi_learn(current_effect,row_param)
    }
    function setValue(value) {
        if(!available || !isFinite(value))return
        value=Math.max(minimum,Math.min(maximum,value))
        if(v_type!=="float")value=Math.round(value)
        knobs.ui_knob_change(current_effect,row_param,value)
        followValue()
    }
    function increment(up) {
        if(!available)return
        if(v_type==="int")setValue(actualValue+(up?1:-1))
        else {
            knobs.ui_knob_inc(current_effect,row_param,up)
            followValue()
        }
    }
    function digit(key) {
        if(key==="±") {
            if(minimum>=0)return
            draft=draft.charAt(0)==="-"?draft.slice(1):"-"+draft
            freshEntry=false
            return
        }
        if(key==="." && v_type!=="float")return
        var next=freshEntry?(key==="."?"0.":key):draft+key
        if(next.length<=12 && /^-?\d*(\.\d*)?$/.test(next)){draft=next;freshEntry=false}
    }
    function finishValue() { if(validValue)setValue(Number(draft)) }
    function resetValue() { if(available)setValue(midiBackend.midiDefault(row_param,target.default_value)) }
    function closePage() { patchStack.pop() }
    onActualValueChanged: if(freshEntry)followValue()
    onMidiCCChanged: learning=false

    Image { anchors.fill: parent; source:"assets/silver-panel.png"; sourceSize.width:1280; sourceSize.height:720; smooth:true }
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
    Text { x: 24; y: 14; text: "MALA"; color: page.theme.text; font.family: "DejaVu Sans"; font.pixelSize: 36; font.letterSpacing: 7 }
    Text { x: 206; y: 29; text: "v0.3.0-beta.11"; color: page.theme.muted; font.family: "DejaVu Sans"; font.pixelSize: 12; font.bold: true }
    Text { x: 876; y: 25; width: 380; horizontalAlignment: Text.AlignRight; text: "MIDI ASSIGNMENT"; color: page.theme.text; font.family: "DejaVu Sans"; font.pixelSize: 17; font.bold: true }
    Rectangle { x: 24; y: 73; width: 1232; height: 1; color: page.theme.border }

    Rectangle {
        id: bay
        x: 24; y: 88; width: 1232; height: 558; radius: 10
        color: page.screenTheme.background
        border.color: page.theme.border; border.width: 1
        Rectangle { anchors.fill: parent; anchors.margins: 2; radius: 8; color: "transparent"; border.color: "#fffdf7"; opacity: .9 }
        Text { x: 20; y: 22; width: 360; text: page.available?MidiLabels.labelFor(page.row_param).toUpperCase():"PARAMETER UNAVAILABLE"; color: page.screenTheme.text; font.family: "DejaVu Sans"; font.pixelSize: 23; font.bold: true; elide: Text.ElideRight }
        Text { x: 20; y: 60; text: "MIDI CONTROLLER"; color: page.screenTheme.muted; font.family: "DejaVu Sans"; font.pixelSize: 13; font.bold: true }
        Rectangle { x: 418; y: 24; width: 1; height: 510; color: page.screenTheme.border; opacity: .55 }

        Rectangle {
            x: 20; y: 100; width: 360; height: 164; radius: 4
            color: page.screenTheme.surface; border.color: page.screenTheme.border
            Rectangle {
                x:22; width:12; height:12; radius:6; anchors.verticalCenter:assignmentStatus.verticalCenter
                color:page.assigned?page.screenTheme.primary:page.learning?"#f3ba22":"#b0a99e"
                border.color:page.assigned?"#00747b":"#8f887e"
                Rectangle { anchors.centerIn:parent; width:20; height:20; radius:10; color:page.learning?"#22f3ba22":"#22008f98"; visible:page.assigned||page.learning }
            }
            Text { id: assignmentStatus; x: 44; y: 16; width: 294; text: page.assigned?"ASSIGNED":page.learning?"WAITING FOR MIDI":"NO ASSIGNMENT"; color: page.assigned||page.learning?page.screenTheme.primary:page.screenTheme.muted; font.family: "DejaVu Sans"; font.pixelSize: 14; font.bold: true }
            Repeater {
                model: ["CHANNEL","CC NUMBER"]
                Column {
                    x: 16+index*174; y: 65; width: 154; spacing: 9
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData; color: page.screenTheme.muted; font.family: "DejaVu Sans"; font.pixelSize: 12; font.bold: true }
                    Text { objectName: index===0?"midi_channel_readout":"midi_cc_readout"; anchors.horizontalCenter: parent.horizontalCenter; text: page.assigned?String(index===0?(page.midiCC>>8)+1:page.midiCC&255):"—"; color: page.screenTheme.text; font.family: "DejaVu Sans"; font.pixelSize: 32; font.bold: true }
                }
            }
        }
        MidiKey { theme: page.screenTheme; objectName: "midi_learn_button"; x: 20; y: 286; width: 360; height: 50; text: page.assigned?"Forget mapping":page.learning?"Waiting for MIDI…":"Learn MIDI"; active: page.assigned||page.learning; enabled: page.available && (!page.learning||page.assigned); onClicked: page.learnOrForget() }
        MidiKey { theme: page.screenTheme; objectName: "midi_reset_default"; x: 20; y: 352; width: 360; height: 50; text: "Reset to default"; enabled: page.available; onClicked: page.resetValue() }
        MidiKey { theme: page.screenTheme; objectName: "midi_spotlight"; x: 20; y: 418; width: 360; height: 50; text: page.inSpotlight?"Remove from Spotlight":"Expose in Spotlight"; enabled: page.available; onClicked: knobs.expose_spotlight(page.current_effect,page.row_param) }
        Text { x: 20; y: 492; width: 360; height: 42; wrapMode: Text.Wrap; text: page.assigned?"Use Forget mapping before learning a different controller.":"Press Learn MIDI, then move the control on your MIDI controller."; color: page.screenTheme.muted; font.family: "DejaVu Sans"; font.pixelSize: 13 }

        Text { x: 452; y: 27; text: "PARAMETER VALUE"; color: page.screenTheme.text; font.family: "DejaVu Sans"; font.pixelSize: 14; font.bold: true }
        Text { x: 452; y: 62; text: page.v_type==="bool"?"SWITCH":"ENTER VALUE"; color: page.screenTheme.muted; font.family: "DejaVu Sans"; font.pixelSize: 12; font.bold: true }
        MidiKey { theme: page.screenTheme; objectName: "midi_value_display"; x: 452; y: 104; width: 188; height: 76; interactive: false; active: true; pointSize: 26; text: page.v_type==="bool"?(page.actualValue>.5?"On":"Off"):page.draft }
        MidiKey { theme: page.screenTheme; objectName: "midi_value_minus"; x: 452; y: 198; width: 88; height: 54; pointSize: 28; text: "−"; visible: page.v_type!=="bool"; enabled: page.available; onClicked: page.increment(false) }
        MidiKey { theme: page.screenTheme; objectName: "midi_value_plus"; x: 552; y: 198; width: 88; height: 54; pointSize: 28; text: "+"; visible: page.v_type!=="bool"; enabled: page.available; onClicked: page.increment(true) }
        Text { x: 452; y: 276; width: 188; wrapMode: Text.Wrap; visible: page.v_type!=="bool"; text: "Range "+page.formatValue(page.minimum)+" to "+page.formatValue(page.maximum)+(page.v_type==="int"?"\nWhole numbers":""); color: page.screenTheme.muted; font.family: "DejaVu Sans"; font.pixelSize: 13; lineHeight: 1.25 }
        Text {
            objectName: "midi_live_value"
            x: 452; y: 326; width: 188
            visible: page.available && page.v_type !== "bool" && !page.freshEntry
            text: "Live value  " + page.formatValue(page.actualValue)
            color: page.screenTheme.muted; font.family: "DejaVu Sans"; font.pixelSize: 13
        }

        Item {
            x: 676; y: 104; width: 524; height: 410; visible: page.v_type!=="bool"
            Grid {
                columns: 3; spacing: 10
                Repeater {
                    model: ["1","2","3","4","5","6","7","8","9","±","0","."]
                    MidiKey { theme: page.screenTheme; objectName: "midi_value_key_"+index; width: 168; height: 62; pointSize: 25; text: modelData; enabled: page.available && (modelData!=="."||page.v_type==="float") && (modelData!=="±"||page.minimum<0); onClicked: page.digit(modelData) }
                }
            }
            MidiKey { theme: page.screenTheme; objectName: "midi_value_backspace"; y: 298; width: 257; height: 46; text: "Backspace"; enabled: page.available; onClicked: {page.draft=page.draft.slice(0,-1);page.freshEntry=false} }
            MidiKey { theme: page.screenTheme; objectName: "midi_value_clear"; x: 267; y: 298; width: 257; height: 46; text: "Clear"; enabled: page.available; onClicked: {page.draft="";page.freshEntry=false} }
            MidiKey { theme: page.screenTheme; objectName: "midi_value_apply"; y: 358; width: 524; height: 50; text: "Apply value"; active: true; enabled: page.validValue; onClicked: page.finishValue() }
        }
        Row { x: 676; y: 104; spacing: 16; visible: page.v_type==="bool"
            MidiKey { theme: page.screenTheme; objectName: "midi_value_off"; width: 254; height: 76; text: "Off"; active: page.actualValue<=.5; enabled: page.available; onClicked: page.setValue(0) }
            MidiKey { theme: page.screenTheme; objectName: "midi_value_on"; width: 254; height: 76; text: "On"; active: page.actualValue>.5; enabled: page.available; onClicked: page.setValue(1) }
        }
    }
    MidiKey { theme: page.screenTheme; objectName: "midi_assignment_back"; x: 24; y: 664; width: 90; text: "Back"; onClicked: page.closePage() }
    Text { x: 132; y: 676; width: 940; text: page.learning?"Move a MIDI controller to complete the assignment":"MIDI Map · "+MidiLabels.labelFor(page.row_param); color: page.theme.muted; font.family: "DejaVu Sans"; font.pixelSize: 13 }
    MidiKey { theme: page.screenTheme; objectName: "midi_assignment_done"; x: 1136; y: 664; width: 120; text: "Done"; onClicked: page.closePage() }
}
