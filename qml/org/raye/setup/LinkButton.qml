// A button that reads like a link: "Change", "Show all layouts",
// "I don't have internet". Accent text, underlined under the pointer.
//
//   LinkButton { text: strings.change; onClicked: ... }
import QtQuick
import QtQuick.Templates as T
import org.raye.ui as Ui
import org.raye.setup

T.AbstractButton {
    id: control

    readonly property color textColor: !enabled ? Theme.textDisabled
                                     : down ? Qt.alpha(Theme.accentText, 0.7)
                                     : hovered ? Qt.lighter(Theme.accentText, 1.12) : Theme.accentText

    implicitWidth: implicitContentWidth + leftPadding + rightPadding
    implicitHeight: Math.max(32, implicitContentHeight + topPadding + bottomPadding)
    leftPadding: 2
    rightPadding: 2
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    font: Theme.body

    Accessible.role: Accessible.Link
    Accessible.name: text
    Accessible.onPressAction: control.clicked()

    Keys.onReturnPressed: event => { control.clicked(); event.accepted = true }
    Keys.onEnterPressed: event => { control.clicked(); event.accepted = true }

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }

    contentItem: Text {
        text: control.text
        font.family: control.font.family
        font.pixelSize: control.font.pixelSize
        font.weight: 500
        font.underline: control.hovered && control.enabled
        color: control.textColor
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        Behavior on color { ColorAnimation { duration: Theme.durationHover } }
    }

    background: Item {
        Ui.FocusRing {
            objectName: "focusRing"
            target: control
            radius: Theme.radiusControl
        }
    }
}
