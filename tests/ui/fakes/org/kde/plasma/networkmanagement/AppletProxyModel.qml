import QtQuick
import org.kde.plasma.networkmanagement

ListModel {
    property var sourceModel
    Component.onCompleted: {
        for (const row of World.rows)
            append(row)
    }
}
