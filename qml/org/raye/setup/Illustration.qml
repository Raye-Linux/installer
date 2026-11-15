// One of the setup pictures. It holds still: the page moves when it comes
// in, the picture does not. Names: Theme.illustrationNames.
//
//   Illustration { name: "network"; size: 280 }
//
// The pictures live next to this file (illustrations/), drawn at 1x and
// 2x; the 2x one is used when the screen needs more pixels than 1x has.
import QtQuick
import QtQuick.Window
import org.raye.setup

Item {
    id: root

    property string name
    property real size: 240
    readonly property bool known: Theme.illustrationNames.indexOf(name) >= 0
    readonly property bool hidpi: size * Screen.devicePixelRatio > 320
    readonly property alias status: lines.status

    implicitWidth: size
    implicitHeight: size
    Accessible.ignored: true

    onNameChanged: if (name !== "" && !known) console.warn("Illustration: no picture named", name)

    Image {
        id: lines
        objectName: "lines"
        width: root.size
        height: root.size
        anchors.centerIn: parent
        source: root.known ? Qt.resolvedUrl("illustrations/" + root.name + (root.hidpi ? "@2x" : "") + ".png") : ""
        sourceSize.width: root.hidpi ? 640 : 320
        sourceSize.height: root.hidpi ? 640 : 320
        smooth: true
        mipmap: true
    }
}
