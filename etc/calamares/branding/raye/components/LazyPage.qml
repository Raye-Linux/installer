// What Calamares loads for each Raye Setup page: nothing but this. The page
// itself is created the first time its step comes on screen, and stays.
//
// Calamares gives every page a QML engine of its own and loads them all at
// start, on as many threads. A dozen engines compiling the setup look and
// creating its shared singletons (Theme, Tokens) at the same time crashed
// Calamares in Qt's loader, once in three or four starts. One page at a
// time never does, and a page nobody reaches costs nothing.
import QtQuick
import io.calamares.ui 1.0

import "../strings.js" as S

Loader {
    // the step's name in strings.js (steps)
    property string step
    readonly property int index: S.steps.indexOf(step)

    active: false
    asynchronous: false

    function arrive() {
        if (ViewManager.currentStepIndex === index)
            active = true
    }
    Connections {
        target: ViewManager
        function onCurrentStepChanged() { arrive() }
    }
    Component.onCompleted: arrive()
}
