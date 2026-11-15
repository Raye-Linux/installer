// Raye Setup: "Let's name your device". Optional: left empty, the account
// page names it from the person's name, as before. The account page
// (usersq.qml) takes the name from answer-hostname.

import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick
import QtQuick.Layouts
import org.raye.setup

import "../strings.js" as S
import "../components"
import "../components/Requests.js" as Requests

RayeFrame {
    id: page
    step: "device"
    illustration: "look"
    title: S.t(lang, "deviceTitle")
    text: S.t(lang, "deviceText")


    onShown: (backward) => {
        name.forceActiveFocus()
        save()
    }
    // textEdited comes before the text binding moves on: read the field
    // itself; a hostname has no hyphen at either end
    function save() { Requests.answer("hostname", name.text.replace(/^-+|-+$/g, "")) }

    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 8

        FieldLabel {
            Layout.fillWidth: true
            text: S.t(page.lang, "deviceName")
            field: name
        }
        TextField {
            id: name
            Layout.fillWidth: true
            Layout.maximumWidth: 420
            maximumLength: 63
            Accessible.name: S.t(page.lang, "deviceName")
            inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText
            // only what a hostname may hold; a space turns into a hyphen
            validator: RegularExpressionValidator { regularExpression: /[A-Za-z0-9-]{0,63}/ }
            onTextEdited: page.save()
            Keys.onSpacePressed: (event) => {
                if (text.length < maximumLength) {
                    insert(cursorPosition, "-")
                    page.save()
                }
                event.accepted = true
            }
        }
        Text {
            Layout.fillWidth: true
            text: S.t(page.lang, "deviceRules")
            font: Theme.caption
            color: Theme.textTertiary
            wrapMode: Text.WordWrap
        }
        Text {
            Layout.fillWidth: true
            Layout.topMargin: 8
            text: S.t(page.lang, "deviceSkip")
            font: Theme.body
            color: Theme.textSecondary
            wrapMode: Text.WordWrap
        }
    }
}
