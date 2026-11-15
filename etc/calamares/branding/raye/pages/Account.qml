// Raye Setup: "Sign in with your Raye account", Windows style, with
// "Use a local account instead" and "Sign in later". The account service
// is not open yet: the page only exists when the preview switch is on
// (raye-setup-run writes account_preview=1 in /run/raye-setup/flags) AND
// the service answers. Otherwise it steps aside on its own, the way it was
// reached, and nothing is ever sent anywhere.
//
// Signing in never happens here: like Settings, it opens the account
// website after Raye starts. This page only remembers the wish
// (answer-account: signin, local or later).

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
    step: "account"
    illustration: "account"
    title: S.t(lang, "accountTitle")
    text: S.t(lang, "accountText")

    property bool available: false
    property string chosen: ""
    // the check is over (answered, refused or too slow)
    property bool known: false
    // how the page was reached, to step aside the same way
    property bool cameBack: false

    function settle(ok) {
        if (known)
            return
        known = true
        available = ok
        if (!ok) {
            Requests.answer("account", "")
            Qt.callLater(() => cameBack ? ViewManager.back() : ViewManager.next())
        }
    }

    // Made when the step comes on screen. Nothing is asked of anyone
    // without the preview switch.
    Component.onCompleted: Requests.flags(flags => {
        if (flags.account_preview !== "1" || !flags.account_server) {
            settle(false)
            return
        }
        const request = new XMLHttpRequest()
        request.onreadystatechange = function() {
            if (request.readyState === XMLHttpRequest.DONE)
                page.settle(request.status === 200 && String(request.responseText).trim() === "ok")
        }
        request.open("GET", flags.account_server.replace(/\/+$/, "") + "/healthz")
        request.send()
        tooSlow.start()
    })
    Timer {
        id: tooSlow
        interval: 3000
        onTriggered: page.settle(false)
    }

    onShown: (backward) => {
        cameBack = backward
        if (known && !available)
            Qt.callLater(() => backward ? ViewManager.back() : ViewManager.next())
    }

    function choose(what) {
        chosen = what
        Requests.answer("account", what)
        if (what !== "signin")
            ViewManager.next()
    }

    ColumnLayout {
        visible: page.available
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 10

        ChoiceCard {
            Layout.fillWidth: true
            accent: true
            illustration: "account"
            illustrationSize: 40
            title: S.t(page.lang, "accountSignIn")
            onClicked: page.choose("signin")
        }
        Text {
            Layout.fillWidth: true
            visible: page.chosen === "signin"
            text: S.t(page.lang, "accountChosen")
            font: Theme.body
            color: Theme.success
            wrapMode: Text.WordWrap
        }
        RowLayout {
            Layout.topMargin: 8
            spacing: 24
            LinkButton {
                text: S.t(page.lang, "accountLocal")
                onClicked: page.choose("local")
            }
            LinkButton {
                text: S.t(page.lang, "accountLater")
                onClicked: page.choose("later")
            }
        }
    }
}
