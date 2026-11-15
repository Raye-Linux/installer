// One line of the disk picture: the parts of a disk, side by side, each as
// wide as it is big, and their names under it.
import QtQuick
import QtQuick.Layouts
import org.raye.setup

import "DiskLogic.js" as Logic

ColumnLayout {
    id: bar
    property string title
    property var parts: []
    property real total: 1
    property string lang: "en"
    spacing: 4

    function fill(kind) {
        switch (kind) {
        case "raye": return Theme.accent
        case "system": return Qt.alpha(Theme.textSecondary, 0.55)
        case "other": return Qt.alpha(Theme.textSecondary, 0.28)
        }
        return "transparent"
    }

    Text {
        text: bar.title
        font: Theme.caption
        color: Theme.textTertiary
    }
    Rectangle {
        Layout.fillWidth: true
        implicitHeight: 14
        radius: 4
        color: Theme.controlFill
        border.color: Theme.controlStroke
        clip: true
        Row {
            anchors.fill: parent
            anchors.margins: 1
            spacing: 1
            Repeater {
                model: bar.parts
                Rectangle {
                    required property var modelData
                    height: parent.height
                    width: Math.max(2, parent.width * modelData.bytes / bar.total - 1)
                    radius: 2
                    color: bar.fill(modelData.kind)
                }
            }
        }
    }
    Flow {
        Layout.fillWidth: true
        spacing: 12
        Repeater {
            model: bar.parts.filter(p => p.label !== "" && p.bytes >= 1024 * 1024 * 1024)
            Row {
                required property var modelData
                spacing: 4
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 8
                    height: 8
                    radius: 2
                    color: bar.fill(modelData.kind)
                    border.color: Theme.controlStroke
                }
                Text {
                    text: modelData.label + " " + Logic.size(modelData.bytes, bar.lang)
                    font: Theme.caption
                    color: Theme.textSecondary
                }
            }
        }
    }
}
