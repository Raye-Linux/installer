import QtQuick
import org.kde.plasma.networkmanagement

QtObject {
    readonly property bool wirelessDeviceAvailable: World.wireless
    readonly property bool wiredDeviceAvailable: World.wired
}
