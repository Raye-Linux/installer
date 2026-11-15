import QtQuick

QtObject {
    signal connectionActivationFailed(string path, string message)
    function requestScan() {}
    function activateConnection(path, device, specific) {}
    function addAndActivateConnection(device, specific, key) {}
}
