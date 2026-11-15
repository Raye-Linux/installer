// The way a setup page comes in: its content slides 40 px in from the
// right and fades in (250 ms, eased like Windows), or from the left when
// the page is reached with Back. It fades out in 167 ms when it leaves.
// With reduced motion, fades only.
//
//   PageEnter {
//       id: enter
//       anchors.fill: parent
//       backward: navigation.wentBack
//       // the page's content
//   }
//
// It plays by itself when it is created and each time it becomes
// visible (autoPlay); enter(backward) and leave() play it by hand.
import QtQuick
import org.raye.setup

Item {
    id: root

    default property alias content: holder.data
    property bool backward: false
    property bool autoPlay: true
    readonly property bool running: entering.running || leaving.running
    // where the content is now, for tests and for pages that need it
    readonly property real offset: shift.x

    signal enterFinished()
    signal leaveFinished()

    function enter(back) {
        leaving.stop()
        const from = Theme.reducedMotion ? 0 : (back ? -Theme.slide : Theme.slide)
        shift.x = from
        holder.opacity = 0
        slideIn.from = from
        entering.restart()
    }

    function leave() {
        entering.stop()
        leaving.restart()
    }

    onVisibleChanged: if (visible && autoPlay) enter(backward)
    Component.onCompleted: if (visible && autoPlay) enter(backward)

    Item {
        id: holder
        width: root.width
        height: root.height
        transform: Translate { id: shift }
    }

    ParallelAnimation {
        id: entering
        NumberAnimation {
            id: slideIn
            target: shift; property: "x"; to: 0
            duration: Theme.durationEnter
            easing.type: Easing.BezierSpline
            easing.bezierCurve: Theme.bezierEnter
        }
        NumberAnimation {
            target: holder; property: "opacity"; to: 1
            duration: Theme.durationEnter
            easing.type: Easing.OutCubic
        }
        onFinished: root.enterFinished()
    }

    NumberAnimation {
        id: leaving
        target: holder; property: "opacity"; to: 0
        duration: Theme.durationExit
        easing.type: Easing.InCubic
        onFinished: root.leaveFinished()
    }
}
