// Raye Setup, the bar along the top: the eye and "Raye Setup" over the
// card's left edge, the stages of setup over its right edge, and the close
// button at the right end of the screen. Closing asks "Quit Setup?" and
// restarts or shuts the PC down: there is no desktop behind Setup to go
// back to. Opened from a desktop (Try Raye Linux), it goes back there.

import io.calamares.ui 1.0
import io.calamares.core 1.0

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import org.raye.setup

import "strings.js" as S
import "components"
import "components/Requests.js" as Requests

Rectangle {
    id: bar
    // the first colour of the page's gradient, so bar and page are one
    color: Theme.backgroundTop
    height: 56
    LayoutMirroring.enabled: { step; ViewManager.nextLabel; return Qt.locale().textDirection === Qt.RightToLeft }
    LayoutMirroring.childrenInherit: true

    readonly property int step: ViewManager.currentStepIndex
    // the language page can change it: read again whenever the step moves
    readonly property string lang: { step; ViewManager.nextLabel; return S.current(Qt.locale()) }
    readonly property int cardWidth: Math.min(1100, width - 96)
    readonly property int cardLeft: Math.round((width - cardWidth) / 2)
    readonly property int stage: S.stageOf(step)
    // Calamares' own Cancel is off (settings.conf): this button is the way out
    readonly property bool closable: S.steps[step] !== "installing" && S.steps[step] !== "done"
    // started by raye-install from a desktop rather than the stick's session
    property bool fromDesktop: false
    Component.onCompleted: Requests.flags(found => fromDesktop = found.desktop === "1")

    function t(key, args) { return S.t(lang, key, args) }

    RowLayout {
        anchors.left: parent.left
        anchors.leftMargin: bar.cardLeft
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10
        Image {
            Layout.preferredWidth: 22
            Layout.preferredHeight: 22
            source: "file:/" + Branding.imagePath(Branding.ProductLogo)
            sourceSize.width: 44
            sourceSize.height: 44
        }
        Text {
            text: bar.t("setupName")
            font: Theme.bodyStrong
            color: Theme.textPrimary
        }
    }

    // where you are: Region, Network, Disk, Account, Privacy, Install
    Row {
        id: stages
        anchors.right: parent.right
        // clear of the close button at the right end
        anchors.rightMargin: Math.max(bar.cardLeft, 64)
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6
        visible: bar.width >= 1000
        Accessible.role: Accessible.StaticText
        Accessible.name: bar.t("stageOf", [bar.stage + 1, S.stages.length, bar.t(S.stages[bar.stage].key)])

        Repeater {
            model: S.stages.length
            Row {
                required property int index
                readonly property bool current: index === bar.stage
                readonly property bool done: index < bar.stage
                spacing: 6
                height: 24

                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 8
                    height: 8
                    radius: 4
                    color: parent.current || parent.done ? Theme.accent : "transparent"
                    border.width: parent.current || parent.done ? 0 : 1
                    border.color: Theme.textTertiary
                    Behavior on color { ColorAnimation { duration: Theme.durationMove } }
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: bar.t(S.stages[index].key)
                    font: parent.current ? Theme.bodyStrong : Theme.body
                    color: parent.current ? Theme.textPrimary
                         : parent.done ? Theme.textSecondary : Theme.textTertiary
                }
                Rectangle {
                    visible: index < S.stages.length - 1
                    anchors.verticalCenter: parent.verticalCenter
                    width: 20
                    height: 1
                    color: parent.done ? Qt.alpha(Theme.accent, 0.7) : Theme.surfaceStroke
                }
            }
        }
    }

    Row {
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        spacing: 4

        // the close button of the Windows setup window
        AbstractButton {
            id: close
            visible: bar.closable
            width: 40
            height: 32
            hoverEnabled: true
            Accessible.role: Accessible.Button
            Accessible.name: bar.t("quit")
            ToolTip.visible: hovered
            ToolTip.delay: 600
            ToolTip.text: bar.t("quit")
            onClicked: quitBox.ask()
            background: Rectangle {
                radius: Theme.radiusControl
                color: close.down ? Qt.alpha("#c42b1c", 0.8) : close.hovered ? "#c42b1c" : "transparent"
                Behavior on color { ColorAnimation { duration: Theme.durationHover } }
            }
            contentItem: Item {
                Repeater {
                    model: 2
                    Rectangle {
                        required property int index
                        anchors.centerIn: parent
                        width: 14
                        height: 1.5
                        antialiasing: true
                        color: Theme.textPrimary
                        rotation: index === 0 ? 45 : -45
                    }
                }
            }
        }
    }

    Overlay {
        id: quitBox
        over: bar
        title: bar.t("quitTitle")

        function ask() {
            showOver()
            backButton.forceActiveFocus()
        }
        function power(what) {
            Requests.send("power " + what)
            hide()
        }
        function leave() {
            Requests.send("close")
            hide()
        }

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(480, parent.width - 48)
            height: quitBody.implicitHeight + 2 * 28
            radius: Theme.radiusCard
            // opaque: the page under it must not show through the words
            color: Qt.alpha(Theme.surface, 1)
            border.color: Theme.surfaceStroke
            Keys.onEscapePressed: quitBox.hide()
            MouseArea { anchors.fill: parent }

            ColumnLayout {
                id: quitBody
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 28 }
                spacing: 12
                Text {
                    Layout.fillWidth: true
                    text: bar.t("quitTitle")
                    font: Theme.subtitle
                    color: Theme.textPrimary
                    wrapMode: Text.WordWrap
                }
                Text {
                    Layout.fillWidth: true
                    text: bar.t(bar.fromDesktop ? "quitTextDesktop" : "quitText")
                    font: Theme.body
                    color: Theme.textSecondary
                    wrapMode: Text.WordWrap
                }
                RowLayout {
                    Layout.topMargin: 12
                    Layout.alignment: Qt.AlignRight
                    spacing: 8
                    PrimaryButton {
                        visible: bar.fromDesktop
                        text: bar.t("quitClose")
                        onClicked: quitBox.leave()
                    }
                    PrimaryButton {
                        visible: !bar.fromDesktop
                        text: bar.t("quitRestart")
                        onClicked: quitBox.power("restart")
                    }
                    SubtleButton {
                        visible: !bar.fromDesktop
                        text: bar.t("quitShutDown")
                        onClicked: quitBox.power("poweroff")
                    }
                    SubtleButton {
                        id: backButton
                        text: bar.t("back")
                        onClicked: quitBox.hide()
                        Keys.onEscapePressed: quitBox.hide()
                    }
                }
            }
        }
    }
}
