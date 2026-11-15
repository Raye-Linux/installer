// The Raye busy ring, the same as on the boot screen and the sign-in
// screens: one arc on a faint track that grows, shrinks and turns all the
// time, violet at the tail to magenta at the head, one loop in 2 s. With
// reduced motion it stands still as a long arc.
//
// Give it a value (0 to 1) and it becomes a ring that fills up (the
// restart countdown, for instance).
//
//   ProgressRing { }                         // busy
//   ProgressRing { size: 64; value: 0.4 }    // 40 %
import QtQuick
import QtQuick.Shapes
import org.raye.setup

Item {
    id: ring

    property real size: 40
    // below 0: busy, no known end; 0 to 1: how far along
    property real value: -1
    property bool running: visible

    readonly property bool busy: value < 0
    readonly property bool orbiting: busy && running && !Theme.reducedMotion
    // reduced motion: the arc is drawn, held still
    readonly property bool pulsing: busy && running && Theme.reducedMotion

    implicitWidth: size
    implicitHeight: size

    Accessible.role: Accessible.ProgressBar
    Accessible.name: Theme.text("busy")
    Accessible.description: busy ? "" : Math.round(value * 100) + " %"

    // --- busy: the arc ----------------------------------------------------
    // Same numbers as theme/art/plymouth.py and the sign-in Spinner: the
    // head gains 270 degrees over the first 60 % of the loop, the tail over
    // the last 60 %, with cubic-bezier(0.6, 0, 0.3, 1), and the ring turns
    // 1.25 times on top of that.
    property real phase: 0.45

    NumberAnimation on phase {
        from: 0
        to: 1
        duration: 2000
        loops: Animation.Infinite
        running: ring.orbiting
    }

    function ease(x) {
        if (x <= 0) return 0
        if (x >= 1) return 1
        let lo = 0, hi = 1, t = 0.5
        for (let i = 0; i < 20; i++) {
            t = (lo + hi) / 2
            const bx = 1.8 * t * (1 - t) * (1 - t) + 0.9 * t * t * (1 - t) + t * t * t
            if (bx < x) lo = t
            else hi = t
        }
        return 3 * t * t * (1 - t) + t * t * t
    }

    readonly property real lineWidth: Math.max(2, Math.round(size * 0.21) / 2)
    readonly property real _turn: 450 * phase
    readonly property real _head: _turn + 12 + 270 * ease(phase / 0.6)
    readonly property real _tail: _turn + 270 * ease((phase - 0.4) / 0.6)
    readonly property real _len: _head - _tail
    readonly property real _c: size / 2
    readonly property real _outer: size / 2
    readonly property real _inner: size / 2 - lineWidth
    readonly property real _cap: lineWidth / 2 / (size / 2 - lineWidth / 2) * 180 / Math.PI

    function _x(r, deg) { return _c + r * Math.sin(deg * Math.PI / 180) }
    function _y(r, deg) { return _c - r * Math.cos(deg * Math.PI / 180) }

    Shape {
        visible: ring.busy
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            fillColor: "transparent"
            strokeColor: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.16)
            strokeWidth: ring.lineWidth
            PathAngleArc {
                centerX: ring._c; centerY: ring._c
                radiusX: ring._outer - ring.lineWidth / 2; radiusY: radiusX
                startAngle: 0; sweepAngle: 360
            }
        }

        // filled, not stroked, so the colour can run along it
        ShapePath {
            strokeColor: "transparent"
            strokeWidth: -1
            fillGradient: ConicalGradient {
                centerX: ring._c; centerY: ring._c
                angle: 90 - ring._head - ring._cap
                GradientStop { position: 0; color: Theme.accentText }
                GradientStop { position: ring._cap / 360; color: Theme.accentText }
                GradientStop { position: (ring._cap + ring._len) / 360; color: Theme.accent }
                GradientStop { position: 1; color: Theme.accent }
            }
            PathAngleArc {
                centerX: ring._c; centerY: ring._c
                radiusX: ring._outer; radiusY: ring._outer
                startAngle: ring._tail - 90; sweepAngle: ring._len
            }
            PathArc {
                x: ring._x(ring._inner, ring._head); y: ring._y(ring._inner, ring._head)
                radiusX: ring.lineWidth / 2; radiusY: ring.lineWidth / 2
            }
            PathAngleArc {
                centerX: ring._c; centerY: ring._c
                radiusX: ring._inner; radiusY: ring._inner
                startAngle: ring._head - 90; sweepAngle: -ring._len
                moveToStart: false
            }
            PathArc {
                x: ring._x(ring._outer, ring._tail); y: ring._y(ring._outer, ring._tail)
                radiusX: ring.lineWidth / 2; radiusY: ring.lineWidth / 2
            }
        }
    }

    // --- value: a ring that fills ---------------------------------------
    Shape {
        id: arc
        visible: !ring.busy
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        readonly property real stroke: Math.max(3, ring.size * 0.08)
        readonly property real r: (ring.size - stroke) / 2

        ShapePath {
            strokeColor: Qt.rgba(1, 1, 1, 0.10)
            strokeWidth: arc.stroke
            fillColor: "transparent"
            PathAngleArc {
                centerX: ring.size / 2; centerY: ring.size / 2
                radiusX: arc.r; radiusY: arc.r
                startAngle: 0; sweepAngle: 360
            }
        }
        ShapePath {
            strokeColor: Theme.accent
            strokeWidth: arc.stroke
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            PathAngleArc {
                centerX: ring.size / 2; centerY: ring.size / 2
                radiusX: arc.r; radiusY: arc.r
                startAngle: -90
                sweepAngle: 360 * Math.max(0, Math.min(1, ring.value))
            }
        }
    }
}
