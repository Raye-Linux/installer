// A text box for setup pages: 40 px high, 4 px corners, a light veil
// with a 1 px edge, and a 2 px accent line along the bottom while you
// type in it (red with error: true).
//
//   TextField { placeholderText: strings.fullName; onTextEdited: ... }
import QtQuick
import QtQuick.Templates as T
import org.raye.setup

T.TextField {
    id: control

    // the text is wrong: red line, the app says why under the field
    property bool error: false
    // what is wrong, read out to screen readers (the page shows it too)
    property string errorText: ""
    property bool compact: false

    readonly property bool typing: activeFocus && !readOnly
    readonly property color fillColor: !enabled ? Theme.controlFillDisabled
                                     : typing ? Theme.inputActive
                                     : hovered ? Theme.controlFillHover : Theme.controlFill
    readonly property color lineColor: error ? Theme.error
                                     : typing ? Theme.accent : Qt.rgba(1, 1, 1, 0.14)
    readonly property real lineWidth: typing || error ? 2 : 1

    implicitWidth: Math.max(240, placeholder.implicitWidth + leftPadding + rightPadding)
    implicitHeight: compact ? Theme.dialogControlHeight : Theme.controlHeight
    leftPadding: 12
    rightPadding: 12
    topPadding: 0
    bottomPadding: 0
    verticalAlignment: TextInput.AlignVCenter
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    selectByMouse: true
    font: Theme.body
    color: enabled ? Theme.textPrimary : Theme.textDisabled
    selectionColor: Theme.accent
    selectedTextColor: Theme.textOnAccent
    placeholderTextColor: enabled ? Theme.textTertiary : Theme.textDisabled

    Accessible.role: Accessible.EditableText
    Accessible.name: placeholderText
    Accessible.description: error ? errorText : ""

    cursorDelegate: Rectangle {
        id: cursor
        width: 1
        color: Theme.textPrimary
        visible: control.activeFocus && control.selectionStart === control.selectionEnd
        SequentialAnimation on opacity {
            running: cursor.visible && !Theme.reducedMotion
            loops: Animation.Infinite
            NumberAnimation { to: 0; duration: 0 }
            PauseAnimation { duration: 530 }
            NumberAnimation { to: 1; duration: 0 }
            PauseAnimation { duration: 530 }
        }
    }

    Text {
        id: placeholder
        x: control.leftPadding
        width: control.width - control.leftPadding - control.rightPadding
        height: control.height
        text: control.placeholderText
        font: control.font
        color: control.placeholderTextColor
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        visible: control.length === 0 && control.preeditText.length === 0
        Accessible.ignored: true
    }

    background: Rectangle {
        radius: Theme.radiusControl
        color: control.fillColor
        border.width: 1
        border.color: control.error ? Qt.alpha(Theme.error, 0.5) : Theme.controlStroke
        Behavior on color { ColorAnimation { duration: Theme.durationHover } }

        // the bottom line, inside the rounded corners
        Rectangle {
            objectName: "underline"
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom
                      leftMargin: parent.radius - 1; rightMargin: parent.radius - 1 }
            height: control.lineWidth
            color: control.lineColor
            Behavior on color { ColorAnimation { duration: Theme.durationHover } }
        }
    }
}
