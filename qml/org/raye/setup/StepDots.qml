// Where you are in setup: a row of small dots, the current one stretched
// into a 16 px pill (250 ms). Steps done are lighter than steps to come.
//
//   StepDots { count: 5; current: 1 }
import QtQuick
import org.raye.setup

Row {
    id: dots

    property int count: 1
    property int current: 0

    spacing: 6

    Accessible.role: Accessible.Indicator
    Accessible.name: Theme.text("step").arg(current + 1).arg(count)

    Repeater {
        model: dots.count
        Rectangle {
            required property int index
            readonly property bool isCurrent: index === dots.current
            objectName: "dot" + index
            anchors.verticalCenter: parent.verticalCenter
            width: isCurrent ? 16 : 6
            height: 6
            radius: 3
            color: isCurrent ? Theme.accent
                 : index < dots.current ? Qt.alpha(Theme.textSecondary, 0.75)
                 : Qt.rgba(1, 1, 1, 0.22)
            Behavior on width { NumberAnimation { duration: Theme.durationMove; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: Theme.durationMove } }
        }
    }
}
