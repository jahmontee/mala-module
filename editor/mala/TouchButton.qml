import QtQuick 2.11
import QtQuick.Controls 2.4
import "."

Button {
    id: button
    property color accent: "#008f98"
    property bool midiMapping: false
    property string midiParameter: ""
    font.pixelSize: 18
    font.bold: true
    signal midiMapRequested(string symbol)
    clip: false
    background: Item {
        anchors.fill: parent
        Rectangle { x: 0; y: 2; width: parent.width; height: parent.height; radius: 10; color: "#22000000"; antialiasing: true }
        Rectangle {
            anchors.fill: parent; radius: 9; antialiasing: true
            gradient: Gradient { GradientStop { position: 0; color: button.highlighted || button.down ? "#d4e5de" : "#fffaf7" } GradientStop { position: 1; color: button.highlighted || button.down ? "#b8d4ca" : "#e8e0d9" } }
            border.width: 1
            border.color: button.highlighted || button.down ? button.accent : "#625750"
            Rectangle { anchors.fill: parent; anchors.margins: 2; color: "transparent"; border.color: "#fffdf7"; radius: 7; antialiasing: true }
        }
    }
    contentItem: Text {
        text: button.text; color: button.highlighted || button.down ? button.accent : "#161412"
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
