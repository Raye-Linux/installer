// Raye Setup, the bar along the bottom: Back and Next under the card's
// right edge, like the Windows setup card, and accessibility on the left
// (on-screen keyboard, screen reader). Back and Next hide while Raye
// installs.

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
    // the last colour of the page's gradient
    color: Theme.backgroundBottom
    height: 64
    LayoutMirroring.enabled: { step; ViewManager.nextLabel; return Qt.locale().textDirection === Qt.RightToLeft }
    LayoutMirroring.childrenInherit: true

    readonly property int step: ViewManager.currentStepIndex
    readonly property string stepName: S.steps[step] || ""
    // the labels change when Calamares retranslates: language changes show at once
    readonly property string lang: { step; ViewManager.nextLabel; return S.current(Qt.locale()) }
    readonly property int cardWidth: Math.min(1100, width - 96)
    readonly property int cardLeft: Math.round((width - cardWidth) / 2)
    property bool keyboardOn: false
    property bool readerOn: false
    property bool hasKeyboard: false
    Component.onCompleted: Requests.flags(found => hasKeyboard = found.osk === "1")

    // Raye's words in English and French; in other languages Calamares'
    // own translated labels (without their & shortcut marks)
    readonly property bool rayeWords: { step; ViewManager.nextLabel; return S.current(Qt.locale()) === "fr" || S.code(Qt.locale()) === "en" }
    function t(key) { return S.t(lang, key) }
    function calamares(label) { return label.replace("&", "") }
    function backText() { return rayeWords ? t("back") : calamares(ViewManager.backLabel) }
    // The disk page says when it has an answer, in a file: each page has a
    // QML engine of its own, and Calamares' own Next knows nothing of it.
    property bool diskReady: false
    Timer {
        running: bar.stepName === "disk"
        interval: 200
        repeat: true
        triggeredOnStart: true
        onTriggered: Requests.read("disk-ready", text => bar.diskReady = text.trim() === "1")
    }
    onStepNameChanged: diskReady = false

    function nextText() {
        if (!rayeWords)
            return calamares(ViewManager.nextLabel)
        switch (stepName) {
        case "privacy": return t("accept")
        case "ready": return t("install")
        default: return t("next")
        }
    }
    function toggleReader() {
        readerOn = !readerOn
        Requests.send("reader")
    }

    // like Windows: the screen reader comes and goes with Win+Alt+S
    Shortcut {
        sequence: "Meta+Alt+S"
        context: Qt.ApplicationShortcut
        onActivated: bar.toggleReader()
    }

    AbstractButton {
        id: access
        anchors.left: parent.left
        anchors.leftMargin: bar.cardLeft
        anchors.verticalCenter: parent.verticalCenter
        width: 40
        height: 40
        hoverEnabled: true
        Accessible.role: Accessible.Button
        Accessible.name: bar.t("accessibility")
        ToolTip.visible: hovered
        ToolTip.delay: 600
        ToolTip.text: bar.t("accessibility")
        onClicked: {
            menu.showOver()
            panel.forceActiveFocus()
        }
        background: Rectangle {
            radius: Theme.radiusControl
            color: access.down ? Theme.controlFillPressed : access.hovered ? Theme.controlFillHover : "transparent"
        }
        // a person in a circle, drawn once
        contentItem: Canvas {
            implicitWidth: 20
            implicitHeight: 20
            onPaint: {
                const c = getContext("2d")
                c.reset()
                c.strokeStyle = Theme.textPrimary
                c.fillStyle = Theme.textPrimary
                c.lineWidth = 1.5
                c.lineCap = "round"
                c.beginPath(); c.arc(10, 10, 8.5, 0, 2 * Math.PI); c.stroke()
                c.beginPath(); c.arc(10, 5.6, 1.5, 0, 2 * Math.PI); c.fill()
                c.beginPath()
                c.moveTo(5.5, 8.2); c.lineTo(14.5, 8.2)
                c.moveTo(10, 8.2); c.lineTo(10, 11.8)
                c.moveTo(10, 11.8); c.lineTo(7.4, 15.4)
                c.moveTo(10, 11.8); c.lineTo(12.6, 15.4)
                c.stroke()
            }
        }
    }

    RowLayout {
        anchors.right: parent.right
        anchors.rightMargin: bar.cardLeft
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8
        visible: ViewManager.backAndNextVisible && bar.stepName !== "installing" && bar.stepName !== "done"

        SubtleButton {
            Layout.minimumWidth: 120
            text: bar.backText()
            visible: bar.step > 0
            enabled: ViewManager.backEnabled
            onClicked: ViewManager.back()
        }
        PrimaryButton {
            Layout.minimumWidth: 120
            text: bar.nextText()
            enabled: ViewManager.nextEnabled && (bar.stepName !== "disk" || bar.diskReady)
            onClicked: ViewManager.next()
        }
    }

    // the accessibility menu, a small panel over the bottom left corner
    Overlay {
        id: menu
        over: bar
        dim: 0
        title: bar.t("accessibility")

        Rectangle {
            id: panel
            x: bar.cardLeft
            y: parent.height - bar.height - height + 4
            width: 320
            height: items.implicitHeight + 16
            radius: Theme.radiusCard
            color: Theme.backgroundBottom
            border.color: Theme.surfaceStroke
            focus: true
            Keys.onEscapePressed: menu.hide()
            MouseArea { anchors.fill: parent }

            ColumnLayout {
                id: items
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 8 }
                spacing: 2
                ListRow {
                    Layout.fillWidth: true
                    visible: bar.hasKeyboard
                    focusPolicy: Qt.StrongFocus
                    text: bar.t("onScreenKeyboard")
                    detail: bar.keyboardOn ? bar.t("on") : bar.t("off")
                    highlighted: bar.keyboardOn
                    onClicked: {
                        bar.keyboardOn = !bar.keyboardOn
                        Requests.send("osk " + (bar.keyboardOn ? "on" : "off"))
                        menu.hide()
                    }
                }
                ListRow {
                    Layout.fillWidth: true
                    focusPolicy: Qt.StrongFocus
                    text: bar.t("screenReader")
                    description: bar.t("screenReaderHint")
                    detail: bar.readerOn ? bar.t("on") : bar.t("off")
                    highlighted: bar.readerOn
                    onClicked: {
                        bar.toggleReader()
                        menu.hide()
                    }
                }
            }
        }
    }
}
