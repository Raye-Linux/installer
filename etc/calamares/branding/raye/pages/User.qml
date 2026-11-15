// Raye Setup: "Who's going to use this PC?". The name, the account name
// made from it (shown, changed only when asked), a password typed twice
// and an optional hint. No security questions. The device name comes from
// the page before (answer-hostname); the hint goes to the new system
// through rayesetupchoices (answer-password-hint).

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
    step: "user"
    illustration: "account"
    title: S.t(lang, "userTitle")
    text: S.t(lang, "userText")

    property bool editLogin: false
    property bool customHost: false
    readonly property bool mismatch: confirm.text !== "" && confirm.text !== password.text
    property bool hintLeaks: false

    onShown: (backward) => {
        Requests.answerOf("hostname", text => {
            const host = text.trim()
            if (host) {
                config.setHostName(host)
                customHost = true
            } else if (customHost) {
                // a name was given, then taken back: name it from the person again
                const first = (config.loginName || "raye").split(/[._-]/)[0]
                config.setHostName(first + "-pc")
                customHost = false
            }
        })
        fullName.forceActiveFocus()
        check()
    }
    // No password yet, or a hint that gives it away, keeps Next off: the
    // second password Calamares checks is made not to match until then.
    // (textEdited comes before the text bindings move on: read the fields)
    function check() {
        const said = hint.text.trim()
        hintLeaks = said !== "" && password.text !== ""
                    && said.toLowerCase().indexOf(password.text.toLowerCase()) >= 0
        const blocked = hintLeaks || password.text === ""
        config.setUserPasswordSecondary(blocked ? confirm.text + "\n" : confirm.text)
        Requests.answer("password-hint", hintLeaks ? "" : said)
    }

    // one line of caption text, the height every message line keeps
    FontMetrics {
        id: lineHeight
        font: Theme.caption
    }

    // a name, its box, and the line under it, 4 px apart; 12 px more
    // before the next name
    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 4

        FieldLabel {
            Layout.fillWidth: true
            text: S.t(page.lang, "fullName")
            field: fullName
        }
        TextField {
            id: fullName
            objectName: "fullName"
            Layout.fillWidth: true
            Accessible.name: S.t(page.lang, "fullName")
            text: config.fullName
            onTextEdited: config.setFullName(text)
        }

        // The account name line, or its field once Change is clicked, sit in
        // one slot as tall as the field, and every message below keeps its
        // line even when it has nothing to say: nothing moves while someone
        // types. (On the 2026-11-08 image the line came in after the first
        // letter of the name and pushed the password fields down 40 px.)
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: login.implicitHeight
            RowLayout {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                visible: config.loginName !== "" && !page.editLogin
                spacing: 12
                Text {
                    text: S.t(page.lang, "userNameLine", [config.loginName])
                    font: Theme.caption
                    color: Theme.textTertiary
                }
                LinkButton {
                    text: S.t(page.lang, "change")
                    onClicked: {
                        page.editLogin = true
                        login.forceActiveFocus()
                    }
                }
                Item { Layout.fillWidth: true }
            }
            TextField {
                id: login
                anchors.left: parent.left
                anchors.right: parent.right
                visible: page.editLogin
                placeholderText: S.t(page.lang, "userName")
                Accessible.name: placeholderText
                text: config.loginName
                error: config.loginNameStatus !== ""
                inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText
                onTextEdited: config.setLoginName(text)
            }
        }
        Text {
            Layout.fillWidth: true
            Layout.preferredHeight: lineHeight.height
            text: config.loginNameStatus !== "" && config.loginName !== "" ? config.loginNameStatus : ""
            font: Theme.caption
            color: Theme.error
            elide: Text.ElideRight
        }

        FieldLabel {
            Layout.fillWidth: true
            Layout.topMargin: 12
            text: S.t(page.lang, "password")
            field: password
        }
        PasswordField {
            id: password
            objectName: "password"
            Layout.fillWidth: true
            Accessible.name: S.t(page.lang, "password")
            onTextEdited: {
                config.setUserPassword(text)
                page.check()
            }
        }
        FieldLabel {
            Layout.fillWidth: true
            Layout.topMargin: 12
            text: S.t(page.lang, "confirmPassword")
            field: confirm
        }
        PasswordField {
            id: confirm
            objectName: "passwordAgain"
            Layout.fillWidth: true
            Accessible.name: S.t(page.lang, "confirmPassword")
            error: page.mismatch
            onTextEdited: page.check()
        }
        Text {
            Layout.fillWidth: true
            Layout.preferredHeight: lineHeight.height
            objectName: "passwordLine"
            text: page.mismatch ? S.t(page.lang, "passwordsDiffer")
                : password.text !== "" && confirm.text === password.text && config.userPasswordValidity !== 0
                  ? config.userPasswordMessage : ""
            font: Theme.caption
            color: Theme.error
            elide: Text.ElideRight
        }

        FieldLabel {
            Layout.fillWidth: true
            Layout.topMargin: 12
            text: S.t(page.lang, "hint")
            field: hint
        }
        TextField {
            id: hint
            objectName: "hint"
            Layout.fillWidth: true
            maximumLength: 120
            Accessible.name: S.t(page.lang, "hint")
            error: page.hintLeaks
            onTextEdited: page.check()
        }
        Text {
            Layout.fillWidth: true
            text: page.hintLeaks ? S.t(page.lang, "hintHasPassword") : S.t(page.lang, "hintLine")
            font: Theme.caption
            color: page.hintLeaks ? Theme.error : Theme.textTertiary
            wrapMode: Text.WordWrap
        }
    }
}
