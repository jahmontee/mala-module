// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.11
import QtQuick.Controls 2.4

// Use the bridge's panel position: pitch and amounts have Beads response curves.
// Artwork is static; only the pointer rotates when a parameter changes.
Item {
    id: knob
    property string paramSymbol
    property string title
    property color accent: "#009fa9"
    property real diameter: 120
    property bool compact: false
    property bool showAccent: compact
    property bool midiMapping: false
    property bool bipolar: false
    property string caption: ""
    property bool connected: false
    // Same vertical travel and default resolution as Echo Field's Knob.qml.
    readonly property real dragTravel: 160
    readonly property real step: .01
    readonly property real position: Math.max(0, Math.min(1, controller.panelPositions[paramSymbol]))
    readonly property string valueText: controls[paramSymbol].value.toFixed(2)
    signal midiMapRequested(string symbol)
    activeFocusOnTab: true
    Accessible.role: Accessible.Slider
    Accessible.name: title
    Accessible.description: "Drag up to increase, down to decrease. " + valueText
    function moveTo(value) {
        if (!midiMapping && enabled) controller.moveKnob(paramSymbol, Math.max(0, Math.min(1, value)));
    }
    Keys.onUpPressed: moveTo(position + .01)
    Keys.onRightPressed: moveTo(position + .01)
    Keys.onDownPressed: moveTo(position - .01)
    Keys.onLeftPressed: moveTo(position - .01)
    Keys.onPressed: {
        if (event.key === Qt.Key_Home) { moveTo(0); event.accepted = true; }
        else if (event.key === Qt.Key_End) { moveTo(1); event.accepted = true; }
    }
    property string labelPlacement: compact ? "right" : "below"
    property string badgeSymbol: "cloud"
    property bool scaleRing: false
    property bool valueOnTouch: false
    property bool showValue: true
    property real faceX: labelPlacement === "right" ? (showAccent ? 42 : 0) : labelPlacement === "left" ? width - diameter : (width - diameter) / 2
    property real faceY: labelPlacement === "above" ? 28 : 0
    property real labelX: labelPlacement === "right" ? faceX + diameter + 14 : 0
    property real labelY: labelPlacement === "above" ? 0 : labelPlacement === "below" ? diameter + 7 : Math.max(6, diameter * .1)
    readonly property real centeredSideLabelY: faceY + (diameter - labelBlock.implicitHeight) / 2
    property real titleSize: 22
    property real valueSize: 24
    property real titleWidth: labelPlacement === "left" ? faceX + 10 : labelPlacement === "right" ? width - labelX : width
    BeadsBadge {
        visible: knob.showAccent; x: face.x - width - 11; y: face.y + (face.height - height) / 2
        width: 30; height: Math.min(68, face.height * .9); accent: knob.accent; symbol: knob.badgeSymbol
    }
    Item {
        id: face
        objectName: "face_" + knob.paramSymbol
        x: knob.faceX; y: knob.faceY; width: knob.diameter; height: width
        Canvas {
            visible: knob.scaleRing
            x: -11; y: -11; width: face.width + 22; height: width
            onPaint: {
                var c=getContext("2d");c.clearRect(0,0,width,height);c.save();
                c.strokeStyle="#b3afaa";c.lineWidth=6;c.lineCap="round";c.beginPath();
                c.arc(width/2,height/2,width/2-5,Math.PI*.75,Math.PI*2.25);c.stroke();c.restore();
            }
        }
        // Normalize the generated sprite's transparent margin at render time.
        // Source pixels and lighting stay fixed; the live pointer is a separate item.
        Image {
            objectName: "knob_art_" + knob.paramSymbol
            source: "assets/knob-body.png"; cache: true; smooth: true; mipmap: true
            sourceSize.width: 256; sourceSize.height: 256
            x: -128 / 980 * face.width; y: -94 / 1004 * face.height
            width: 1254 / 980 * face.width; height: 1254 / 1004 * face.height
        }
        Item {
            objectName: "pointer_" + knob.paramSymbol
            anchors.fill: parent; rotation: -135 + 270 * knob.position
            Rectangle {
                x: (parent.width - width) / 2; y: parent.width * .015
                width: Math.max(4, parent.width * .063); height: parent.width * .28
                color: "#fffef8"; antialiasing: true
            }
        }
        Rectangle {
            anchors.fill: parent; anchors.margins: -4; radius: width / 2; color: "transparent"
            border.color: knob.accent; border.width: 2; antialiasing: true
            visible: touch.pressed || knob.activeFocus || knob.midiMapping
        }
    }
    Column {
        id: labelBlock
        x: knob.labelX; y: knob.labelY; width: knob.titleWidth; spacing: 2
        Label {
            objectName: "title_" + knob.paramSymbol
            width: parent.width; text: knob.title; color: "#161616"; font.pixelSize: knob.titleSize; font.bold: true
            horizontalAlignment: knob.labelPlacement === "left" ? Text.AlignRight : knob.labelPlacement === "right" ? Text.AlignLeft : Text.AlignHCenter
        }
        Label {
            objectName: knob.valueOnTouch ? "" : "value_" + knob.paramSymbol
            visible: knob.showValue && !knob.valueOnTouch
            width: parent.width; text: knob.valueText; color: "#151515"; font.pixelSize: knob.valueSize
            horizontalAlignment: knob.labelPlacement === "left" ? Text.AlignRight : knob.labelPlacement === "right" ? Text.AlignLeft : Text.AlignHCenter
        }
    }
    Rectangle {
        visible: knob.showValue && knob.valueOnTouch && (touch.pressed || knob.activeFocus)
        x: face.x + face.width + 7; y: face.y + face.height - 29; width: 66; height: 28
        radius: 6; color: "#fffaf0"; border.color: knob.accent
        Label { objectName: knob.valueOnTouch ? "value_" + knob.paramSymbol : ""; anchors.centerIn: parent; text: knob.valueText; color: "#191714"; font.pixelSize: 16 }
    }
    ToolTip.visible: knob.showValue && touch.containsMouse && !touch.pressed && knob.caption.length > 0
    ToolTip.delay: 600
    ToolTip.text: knob.valueText + " · " + knob.caption
    MouseArea {
        id: touch
        objectName: "knob_touch_" + knob.paramSymbol
        x: face.x; y: face.y; width: face.width; height: face.height; preventStealing: true
        hoverEnabled: true
        cursorShape: Qt.SizeVerCursor
        property real startY: 0
        property real startPosition: 0
        onPressed: { knob.forceActiveFocus(); startY = mouse.y; startPosition = knob.position; }
        // Relative motion avoids jumping to the contact point on a touchscreen.
        onPositionChanged: if (pressed && !knob.midiMapping) {
            var position = startPosition + (startY - mouse.y) / knob.dragTravel;
            knob.moveTo(Math.round(position / knob.step) * knob.step);
        }
        onClicked: if (knob.midiMapping) knob.midiMapRequested(knob.paramSymbol)
        onDoubleClicked: if (!knob.midiMapping) knob.moveTo(0)
        onWheel: {
            if (!knob.midiMapping && wheel.angleDelta.y !== 0) knob.moveTo(knob.position + (wheel.angleDelta.y > 0 ? knob.step : -knob.step));
            wheel.accepted = true;
        }
    }
}
