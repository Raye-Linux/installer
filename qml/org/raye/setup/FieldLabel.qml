// The name over a text box, the way Settings shows it. Point `field` at the
// box: a click on the name puts the cursor in it.
//
//   FieldLabel { text: strings.password; field: password }
//   PasswordField { id: password; Accessible.name: ... }
import QtQuick
import org.raye.setup

Text {
    id: label

    property Item field

    font: Theme.label
    color: field && !field.enabled ? Theme.textDisabled : Theme.textPrimary
    elide: Text.ElideRight
    Accessible.ignored: true

    MouseArea {
        anchors.fill: parent
        enabled: label.field !== null
        cursorShape: Qt.IBeamCursor
        onClicked: label.field.forceActiveFocus()
    }
}
