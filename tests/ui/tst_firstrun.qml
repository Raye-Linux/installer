// The recovery key page of the welcome shown after the first sign-in
// (raye-first-run). Run by the same runner as tst_setup.qml (tests/ui).
//
// Why this test exists. Until 2026-11-06 the first window a person saw
// after an encrypted install was a kdialog --msgbox, written into
// ~/.config/autostart by the installer's encryption job. It carried the
// 48 digits that open the disk, in plain text, with one OK button: no way
// to copy them, no way to keep them, and not a Raye window at all --
// kdialog is a QtWidgets program and the Raye look is the QML module
// org.raye.setup, which it cannot load. That box was the product's first
// impression AND the screen holding the machine's most important secret.
//
// So this file asks of the page what a message box can never give: the
// Raye night behind it, the key in readable groups, a way to copy it and
// a way to keep a copy, a sentence saying why it matters, and a Done that
// waits until the person says they wrote it down.
//
// The key below is a FAKE of the right shape. The real one is never read
// by a test, never printed and never copied anywhere.
import QtQuick
import QtTest
import org.raye.setup

import "../../app/firstrun/qml/words.js" as W

Item {
    id: root
    width: 1280
    height: 800

    // eight groups of six digits, like the installer writes them
    readonly property string fakeKey: "111111-222222-333333-444444-555555-666666-777777-888888"

    function findByName(item, name) {
        if (!item)
            return null
        if (item.objectName === name)
            return item
        for (let i = 0; i < item.children.length; ++i) {
            const found = findByName(item.children[i], name)
            if (found)
                return found
        }
        return null
    }

    Loader {
        id: loader
        anchors.fill: parent
        asynchronous: false
        source: Qt.resolvedUrl("../../app/firstrun/qml/RecoveryKeyPage.qml")
        onLoaded: item.key = root.fakeKey
    }

    TestCase {
        id: suite
        name: "FirstRun"
        when: windowShown

        property Item page: loader.item

        function initTestCase() {
            // A missing page is the red this file was written for: say so
            // in words rather than let every check die on "null".
            verify(loader.status === Loader.Ready,
                   "app/firstrun/qml/RecoveryKeyPage.qml did not load: " + loader.source)
        }

        // The heart of the defect: a Raye window, not a message box.
        function test_it_is_a_raye_window_and_not_a_message_box() {
            const background = findByName(page, "night")
            verify(background, "the page has no Raye background behind it")
            compare(String(background.color), String(Theme.background))
            // and the type is setup's, not whatever style the session hands out
            const title = findByName(page, "title")
            verify(title, "the page has no title")
            compare(title.font.family, Theme.displayFamily)
            compare(title.color, Theme.textPrimary)
        }

        function test_the_key_is_shown_in_groups_of_six() {
            compare(page.grouped, "111111 222222 333333 444444 555555 666666 777777 888888")
            const shown = findByName(page, "keyText")
            verify(shown, "the key is not shown")
            compare(shown.text, page.grouped)
        }

        // A message box gives one OK button. These two are the point.
        function test_the_key_can_be_copied_and_kept() {
            const copy = findByName(page, "copyButton")
            const save = findByName(page, "saveButton")
            verify(copy, "no way to copy the recovery key")
            verify(save, "no way to keep a copy of the recovery key")
            verify(copy.enabled)
            verify(save.enabled)
            let copied = 0
            page.copyWanted.connect(function () { copied += 1 })
            mouseClick(copy)
            compare(copied, 1)
            compare(page.handedToClipboard, page.grouped)
        }

        function test_it_says_why_the_key_matters() {
            const why = findByName(page, "why")
            verify(why, "the page does not say what the key is for")
            verify(why.text.length > 40, "one line is not an explanation: " + why.text)
            verify(why.text.toLowerCase().indexOf("disk") >= 0
                   || why.text.toLowerCase().indexOf("disque") >= 0,
                   "the explanation never mentions the disk: " + why.text)
        }

        // A real click, never toggle(): AbstractButton::toggle() does
        // not emit toggled(), so a check driven by toggle() can pass on a
        // page whose box is not wired to anything.
        function test_done_waits_until_the_person_ticked_the_box() {
            const done = findByName(page, "doneButton")
            const box = findByName(page, "savedCheck")
            verify(done, "the page has no Done button")
            verify(box, "the page never asks whether the key was written down")
            verify(!box.checked)
            verify(!done.enabled, "Done is offered before the key is saved")
            mouseClick(box)
            verify(box.checked)
            verify(done.enabled, "Done stays off after the box was ticked")
            let finished = 0
            page.finished.connect(function () { finished += 1 })
            mouseClick(done)
            compare(finished, 1)
        }

        // Closes the loop the table checks cannot: a slot really reads
        // the table, so a French install gets French words on screen.
        function test_the_words_on_screen_follow_the_language() {
            const heading = findByName(page, "title")
            const why = findByName(page, "why")
            page.lang = "en"
            const englishHeading = heading.text
            const englishWhy = why.text
            page.lang = "fr"
            verify(heading.text !== englishHeading, "the heading did not change language")
            verify(why.text !== englishWhy, "the explanation did not change language")
            verify(heading.text.indexOf("récupération") >= 0, heading.text)
            page.lang = "en"
            compare(heading.text, englishHeading)
        }

        function test_escape_leaves_it_for_the_next_sign_in() {
            let postponed = 0
            page.postponed.connect(function () { postponed += 1 })
            page.forceActiveFocus()
            keyClick(Qt.Key_Escape)
            compare(postponed, 1)
        }
    }

    // The words of the page, both languages. t() falls back to English on
    // a key the table does not carry, so a forgotten French line reads as
    // an English sentence and never as "heading" -- which means nothing
    // on screen would point at it. These checks are what does.
    TestCase {
        name: "FirstRunWords"

        function test_both_languages_carry_the_same_keys() {
            compare(W.languages(), ["en", "fr"])
            compare(W.keys("fr"), W.keys("en"))
            verify(W.keys("en").length >= 9)
        }

        function test_nothing_is_left_untranslated() {
            const same = W.keys("en").filter(function (k) {
                return W.t("fr", k) === W.t("en", k)
            })
            compare(same, [], "these read the same in both languages: " + same)
        }

        function test_an_unknown_key_falls_back_to_english_text() {
            compare(W.t("de", "done"), W.t("en", "done"))
            compare(W.t("en", "nosuchkey"), "")
        }
    }
}
