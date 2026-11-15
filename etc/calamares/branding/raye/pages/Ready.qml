// Raye Setup: "Ready to install". What each page decided, in words, one card
// each, and when the disk is erased a red line saying so. Next reads Install:
// it is the confirmation, as in Windows setup. What will happen to the disk,
// partition by partition, is one click away for whoever wants it.

import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.raye.setup

import "../strings.js" as S
import "../components"
import "../components/Requests.js" as Requests
import "../components/Summary.js" as Summary

RayeFrame {
    id: page
    step: "ready"
    illustration: "summary"
    title: S.t(lang, "readyTitle")
    text: S.t(lang, "readyText")

    property string install: ""
    property string zone: ""
    property string keyboard: ""
    property string hostName: ""
    property string fullName: ""
    // the disk page's answer: answer-disk
    property string diskLabel: ""
    property string diskDetails: ""
    property bool encrypted: false
    property bool detailsOpen: false

    readonly property bool erasing: install === "erase"
    readonly property var cards: Summary.cards({
        lang: lang, code: S.code(Qt.locale()), nativeName: Qt.locale().nativeLanguageName,
        zone: zone, keyboard: keyboard, install: install, diskLabel: diskLabel, encrypted: encrypted,
        fullName: fullName, hostName: hostName })

    onShown: (backward) => {
        const region = Global.value("locationRegion")
        const city = Global.value("locationZone")
        zone = region && city ? region + "/" + city : ""
        fullName = Global.value("fullname") || ""
        detailsOpen = false
        Requests.answerOf("keyboard-label", text => keyboard = text.trim())
        Requests.answerOf("hostname", text => hostName = text.trim() || Global.value("hostname") || "")
        Requests.answerOf("disk", text => {
            let answer = {}
            try { answer = JSON.parse(text) } catch (e) { answer = {} }
            install = answer.install || ""
            diskLabel = answer.diskLabel || ""
            diskDetails = answer.details || ""
            encrypted = !!answer.encrypt
        })
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Rectangle {
            Layout.fillWidth: true
            visible: page.erasing
            implicitHeight: eraseText.implicitHeight + 20
            radius: Theme.radiusControl
            color: Qt.alpha(Theme.error, 0.12)
            border.color: Qt.alpha(Theme.error, 0.45)
            Text {
                id: eraseText
                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 12 }
                text: S.t(page.lang, "readyErase")
                font: Theme.bodyStrong
                color: Theme.textPrimary
                wrapMode: Text.WordWrap
            }
        }

        Flickable {
            id: scroller
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentHeight: column.implicitHeight
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}

            ColumnLayout {
                id: column
                width: scroller.width
                spacing: 8

                Repeater {
                    model: page.cards
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: card.implicitHeight + 24
                        radius: Theme.radiusControl
                        color: Theme.controlFill
                        border.color: Theme.controlStroke
                        ColumnLayout {
                            id: card
                            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                            spacing: 4
                            Text {
                                Layout.fillWidth: true
                                Layout.bottomMargin: 2
                                text: modelData.title
                                font: Theme.bodyStrong
                                color: Theme.textPrimary
                                Accessible.role: Accessible.Heading
                                Accessible.name: text
                            }
                            Repeater {
                                model: modelData.rows
                                delegate: RowLayout {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: 12
                                    Text {
                                        Layout.preferredWidth: 130
                                        Layout.alignment: Qt.AlignTop
                                        text: modelData.label
                                        font: Theme.caption
                                        color: Theme.textTertiary
                                        wrapMode: Text.WordWrap
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        Layout.alignment: Qt.AlignTop
                                        text: modelData.value
                                        font: Theme.caption
                                        color: Theme.textPrimary
                                        wrapMode: Text.WordWrap
                                    }
                                }
                            }
                        }
                    }
                }

                LinkButton {
                    visible: page.diskDetails !== ""
                    text: S.t(page.lang, page.detailsOpen ? "readyDetailsHide" : "readyDetailsShow")
                    onClicked: page.detailsOpen = !page.detailsOpen
                }
                Text {
                    Layout.fillWidth: true
                    visible: page.detailsOpen
                    text: page.diskDetails
                    textFormat: Text.StyledText
                    font: Theme.caption
                    color: Theme.textSecondary
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
