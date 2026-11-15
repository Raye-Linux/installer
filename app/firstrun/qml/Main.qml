// The window of raye-first-run: full screen, the Raye night behind it,
// and today one page -- the disk recovery key. The other pages of the
// welcome (privacy, look, account picture) land later; this file is where
// they are strung together.
//
// Nothing here reads or writes a file: Keeper does, so the page and this
// window can be opened with a fake key and no home folder.
import QtQuick
import QtQuick.Window
import QtQuick.Dialogs
import org.raye.setup

import "words.js" as W

Window {
    id: window

    visibility: Window.FullScreen
    visible: true
    color: Theme.backgroundTop
    title: W.t(page.lang, "heading")

    RecoveryKeyPage {
        id: page
        anchors.fill: parent
        key: Keeper.readKey()

        onSaveWanted: save.open()
        onFinished: {
            Keeper.markSaved()
            Qt.quit()
        }
        // Not stamped: the page comes back at the next sign-in, which is
        // the point of "Later".
        onPostponed: Qt.quit()
    }

    FileDialog {
        id: save
        title: W.t(page.lang, "save")
        fileMode: FileDialog.SaveFile
        currentFolder: Keeper.documentsFolder()
        selectedFile: Keeper.documentsFolder() + "/" + Keeper.suggestedName()
        nameFilters: [W.t(page.lang, "fileKind")]
        defaultSuffix: "txt"
        onAccepted: Keeper.saveCopy(selectedFile, page.grouped, W.t(page.lang, "why"))
    }
}
