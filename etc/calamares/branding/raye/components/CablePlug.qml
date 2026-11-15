// A network cable plug, drawn in lines on a 24 px grid. The icon theme's
// "network-wired" is a screen, which read as "Connected with a display".
import QtQuick
import QtQuick.Shapes

Item {
    id: plug
    property color color: "white"
    property real lineWidth: 1.6
    implicitWidth: 24
    implicitHeight: 24

    Shape {
        anchors.centerIn: parent
        width: 24
        height: 24
        scale: Math.min(plug.width, plug.height) / 24
        preferredRendererType: Shape.CurveRenderer

        // the plug, its latch at the top
        ShapePath {
            strokeColor: plug.color
            strokeWidth: plug.lineWidth
            fillColor: "transparent"
            joinStyle: ShapePath.RoundJoin
            capStyle: ShapePath.RoundCap
            startX: 6; startY: 5
            PathLine { x: 9.5; y: 5 }
            PathLine { x: 9.5; y: 3 }
            PathLine { x: 14.5; y: 3 }
            PathLine { x: 14.5; y: 5 }
            PathLine { x: 18; y: 5 }
            PathLine { x: 18; y: 13 }
            PathLine { x: 6; y: 13 }
            PathLine { x: 6; y: 5 }
        }
        // the contacts
        ShapePath {
            strokeColor: plug.color
            strokeWidth: plug.lineWidth
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            startX: 9.5; startY: 8
            PathLine { x: 9.5; y: 10 }
            PathMove { x: 12; y: 8 }
            PathLine { x: 12; y: 10 }
            PathMove { x: 14.5; y: 8 }
            PathLine { x: 14.5; y: 10 }
        }
        // the boot and the cable leaving it
        ShapePath {
            strokeColor: plug.color
            strokeWidth: plug.lineWidth
            fillColor: "transparent"
            joinStyle: ShapePath.RoundJoin
            capStyle: ShapePath.RoundCap
            startX: 9; startY: 13
            PathLine { x: 9.5; y: 16.5 }
            PathLine { x: 14.5; y: 16.5 }
            PathLine { x: 15; y: 13 }
            PathMove { x: 12; y: 16.5 }
            PathQuad { x: 15; y: 21.5; controlX: 12; controlY: 21 }
        }
    }
}
