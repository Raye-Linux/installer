// What the "Ready to install" page says, worked out from what the other
// pages decided, in words.
.pragma library
.import "../strings.js" as S
.import "Countries.js" as Countries

function whatHappens(choice) {
    switch (choice) {
    case "erase": return "readyWhatErase"
    case "alongside": return "readyWhatAlongside"
    case "replace": return "readyWhatReplace"
    default: return "readyWhatOther"
    }
}

function languageName(code, nativeName, lang) {
    if (code === "en")
        return "English"
    if (code === "fr")
        return "Français"
    return nativeName ? S.listName(nativeName) : languageName(lang, "", "en")
}

// "Toronto" from America/Toronto, or the country's own name for its zone
function zoneName(zone, lang) {
    const country = Countries.ofZone(zone)
    const label = country ? Countries.zoneLabel(country, zone, lang) : ""
    return label || String(zone).replace(/^[^/]*\//, "").replace(/_/g, " ")
}

function countryName(zone, lang) {
    const country = Countries.ofZone(zone)
    return country ? (lang === "fr" ? country.fr : country.en) : ""
}

// the session the account signs in to; KDE Plasma unless Hyprland was picked
function desktopName(choice) {
    return choice === "hyprland" ? "Hyprland" : "KDE Plasma"
}

function row(lang, key, value) {
    return { label: S.t(lang, key), value: String(value) }
}

// Cards of label and value, a row with nothing to say left out.
//   choices: { lang, code, nativeName, zone, keyboard, install, diskLabel,
//              encrypted, fullName, hostName, desktop }
function cards(c) {
    const lang = c.lang
    const language = [
        row(lang, "readyLanguage", languageName(c.code, c.nativeName, lang)),
        row(lang, "readyCountry", countryName(c.zone, lang)),
        row(lang, "timeZone", zoneName(c.zone, lang)),
        row(lang, "readyKeyboard", c.keyboard || "")
    ]
    const disk = [
        row(lang, "readyWhat", S.t(lang, whatHappens(c.install))),
        row(lang, "readyDisk", c.diskLabel || ""),
        row(lang, "readyEncryption", S.t(lang, c.encrypted ? "readyEncrypted" : "readyNotEncrypted"))
    ]
    const account = [
        row(lang, "readyName", c.fullName || ""),
        row(lang, "readyPcName", c.hostName || ""),
        row(lang, "readyDesktop", desktopName(c.desktop))
    ]
    const keep = rows => rows.filter(r => r.value !== "")
    return [
        { title: S.t(lang, "readyRegionCard"), rows: keep(language) },
        { title: S.t(lang, "readyDiskCard"), rows: keep(disk) },
        { title: S.t(lang, "readyAccountCard"), rows: keep(account) }
    ].filter(card => card.rows.length > 0)
}
