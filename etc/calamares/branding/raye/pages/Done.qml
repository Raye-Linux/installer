// Raye Setup, the last page: "Raye is installed", and the PC restarts by
// itself after a short countdown (Restart now does it at once), like
// Windows setup. If the install failed, plain words, what happened, and
// Restart.

import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.raye.setup

import "../strings.js" as S
import "../components"

RayeFrame {
    id: page
    step: "done"
    illustration: config.failed ? "error" : "done"
    title: S.t(lang, config.failed ? "failedTitle" : "doneTitle")
    text: S.t(lang, config.failed ? "failedText" : "doneText")

    readonly property int countdownSeconds: 15
    property int secondsLeft: countdownSeconds

    onShown: (backward) => {
        secondsLeft = countdownSeconds
        countdown.running = !config.failed
    }
    function restart() {
        countdown.running = false
        config.doRestart(true)
    }

    Timer {
        id: countdown
        interval: 1000
        repeat: true
        onTriggered: {
            page.secondsLeft -= 1
            if (page.secondsLeft <= 0)
                page.restart()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        RowLayout {
            visible: !config.failed
            spacing: 16
            ProgressRing {
                size: 48
                value: page.secondsLeft / page.countdownSeconds
                Behavior on value { NumberAnimation { duration: 900 } }
            }
            Text {
                text: S.t(page.lang, "restartIn", [page.secondsLeft])
                font: Theme.bodyLarge
                color: Theme.textPrimary
            }
        }

        Text {
            Layout.fillWidth: true
            visible: config.failed
            text: S.t(page.lang, S.failureKey(config.failureMessage, config.failureDetails))
            font: Theme.body
            color: Theme.textSecondary
            wrapMode: Text.WordWrap
        }
        Text {
            visible: config.failed && config.failureMessage !== ""
            text: S.t(page.lang, "failedDetails")
            font: Theme.bodyStrong
            color: Theme.textPrimary
        }
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: config.failed
            clip: true
            TextArea {
                readOnly: true
                wrapMode: TextEdit.Wrap
                textFormat: TextEdit.PlainText
                text: config.failureMessage + (config.failureDetails ? "\n\n" + config.failureDetails : "")
                font: Theme.caption
                color: Theme.textSecondary
                background: null
            }
        }
        Item { Layout.fillHeight: true; visible: !config.failed }

        // the installer's licence wants its notice reachable from the
        // interface: one click away here, never on the main screens
        Text {
            id: licence
            Layout.fillWidth: true
            visible: false
            text: S.t(page.lang, "licenceText")
            font: Theme.caption
            color: Theme.textTertiary
            wrapMode: Text.WordWrap
        }
        RowLayout {
            Layout.fillWidth: true
            LinkButton {
                text: S.t(page.lang, "licences")
                onClicked: licence.visible = !licence.visible
            }
            Item { Layout.fillWidth: true }
            PrimaryButton {
                // the label changes with the language after the page is laid out
                Layout.preferredWidth: implicitWidth
                text: S.t(page.lang, "restartNow")
                onClicked: page.restart()
            }
        }
    }
}
