// Stands in for Calamares' ViewManager in tests/ui/tst_pages.qml.
pragma Singleton
import QtQuick

QtObject {
    property int currentStepIndex: 0
    property string nextLabel: ""
    property string backLabel: "&Back"
    property bool backAndNextVisible: true
    property bool backEnabled: true
    property bool nextEnabled: true
    signal currentStepChanged()
    property int nextCalls: 0
    function next() { nextCalls += 1 }
    function back() {}
}
