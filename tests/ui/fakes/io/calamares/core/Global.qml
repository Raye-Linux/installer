// Stands in for Calamares' GlobalStorage in tests/ui/tst_pages.qml.
pragma Singleton
import QtQuick

QtObject {
    property var values: ({})
    function value(key) { return values[key] }
    function contains(key) { return values[key] !== undefined }
}
