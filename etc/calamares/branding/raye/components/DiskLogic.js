// What the disk page says and sends, worked out from what raye-disks found.
// The rules of what may be offered are in rayedisk_core.py: this only turns
// one offer into words, a picture and the answer the install reads.
.pragma library
.import "../strings.js" as S

var GIB = 1024 * 1024 * 1024
var MIB = 1024 * 1024
var PASSPHRASE_MINIMUM = 8

// Windows says GB for what it counts in GiB, and so does Raye
function size(bytes, lang) {
    var gib = Number(bytes) / GIB
    var shown = gib >= 100 ? Math.round(gib) : Math.round(gib * 10) / 10
    var text = String(shown)
    return S.t(lang, "diskSize", [lang === "fr" ? text.replace(".", ",") : text])
}

function diskLabel(disk) {
    var model = disk.model || ""
    return model ? model + " (" + disk.node + ")" : disk.node
}

function diskLine(disk, lang) {
    return diskLabel(disk) + " · " + size(disk.size, lang)
}

// What the person calls the thing a card changes: the system os-prober
// named, else the partition itself ("partition sda3 (ext4)"), never a bare
// file system name
function systemName(option, lang) {
    if (option.name)
        return option.name
    if (option.node)
        return S.t(lang, "diskReplacePartition", [String(option.node).replace("/dev/", ""),
                                                  option.fstype || size(option.bytes || 0, lang)])
    return S.t(lang, "diskThisPartition")
}

function title(option, disk, lang) {
    switch (option.mode) {
    case "shrink": return S.t(lang, "diskShrinkTitle", [systemName(option, lang)])
    case "free": return S.t(lang, "diskFreeTitle")
    case "replace": return S.t(lang, "diskReplaceTitle", [systemName(option, lang)])
    case "erase": return S.t(lang, disk.empty ? "diskEmptyTitle" : "diskEraseTitle")
    }
    return ""
}

function line(option, disk, lang) {
    switch (option.mode) {
    case "shrink": return S.t(lang, "diskShrinkLine", [systemName(option, lang)])
    case "free": return S.t(lang, "diskFreeLine", [size(option.bytes, lang)])
    case "replace": return S.t(lang, "diskReplaceLine", [systemName(option, lang), size(option.bytes, lang)])
    case "erase": return S.t(lang, disk.empty ? "diskEmptyLine" : "diskEraseLine")
    }
    return ""
}

// a choice that deletes something says so in red
function deletes(option, disk) {
    return option.mode === "replace" || (option.mode === "erase" && !disk.empty)
}

function refusedText(refusal, lang) {
    if (refusal.reason === "old-table")
        return S.t(lang, "diskOldTable")
    if (refusal.reason === "full-table")
        return S.t(lang, "fullTable")
    if (refusal.reason === "shared-efi")
        return S.t(lang, "sharedEfi")
    return S.t(lang, S.findingKey(refusal.finding), [refusal.name || S.t(lang, "diskThisPartition")])
}

// The note under the size slider: Windows checks its disk afterwards,
// another Linux does not
function shrinkNote(option, lang) {
    return S.t(lang, option && option.fstype && option.fstype !== "ntfs" ? "diskShrinkNoteLinux" : "diskShrinkNote")
}

// The question asked before a card that deletes or resizes something is
// picked, as Windows asks before it deletes a partition. null: nothing to ask.
function confirm(option, disk, lang) {
    if (!option)
        return null
    if (option.mode === "erase" && !disk.empty)
        return { title: S.t(lang, "confirmEraseTitle"),
                 text: S.t(lang, "confirmEraseText", [diskLabel(disk)]),
                 button: S.t(lang, "confirmErase"), danger: true }
    if (option.mode === "replace")
        return { title: S.t(lang, "confirmReplaceTitle", [systemName(option, lang)]),
                 text: S.t(lang, "confirmReplaceText", [systemName(option, lang), size(option.bytes, lang)]),
                 button: S.t(lang, "confirmReplace"), danger: true }
    if (option.mode === "shrink")
        return { title: S.t(lang, "confirmShrinkTitle", [systemName(option, lang)]),
                 text: S.t(lang, "confirmShrinkText", [systemName(option, lang)]),
                 button: S.t(lang, "confirmShrink"), danger: false }
    return null
}

function blockedText(blocked, lang) {
    switch (blocked) {
    case "live": return S.t(lang, "diskBlockedLive")
    case "small": return S.t(lang, "diskBlockedSmall")
    case "in-use": return S.t(lang, "diskBlockedInUse")
    case "unreadable": return S.t(lang, "diskBlockedUnreadable")
    }
    return ""
}

// The disk as it is, and as it will be: parts of a bar, in order.
//   kinds: other, system (the one this choice changes), free, raye
// after is empty until something is chosen.
function bars(disk, option, keep, lang) {
    var parts = (disk.parts || []).slice().sort(function(a, b) { return a.start - b.start })
    var sector = disk.sector || 512
    var freeWord = S.t(lang, "diskFreeWord")
    var before = []
    var after = []
    function push(list, kind, bytes, label) {
        if (bytes > 0)
            list.push({ kind: kind, bytes: bytes, label: label })
    }
    // what is at each place on the disk, gaps counted
    var at = disk.first || 2048
    var layout = []
    for (var i = 0; i < parts.length; ++i) {
        if ((parts[i].start - at) * sector >= MIB)
            layout.push({ free: true, start: at, bytes: (parts[i].start - at) * sector })
        layout.push({ part: parts[i], bytes: parts[i].sectors * sector })
        at = parts[i].start + parts[i].sectors
    }
    var tail = (Number(disk.last) + 1 - at) * sector
    if (tail >= MIB)
        layout.push({ free: true, start: at, bytes: tail })

    var chosen = option && option.node ? option.node : ""
    for (var j = 0; j < layout.length; ++j) {
        var place = layout[j]
        if (place.free)
            push(before, "free", place.bytes, freeWord)
        else
            push(before, place.part.node === chosen ? "system" : "other", place.bytes,
                 place.part.os || place.part.label || "")
    }
    if (!option)
        return { before: before, after: after, total: disk.size }
    if (option.mode === "erase") {
        push(after, "raye", disk.size, "Raye")
        return { before: before, after: after, total: disk.size }
    }
    for (var k = 0; k < layout.length; ++k) {
        var here = layout[k]
        if (here.free) {
            // the gap behind a shrunk volume goes to Raye with it
            var behindShrunk = option.mode === "shrink" && k > 0 && layout[k - 1].part
                && layout[k - 1].part.node === option.node
            if (behindShrunk)
                continue
            if (option.mode === "free" && Number(option.start) >= here.start
                    && Number(option.start) < here.start + here.bytes / sector) {
                push(after, "raye", option.bytes, "Raye")
                push(after, "free", here.bytes - option.bytes, freeWord)
            } else {
                push(after, "free", here.bytes, freeWord)
            }
        } else if (here.part.node !== chosen) {
            push(after, "other", here.bytes, here.part.os || here.part.label || "")
        } else if (option.mode === "shrink") {
            push(after, "system", keep, here.part.os || here.part.label || "")
            push(after, "raye", option.total - keep, "Raye")
        } else {
            push(after, "raye", here.bytes, "Raye")
        }
    }
    return { before: before, after: after, total: disk.size }
}

function passphraseProblem(encrypt, first, second, lang) {
    if (!encrypt)
        return ""
    if (first.length < PASSPHRASE_MINIMUM)
        return S.t(lang, "diskPassShort", [PASSPHRASE_MINIMUM])
    if (first !== second)
        return S.t(lang, "diskPassMismatch")
    return ""
}

// What the line under the fields says. A field nobody typed in yet is not
// wrong yet: Next waits on passphraseProblem, the words wait on the typing.
function passphraseShown(encrypt, first, second, lang) {
    if (!encrypt || (first === "" && second === ""))
        return ""
    if (second === "" && first.length >= PASSPHRASE_MINIMUM)
        return ""
    return passphraseProblem(encrypt, first, second, lang)
}

// In words, for "Ready to install": what stays, what goes, what is made.
function details(disk, option, keep, encrypt, lang) {
    var lines = []
    if (option.mode === "erase") {
        lines.push(S.t(lang, "diskDetailErase", [diskLabel(disk)]))
    } else if (option.mode === "shrink") {
        lines.push(S.t(lang, "diskDetailShrink", [systemName(option, lang), size(keep, lang)]))
        lines.push(S.t(lang, "diskDetailRaye", [size(option.total - keep, lang)]))
    } else if (option.mode === "replace") {
        lines.push(S.t(lang, "diskDetailReplace", [systemName(option, lang), size(option.bytes, lang)]))
    } else {
        lines.push(S.t(lang, "diskDetailRaye", [size(option.bytes, lang)]))
    }
    if (encrypt)
        lines.push(S.t(lang, "diskDetailEncrypted"))
    return lines.join("<br/>")
}

// What the rayedisk job reads. keep in whole MiB, as the page's slider moves.
function answer(disk, option, keep, encrypt, lang) {
    var result = { mode: option.mode, disk: disk.node, id: disk.id, encrypt: !!encrypt,
                   install: option.mode === "erase" ? "erase"
                          : option.mode === "replace" ? "replace" : "alongside",
                   diskLabel: diskLabel(disk),
                   details: details(disk, option, keep, encrypt, lang) }
    if (option.mode === "shrink") {
        result.partition = option.node
        result.keep = keep
    } else if (option.mode === "replace") {
        result.partition = option.node
    } else if (option.mode === "free") {
        result.start = option.start
    }
    return result
}
