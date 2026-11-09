import QtQuick 2.11
import QtQuick.Controls 2.4
import "."
import QtQuick.Controls.Material 2.4

Item {
    id: root
    property string paramSymbol
    property string title: controls[paramSymbol].name
    property color accent: "#8ce6c7"
    property bool vertical: false
    property string leftText: ""
    property string rightText: ""
    property bool amounts: false
    property bool midiMapping: false
    // Beads' quick assignments are fixed at full depth. Editing their selected
    // amount enters custom routing through the existing weighted CV ports.
    property int assignmentIndex: -1
    readonly property bool quickAssignment: assignmentIndex >= 0 && controls.assign_destination.value < 3
    readonly property bool quickSelected: quickAssignment && controls.assign_destination.value === assignmentIndex
    readonly property string valueText: quickAssignment ? (quickSelected ? "1.00 ×" : "0.00 ×") : controls[paramSymbol].value.toFixed(2)
    function moveParameter(position) {
        if (quickAssignment) {
            if (!quickSelected) return;
            var amounts = ["feedback_cv_amount", "mix_cv_amount", "reverb_cv_amount"];
            // Prepare weights while the fixed route still ignores them. Enable
            // weighted routing last, so old custom weights cannot leak through.
            for (var i = 0; i < amounts.length; ++i) {
                if (i !== assignmentIndex) controller.change(amounts[i], 0);
            }
            controller.moveKnob(paramSymbol, position);
            controller.change("assign_destination", 3);
        } else {
            controller.moveKnob(paramSymbol, position);
        }
    }
    signal midiMapRequested(string symbol)
    readonly property int touchExtent: 48
    readonly property int trackThickness: 10
    readonly property int thumbDiameter: 28
    Label { text: root.title; color: root.accent; font.pixelSize: 18; anchors.top: parent.top; anchors.horizontalCenter: parent.horizontalCenter }
    Slider {
        id: slider
        objectName: "slider_" + root.paramSymbol
        x: root.vertical ? (root.width - width)/2 : 4
        // Preserve the track's position while enlarging its invisible input box.
        y: root.vertical ? 28 : Math.max(36, 28 + (root.height - 60)/2) - height/2
        width: root.vertical ? 72 : root.width - 8
        height: root.vertical ? root.height - 60 : Math.max(root.touchExtent, root.height - 60)
        orientation: root.vertical ? Qt.Vertical : Qt.Horizontal
        from: 0
        to: 1
        value: root.quickAssignment ? (root.quickSelected ? 1 : 0) : controller.panelPositions[root.paramSymbol]
        Material.accent: root.accent
        onMoved: root.moveParameter(value)
        background: Rectangle {
            objectName: slider.objectName + "_track"
            x: slider.leftPadding + (slider.horizontal ? 0 : (slider.availableWidth - width)/2)
            y: slider.topPadding + (slider.horizontal ? (slider.availableHeight - height)/2 : 0)
            width: slider.horizontal ? slider.availableWidth : root.trackThickness
            height: slider.horizontal ? root.trackThickness : slider.availableHeight
            radius: root.trackThickness/2
            scale: slider.horizontal && slider.mirrored ? -1 : 1
            color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, .3)
            opacity: slider.enabled ? 1 : .4
            Rectangle {
                y: slider.horizontal ? 0 : slider.visualPosition * parent.height
                width: slider.horizontal ? slider.position * parent.width : parent.width
                height: slider.horizontal ? parent.height : slider.position * parent.height
                radius: root.trackThickness/2; color: root.accent
            }
        }
        handle: Rectangle {
            objectName: slider.objectName + "_thumb"
            width: root.thumbDiameter; height: root.thumbDiameter
            implicitWidth: root.thumbDiameter; implicitHeight: root.thumbDiameter
            x: slider.leftPadding + (slider.horizontal ? slider.visualPosition * (slider.availableWidth - width) : (slider.availableWidth - width)/2)
            y: slider.topPadding + (slider.horizontal ? (slider.availableHeight - height)/2 : slider.visualPosition * (slider.availableHeight - height))
            radius: width/2; color: root.accent
            opacity: slider.enabled ? 1 : .4
            border.width: slider.pressed || slider.visualFocus ? 2 : 0
            border.color: "#edf4f7"
        }
    }
    Row {
        visible: !root.vertical
        anchors.bottom: parent.bottom; width: parent.width
        Label { width: parent.width/3; text: root.leftText; color: "#9caab1"; font.pixelSize: 14 }
        Label { width: parent.width/3; horizontalAlignment: Text.AlignHCenter; text: root.valueText; color: "#ebf0f4"; font.pixelSize: 16 }
        Label { width: parent.width/3; horizontalAlignment: Text.AlignRight; text: root.rightText; color: "#9caab1"; font.pixelSize: 14 }
    }
    Label {
        visible: root.vertical; anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter
        text: root.valueText; color: "#ebf0f4"; font.pixelSize: 18
    }
    Item {
        objectName: root.paramSymbol + "_notches"; x: slider.x; y: root.height+2; width: slider.width; height: 14
        visible: root.paramSymbol === "pitch" && controls.panel_response.value > .5
        Repeater {
            model: root.paramSymbol === "pitch" ? controller.pitchNotches : []
            Label {
                x: slider.leftPadding + (slider.handle ? slider.handle.width/2 : 0) + (slider.availableWidth - (slider.handle ? slider.handle.width : 0))*modelData.position - width/2
                text: (modelData.value > 0 ? "+" : "") + modelData.value
                color: "#9caab1"; font.pixelSize: 10
            }
        }
    }
    MouseArea {
        objectName: "midi_target_" + root.paramSymbol
        anchors.fill: parent; z: 10
        visible: root.midiMapping
        preventStealing: true
        onClicked: root.midiMapRequested(root.paramSymbol)
    }
}
