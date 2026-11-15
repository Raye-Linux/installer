// A row of a setup list (keyboard layouts, Wi-Fi networks, time zones):
// 40 px high, 4 px corners, a light veil under the pointer; the chosen
// row gets the accent veil and a 3 x 16 px accent pill on the left.
//
//   ListView {
//       model: layouts
//       delegate: ListRow {
//           width: ListView.view.width
//           text: model.name
//           detail: model.recommended ? strings.recommended : ""
//           highlighted: ListView.isCurrentItem
//           onClicked: ListView.view.currentIndex = index
//       }
//   }
//
// The list is one stop in the Tab order: the rows take no focus of their
// own, the current row shows the focus ring while the list has it, and
// the arrow keys move in the list. A row on its own (not in a ListView)
// can take focus with focusPolicy: Qt.StrongFocus.
import QtQuick
import QtQuick.Layouts
import QtQuick.Templates as T
import org.raye.ui as Ui
import org.raye.setup

T.ItemDelegate {
    id: control

    // a second line under the name
    property string description
    // a word on the right end ("Recommended", "Connected")
    property string detail

    readonly property bool inList: ListView.view !== null && ListView.view !== undefined
    readonly property bool focusShown: inList ? ListView.view.activeFocus && highlighted : visualFocus
    readonly property color fillColor: !enabled ? "transparent"
                                     : highlighted ? (down ? Qt.alpha(Theme.accent, 0.14) : Theme.selected)
                                     : down ? Theme.controlFillPressed
                                     : hovered ? Theme.controlFillHover : "transparent"

    implicitWidth: Math.max(200, implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(description !== "" ? 56 : 40, implicitContentHeight + topPadding + bottomPadding)
    leftPadding: 16
    rightPadding: 12
    topPadding: 6
    bottomPadding: 6
    hoverEnabled: true
    focusPolicy: Qt.NoFocus
    font: Theme.body

    Accessible.role: Accessible.ListItem
    Accessible.name: text
    Accessible.description: description !== "" ? description : detail
    Accessible.selectable: true
    Accessible.selected: highlighted

    contentItem: RowLayout {
        spacing: 12
        ColumnLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            spacing: 0
            Text {
                Layout.fillWidth: true
                text: control.text
                font: control.highlighted ? Theme.bodyStrong : control.font
                color: control.enabled ? Theme.textPrimary : Theme.textDisabled
                elide: Text.ElideRight
                // a name in another script (العربية, فارسی) starts where the
                // others do; a right-to-left page mirrors this too
                horizontalAlignment: Text.AlignLeft
            }
            Text {
                Layout.fillWidth: true
                visible: text !== ""
                text: control.description
                font: Theme.caption
                color: control.enabled ? Theme.textSecondary : Theme.textDisabled
                elide: Text.ElideRight
            }
        }
        Text {
            visible: text !== ""
            Layout.alignment: Qt.AlignVCenter
            text: control.detail
            font: Theme.caption
            color: control.enabled ? Theme.textSecondary : Theme.textDisabled
        }
    }

    background: Rectangle {
        radius: Theme.radiusControl
        color: control.fillColor
        Behavior on color { ColorAnimation { duration: Theme.durationHover } }

        Rectangle {
            objectName: "pill"
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: 3
            height: control.highlighted ? (control.down ? 10 : 16) : 0
            radius: 1.5
            color: Theme.accent
            visible: height > 0
            Behavior on height { NumberAnimation { duration: Theme.durationMove; easing.type: Easing.OutCubic } }
        }

        Ui.FocusRing {
            objectName: "focusRing"
            target: control
            radius: Theme.radiusControl
            shown: control.focusShown
        }
    }
}
