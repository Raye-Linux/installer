// Raye Setup: "Choose your desktop". KDE Plasma, picked unless the person
// changes it, or Hyprland. The rayedesktop job reads answer-desktop and adds
// Hyprland to the new system; KDE Plasma stays installed either way.

import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Templates as T
import org.raye.setup
import org.raye.ui as Ui

import "../strings.js" as S
import "../components"
import "../components/Requests.js" as Requests

RayeFrame {
    id: page
    step: "desktop"
    illustration: "desktop"
    title: S.t(lang, "desktopTitle")
    text: S.t(lang, "desktopText")

    property string choice: "plasma"
    // "1": the stick carries Hyprland, "0": it is downloaded, "": nobody said
    property string offline: ""

    onShown: (backward) => {
        Requests.flags(flags => {
            if (flags.hyprland_offline !== undefined)
                page.offline = flags.hyprland_offline
        })
        save()
    }
    function save() { Requests.answer("desktop", choice) }
    function pick(name) {
        if (choice === name)
            return
        choice = name
        save()
    }

    ButtonGroup { id: picks }

    component DesktopCard: T.AbstractButton {
        id: card
        property string name
        property string line
        default property alias preview: screen.data

        checkable: true
        checked: page.choice === name
        ButtonGroup.group: picks
        implicitWidth: 240
        implicitHeight: implicitContentHeight + topPadding + bottomPadding
        hoverEnabled: true
        focusPolicy: Qt.StrongFocus
        padding: 12
        Accessible.role: Accessible.RadioButton
        Accessible.name: text
        Accessible.description: line
        Accessible.checkable: true
        Accessible.checked: checked
        Accessible.onPressAction: page.pick(name)
        onClicked: {
            checked = Qt.binding(() => page.choice === name)
            page.pick(name)
        }
        Keys.onReturnPressed: event => { page.pick(name); event.accepted = true }
        Keys.onEnterPressed: event => { page.pick(name); event.accepted = true }

        contentItem: ColumnLayout {
            spacing: 10
            // a small picture of the desktop, 16:10 like most screens
            Rectangle {
                id: screen
                Layout.fillWidth: true
                Layout.preferredHeight: Math.round(width * 10 / 16)
                radius: 6
                clip: true
                color: Qt.darker(Theme.background, 1.35)
                border.width: 1
                border.color: Theme.surfaceStroke
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                // the radio circle, as on the disk page
                Rectangle {
                    Layout.alignment: Qt.AlignTop
                    Layout.topMargin: 3
                    implicitWidth: 20
                    implicitHeight: 20
                    radius: 10
                    color: card.checked ? Theme.accent : "transparent"
                    border.width: card.checked ? 0 : 1
                    border.color: Theme.strokeStrong
                    Rectangle {
                        anchors.centerIn: parent
                        visible: card.checked
                        width: card.down ? 8 : card.hovered ? 12 : 10
                        height: width
                        radius: width / 2
                        color: Theme.textOnAccent
                        Behavior on width { NumberAnimation { duration: Theme.durationHover } }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text {
                        Layout.fillWidth: true
                        text: card.text
                        font: Theme.subtitle
                        color: Theme.textPrimary
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        text: card.line
                        font: Theme.body
                        color: Theme.textSecondary
                        wrapMode: Text.WordWrap
                    }
                }
            }
            // a card stretched to its neighbour's height keeps its words at the top
            Item { Layout.fillHeight: true }
        }

        background: Rectangle {
            radius: Theme.radiusCard
            color: card.checked ? Theme.selected
                 : card.down ? Theme.controlFillPressed
                 : card.hovered ? Theme.controlFillHover : Theme.controlFill
            border.width: 1
            border.color: card.checked ? Theme.accent : Theme.surfaceStroke
            Behavior on color { ColorAnimation { duration: Theme.durationHover } }
            Ui.FocusRing {
                target: card
                radius: Theme.radiusCard
            }
        }
    }

    // a window of the small pictures: a title strip and a body
    component MiniWindow: Rectangle {
        property bool active: false
        radius: 3
        color: Qt.lighter(Theme.surface, active ? 1.5 : 1.25)
        border.width: 1
        border.color: active ? Theme.accent : Qt.rgba(1, 1, 1, 0.10)
        Rectangle {
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 1 }
            height: Math.max(4, parent.height * 0.12)
            radius: 2
            color: Qt.rgba(1, 1, 1, 0.06)
        }
    }

    GridLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        columns: page.contentWidth >= 560 ? 2 : 1
        columnSpacing: 12
        rowSpacing: 12

        DesktopCard {
            id: plasma
            objectName: "plasmaCard"
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            // both cards as tall as the taller one, side by side
            Layout.fillHeight: parent.columns > 1
            name: "plasma"
            text: S.t(page.lang, "desktopPlasma")
            line: S.t(page.lang, "desktopPlasmaLine")

            // windows that overlap, and the taskbar with Start in the middle
            Item {
                anchors.fill: parent
                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0; color: Qt.alpha(Theme.accent, 0.20) }
                        GradientStop { position: 1; color: "transparent" }
                    }
                }
                MiniWindow {
                    x: parent.width * 0.10; y: parent.height * 0.12
                    width: parent.width * 0.52; height: parent.height * 0.52
                }
                MiniWindow {
                    active: true
                    x: parent.width * 0.36; y: parent.height * 0.26
                    width: parent.width * 0.54; height: parent.height * 0.50
                }
                Rectangle {
                    anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 1 }
                    height: parent.height * 0.13
                    color: Qt.rgba(1, 1, 1, 0.07)
                    Row {
                        anchors.centerIn: parent
                        spacing: parent.height * 0.3
                        Repeater {
                            model: 4
                            Rectangle {
                                required property int index
                                width: parent.parent.height * 0.52
                                height: width
                                radius: 2
                                color: index === 0 ? Theme.accent : Qt.rgba(1, 1, 1, 0.28)
                            }
                        }
                    }
                }
            }
        }

        DesktopCard {
            id: hyprland
            objectName: "hyprlandCard"
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            // both cards as tall as the taller one, side by side
            Layout.fillHeight: parent.columns > 1
            name: "hyprland"
            text: S.t(page.lang, "desktopHyprland")
            line: S.t(page.lang, "desktopHyprlandLine")

            // a thin bar at the top and windows tiled side by side
            Item {
                id: tiles
                anchors.fill: parent
                readonly property real gap: Math.max(3, width * 0.025)
                readonly property real below: parent.height * 0.09 + gap
                Rectangle {
                    x: tiles.gap; y: tiles.gap * 0.6
                    width: parent.width - 2 * tiles.gap
                    height: parent.height * 0.08
                    radius: height / 2
                    color: Qt.rgba(1, 1, 1, 0.07)
                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        x: parent.height * 0.4
                        width: parent.height * 0.5; height: width; radius: width / 2
                        color: Theme.accent
                    }
                }
                MiniWindow {
                    active: true
                    x: tiles.gap; y: tiles.below
                    width: (parent.width - 3 * tiles.gap) * 0.55
                    height: parent.height - tiles.below - tiles.gap
                }
                MiniWindow {
                    x: tiles.gap * 2 + (parent.width - 3 * tiles.gap) * 0.55; y: tiles.below
                    width: (parent.width - 3 * tiles.gap) * 0.45
                    height: (parent.height - tiles.below - 2 * tiles.gap) / 2
                }
                MiniWindow {
                    x: tiles.gap * 2 + (parent.width - 3 * tiles.gap) * 0.55
                    y: tiles.below + (parent.height - tiles.below - 2 * tiles.gap) / 2 + tiles.gap
                    width: (parent.width - 3 * tiles.gap) * 0.45
                    height: (parent.height - tiles.below - 2 * tiles.gap) / 2
                }
            }
        }

        Text {
            objectName: "afterLine"
            Layout.columnSpan: parent.columns
            Layout.fillWidth: true
            visible: page.choice === "hyprland"
            text: S.t(page.lang, "desktopBoth")
                  + (page.offline === "0" ? " " + S.t(page.lang, "desktopDownload") : "")
            font: Theme.body
            color: Theme.textSecondary
            wrapMode: Text.WordWrap
        }
    }
}
