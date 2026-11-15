// One page of Raye Setup in a window, against the fakes tst_pages.qml uses:
//   tests/ui/run-page-preview.sh <Page.qml> <step> <scenario> [LANG]
// Scenarios: cable, wifi, offline, encrypted, plain.
import QtQuick
import QtQuick.Window
import io.calamares.core 1.0
import org.kde.plasma.networkmanagement as PlasmaNM

import "../../etc/calamares/branding/raye/strings.js" as S

Window {
    id: win
    readonly property var args: Qt.application.arguments
    readonly property string file: args[args.length - 3]
    readonly property string step: args[args.length - 2]
    readonly property string scenario: args[args.length - 1]
    width: Screen.width
    height: Screen.height
    visible: true
    color: "black"

    property var config: QtObject {
        property var summaryModel: entries
        property var languagesModel: languages
        property int localeIndex: 0
        property var requirementsModel: QtObject {
            property bool satisfiedRequirements: true
            property bool satisfiedMandatory: true
        }
    }
    ListModel { id: entries }
    ListModel {
        id: languages
        ListElement { label: "American English"; englishLabel: "English" }
        ListElement { label: "français"; englishLabel: "French" }
    }

    readonly property string encrypted:
        "<strong>Erase</strong> disk <strong>/dev/sda</strong> (QEMU HARDDISK) and install Raye 0.1 Beta<br/>"
        + "Creating new <strong>GPT</strong> partition table on <strong>/dev/sda</strong> (QEMU HARDDISK)...<br/>"
        + "Create new <strong>1024MiB</strong> partition on <strong>/dev/sda</strong> (QEMU HARDDISK) with entries EFI<br/>"
        + "Set flags on 1024MiB <strong>fat32</strong> partition to <strong>boot</strong><br/>"
        + "Create new <strong>2048MiB</strong> partition on <strong>/dev/sda</strong> (QEMU HARDDISK) with entries raye_boot<br/>"
        + "Create new <strong>62461MiB</strong> partition on <strong>/dev/sda</strong> (QEMU HARDDISK) with entries raye<br/>"
        + "Install Raye on <strong>new</strong> btrfs system partition"
    readonly property string plain:
        "<strong>Erase</strong> disk <strong>/dev/sda</strong> (QEMU HARDDISK) and install Raye 0.1 Beta<br/>"
        + "Create new <strong>63485MiB</strong> partition on <strong>/dev/sda</strong> (QEMU HARDDISK) with entries raye"

    Loader {
        id: loader
        anchors.fill: parent
        onLoaded: {
            // what the disk and keyboard pages leave for "Ready to install"
            if ("keyboard" in item)
                item.keyboard = "English (US)"
            if ("diskLabel" in item) {
                item.install = "erase"
                item.diskLabel = "QEMU HARDDISK (/dev/sda)"
                item.encrypted = win.scenario !== "plain"
                item.diskDetails = "Everything on QEMU HARDDISK (/dev/sda) is deleted."
            }
        }
    }

    Component.onCompleted: {
        const wired = { Ssid: "", ConnectionPath: "/c/1", DevicePath: "/d/1", SpecificPath: "",
                        ConnectionState: 2, SecurityType: 0, Signal: 0 }
        const home = { Ssid: "Home", ConnectionPath: "/c/2", DevicePath: "/d/2", SpecificPath: "/ap/1",
                       ConnectionState: 2, SecurityType: 2, Signal: 80 }
        const other = { Ssid: "Cafe", ConnectionPath: "", DevicePath: "/d/2", SpecificPath: "/ap/2",
                        ConnectionState: 0, SecurityType: 0, Signal: 40 }
        if (scenario === "cable") {
            PlasmaNM.World.connectivity = 4; PlasmaNM.World.wired = true; PlasmaNM.World.rows = [wired]
        } else if (scenario === "wifi") {
            PlasmaNM.World.connectivity = 4; PlasmaNM.World.wireless = true; PlasmaNM.World.wired = true
            PlasmaNM.World.rows = [wired, home, other]
        } else if (scenario === "offline") {
            PlasmaNM.World.connectivity = 1; PlasmaNM.World.wired = true; PlasmaNM.World.rows = [wired]
        }
        entries.append({ title: "Partitions", message: scenario === "plain" ? plain : encrypted })
        Global.values = ({ partitionChoices: { install: "erase" }, locationRegion: "America",
                           locationZone: "Toronto", fullname: "Test Raye", hostname: "raye-test" })
        ViewManager.currentStepIndex = S.steps.indexOf(step)
        loader.source = "../../etc/calamares/branding/raye/pages/" + file
    }
}
