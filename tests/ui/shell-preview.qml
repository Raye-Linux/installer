// A whole Raye Setup screen in a window: the top bar, one page and the
// bottom bar, the way Calamares stacks them, against the fakes of
// page-preview.qml. For looking at the setup, not for testing it:
//   tests/ui/run-shell-preview.sh <Page.qml> <step> <scenario> [LANG]
import QtQuick
import QtQuick.Window
import io.calamares.core 1.0

Window {
    id: win
    readonly property var args: Qt.application.arguments
    width: Screen.width
    height: Screen.height
    visible: true
    color: "black"

    Column {
        anchors.fill: parent
        Loader {
            id: top
            width: parent.width
            source: "../../etc/calamares/branding/raye/calamares-sidebar.qml"
        }
        Item {
            id: middle
            width: parent.width
            height: win.height - top.height - bottom.height
        }
        Loader {
            id: bottom
            width: parent.width
            source: "../../etc/calamares/branding/raye/calamares-navigation.qml"
        }
    }
    Component.onCompleted: {
        const preview = Qt.createComponent("page-preview.qml").createObject(null, { visible: false })
        // the page is moved out of the preview's window into the middle
        const page = preview.contentItem.children[0]
        page.parent = middle
        page.anchors.fill = middle
        fill.page = page.item
        fill.start()
    }

    function find(item, name) {
        if (!item)
            return null
        if (item.objectName === name)
            return item
        for (let i = 0; i < item.children.length; ++i) {
            const found = find(item.children[i], name)
            if (found)
                return found
        }
        if (item.contentItem && item.contentItem !== item)
            return find(item.contentItem, name)
        return null
    }

    // what a person would have typed by the time of the picture
    Timer {
        id: fill
        property var page
        interval: 300
        onTriggered: {
            const scenario = win.args[win.args.length - 1]
            if (page && "report" in page) {
                const gib = 1024 * 1024 * 1024
                page.report = { firmware: "efi", disks: [{
                    node: "/dev/sda", model: "QEMU HARDDISK", size: 64 * gib, sector: 512, first: 2048,
                    last: 64 * gib / 512 - 34, id: "a", empty: true, parts: [], blocked: "", refused: [],
                    options: [{ mode: "erase" }] }] }
                page.scanning = false
                page.choose(0)
            }
            const encrypt = win.find(page, "encrypt")
            if (encrypt && scenario !== "plain")
                encrypt.checked = true
            const typed = { password: "correct horse", passwordAgain: scenario === "mismatch" ? "correct hose" : "correct horse",
                            fullName: "Test Raye" }
            for (const name in typed) {
                const field = win.find(page, name)
                if (field)
                    field.text = typed[name]
            }
        }
    }
}
