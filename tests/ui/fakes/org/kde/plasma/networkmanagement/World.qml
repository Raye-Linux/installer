// What the fake NetworkManager says: a test sets this before it loads the
// page. rows carries the same roles as Plasma's NetworkModel. The cable's
// connection is in that model too, with an empty Ssid.
pragma Singleton
import QtQuick

QtObject {
    property int connectivity: 0
    property bool wireless: false
    property bool wired: false
    property var rows: []
}
