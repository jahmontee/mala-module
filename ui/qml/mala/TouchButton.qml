import QtQuick 2.11
import QtQuick.Controls 2.4
import "."

Button {
    id: button
    property color accent: "#8ce6c7"
    property bool midiMapping: false
    property string midiParameter: ""
    signal midiMapRequested(string symbol)
    clip: true
    background: Rectangle {
        radius: 11
        color: button.highlighted || button.down ? "#304b48" : "#202c38"
        border.width: 1.5
        border.color: button.highlighted || button.down ? button.accent : "#3c4b59"
    }
    contentItem: Text {
        text: button.text; color: button.highlighted || button.down ? button.accent : "#e0e8ed"
        font: button.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        wrapMode: Text.Wrap
    }
    MouseArea {
        objectName: button.objectName + "_midi_target"
        anchors.fill: parent; z: 10
        visible: button.midiMapping && button.midiParameter.length > 0
        preventStealing: true
        onClicked: button.midiMapRequested(button.midiParameter)
    }
}
