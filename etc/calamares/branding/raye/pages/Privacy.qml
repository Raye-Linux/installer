// Raye Setup: "Choose privacy settings for your device". Only what Raye
// really has, the same switches as Settings > Privacy & security, with
// the same defaults: location on (apps still ask first), usage statistics
// off, activity history on. rayesetupchoices writes them into the new
// account (answer-privacy).

import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick
import QtQuick.Layouts
import org.raye.setup
import org.raye.ui as Ui

import "../strings.js" as S
import "../components"
import "../components/Requests.js" as Requests

RayeFrame {
    id: page
    step: "privacy"
    illustration: "privacy"
    title: S.t(lang, "privacyTitle")
    text: S.t(lang, "privacyText")

    onShown: (backward) => {
        save()
    }
    function save() {
        Requests.answer("privacy", "location=" + (location.checked ? 1 : 0)
                                   + " diagnostics=" + (diagnostics.checked ? 1 : 0)
                                   + " history=" + (history.checked ? 1 : 0))
    }

    component Choice: RowLayout {
        id: choice
        property string name
        property string lineOn
        property string lineOff
        property alias checked: toggle.checked
        Layout.fillWidth: true
        spacing: 16
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Text {
                Layout.fillWidth: true
                text: choice.name
                font: Theme.bodyStrong
                color: Theme.textPrimary
            }
            Text {
                Layout.fillWidth: true
                text: toggle.checked ? choice.lineOn : choice.lineOff
                font: Theme.body
                color: Theme.textSecondary
                wrapMode: Text.WordWrap
            }
        }
        Ui.Switch {
            id: toggle
            Layout.alignment: Qt.AlignTop
            onText: S.t(page.lang, "on")
            offText: S.t(page.lang, "off")
            Accessible.name: choice.name
            onToggled: page.save()
        }
    }

    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 20

        Choice {
            id: location
            name: S.t(page.lang, "location")
            lineOn: S.t(page.lang, "locationOn")
            lineOff: S.t(page.lang, "locationOff")
            checked: true
        }
        Choice {
            id: diagnostics
            name: S.t(page.lang, "diagnostics")
            lineOn: S.t(page.lang, "diagnosticsOn")
            lineOff: S.t(page.lang, "diagnosticsOff")
            checked: false
        }
        Choice {
            id: history
            name: S.t(page.lang, "history")
            lineOn: S.t(page.lang, "historyOn")
            lineOff: S.t(page.lang, "historyOff")
            checked: true
        }
    }
}
