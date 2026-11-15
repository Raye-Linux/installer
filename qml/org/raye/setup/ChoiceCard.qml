// A big choice on a setup page: a language, Install or Try, a way to use
// the disk, Dark or Light. A card with 8 px corners, a title, an
// optional line under it and an optional picture on the left.
//
//   ChoiceCard { title: "English"; description: "Canada"; checkable: true }
//   ChoiceCard { accent: true; illustration: "install"; title: strings.install
//                description: strings.installLine; onClicked: ... }
//
// checkable: picked with a click or Space, shown by an accent outline
// (put the cards of one question in a ButtonGroup, or set autoExclusive).
// Not checkable: the card is an action and shows an arrow on the right.
// accent: the main action, filled with the accent.
import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes
import QtQuick.Templates as T
import org.raye.ui as Ui
import org.raye.setup

T.AbstractButton {
    id: control

    property string title: text
    property string description
    property string illustration
    property int illustrationSize: 64
    property bool accent: false
    // a radio circle on the left, for the cards of a list of options
    property bool showRadio: false
    // choosing this card deletes something: the line under the title says so in red
    property bool danger: false

    readonly property color fillColor: !enabled ? Theme.controlFillDisabled
                                     : accent ? (down ? Theme.accentPressed
                                                      : hovered ? Theme.accentHover : Theme.accent)
                                     : checked ? Theme.selected
                                     : down ? Theme.controlFillPressed
                                     : hovered ? Theme.controlFillHover : Theme.controlFill
    readonly property color titleColor: !enabled ? Theme.textDisabled
                                      : accent ? Theme.textOnAccent : Theme.textPrimary
    readonly property color lineColor: !enabled ? Theme.textDisabled
                                     : danger ? Qt.lighter(Theme.error, 1.35)
                                     : accent ? Qt.alpha(Theme.textOnAccent, 0.82) : Theme.textSecondary

    implicitWidth: Math.max(240, implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(48, implicitContentHeight + topPadding + bottomPadding)
    padding: 16
    spacing: 16
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus

    Accessible.role: checkable ? Accessible.RadioButton : Accessible.Button
    Accessible.name: title
    Accessible.description: description
    Accessible.checkable: checkable
    Accessible.checked: checked
    Accessible.onPressAction: control.clicked()

    // Enter picks the card too, like Space; it never takes the pick away
    Keys.onReturnPressed: event => { control.pick(); control.clicked(); event.accepted = true }
    Keys.onEnterPressed: event => { control.pick(); control.clicked(); event.accepted = true }

    function pick() {
        if (checkable && !checked) {
            checked = true
            toggled()
        }
    }

    contentItem: RowLayout {
        spacing: control.spacing

        // radio circle
        Rectangle {
            visible: control.showRadio
            Layout.alignment: Qt.AlignVCenter
            implicitWidth: 20
            implicitHeight: 20
            radius: 10
            color: control.checked ? Theme.accent : "transparent"
            border.width: control.checked ? 0 : 1
            border.color: control.enabled ? Theme.strokeStrong : Theme.textDisabled
            Rectangle {
                anchors.centerIn: parent
                visible: control.checked
                width: control.down ? 8 : control.hovered ? 12 : 10
                height: width
                radius: width / 2
                color: Theme.textOnAccent
                Behavior on width { NumberAnimation { duration: Theme.durationHover } }
            }
        }

        // on the accent fill the picture sits in a dark well, so its
        // lines keep their contrast
        Rectangle {
            visible: control.illustration !== "" && control.accent
            Layout.alignment: Qt.AlignVCenter
            Layout.preferredWidth: control.illustrationSize + 12
            Layout.preferredHeight: control.illustrationSize + 12
            radius: Theme.radiusCard
            color: Qt.alpha(Theme.backgroundTop, control.enabled ? 0.72 : 0.4)
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, 0.12)
            Illustration {
                anchors.centerIn: parent
                name: control.accent ? control.illustration : ""
                size: control.illustrationSize
            }
        }

        Illustration {
            visible: control.illustration !== "" && !control.accent
            Layout.alignment: Qt.AlignVCenter
            Layout.preferredWidth: control.illustrationSize
            Layout.preferredHeight: control.illustrationSize
            name: control.accent ? "" : control.illustration
            size: control.illustrationSize
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            spacing: 2
            Text {
                Layout.fillWidth: true
                text: control.title
                font: control.illustrationSize >= 64 && control.illustration !== "" ? Theme.subtitle : Theme.bodyStrong
                color: control.titleColor
                wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                visible: text !== ""
                text: control.description
                font: Theme.body
                color: control.lineColor
                wrapMode: Text.WordWrap
            }
        }

        // the arrow of an action card
        Shape {
            visible: !control.checkable
            Layout.alignment: Qt.AlignVCenter
            implicitWidth: 16
            implicitHeight: 16
            preferredRendererType: Shape.CurveRenderer
            transform: Translate { x: control.hovered && !Theme.reducedMotion ? 2 : 0
                Behavior on x { NumberAnimation { duration: Theme.durationHover } } }
            ShapePath {
                strokeColor: control.titleColor
                strokeWidth: 1.5
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                joinStyle: ShapePath.RoundJoin
                startX: 6; startY: 3
                PathLine { x: 11; y: 8 }
                PathLine { x: 6; y: 13 }
            }
        }
    }

    background: Rectangle {
        radius: Theme.radiusCard
        color: control.fillColor
        border.width: 1
        border.color: control.checked && !control.accent ? Theme.accent
                    : control.accent ? Qt.rgba(1, 1, 1, 0.14) : Theme.surfaceStroke
        Behavior on color { ColorAnimation { duration: Theme.durationHover } }

        Ui.FocusRing {
            objectName: "focusRing"
            target: control
            radius: Theme.radiusCard
        }
    }
}
