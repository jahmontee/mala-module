// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.11
import QtQuick.Controls 2.4

TouchButton {
    id: key
    property var theme: ({primary: "#008f98"})
    property bool active: false
    property bool interactive: true
    property int pointSize: 18
    width: 112
    height: 44
    accent: theme.primary
    highlighted: active
    font.pixelSize: pointSize
    opacity: enabled ? 1 : .38
    focusPolicy: interactive ? Qt.StrongFocus : Qt.NoFocus
    MouseArea {
        anchors.fill: parent
        z: 20
        visible: !key.interactive
        onPressed: mouse.accepted = true
    }
}
