// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.11
import QtQuick.Controls 2.4
import "."
TouchButton {
    id: button
    property real diameter: 62
    property bool isLamp: false
    readonly property bool yellowLit: highlighted || down
    padding: 0
    background: Item {}
    contentItem: Item {
        Item {
            objectName: button.objectName + "_face"
            x: 0; y: (parent.height - height) / 2; width: button.diameter; height: width
            // Stationary translucent rings avoid a blur effect or animation timer.
            Repeater {
                model: 7
                Rectangle {
                    visible: button.yellowLit
                    x: -13 + index*1.6; y: x
                    width: button.diameter + 26 - index*3.2; height: width; radius: width/2
                    color: Qt.rgba(1,.76,.04,.025+index*.012); antialiasing: true
                }
            }
            Image {
                source: "assets/silver-button.png"; cache: true; smooth: true; mipmap: true
                sourceSize.width: 160; sourceSize.height: 160
                x: -298 / 644 * parent.width; y: -294 / 664 * parent.height
                width: 1254 / 644 * parent.width; height: 1254 / 664 * parent.height
                opacity: button.down ? .78 : 1
            }
            Rectangle {
                objectName: button.objectName + "_yellow_face"
                visible: button.yellowLit
                anchors.fill: parent; anchors.margins: 3; radius: width/2; antialiasing: true
                opacity: .67
                gradient: Gradient {
                    GradientStop { position: 0; color: "#fff9b6" }
                    GradientStop { position: 1; color: "#ffcf35" }
                }
            }
            Rectangle {
                anchors.fill: parent; radius: width / 2; antialiasing: true
                visible: button.isLamp || button.yellowLit
                color: "transparent"
                border.width: button.yellowLit ? 2 : 1
                border.color: button.yellowLit ? "#e1ae16" : "#80766a"
            }
        }
        Text { objectName: button.objectName + "_label"; x: button.diameter + 19; y: 0; width: parent.width - x; height: parent.height; text: button.text; color: "#161616"; font.pixelSize: 21; font.bold: true; verticalAlignment: Text.AlignVCenter }
    }
}
