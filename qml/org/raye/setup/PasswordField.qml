// A password box: the setup text box with an eye on the right that shows
// the password while you want it. The eye appears once something is
// typed; Alt+F8 does the same from the keyboard, like Windows, so the
// eye stays out of the Tab order (name, password, confirm, ...).
//
//   PasswordField { placeholderText: strings.password }
import QtQuick
import QtQuick.Templates as T
import org.raye.setup

TextField {
    id: control

    property bool revealed: false
    // false where a page must never show what is typed
    property bool revealable: true

    echoMode: revealed ? TextInput.Normal : TextInput.Password
    passwordCharacter: "•"
    inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
    rightPadding: reveal.visible ? reveal.width + 8 : 12

    // nothing typed means nothing to show: start hidden again
    onTextChanged: if (length === 0) revealed = false
    // leaving the box hides the password again
    onActiveFocusChanged: if (!activeFocus) revealed = false

    Keys.onPressed: event => {
        if (event.key === Qt.Key_F8 && (event.modifiers & Qt.AltModifier) && revealable && length > 0) {
            revealed = !revealed
            event.accepted = true
        }
    }

    T.AbstractButton {
        id: reveal
        objectName: "reveal"
        anchors { right: parent.right; rightMargin: 4; verticalCenter: parent.verticalCenter }
        width: 32
        height: control.height - 8
        visible: control.revealable && control.length > 0 && control.enabled
        focusPolicy: Qt.NoFocus
        hoverEnabled: true
        Accessible.role: Accessible.Button
        Accessible.name: control.revealed ? Theme.text("hidePassword") : Theme.text("showPassword")
        onClicked: control.revealed = !control.revealed

        background: Rectangle {
            radius: Theme.radiusControl
            color: reveal.down ? Theme.controlFillPressed
                 : reveal.hovered ? Theme.controlFillHover : "transparent"
            Behavior on color { ColorAnimation { duration: Theme.durationHover } }
        }
        contentItem: Item {
            RevealEye {
                anchors.centerIn: parent
                width: 18
                height: 18
                struck: control.revealed
                color: reveal.hovered ? Theme.textPrimary : Theme.textSecondary
            }
        }
    }
}
