// One page of Raye Setup in a window, against the fakes tst_pages.qml uses:
//   tests/ui/run-page-preview.sh <Page.qml> <step> <scenario> [LANG]
// Scenarios: cable, wifi, offline, encrypted, plain; for Disk.qml linux,
// linux-ask (the "Delete ...?" box), linux-shrink, bios, keep, keep-ask,
// keep-home, keep-room and keep-picked; for Done.qml keep-done, keep-left and
// desktop-fallback; for Desktop.qml hyprland and hyprland-online.
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
        // the last page: an install that went through
        property bool failed: false
        function doRestart(now) {}
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
            if ("report" in item)
                win.showDisks(item)
            if ("keepText" in item && win.scenario === "keep-done")
                item.keepText = '{"way":"stage","name":"Linux Mint 22","ok":true}'
            if ("desktopResult" in item && win.scenario === "desktop-fallback")
                item.desktopResult = "plasma-fallback"
            if ("offline" in item && win.scenario.indexOf("hyprland") === 0) {
                item.choice = "hyprland"
                item.offline = win.scenario === "hyprland-online" ? "0" : "1"
            }
            if ("keepText" in item && win.scenario === "keep-left")
                item.keepText = '{"way":"stage","name":"Linux Mint 22","ok":false,"left":true}'
            if ("diskLabel" in item) {
                item.install = "erase"
                item.diskLabel = "QEMU HARDDISK (/dev/sda)"
                item.encrypted = win.scenario !== "plain"
                item.diskDetails = "Everything on QEMU HARDDISK (/dev/sda) is deleted."
            }
        }
    }

    readonly property real gib: 1024 * 1024 * 1024
    function showDisks(page) {
        const linux = { node: "/dev/nvme0n1", model: "Samsung SSD 980", size: 500 * gib, sector: 512, first: 2048,
                        last: 500 * gib / 512 - 34, id: "a", empty: false, blocked: "",
                        parts: [{ node: "/dev/nvme0n1p1", start: 2048, sectors: gib / 512, fstype: "vfat" },
                                { node: "/dev/nvme0n1p2", start: 2048 + gib / 512, sectors: 380 * gib / 512, fstype: "btrfs", os: "Arch Linux" },
                                { node: "/dev/nvme0n1p3", start: 2048 + 381 * gib / 512, sectors: 100 * gib / 512, fstype: "xfs", os: "Fedora Linux" }],
                        options: [{ mode: "shrink", node: "/dev/nvme0n1p2", name: "Arch Linux", fstype: "btrfs",
                                    total: 380 * gib, keepMin: 60 * gib, keepMax: 350 * gib, keepDefault: 190 * gib },
                                  { mode: "free", start: 2048 + 481 * gib / 512, bytes: 18 * gib },
                                  { mode: "replace", node: "/dev/nvme0n1p2", name: "Arch Linux", fstype: "btrfs", bytes: 380 * gib },
                                  { mode: "replace", node: "/dev/nvme0n1p3", name: "Fedora Linux", fstype: "xfs", bytes: 100 * gib },
                                  { mode: "erase" }],
                        refused: [{ mode: "shrink", node: "/dev/nvme0n1p3", name: "Fedora Linux", finding: "xfs" }] }
        const old = { node: "/dev/sda", model: "WDC WD5000", size: 500 * gib, sector: 512, first: 2048,
                      last: 500 * gib / 512 - 1, id: "b", empty: false, blocked: "", table: "dos",
                      parts: [{ node: "/dev/sda1", start: 2048, sectors: gib / 1024, fstype: "ntfs", label: "System Reserved" },
                              { node: "/dev/sda2", start: 2048 + gib / 1024, sectors: 499 * gib / 512, fstype: "ntfs", os: "Windows" }],
                      options: [{ mode: "shrink", node: "/dev/sda2", name: "Windows", fstype: "ntfs",
                                  total: 499 * gib, keepMin: 80 * gib, keepMax: 470 * gib, keepDefault: 250 * gib },
                                { mode: "replace", node: "/dev/sda2", name: "Windows", fstype: "ntfs", bytes: 499 * gib },
                                { mode: "erase" }],
                      refused: [] }
        const mintUsers = [{ name: "alice", folders: [
                               { kind: "desktop", files: 12, bytes: 0.2 * gib },
                               { kind: "documents", files: 1204, bytes: 3.2 * gib },
                               { kind: "downloads", files: 87, bytes: 6.4 * gib },
                               { kind: "music", files: 2310, bytes: 14.9 * gib },
                               { kind: "pictures", files: 8402, bytes: 41.6 * gib },
                               { kind: "videos", files: 64, bytes: 22.5 * gib }] }]
        const mint = { node: "/dev/nvme0n1", model: "Samsung SSD 980", size: 500 * gib, sector: 512, first: 2048,
                       last: 500 * gib / 512 - 34, id: "c", empty: false, blocked: "",
                       parts: [{ node: "/dev/nvme0n1p1", start: 2048, sectors: gib / 512, fstype: "vfat" },
                               { node: "/dev/nvme0n1p2", start: 2048 + gib / 512, sectors: 499 * gib / 512, fstype: "ext4", os: "Linux Mint 22" }],
                       options: [{ mode: "shrink", node: "/dev/nvme0n1p2", name: "Linux Mint 22", fstype: "ext4",
                                   total: 499 * gib, keepMin: 120 * gib, keepMax: 470 * gib, keepDefault: 250 * gib },
                                 { mode: "keep", way: "stage", node: "/dev/nvme0n1p2", name: "Linux Mint 22", fstype: "ext4",
                                   bytes: 499 * gib, users: mintUsers, files: 12079, size: 88.8 * gib },
                                 { mode: "replace", node: "/dev/nvme0n1p2", name: "Linux Mint 22", fstype: "ext4", bytes: 499 * gib },
                                 { mode: "erase" }],
                       refused: [] }
        const homeUsers = [mintUsers[0], { name: "sam", folders: [{ kind: "documents", files: 310, bytes: 1.1 * gib },
                                                                  { kind: "pictures", files: 920, bytes: 7.3 * gib }] }]
        const split = { node: "/dev/sda", model: "Crucial MX500", size: 1000 * gib, sector: 512, first: 2048,
                        last: 1000 * gib / 512 - 34, id: "d", empty: false, blocked: "",
                        parts: [{ node: "/dev/sda1", start: 2048, sectors: gib / 512, fstype: "vfat" },
                                { node: "/dev/sda2", start: 2048 + gib / 512, sectors: 80 * gib / 512, fstype: "btrfs", os: "Arch Linux" },
                                { node: "/dev/sda3", start: 2048 + 81 * gib / 512, sectors: 919 * gib / 512, fstype: "ext4", label: "home" }],
                        options: [{ mode: "keep", way: "home", node: "/dev/sda2", name: "Arch Linux", fstype: "btrfs", bytes: 80 * gib,
                                    home: "/dev/sda3", homeFs: "ext4", users: homeUsers, files: 13309, size: 97.2 * gib },
                                  { mode: "replace", node: "/dev/sda2", name: "Arch Linux", fstype: "btrfs", bytes: 80 * gib },
                                  { mode: "erase" }],
                        refused: [] }
        const full = Object.assign({}, mint, { id: "e", size: 256 * gib, last: 256 * gib / 512 - 34,
                        options: [mint.options[0], mint.options[2], { mode: "erase" }],
                        refused: [{ mode: "keep", node: "/dev/nvme0n1p2", name: "Linux Mint 22", reason: "room",
                                    needed: 212.4 * gib, have: 255 * gib - 50 * gib }] })
        let shown = scenario === "bios" ? old : linux
        if (scenario.indexOf("keep") === 0)
            shown = scenario === "keep-home" ? split : scenario === "keep-room" ? full : mint
        page.report = { firmware: scenario === "bios" ? "bios" : "efi", disks: [shown] }
        page.scanning = false
        page.choose(0)
        if (scenario === "linux-ask")
            page.ask(2)
        if (scenario === "linux-shrink") {
            page.pick(0)
        }
        if (scenario === "keep-ask")
            page.ask(1)
        if (scenario === "keep-home")
            page.ask(0)
        if (scenario === "keep-picked")
            page.pick(1)
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
