// The small eye of a password box, drawn in the shape of the Raye eye:
// open when the password is hidden (press to see it), struck through
// when it shows (press to hide it again).
import QtQuick
import QtQuick.Shapes

Item {
    id: eye

    property bool struck: false
    property color color: "white"

    implicitWidth: 16
    implicitHeight: 16

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        antialiasing: true

        // the almond
        ShapePath {
            strokeColor: eye.color
            strokeWidth: 1.3
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            startX: eye.width * 0.06; startY: eye.height * 0.5
            PathQuad { x: eye.width * 0.94; y: eye.height * 0.5; controlX: eye.width * 0.5; controlY: -eye.height * 0.06 }
            PathQuad { x: eye.width * 0.06; y: eye.height * 0.5; controlX: eye.width * 0.5; controlY: eye.height * 1.06 }
        }
        // the iris
        ShapePath {
            strokeColor: "transparent"
            fillColor: eye.color
            PathAngleArc {
                centerX: eye.width * 0.5; centerY: eye.height * 0.5
                radiusX: eye.width * 0.17; radiusY: eye.width * 0.17
                startAngle: 0; sweepAngle: 360
            }
        }
        // struck through
        ShapePath {
            strokeColor: eye.struck ? eye.color : "transparent"
            strokeWidth: 1.3
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            startX: eye.width * 0.16; startY: eye.height * 0.84
            PathLine { x: eye.width * 0.84; y: eye.height * 0.16 }
        }
    }
}
