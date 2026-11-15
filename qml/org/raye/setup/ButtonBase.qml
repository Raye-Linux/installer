// What PrimaryButton and SubtleButton share: 40 px high (32 with
// compact), 4 px corners, Body text, the colour moving in 83 ms, and the
// focus ring when the focus came from the keyboard.
import QtQuick
import QtQuick.Templates as T
import org.kde.kirigami as Kirigami
import org.raye.ui as Ui
import org.raye.setup

T.Button {
    id: control

    property bool accent: false
    // 32 px, for dialogs drawn over a setup page
    property bool compact: false

    readonly property color fillColor: !enabled ? (accent ? Theme.accentDisabled : Theme.controlFillDisabled)
                                     : accent ? (down ? Theme.accentPressed
                                                      : hovered ? Theme.accentHover : Theme.accent)
                                     : down ? Theme.controlFillPressed
                                     : hovered ? Theme.controlFillHover : Theme.controlFill
    readonly property color textColor: !enabled ? (accent ? Qt.alpha(Theme.textOnAccent, 0.6) : Theme.textDisabled)
                                     : accent ? Theme.textOnAccent
                                     : down ? Theme.textSecondary : Theme.textPrimary

    implicitWidth: Math.max(compact ? 96 : 120, implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: compact ? Theme.dialogControlHeight : Theme.controlHeight
    leftPadding: compact ? 12 : 20
    rightPadding: leftPadding
    spacing: 8
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    font: Theme.button
    icon.width: 16
    icon.height: 16

    Accessible.role: Accessible.Button
    Accessible.name: text
    Accessible.onPressAction: control.clicked()

    // Enter presses the button too, like Space
    Keys.onReturnPressed: event => { control.clicked(); event.accepted = true }
    Keys.onEnterPressed: event => { control.clicked(); event.accepted = true }

    contentItem: Item {
        // from the label's own width, not the row's: the label is cut to the
        // room it has, so a button laid out for a short word stayed narrow
        // when the language changed and read "Redémarr..."
        implicitWidth: (buttonIcon.visible ? buttonIcon.implicitWidth + control.spacing : 0) + buttonLabel.implicitWidth
        implicitHeight: row.implicitHeight
        Row {
            id: row
            anchors.centerIn: parent
            spacing: control.spacing
            Kirigami.Icon {
                id: buttonIcon
                anchors.verticalCenter: parent.verticalCenter
                visible: control.icon.name !== "" || control.icon.source.toString() !== ""
                source: control.icon.name !== "" ? control.icon.name : control.icon.source
                implicitWidth: control.icon.width
                implicitHeight: control.icon.height
                color: control.textColor
                isMask: true
            }
            Text {
                id: buttonLabel
                anchors.verticalCenter: parent.verticalCenter
                width: Math.min(implicitWidth, control.availableWidth)
                text: control.text
                font: control.font
                color: control.textColor
                elide: Text.ElideRight
                Behavior on color { ColorAnimation { duration: Theme.durationHover } }
            }
        }
    }

    background: Rectangle {
        radius: Theme.radiusControl
        color: control.fillColor
        border.width: control.accent ? 0 : 1
        border.color: Theme.controlStroke
        Behavior on color { ColorAnimation { duration: Theme.durationHover } }

        // a lit top edge on the accent button at rest and under the pointer
        Rectangle {
            visible: control.accent && control.enabled && !control.down
            anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: parent.radius; rightMargin: parent.radius }
            height: 1
            color: Qt.rgba(1, 1, 1, 0.18)
        }

        Ui.FocusRing {
            objectName: "focusRing"
            target: control
            radius: Theme.radiusControl
        }
    }
}
