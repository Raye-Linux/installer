// Raye Setup: "Is this the right country or region?". The country sets
// the time zone, and with the language of the first page the formats of
// dates and numbers. Countries with several time zones get a second
// list; any other place is reached through "My country isn't listed".
//
// When the PC is online at start (a cable), Calamares has already set
// the time zone from the network, and the list opens on that country.

import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.raye.setup

import "../strings.js" as S
import "../components"
import "../components/Countries.js" as Countries

RayeFrame {
    id: page
    step: "region"
    illustration: "language"
    title: S.t(lang, "regionTitle")
    text: S.t(lang, "regionText")

    // "countries", "zones" (of one country) or "manual" (every time zone)
    property string view: "countries"
    // a country was picked here: the language no longer suggests one
    property bool picked: false
    readonly property string zone: config.currentLocation
                                   ? config.currentLocation.region + "/" + config.currentLocation.zone : ""
    readonly property var country: Countries.ofZone(zone)
    readonly property string code: { ViewManager.currentStepIndex; return S.code(Qt.locale()) }

    // Countries where the language of Setup is spoken come first, named in
    // that language; the rest follow in English or French.
    function spoken(c) {
        const name = code + "_" + c.code
        return Qt.locale(name).name === name
    }
    function nameOf(c) {
        if (lang === "fr")
            return c.fr
        if (code !== "en" && spoken(c)) {
            const ownName = Qt.locale(code + "_" + c.code).nativeTerritoryName
            if (ownName)
                return ownName
        }
        return c.en
    }
    function countries(search) {
        const needle = Countries.plain(search)
        const all = Countries.list.map(c => ({ code: c.code, zones: c.zones, en: c.en, fr: c.fr,
                                                name: nameOf(c), suggested: spoken(c) }))
            .filter(c => needle === "" || Countries.plain(c.name).indexOf(needle) >= 0
                         || Countries.plain(c.en).indexOf(needle) >= 0)
        // the country chosen now first, then the language's, then the rest
        const now = country ? country.code : ""
        const rank = c => c.code === now ? 0 : c.suggested ? 1 : 2
        all.sort((a, b) => rank(a) !== rank(b) ? rank(a) - rank(b) : a.name.localeCompare(b.name, code))
        return all
    }

    // where the PC is, from the network, once: only used while nobody has
    // picked a country here
    property bool located: false
    // what the network said, "" until it answers
    property string geoZone: ""
    function locate() {
        located = true
        const request = new XMLHttpRequest()
        request.onreadystatechange = function() {
            if (request.readyState !== XMLHttpRequest.DONE || request.status !== 200 || page.picked)
                return
            try {
                const found = JSON.parse(request.responseText).time_zone
                if (found && found.indexOf("/") > 0) {
                    page.geoZone = found
                    config.setCurrentLocation(found)
                }
            } catch (e) {
                console.warn("raye: time zone look-up:", e)
            }
        }
        request.open("GET", "https://geoip.kde.org/v1/calamares")
        request.send()
    }

    // Calamares works the formats out again only when the place changes, so
    // after French then English on the first page they stayed French.
    // Moving away and back has it redo them; formats set by hand it keeps.
    property string formatsFor: ""
    function setupLanguage() {
        const conf = Global.value("localeConf")
        return String(conf && conf.LANG ? conf.LANG : code).split(/[_.@]/)[0]
    }
    function refreshFormats() {
        const now = setupLanguage()
        if (formatsFor !== "" && formatsFor !== now && zone !== "") {
            const here = zone
            config.setCurrentLocation(here === "America/New_York" ? "Europe/London" : "America/New_York")
            config.setCurrentLocation(here)
        }
        formatsFor = now
    }

    onShown: (backward) => {
        refreshFormats()
        if (!located)
            locate()
        search.text = ""
        view = "countries"
        // Spanish, Arabic...: without the network's word, start on the
        // language's home country (English and French keep the default)
        if (!picked && geoZone === "" && lang === "en" && code !== "en" && !(country && spoken(country))) {
            const home = Countries.list.find(c => c.code === Qt.locale(code).name.split("_")[1])
            if (home)
                config.setCurrentLocation(home.zones[0][0])
        }
        Qt.callLater(countryList.positionAtCountry)
    }

    function pick(c) {
        picked = true
        const now = Countries.ofZone(zone)
        if (!now || now.code !== c.code)
            config.setCurrentLocation(c.zones[0][0])
        if (c.zones.length > 1)
            view = "zones"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        TextField {
            id: search
            Layout.fillWidth: true
            visible: page.view === "countries"
            placeholderText: S.t(page.lang, "regionSearch")
            Accessible.name: placeholderText
        }

        // the countries
        ListView {
            id: countryList
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: page.view === "countries"
            clip: true
            focus: visible
            keyNavigationEnabled: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            Accessible.role: Accessible.List
            Accessible.name: page.title
            model: page.countries(search.text)
            // a list handed to a view is copied: find the country by its code
            currentIndex: page.country ? model.findIndex(c => c.code === page.country.code) : -1

            function positionAtCountry() {
                if (currentIndex >= 0)
                    positionViewAtIndex(currentIndex, ListView.Contain)
            }

            delegate: ListRow {
                required property var modelData
                required property int index
                width: ListView.view.width
                text: modelData.name
                detail: modelData.zones.length > 1 && highlighted
                        ? Countries.zoneLabel(modelData, page.zone, page.lang) : ""
                highlighted: page.country !== null && modelData.code === page.country.code
                onClicked: {
                    ListView.view.currentIndex = index
                    page.pick(modelData)
                }
            }
            Keys.onReturnPressed: if (currentIndex >= 0) page.pick(model[currentIndex])
        }

        // the time zones of a country that has several
        ListView {
            id: zoneList
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: page.view === "zones" && page.country !== null
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            Accessible.role: Accessible.List
            Accessible.name: S.t(page.lang, "timeZone")
            model: page.country ? page.country.zones : []
            header: Text {
                width: ListView.view.width
                bottomPadding: 8
                text: page.country ? S.t(page.lang, "timeZone") + " · " + page.nameOf(page.country) : ""
                font: Theme.bodyStrong
                color: Theme.textPrimary
            }
            delegate: ListRow {
                required property var modelData
                width: ListView.view.width
                text: modelData[page.lang === "fr" ? 2 : 1]
                highlighted: modelData[0] === page.zone
                onClicked: {
                    page.picked = true
                    config.setCurrentLocation(modelData[0])
                }
            }
        }

        // any time zone, by area and city
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: page.view === "manual"
            spacing: 12

            ListView {
                id: areas
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                Accessible.role: Accessible.List
                Accessible.name: S.t(page.lang, "zoneArea")
                model: config.regionModel
                delegate: ListRow {
                    required property string name
                    required property string key
                    width: ListView.view.width
                    text: name
                    highlighted: config.currentLocation && config.currentLocation.region === key
                    onClicked: config.regionalZonesModel.region = key
                }
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                Accessible.role: Accessible.List
                Accessible.name: S.t(page.lang, "zoneCity")
                model: config.regionalZonesModel
                delegate: ListRow {
                    required property string name
                    required property string key
                    width: ListView.view.width
                    text: name
                    highlighted: page.zone === config.regionalZonesModel.region + "/" + key
                    onClicked: {
                        page.picked = true
                        config.setCurrentLocation(config.regionalZonesModel.region, key)
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            LinkButton {
                visible: page.view !== "countries"
                text: S.t(page.lang, "backToList")
                onClicked: page.view = "countries"
            }
            LinkButton {
                visible: page.view === "countries"
                text: S.t(page.lang, "notListed")
                onClicked: {
                    if (config.currentLocation)
                        config.regionalZonesModel.region = config.currentLocation.region
                    page.view = "manual"
                }
            }
            Item { Layout.fillWidth: true }
            Text {
                text: S.t(page.lang, "timeZone") + (page.lang === "fr" ? "\u00a0: " : ": ")
                      + page.zone.replace(/^[^/]*\//, "").replace(/_/g, " ")
                font: Theme.caption
                color: Theme.textTertiary
                elide: Text.ElideLeft
                Layout.maximumWidth: page.contentWidth * 0.6
            }
        }
    }
}
