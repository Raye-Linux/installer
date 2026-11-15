// A box over the whole screen the installer is on: Quit Setup, About, the
// accessibility menu. The bars are each their own small Qt Quick scene,
// so a popup drawn in one would be cut at its size: this is a window of
// its own. A click outside the box closes it; the box itself goes in as
// the content, and keeps its clicks with a MouseArea of its own.
//
//   Overlay { id: box; over: bar; Rectangle { ... } }    box.showOver()
import QtQuick
import QtQuick.Window
import org.raye.setup

Window {
    id: overlay

    // an item of the installer's window, to know which screen it is on
    property Item over
    property real dim: 0.72
    default property alias card: holder.data

    function showOver() {
        // Screen here would be this window's own: over.Screen is where
        // the installer is, which is not always the first screen
        const here = Qt.application.screens.find(s => s.name === over.Screen.name)
        if (here)
            screen = here
        x = over.Screen.virtualX
        y = over.Screen.virtualY
        width = over.Screen.width
        height = over.Screen.height
        showFullScreen()
        requestActivate()
    }

    flags: Qt.Window | Qt.FramelessWindowHint
    modality: Qt.ApplicationModal
    transientParent: null
    visible: false
    color: "transparent"

    Rectangle {
        anchors.fill: parent
        color: Theme.backgroundTop
        opacity: overlay.dim
        MouseArea {
            anchors.fill: parent
            onClicked: overlay.hide()
        }
    }
    Item {
        id: holder
        anchors.fill: parent
    }
}
