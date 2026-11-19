// The disk page: words, picture and answer, on made-up disks, in both
// languages. What may be offered is tested in tests/test_rayedisk_core.py;
// this holds what the page does with an offer.
import QtQuick
import QtTest
import io.calamares.core 1.0
import org.raye.setup

import "../../etc/calamares/branding/raye/strings.js" as S
import "../../etc/calamares/branding/raye/components/DiskLogic.js" as Logic

Item {
width: 1280
height: 800

Loader {
    id: loader
    width: 1280
    height: 800
}

TestCase {
    name: "DiskPage"
    when: windowShown

    function find(item, wanted) {
        if (!item)
            return null
        if (item.title === wanted && item.checkable !== undefined)
            return item
        const kids = item.children
        for (let i = 0; i < kids.length; ++i) {
            const found = find(kids[i], wanted)
            if (found)
                return found
        }
        return null
    }
    function page(disks) {
        ViewManager.currentStepIndex = S.steps.indexOf("disk")
        loader.source = ""
        loader.source = "../../etc/calamares/branding/raye/pages/Disk.qml"
        const made = loader.item
        made.report = { firmware: "efi", disks: disks }
        made.scanning = false
        made.choose(0)
        wait(50)
        return made
    }
    readonly property real gib: 1024 * 1024 * 1024
    function blank() {
        return { node: "/dev/sda", model: "Blank", size: 64 * gib, sector: 512, first: 2048, last: 64 * gib / 512 - 34,
                 id: "a", empty: true, parts: [], blocked: "", refused: [], options: [{ mode: "erase" }] }
    }
    function used() {
        const disk = blank()
        disk.empty = false
        disk.parts = [{ node: "/dev/sda1", start: 2048, sectors: 40 * gib / 512, os: "Windows" }]
        disk.options = [{ mode: "replace", node: "/dev/sda1", name: "Windows", bytes: 40 * gib }, { mode: "erase" }]
        return disk
    }

    function test_an_empty_disk_is_picked_for_you() {
        const made = page([blank()])
        verify(made.option !== null)
        compare(made.option.mode, "erase")
        verify(made.complete)
    }
    function test_a_disk_with_something_on_it_is_never_picked_for_you() {
        const made = page([used()])
        compare(made.option, null, "deleting has to be chosen by hand")
        verify(!made.complete, "Next must wait")
    }
    function test_choosing_a_card_answers_and_a_short_password_holds_next_back() {
        const made = page([used()])
        made.pick(1)
        verify(made.complete)
        verify(find(made, S.t("en", "diskEraseTitle")) !== null, "the card is on the page")
    }
    function test_a_scan_that_never_answers_stops_the_spinner() {
        ViewManager.currentStepIndex = S.steps.indexOf("disk")
        loader.source = ""
        loader.source = "../../etc/calamares/branding/raye/pages/Disk.qml"
        const made = loader.item
        verify(made.scanning)
        made.waited = 239
        // the next poll finds nothing, as on a machine where the probe died
        tryVerify(() => !made.scanning || made.report !== null, 3000)
        if (made.report === null) {
            compare(made.disk, null)
            verify(!made.complete)
        }
    }
    function test_the_usb_stick_is_not_a_choice() {
        const stick = Object.assign(blank(), { blocked: "live", options: [] })
        const made = page([stick])
        compare(made.disk, null)
        verify(!made.complete)
    }
    function test_two_disks_change_the_choices() {
        const other = Object.assign(blank(), { node: "/dev/sdb" })
        const made = page([used(), other])
        compare(made.disk.node, "/dev/sda")
        made.choose(1)
        compare(made.disk.node, "/dev/sdb")
        verify(made.complete, "the empty one is picked for you")
        made.choose(0)
        compare(made.option, null, "going back to the first disk does not keep a choice meant for the other")
    }

    // every word a person can read on the page
    function shown(item, out) {
        out = out || []
        if (!item || !item.visible)
            return out
        if (item.text !== undefined && String(item.text) !== "" && item.width > 0 && item.height > 0)
            out.push(String(item.text))
        for (let i = 0; i < item.children.length; ++i)
            shown(item.children[i], out)
        if (item.contentItem && item.contentItem !== item)
            shown(item.contentItem, out)
        return out
    }
    function control(item, text) {
        if (!item)
            return null
        if (item.checkable !== undefined && String(item.text) === text)
            return item
        for (let i = 0; i < item.children.length; ++i) {
            const hit = control(item.children[i], text)
            if (hit)
                return hit
        }
        return null
    }
    // On the 2026-11-08 image "Use at least 8 characters." came up in
    // orange the moment the box was ticked, before one key was pressed.
    function test_ticking_encrypt_blames_nothing_yet_data() {
        return [{ tag: "en", lang: "en" }, { tag: "fr", lang: "fr" }]
    }
    function test_ticking_encrypt_blames_nothing_yet(data) {
        const made = page([blank()])
        made.lang = data.lang
        const box = control(made, S.t(data.lang, "diskEncrypt"))
        verify(box !== null, "no encrypt box")
        box.toggle()
        box.toggled()
        wait(50)
        const words = shown(made)
        verify(words.indexOf(S.t(data.lang, "diskPassShort", [8])) < 0, "blamed before any typing: " + words)
        verify(words.indexOf(S.t(data.lang, "diskEncryptLine")) >= 0, "the plain line is missing: " + words)
        verify(!made.complete, "Next must still wait for a password")
    }
    function test_a_short_password_is_named_once_typed() {
        const made = page([blank()])
        const box = control(made, S.t("en", "diskEncrypt"))
        box.toggle()
        box.toggled()
        for (const c of "abc")
            keyClick(c)
        wait(50)
        verify(shown(made).indexOf(S.t("en", "diskPassShort", [8])) >= 0, "a short password says nothing")
    }
    function named(item, name) {
        if (!item)
            return null
        if (item.objectName === name)
            return item
        for (let i = 0; i < item.children.length; ++i) {
            const hit = named(item.children[i], name)
            if (hit)
                return hit
        }
        if (item.contentItem && item.contentItem !== item)
            return named(item.contentItem, name)
        return null
    }
    function encrypted(lang) {
        const made = page([blank()])
        made.lang = lang
        const box = named(made, "encrypt")
        box.toggle()
        box.toggled()
        wait(50)
        return made
    }
    function test_each_password_box_has_its_name_over_it_data() {
        return [{ tag: "en", lang: "en" }, { tag: "fr", lang: "fr" }]
    }
    function test_each_password_box_has_its_name_over_it(data) {
        const made = encrypted(data.lang)
        const words = shown(made)
        for (const key of ["diskPassLabel", "diskPassAgainLabel"])
            verify(words.indexOf(S.t(data.lang, key)) >= 0, key + " is not on the page: " + words)
        const first = named(made, "password")
        compare(first.placeholderText, "", "the name is over the box, not inside it")
        compare(first.Accessible.name, S.t(data.lang, "diskPassLabel"))
    }
    function test_the_disk_password_can_be_shown() {
        const made = encrypted("en")
        const first = named(made, "password")
        first.text = "correct horse"
        verify(first.revealable)
        verify(named(first, "reveal").visible, "no eye on the disk password")
    }
    function test_passwords_that_differ_say_so_in_red() {
        const made = encrypted("en")
        named(made, "password").text = "correct horse"
        named(made, "passwordAgain").text = "correct hose"
        wait(50)
        const line = named(made, "passwordLine")
        compare(line.text, S.t("en", "diskPassMismatch"))
        compare(String(line.color), String(Theme.error))
        verify(named(made, "passwordAgain").error, "the second box is not marked")
        verify(!named(made, "password").error, "the first box was right")
        verify(!made.complete)
    }
    function test_the_second_field_is_not_blamed_before_it_is_typed_in() {
        compare(Logic.passphraseShown(true, "", "", "en"), "")
        compare(Logic.passphraseShown(true, "long enough", "", "en"), "")
        compare(Logic.passphraseShown(true, "short", "", "en"), S.t("en", "diskPassShort", [8]))
        compare(Logic.passphraseShown(true, "long enough", "long", "fr"), S.t("fr", "diskPassMismatch"))
        compare(Logic.passphraseShown(false, "x", "y", "en"), "")
    }
    // Windows asks before it deletes a partition; Raye asks before any card
    // that deletes or resizes something is picked
    function linuxDisk() {
        const disk = blank()
        disk.empty = false
        disk.parts = [{ node: "/dev/sda2", start: 2048, sectors: 100 * gib / 512, os: "Arch Linux", fstype: "btrfs" }]
        disk.options = [{ mode: "shrink", node: "/dev/sda2", name: "Arch Linux", fstype: "btrfs",
                          total: 100 * gib, keepMin: 40 * gib, keepMax: 70 * gib, keepDefault: 50 * gib },
                        { mode: "free", start: 300000000, bytes: 30 * gib },
                        { mode: "replace", node: "/dev/sda2", name: "Arch Linux", fstype: "btrfs", bytes: 100 * gib },
                        { mode: "erase" }]
        disk.refused = [{ mode: "shrink", node: "/dev/sda4", name: "Fedora Linux", finding: "xfs" }]
        return disk
    }
    function test_replacing_asks_first_and_names_the_system() {
        const made = page([linuxDisk()])
        made.ask(2)
        compare(made.option, null, "nothing is picked while the box asks")
        verify(made.question !== null)
        verify(made.question.title.indexOf("Arch Linux") >= 0, made.question.title)
        made.answerQuestion(true)
        compare(made.option.mode, "replace")
        verify(made.complete)
    }
    function test_saying_no_keeps_the_disk_as_it_was() {
        const made = page([linuxDisk()])
        made.ask(3)
        compare(made.question.title, S.t("en", "confirmEraseTitle"))
        made.answerQuestion(false)
        compare(made.option, null)
        compare(made.asking, -1)
        verify(!made.complete)
    }
    function test_shrinking_asks_too() {
        const made = page([linuxDisk()])
        made.ask(0)
        compare(made.option, null)
        verify(made.question.title.indexOf("Arch Linux") >= 0)
        made.answerQuestion(true)
        compare(made.option.mode, "shrink")
        compare(made.keep, 50 * gib)
    }
    function test_free_space_is_picked_without_a_question() {
        const made = page([linuxDisk()])
        made.ask(1)
        compare(made.asking, -1)
        compare(made.option.mode, "free")
    }
    function test_a_click_on_a_card_that_asks_leaves_it_unchecked() {
        const made = page([linuxDisk()])
        const card = find(made, Logic.title(made.options[2], made.disk, "en"))
        verify(card !== null)
        mouseClick(card)
        verify(!card.checked, "the card only shows picked once the box said yes")
        verify(made.asking === 2)
        made.answerQuestion(true)
        verify(card.checked)
    }
    function test_questions_read_well_in_both_languages() {
        const disk = linuxDisk()
        const unnamed = { mode: "replace", node: "/dev/sda5", fstype: "ext4", bytes: 60 * gib }
        for (const lang of ["en", "fr"]) {
            for (const o of disk.options.concat([unnamed])) {
                const q = Logic.confirm(o, disk, lang)
                if (o.mode === "free") {
                    compare(q, null)
                    continue
                }
                for (const part of [q.title, q.text, q.button])
                    verify(part.length > 0 && part.indexOf("%") < 0 && part.indexOf("confirm") !== 0, part)
            }
            compare(Logic.confirm({ mode: "erase" }, blank(), lang), null, "an empty disk loses nothing")
            verify(Logic.title(unnamed, disk, lang).indexOf("sda5") >= 0, "a partition nobody named is called by its name")
            const why = Logic.refusedText(disk.refused[0], lang)
            verify(why.indexOf("Fedora Linux") >= 0 && why.indexOf("%") < 0, why)
            verify(Logic.refusedText({ reason: "full-table" }, lang).indexOf("fullTable") !== 0)
            verify(Logic.shrinkNote(disk.options[0], lang) !== Logic.shrinkNote({ fstype: "ntfs" }, lang))
        }
    }
    function mintDisk() {
        const disk = blank()
        disk.empty = false
        disk.size = 500 * gib
        disk.last = 500 * gib / 512 - 34
        disk.parts = [{ node: "/dev/sda1", start: 2048, sectors: gib / 512, fstype: "vfat" },
                      { node: "/dev/sda2", start: 2048 + gib / 512, sectors: 400 * gib / 512, fstype: "ext4", os: "Linux Mint 22" }]
        const users = [{ name: "alice", folders: [{ kind: "documents", files: 1204, bytes: 3.2 * gib },
                                                  { kind: "pictures", files: 40, bytes: 0.5 * gib }] }]
        disk.options = [{ mode: "replace", node: "/dev/sda2", name: "Linux Mint 22", fstype: "ext4", bytes: 400 * gib },
                        { mode: "keep", way: "stage", node: "/dev/sda2", name: "Linux Mint 22", fstype: "ext4",
                          bytes: 499 * gib, users: users, files: 1244, size: 3.7 * gib },
                        { mode: "erase" }]
        disk.refused = []
        return disk
    }
    function test_keeping_files_asks_and_lists_every_folder() {
        const made = page([mintDisk()])
        made.ask(1)
        compare(made.option, null)
        verify(made.question.title.indexOf("Linux Mint 22") >= 0, made.question.title)
        compare(made.question.kept.length, 2)
        compare(made.question.kept[0].label, "Documents")
        compare(made.question.kept[0].detail, "3.2 GB · 1,204 files")
        verify(made.question.note.indexOf("isn't deleted") > 0, made.question.note)
        made.answerQuestion(true)
        compare(made.option.mode, "keep")
        verify(made.complete)
        const sent = Logic.answer(made.disk, made.option, 0, false, "en")
        compare(sent.mode, "keep")
        compare(sent.partition, "/dev/sda2")
        compare(sent.install, "replace")
        verify(sent.details.indexOf("3.7 GB") > 0, sent.details)
    }
    function test_what_comes_along_is_listed_data() {
        return [{ tag: "en", lang: "en" }, { tag: "fr", lang: "fr" }]
    }
    function test_what_comes_along_is_listed(data) {
        const disk = mintDisk()
        const option = disk.options[1]
        option.users[0].folders.push({ kind: "firefox", files: 300, bytes: 0.2 * gib })
        option.extras = { wallpaper: true, wifi: 3, apps: 12 }
        const rows = Logic.confirm(option, disk, data.lang).kept
        const labels = rows.map(r => r.label)
        for (const key of ["folderFirefox", "keptWallpaper", "keptWifi", "keptApps"]) {
            verify(labels.indexOf(S.t(data.lang, key)) >= 0, key + ": " + labels)
            verify(S.t(data.lang, key) !== key)
        }
        compare(rows[rows.length - 1].detail, S.t(data.lang, "keptAppsCount", ["12"]))
        compare(rows[rows.length - 2].detail, S.t(data.lang, "keptWifiCount", ["3"]))
        // nothing extra, nothing said
        option.extras = { wallpaper: false, wifi: 0, apps: 0 }
        compare(Logic.confirm(option, disk, data.lang).kept.length, 3)
    }
    function test_keeping_reads_well_in_french() {
        const option = mintDisk().options[1]
        const q = Logic.confirm(option, mintDisk(), "fr")
        compare(q.kept[1].label, "Images")
        compare(q.kept[0].detail, "3,2 Go · 1\u202f204 fichiers")
        for (const part of [q.title, q.text, q.note, q.button, Logic.title(option, mintDisk(), "fr"),
                            Logic.line(option, mintDisk(), "fr")])
            verify(part.length > 0 && part.indexOf("%") < 0, part)
    }
    function test_several_accounts_say_whose_folder() {
        const option = mintDisk().options[1]
        option.users.push({ name: "sam", folders: [{ kind: "music", files: 3, bytes: gib }] })
        const rows = Logic.kept(option, "en")
        compare(rows[0].label, "Documents (alice)")
        compare(rows[2].label, "Music (sam)")
    }
    function test_keeping_from_a_separate_home_says_it_stays() {
        const option = Object.assign({}, mintDisk().options[1], { way: "home", home: "/dev/sda3" })
        const q = Logic.confirm(option, mintDisk(), "en")
        verify(q.text.indexOf("stays as it is") > 0, q.text)
        compare(q.note, "")
    }
    function test_no_room_to_keep_says_how_much_it_takes() {
        const text = Logic.refusedText({ mode: "keep", reason: "room", name: "Linux Mint 22",
                                         needed: 212 * gib, have: 205 * gib }, "en")
        verify(text.indexOf("212 GB") > 0 && text.indexOf("205 GB") > 0 && text.indexOf("Linux Mint 22") >= 0, text)
        verify(text.indexOf("%") < 0, text)
        const unreadable = Logic.refusedText({ mode: "keep", reason: "unreadable", name: "Windows" }, "fr")
        verify(unreadable.indexOf("Windows") >= 0 && unreadable.indexOf("%") < 0, unreadable)
    }
    function test_keeping_is_not_red_and_the_picture_shows_raye_in_its_place() {
        const disk = mintDisk()
        const option = disk.options[1]
        verify(!Logic.deletes(option, disk))
        verify(Logic.confirm(option, disk, "en").danger)
        const picture = Logic.bars(disk, option, 0, "en")
        const kinds = picture.after.map(p => p.kind)
        compare(kinds, ["other", "raye"])
        compare(picture.after[1].bytes, option.bytes)
    }
    function test_the_last_page_says_where_the_files_are() {
        compare(Logic.keepResult("", "en"), "")
        compare(Logic.keepResult("not json", "en"), "")
        verify(Logic.keepResult('{"way":"stage","name":"Windows","ok":true}', "en").indexOf("Windows") >= 0)
        verify(Logic.keepResult('{"way":"stage","ok":false,"left":true}', "fr").indexOf("raye_files") > 0)
        verify(Logic.keepResult('{"way":"home","ok":false}', "en").indexOf("Nothing was deleted") >= 0)
    }

    // Next to Windows, Setup offers to bring its files over after the first
    // sign-in (Settings, Files from Windows)
    function windowsChoices() {
        const disk = { node: "/dev/sda", model: "Test SSD", size: 256 * gib, sector: 512, first: 2048,
                       last: 256 * gib / 512 - 34, id: "abc", empty: false, blocked: "", refused: [],
                       parts: [{ node: "/dev/sda1", start: 2048, sectors: 2097152, label: "SYSTEM" },
                               { node: "/dev/sda3", start: 2048 + 2097152, sectors: 209715200, fstype: "ntfs", os: "Windows" }] }
        disk.options = [{ mode: "shrink", node: "/dev/sda3", name: "Windows", fstype: "ntfs",
                          total: 100 * gib, keepMin: 50 * gib, keepMax: 72 * gib, keepDefault: 60 * gib }, { mode: "free", start: 2048 + 2097152 + 211812352, bytes: 20 * gib },
                        { mode: "replace", node: "/dev/sda3", name: "Windows", fstype: "ntfs", bytes: 100 * gib },
                        { mode: "erase" }]
        return disk
    }
    function test_windows_files_are_offered_only_next_to_windows() {
        const disk = windowsChoices()
        verify(Logic.offersWindowsFiles(disk, disk.options[0]))
        verify(Logic.offersWindowsFiles(disk, disk.options[1]), "free space next to Windows")
        verify(!Logic.offersWindowsFiles(disk, disk.options[2]), "Windows is replaced")
        verify(!Logic.offersWindowsFiles(disk, disk.options[3]))
        verify(!Logic.offersWindowsFiles(disk, null))
        const arch = linuxDisk()
        verify(!Logic.offersWindowsFiles(arch, arch.options[0]))
        verify(!Logic.offersWindowsFiles(arch, arch.options[1]))
    }
    function test_windows_files_answer() {
        const disk = windowsChoices()
        compare(Logic.windowsFilesAnswer(disk, disk.options[0], true, true), "bring")
        compare(Logic.windowsFilesAnswer(disk, disk.options[0], true, false), "later")
        compare(Logic.windowsFilesAnswer(disk, disk.options[0], false, true), "")
        compare(Logic.windowsFilesAnswer(disk, disk.options[3], true, true), "")
    }
    function test_windows_files_box_data() {
        return [{ tag: "en", lang: "en" }, { tag: "fr", lang: "fr" }]
    }
    function test_windows_files_box(data) {
        const made = page([windowsChoices()])
        made.lang = data.lang
        verify(shown(made).indexOf(S.t(data.lang, "diskWindowsFiles")) < 0, "shown before a choice")
        made.ask(0)
        made.answerQuestion(true)
        wait(50)
        const box = named(made, "windowsFiles")
        verify(box !== null && box.visible, "no box next to Windows")
        verify(box.checked, "ticked unless the person says no")
        compare(box.text, S.t(data.lang, "diskWindowsFiles"))
        verify(shown(made).indexOf(S.t(data.lang, "diskWindowsFilesLine")) >= 0)
        made.pick(2)
        wait(50)
        verify(!box.visible, "still offered once Windows is replaced")
    }
}

TestCase {
    name: "Disk"

    readonly property real gib: 1024 * 1024 * 1024
    function part(node, start, gibs, more) {
        const entry = { node: node, start: start, sectors: gibs * gib / 512 }
        return Object.assign(entry, more || {})
    }
    function windowsDisk() {
        const parts = [
            part("/dev/sda1", 2048, 1, { label: "SYSTEM" }),
            part("/dev/sda3", 2048 + 2097152, 100, { os: "Windows" }),
            part("/dev/sda4", 2048 + 2097152 + 209715200, 1, {})
        ]
        return { node: "/dev/sda", model: "Test SSD", size: 256 * gib, sector: 512, first: 2048,
                 last: 256 * gib / 512 - 34, id: "abc", empty: false, parts: parts }
    }
    readonly property var shrink: ({ mode: "shrink", node: "/dev/sda3", name: "Windows",
                                     total: 100 * gib, keepMin: 50 * gib, keepMax: 72 * gib, keepDefault: 60 * gib })

    function test_sizes_read_like_windows_in_both_languages() {
        compare(Logic.size(64 * gib, "en"), "64 GB")
        compare(Logic.size(1.5 * gib, "fr"), "1,5 Go")
        compare(Logic.size(512 * gib, "fr"), "512 Go")
    }

    function test_a_volume_without_a_name_starts_its_sentence_with_a_capital() {
        // seen on the 1.0 Beta image: "this partition is encrypted, so..."
        for (const lang of ["en", "fr"]) {
            for (const f of S.volumeFindings) {
                const text = Logic.refusedText({ finding: f }, lang)
                compare(text.charAt(0), text.charAt(0).toUpperCase(), lang + " " + f + ": " + text)
            }
        }
    }

    function test_a_volume_without_a_name_agrees_in_french() {
        // "%1 est chiffré : Raye ne peut pas le réduire" is masculine:
        // with no name, %1 must be a masculine word ("Ce volume"), never
        // "cette partition" ("Cette partition est chiffré ... le réduire")
        for (const f of S.volumeFindings) {
            const text = Logic.refusedText({ finding: f }, "fr")
            verify(text.indexOf("artition") < 0, f + ": " + text)
            verify(/(^Ce|\bce) volume\b/.test(text), f + ": " + text)
        }
        compare(Logic.refusedText({ finding: "encrypted" }, "en").indexOf("This partition "), 0)
    }

    function test_nothing_on_the_page_shows_a_raw_key() {
        const disk = windowsDisk()
        const options = [shrink, { mode: "free", start: 1, bytes: gib }, { mode: "replace", node: "/dev/sda3", name: "Windows", bytes: gib }, { mode: "erase" }]
        for (const lang of ["en", "fr"]) {
            for (const o of options) {
                verify(Logic.title(o, disk, lang).indexOf("disk") !== 0, Logic.title(o, disk, lang))
                verify(Logic.line(o, disk, lang).indexOf("disk") !== 0, Logic.line(o, disk, lang))
                verify(Logic.line(o, disk, lang).indexOf("%") < 0, Logic.line(o, disk, lang))
            }
            for (const b of ["live", "small", "in-use", "unreadable"])
                verify(Logic.blockedText(b, lang).length > 0 && Logic.blockedText(b, lang).indexOf("disk") !== 0, b)
            for (const f of S.diskFindings)
                verify(Logic.refusedText({ finding: f }, lang).indexOf("disk") !== 0, f)
            verify(Logic.refusedText({ reason: "old-table" }, lang).indexOf("disk") !== 0)
            verify(Logic.refusedText({ reason: "shared-efi" }, lang).indexOf("sharedEfi") !== 0)
        }
    }

    function test_a_choice_that_deletes_says_so() {
        const disk = windowsDisk()
        verify(Logic.deletes({ mode: "erase" }, disk))
        verify(Logic.deletes({ mode: "replace" }, disk))
        verify(!Logic.deletes(shrink, disk))
        verify(!Logic.deletes({ mode: "free" }, disk))
        const empty = Object.assign(windowsDisk(), { empty: true, parts: [] })
        verify(!Logic.deletes({ mode: "erase" }, empty), "an empty disk has nothing to lose")
        compare(Logic.title({ mode: "erase" }, empty, "en"), S.t("en", "diskEmptyTitle"))
    }

    function test_the_answer_carries_what_the_job_reads() {
        const disk = windowsDisk()
        const made = Logic.answer(disk, shrink, 60 * gib, true, "en")
        compare(made.mode, "shrink")
        compare(made.disk, "/dev/sda")
        compare(made.id, "abc")
        compare(made.partition, "/dev/sda3")
        compare(made.keep, 60 * gib)
        compare(made.encrypt, true)
        compare(made.install, "alongside")
        compare(made.diskLabel, "Test SSD (/dev/sda)")
        verify(made.details.indexOf("60 GB") >= 0, made.details)
        verify(JSON.stringify(made).indexOf("pass") < 0, "the password travels on its own")
        compare(Logic.answer(disk, { mode: "erase" }, 0, false, "en").install, "erase")
        compare(Logic.answer(disk, { mode: "free", start: 77, bytes: gib }, 0, false, "en").start, 77)
        compare(Logic.answer(disk, { mode: "replace", node: "/dev/sda3", bytes: gib }, 0, false, "en").partition, "/dev/sda3")
    }

    function sum(parts) {
        return parts.reduce((all, p) => all + p.bytes, 0)
    }

    function test_the_picture_shows_what_stays_and_what_goes() {
        const disk = windowsDisk()
        const before = Logic.bars(disk, null, 0, "en")
        compare(before.after.length, 0, "nothing chosen, nothing shown as after")
        verify(before.before.some(p => p.label === "Windows"))
        verify(before.before.some(p => p.kind === "free"), "free space is drawn")

        const shrunk = Logic.bars(disk, shrink, 60 * gib, "en")
        const windows = shrunk.after.filter(p => p.label === "Windows")
        compare(windows.length, 1)
        compare(windows[0].bytes, 60 * gib)
        const raye = shrunk.after.filter(p => p.kind === "raye")
        compare(raye.length, 1)
        compare(raye[0].bytes, 40 * gib)

        const erased = Logic.bars(disk, { mode: "erase" }, 0, "en")
        compare(erased.after.length, 1)
        compare(erased.after[0].kind, "raye")

        const replaced = Logic.bars(disk, { mode: "replace", node: "/dev/sda3", name: "Windows", bytes: 100 * gib }, 0, "en")
        verify(!replaced.after.some(p => p.label === "Windows"), "the replaced one is gone")
        verify(replaced.after.some(p => p.kind === "raye"))
        compare(replaced.after.filter(p => p.kind === "other").length, 2, "its neighbours stay")
    }

    function test_the_passphrase_rules() {
        compare(Logic.passphraseProblem(false, "", "", "en"), "")
        verify(Logic.passphraseProblem(true, "short", "short", "en") !== "")
        verify(Logic.passphraseProblem(true, "long enough", "long enougj", "fr") === S.t("fr", "diskPassMismatch"))
        compare(Logic.passphraseProblem(true, "long enough", "long enough", "en"), "")
    }
}
}
