// Raye Setup: "Let's connect you to a network". The Wi-Fi list comes from
// Plasma's own network component (NetworkManager underneath), so it needs
// nothing else running in the setup session. A cable joins on its own.
// Offline, "I don't have internet" goes on without it, like Windows.
//
// Calamares runs as root, which has no secret agent: connections made here
// are system connections (etc/xdg/plasma-nm), and the new system gets them.

import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.networkmanagement as PlasmaNM
import org.raye.setup

import "../strings.js" as S
import "../components"

RayeFrame {
    id: page
    step: "network"
    illustration: "network"
    title: S.t(lang, "networkTitle")
    text: S.t(lang, "networkText")

    // NetworkManager says "full" (4) once it can reach the internet
    readonly property bool online: status.connectivity === 4
    readonly property string hint: {
        if (online) return ""
        if (status.connectivity === 2) return S.t(lang, "signInPage")
        if (status.connectivity === 3) return S.t(lang, "limited")
        if (!devices.wirelessDeviceAvailable && !devices.wiredDeviceAvailable) return S.t(lang, "noCard")
        if (!devices.wirelessDeviceAvailable) return S.t(lang, "noWifi")
        return ""
    }
    property string asking: ""      // network waiting for its key
    property string failed: ""      // network that refused the key
    // the Wi-Fi network in use, "" when there is none. The model also lists
    // the cable's connection, with no SSID: taken for Wi-Fi, it hid the line
    // saying you are online, and a PC on a cable got an empty page.
    property string wifiInUse: ""
    function noteWifi(ssid, connected) {
        if (ssid.length === 0)
            return
        if (connected)
            wifiInUse = ssid
        else if (wifiInUse === ssid)
            wifiInUse = ""
    }

    onShown: (backward) => {
        handler.requestScan()
    }

    PlasmaNM.NetworkStatus { id: status }
    PlasmaNM.AvailableDevices { id: devices }
    PlasmaNM.Handler {
        id: handler
        onConnectionActivationFailed: (path, message) => page.failed = page.asking !== "" ? page.asking : message
    }
    PlasmaNM.AppletProxyModel {
        id: networks
        sourceModel: PlasmaNM.NetworkModel {}
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // the cable, when there is one
        Rectangle {
            Layout.fillWidth: true
            visible: page.online && page.wifiInUse === ""
            implicitHeight: cable.implicitHeight + 24
            radius: Theme.radiusControl
            color: Theme.controlFill
            border.color: Theme.controlStroke
            RowLayout {
                id: cable
                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 14 }
                spacing: 12
                CablePlug {
                    objectName: "cablePlug"
                    visible: devices.wiredDeviceAvailable
                    color: Theme.accentText
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                }
                Kirigami.Icon {
                    visible: !devices.wiredDeviceAvailable
                    source: "network-connect"
                    color: Theme.accentText
                    isMask: true
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        Layout.fillWidth: true
                        visible: devices.wiredDeviceAvailable
                        text: S.t(page.lang, "wiredConnected")
                        font: Theme.bodyStrong
                        color: Theme.textPrimary
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        text: S.t(page.lang, "online")
                        font: Theme.body
                        color: devices.wiredDeviceAvailable ? Theme.textSecondary : Theme.textPrimary
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            visible: page.hint !== ""
            text: page.hint
            font: Theme.body
            color: Theme.textSecondary
            wrapMode: Text.WordWrap
        }

        Text {
            Layout.fillWidth: true
            visible: page.failed !== ""
            text: S.t(page.lang, "couldNotConnect", [page.failed])
            font: Theme.body
            color: Theme.error
            wrapMode: Text.WordWrap
        }

        ListView {
            id: wifi
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: devices.wirelessDeviceAvailable
            clip: true
            spacing: 2
            boundsBehavior: Flickable.StopAtBounds
            model: networks
            ScrollBar.vertical: ScrollBar {}
            Accessible.role: Accessible.List
            Accessible.name: "Wi-Fi"

            Text {
                anchors.centerIn: parent
                visible: wifi.count === 0
                text: S.t(page.lang, "scanning")
                font: Theme.body
                color: Theme.textTertiary
            }

            delegate: Column {
                id: row
                // the model's roles start with a capital letter, which QML
                // does not allow for property names: read them through model
                readonly property string ssid: model.Ssid
                readonly property string connectionPath: model.ConnectionPath
                readonly property string devicePath: model.DevicePath
                readonly property string specificPath: model.SpecificPath
                readonly property int connectionState: model.ConnectionState
                readonly property int securityType: model.SecurityType
                readonly property int strength: model.Signal
                readonly property bool connected: connectionState === PlasmaNM.Enums.Activated
                readonly property bool connecting: connectionState === PlasmaNM.Enums.Activating
                readonly property bool secured: securityType !== PlasmaNM.Enums.NoneSecurity
                                                && securityType !== PlasmaNM.Enums.UnknownSecurity
                readonly property bool askingHere: page.asking === ssid

                // only Wi-Fi networks: wired ones have no SSID
                visible: ssid.length > 0
                height: visible ? implicitHeight : 0
                width: ListView.view.width
                spacing: 6
                onConnectedChanged: page.noteWifi(ssid, connected)
                Component.onCompleted: page.noteWifi(ssid, connected)
                Component.onDestruction: if (connected) page.noteWifi(ssid, false)

                function join(key) {
                    page.failed = ""
                    if (connectionPath.length > 0)
                        handler.activateConnection(connectionPath, devicePath, specificPath)
                    else
                        handler.addAndActivateConnection(devicePath, specificPath, key)
                }

                ListRow {
                    width: parent.width
                    text: row.ssid
                    description: row.connected ? S.t(page.lang, "connected")
                               : row.connecting ? S.t(page.lang, "connecting")
                               : row.secured ? S.t(page.lang, "secured") : S.t(page.lang, "open")
                    highlighted: row.connected || row.askingHere
                    Accessible.name: row.ssid + ", " + description
                    onClicked: {
                        if (row.connected)
                            return
                        if (row.secured && row.connectionPath.length === 0) {
                            page.asking = row.ssid
                            key.forceActiveFocus()
                        } else {
                            page.asking = ""
                            row.join("")
                        }
                    }

                    // signal bars on the right
                    Row {
                        anchors.right: parent.right
                        anchors.rightMargin: 14
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2
                        Repeater {
                            model: 4
                            Rectangle {
                                required property int index
                                anchors.bottom: parent.bottom
                                width: 3
                                height: 4 + index * 3
                                radius: 1
                                color: row.strength > index * 25 ? Theme.textPrimary : Theme.textDisabled
                            }
                        }
                    }
                }

                RowLayout {
                    visible: row.askingHere
                    width: parent.width
                    spacing: 8
                    PasswordField {
                        id: key
                        Layout.fillWidth: true
                        placeholderText: S.t(page.lang, "wifiPassword")
                        Accessible.name: placeholderText
                        onAccepted: if (key.text.length >= 8) joinButton.clicked()
                    }
                    PrimaryButton {
                        id: joinButton
                        text: S.t(page.lang, "connect")
                        enabled: key.text.length >= 8
                        onClicked: {
                            row.join(key.text)
                            key.text = ""
                        }
                    }
                }
            }
        }

        Item {
            Layout.fillHeight: true
            visible: !wifi.visible
        }

        LinkButton {
            visible: !page.online
            text: S.t(page.lang, "noInternet")
            onClicked: ViewManager.next()
        }
    }
}
