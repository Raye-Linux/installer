// "Who's going to use this PC?": the fields stay where they are while a
// person types. On the 2026-11-08 image the "Account name: testr · Change"
// line came in after the first letter of the name and pushed every field
// under it down by about 40 px: a click aimed at the password field landed
// in the one above, and the password was typed where it could be read.
import QtQuick
import QtTest
import io.calamares.core 1.0
import org.raye.setup

import "../../etc/calamares/branding/raye/strings.js" as S

Item {
    id: root
    width: 1280
    height: 800

    // what Calamares' users module gives the page, reduced to what it reads
    property var config: QtObject {
        property string fullName: ""
        property string loginName: ""
        property string loginNameStatus: ""
        property int userPasswordValidity: 0
        property string userPasswordMessage: ""
        function setFullName(name) {
            fullName = name
            loginName = name.toLowerCase().replace(/[^a-z0-9]/g, "")
        }
        function setLoginName(name) { loginName = name }
        function setHostName(name) {}
        function setUserPassword(text) {}
        function setUserPasswordSecondary(text) {}
    }

    Loader {
        id: loader
        anchors.fill: parent
    }

    TestCase {
        name: "UserPage"
        when: windowShown

        function load(lang) {
            config.fullName = ""
            config.loginName = ""
            config.loginNameStatus = ""
            loader.source = ""
            ViewManager.currentStepIndex = S.steps.indexOf("user")
            loader.source = "../../etc/calamares/branding/raye/pages/User.qml"
            tryVerify(() => loader.status === Loader.Ready, 5000, "the page did not load")
            loader.item.lang = lang
            loader.item.shown(false)
            wait(50)
            return loader.item
        }
        function fields(item, out) {
            out = out || []
            if (!item)
                return out
            if (item.visible && item.placeholderText !== undefined && item.echoMode !== undefined)
                out.push(item)
            for (let i = 0; i < item.children.length; ++i)
                fields(item.children[i], out)
            return out
        }
        function field(page, key) {
            const wanted = S.t(page.lang, key)
            const hit = fields(page).filter(f => f.Accessible.name === wanted)
            verify(hit.length === 1, "no field " + key)
            return hit[0]
        }
        // where each field is on screen, by its name
        function where(page) {
            const out = {}
            for (const key of ["fullName", "password", "confirmPassword", "hint"]) {
                const f = field(page, key)
                out[key] = Math.round(f.mapToItem(root, 0, 0).y)
            }
            return out
        }
        function same(before, after, what) {
            for (const key in before)
                compare(after[key], before[key], key + " moved " + (after[key] - before[key]) + " px " + what)
        }
        function type(item, text) {
            item.forceActiveFocus()
            for (const c of text)
                keyClick(c)
            wait(50)
        }

        function test_typing_the_name_moves_nothing_data() {
            return [{ tag: "en", lang: "en" }, { tag: "fr", lang: "fr" }]
        }
        function test_typing_the_name_moves_nothing(data) {
            const page = load(data.lang)
            const before = where(page)
            type(field(page, "fullName"), "Test Raye")
            verify(config.loginName === "testraye", "the fake made no account name")
            same(before, where(page), "after the name was typed")
        }
        function test_a_bad_account_name_moves_nothing() {
            const page = load("en")
            type(field(page, "fullName"), "Test")
            const before = where(page)
            config.loginNameStatus = "This account name is already taken by the system."
            wait(50)
            same(before, where(page), "when the account name is refused")
        }
        function test_passwords_that_differ_move_nothing() {
            const page = load("en")
            type(field(page, "fullName"), "Test")
            const before = where(page)
            type(field(page, "password"), "abcdefgh")
            type(field(page, "confirmPassword"), "abc")
            verify(page.mismatch)
            same(before, where(page), "when the two passwords differ")
        }
        function words(item, out) {
            out = out || []
            if (!item || !item.visible)
                return out
            if (item.text !== undefined && String(item.text) !== "" && item.width > 0 && item.height > 0)
                out.push(item)
            for (let i = 0; i < item.children.length; ++i)
                words(item.children[i], out)
            return out
        }
        function test_every_box_has_its_name_over_it_data() {
            return [{ tag: "en", lang: "en" }, { tag: "fr", lang: "fr" }]
        }
        function test_every_box_has_its_name_over_it(data) {
            const page = load(data.lang)
            const shown = words(page)
            for (const key of ["fullName", "password", "confirmPassword", "hint"]) {
                const box = field(page, key)
                const name = shown.filter(t => t.text === S.t(data.lang, key) && t !== box)
                verify(name.length === 1, key + " has no name on screen")
                const nameY = name[0].mapToItem(root, 0, 0).y
                const boxY = box.mapToItem(root, 0, 0).y
                verify(nameY < boxY && boxY - nameY < 32, key + ": the name is not right over its box")
                compare(box.placeholderText, "", key + " repeats its name inside the box")
            }
        }
        function test_passwords_that_differ_say_so_in_red() {
            const page = load("en")
            type(field(page, "password"), "abcdefgh")
            type(field(page, "confirmPassword"), "abcdefgx")
            const line = words(page).filter(t => t.objectName === "passwordLine")[0]
            compare(line.text, S.t("en", "passwordsDiffer"))
            compare(String(line.color), String(Theme.error))
            verify(field(page, "confirmPassword").error)
        }
        function test_changing_the_account_name_moves_nothing() {
            const page = load("en")
            type(field(page, "fullName"), "Test")
            const before = where(page)
            page.editLogin = true
            wait(50)
            same(before, where(page), "when Change opens the account name field")
            verify(fields(page).some(f => f.placeholderText === S.t("en", "userName")), "the field did not open")
        }
    }
}
