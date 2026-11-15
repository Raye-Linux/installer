// A check box the Windows way: a 20 px box with 4 px corners, the label
// 8 px to its right. Checked: accent fill and a white check.
//
//   CheckBox { text: strings.savedKey; onToggled: ... }
import QtQuick
import QtQuick.Shapes
import QtQuick.Templates as T
import org.raye.ui as Ui
import org.raye.setup

T.CheckBox {
    id: control

    readonly property color boxColor: !enabled ? (checked ? Theme.accentDisabled : Theme.controlFillDisabled)
                                    : checked ? (down ? Theme.accentPressed
                                                      : hovered ? Theme.accentHover : Theme.accent)
                                    : down ? Theme.controlFillPressed
                                    : hovered ? Theme.controlFillHover : Theme.controlFill

    implicitWidth: implicitContentWidth + leftPadding + rightPadding
    implicitHeight: Math.max(32, implicitContentHeight + topPadding + bottomPadding,
                             implicitIndicatorHeight + topPadding + bottomPadding)
    padding: 0
    spacing: 8
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    font: Theme.body

    Accessible.role: Accessible.CheckBox
    Accessible.name: text
    Accessible.checkable: true
    Accessible.checked: checked

    indicator: Rectangle {
        x: control.leftPadding
        y: control.topPadding + (control.availableHeight - height) / 2
        implicitWidth: 20
        implicitHeight: 20
        radius: Theme.radiusControl
        color: control.boxColor
        border.width: control.checked ? 0 : 1
        border.color: control.enabled ? Theme.strokeStrong : Theme.textDisabled
        Behavior on color { ColorAnimation { duration: Theme.durationHover } }

        Shape {
            anchors.fill: parent
            visible: control.checked
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: control.enabled ? Theme.textOnAccent : Qt.alpha(Theme.textOnAccent, 0.6)
                strokeWidth: 1.6
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                joinStyle: ShapePath.RoundJoin
                startX: 5; startY: 10.5
                PathLine { x: 8.5; y: 14 }
                PathLine { x: 15; y: 6.5 }
            }
        }

        Ui.FocusRing {
            objectName: "focusRing"
            target: control
            radius: Theme.radiusControl
        }
    }

    contentItem: Text {
        leftPadding: control.indicator.width + control.spacing
        text: control.text
        font: control.font
        color: control.enabled ? Theme.textPrimary : Theme.textDisabled
        wrapMode: Text.WordWrap
        verticalAlignment: Text.AlignVCenter
    }
}
