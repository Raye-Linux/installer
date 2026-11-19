// What the pages ask of the setup session (raye-setup-run reads the FIFO),
// what it left for them, and the answers they leave for the install.
// Calamares runs as root and cannot reach the session's D-Bus; a line in
// a FIFO is all it takes. Its GlobalStorage is read-only from QML and each
// page has a QML engine of its own, so answers go through small files in
// /run/raye-setup: the rayesetupchoices job reads them (answer-<key>).
.pragma library

var folder = "file:///run/raye-setup/"
// Root's alone (raye-setup-private): the disk password goes here, never in
// the folder above, which the live account owns and everyone can read.
var privateFolder = "file:///run/raye-setup-root/"

// One write at a time per file: answers typed quickly must land in order,
// and only the last one matters. (A synchronous PUT sends no body.)
var busy = {}
var waiting = {}

function put(base, name, text) {
    var key = base + name
    if (busy[key]) {
        waiting[key] = String(text)
        return
    }
    busy[key] = true
    var request = new XMLHttpRequest()
    request.onreadystatechange = function() {
        if (request.readyState !== XMLHttpRequest.DONE)
            return
        busy[key] = false
        if (waiting[key] !== undefined) {
            var next = waiting[key]
            delete waiting[key]
            put(base, name, next)
        }
    }
    request.open("PUT", key)
    request.send(String(text))
}

function write(name, text) {
    put(folder, name, text)
}

// A secret: the file is made 0600 and empty before Setup starts, a PUT
// keeps that mode. With the folder missing the write fails, and the job
// says the password never arrived instead of reading it from somewhere else.
function secret(name, text) {
    put(privateFolder, name, text)
}

// The FIFO keeps every line: requests go out as they come.
function send(line) {
    var request = new XMLHttpRequest()
    request.open("PUT", folder + "requests")
    request.send(line + "\n")
}

function answer(key, value) {
    write("answer-" + key, value)
}

// A small file of the session, handed to done(text), "" when it is not
// there. Never synchronous: a synchronous request runs an event loop of its
// own in the middle of whatever QML is doing, and Calamares loads its pages
// on other threads at the same time (that crashed it, once in a few starts).
function read(name, done) {
    var request = new XMLHttpRequest()
    request.onreadystatechange = function() {
        if (request.readyState === XMLHttpRequest.DONE)
            done(request.status === 200 || request.status === 0 ? String(request.responseText || "") : "")
    }
    request.open("GET", folder + name)
    request.send()
}

// The same from root's own folder: what a job left for the last page.
function readPrivate(name, done) {
    var request = new XMLHttpRequest()
    request.onreadystatechange = function() {
        if (request.readyState === XMLHttpRequest.DONE)
            done(request.status === 200 || request.status === 0 ? String(request.responseText || "") : "")
    }
    request.open("GET", privateFolder + name)
    request.send()
}

function answerOf(key, done) {
    read("answer-" + key, done)
}

// /run/raye-setup/flags as an object: osk, account_preview, account_server
function flags(done) {
    read("flags", function(text) {
        var result = {}
        var lines = text.split("\n")
        for (var i = 0; i < lines.length; ++i) {
            var at = lines[i].indexOf("=")
            if (at > 0)
                result[lines[i].slice(0, at)] = lines[i].slice(at + 1)
        }
        done(result)
    })
}

// raye-preflight's findings: ["bitlocker", "hibernated", "shared-efi"]
function preflight(done) {
    read("preflight", function(text) {
        var found = []
        var lines = text.split("\n")
        for (var i = 0; i < lines.length; ++i) {
            var word = lines[i].split(" ")[0]
            if (word !== "" && found.indexOf(word) < 0)
                found.push(word)
        }
        done(found)
    })
}

// raye-cpu-check's lines as { level, verdict, missing }; {} when it left none
function parseCpu(text) {
    var result = {}
    var lines = String(text).split("\n")
    for (var i = 0; i < lines.length; ++i) {
        var at = lines[i].indexOf(" ")
        if (at > 0)
            result[lines[i].slice(0, at)] = lines[i].slice(at + 1)
    }
    return result
}

function cpu(done) {
    read("cpu", function(text) { done(parseCpu(text)) })
}
