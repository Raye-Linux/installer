# SPDX-License-Identifier: GPL-3.0-or-later
"""The disk page and its job: btrfs and nothing else, as few questions as
the disk allows, and the settings the jobs after it depend on.

Setup does not use the partition module any more: its page could not be
drawn in Raye's frame, and its "install alongside" ran ntfsresize with
--force through KPMcore (the UTF-16 literals are in libkpmcore.so.24.12.3).
The page is pages/Disk.qml, the rules are rayedisk_core.py
(tests/test_rayedisk_core.py), the writing is rayedisk_apply.py
(tests/test_rayedisk_apply.py). This file holds what connects them to the
rest of Setup.

⚠️ The owner asked (2026-11-06) for the manual page to be KEPT. It was off
before this page and it still is: nothing here can draw it. It is reported,
not forgotten.
"""
import importlib.util
import pathlib
import re

ETC = pathlib.Path(__file__).parent.parent / "etc/calamares"
MOUNT = ETC / "modules/mount.conf"
FSTAB = ETC / "modules/fstab.conf"
JOB = pathlib.Path(__file__).parent.parent / "usr/lib/calamares/modules/rayedisk"
MOUNT_TEXT = MOUNT.read_text()

spec = importlib.util.spec_from_file_location("rayedisk_core", JOB / "rayedisk_core.py")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def steps_of(part):
    text = (ETC / "settings.conf").read_text()
    if part == "exec":
        body = text.split("- exec:", 1)[1].split("- show:", 1)[0]
    else:
        body = text.split("- show:", 1)[1].split("- exec:", 1)[0]
    return [l.strip().lstrip("- ").strip() for l in body.splitlines() if l.strip().startswith("-")]


# ------------------------------------------------------------ the page and its job


def test_the_page_and_its_job_replace_the_partition_module():
    assert "partition" not in steps_of("show")
    assert "notesqml@raye_disk" in steps_of("show")
    assert "partition" not in steps_of("exec")
    assert steps_of("exec")[0] == "rayedisk", "the disk comes before anything is mounted"
    assert not (ETC / "modules/partition.conf").exists(), "a settings file nothing reads"


def test_the_job_is_a_module_calamares_can_load():
    desc = (JOB / "module.desc").read_text()
    assert re.search(r'^type:\s+"job"$', desc, re.M)
    assert re.search(r'^interface:\s+"python"$', desc, re.M)
    assert re.search(r'^script:\s+"main.py"$', desc, re.M)


def test_the_job_leaves_what_the_jobs_after_it_read():
    """Measured in Calamares 3.3.14: fstab reads partitionChoices for the swap
    file, bootloader reads firmwareType and efiSystemPartition, and everything
    reads partitions. The partition module used to set them when it loaded."""
    text = (JOB / "main.py").read_text()
    for key in ("partitions", "firmwareType", "efiSystemPartition", "partitionChoices"):
        assert f'gs.insert("{key}"' in text, key
    assert '"swap": "file"' in text


# ------------------------------------------------------------ btrfs, only


def test_the_root_is_btrfs_and_nothing_else_makes_one():
    text = (JOB / "rayedisk_apply.py").read_text()
    made = re.findall(r'"mkfs\.(\w+)"', text)
    assert sorted(set(made)) == ["btrfs", "ext4", "vfat"]
    # ext4 is /boot and only /boot: it is read before anything is unlocked
    assert re.findall(r'"mkfs\.ext4".*\n.*\n', text)[0].count('"/boot"') == 1
    assert 'self._entry(node, "/", "btrfs", "raye", True)' in text


def test_the_encrypted_root_is_btrfs_too():
    text = (JOB / "rayedisk_apply.py").read_text()
    assert 'self.run(["mkfs.btrfs", "-f", "-q", "-L", "raye", inner])' in text
    assert '"--type", "luks2"' in text


# ------------------------------------------------- next to another system


# Windows creates its EFI partition at "100 MB". Read as decimal that is
# 95.37 MiB, and some versions make it 100 MiB: a minimum anywhere
# between the two rejects one of them.
WINDOWS_ESP = 100 * 1000 ** 2
# Under this a FAT32 EFI partition is not valid at all.
EFI_FLOOR = 32 * 1024 ** 2


def test_an_existing_efi_partition_from_windows_is_accepted():
    """This is what stops a dual boot when it is wrong: a minimum above
    Windows' own partition makes installing next to it impossible."""
    assert core.ESP_MINIMUM <= WINDOWS_ESP, (
        f"the minimum is {core.ESP_MINIMUM} bytes, more than Windows' {WINDOWS_ESP} bytes"
    )
    assert core.ESP_MINIMUM >= EFI_FLOOR, "the firmware spec has a floor too"


def test_a_fresh_disk_still_gets_a_roomy_efi_partition():
    """The minimum is for partitions we did not make. On a disk we erase,
    the one we create must have room for several kernels."""
    assert core.ESP_SIZE >= 512 * 1024 ** 2


def test_the_first_boot_menu_gets_plain_names():
    """The bootloader module calls grub-mkconfig itself, so it never goes
    through Raye's update-grub: without a step of its own, the very first
    menu -- the one a person sees on a machine that holds another system
    -- would carry os-prober's wording. The step must come AFTER the
    bootloader, or it would rewrite a menu that does not exist yet.
    """
    text = (ETC / "settings.conf").read_text()
    exec_part = text.split("- exec:", 1)[1].split("- show:", 1)[0]
    steps = [l.strip().lstrip("- ").strip()
             for l in exec_part.splitlines() if l.strip().startswith("-")]
    assert "shellprocess@raye_grub" in steps, steps
    assert steps.index("shellprocess@raye_grub") > steps.index("bootloader")
    conf = (ETC / "modules/shellprocess_raye_grub.conf").read_text()
    assert "raye-grub-titles" in conf
    assert '"-/usr' in conf, (
        "the leading - must stay: a failed title pass cannot fail an install"
    )


def test_other_systems_are_looked_for_at_boot():
    """Without os-prober nothing else appears in the boot menu, and the
    machine boots straight into Raye as if the other system were gone."""
    grub = (ETC.parent.parent / "../iso/packages/raye-base/release/grub/50-raye.cfg")
    if not grub.exists():   # the iso repo is not always checked out next door
        return
    text = grub.read_text()
    assert "GRUB_DISABLE_OS_PROBER=false" in text
    assert 'GRUB_DISTRIBUTOR="Raye Linux"' in text


# ------------------------------------------------------- btrfs, set up right


def test_the_root_is_mounted_with_compression_and_no_access_times():
    block = re.search(
        r"- filesystem: btrfs\n((?:[ \t]+\S.*\n)+)", MOUNT_TEXT, re.M
    )
    assert block, "mount.conf says nothing about btrfs"
    options = block.group(1)
    assert "compress=zstd" in options
    assert "noatime" in options
    assert "discard=async" in options, "an SSD should trim itself"


def test_a_snapshot_of_the_system_leaves_the_rest_alone():
    """Four subvolumes: a snapshot of / must not carry home, logs or the
    caches with it, or a rollback would take back the user's files."""
    subvolumes = dict(
        re.findall(r"- mountPoint: (\S+)\n\s+subvolume: (\S+)", MOUNT_TEXT)
    )
    assert subvolumes == {
        "/": "/@",
        "/home": "/@home",
        "/var/log": "/@var_log",
        "/var/cache": "/@cache",
    }, subvolumes
    assert "btrfsSwapSubvol:" in MOUNT_TEXT, "the swap file needs its own subvolume"


def test_the_efi_partition_is_not_readable_by_everyone():
    assert "umask=0077" in FSTAB.read_text()


def test_next_waits_for_the_disk_page():
    """QmlViewStep's isNextEnabled is always true (QmlViewStep.cpp), so nothing
    but the bar itself can hold Next back while no choice has been made."""
    bar = (ETC / "branding/raye/calamares-navigation.qml").read_text()
    assert 'enabled: ViewManager.nextEnabled && (bar.stepName !== "disk" || bar.diskReady)' in bar
    assert 'Requests.read("disk-ready"' in bar
    page = (ETC / "branding/raye/pages/Disk.qml").read_text()
    assert 'Requests.write("disk-ready"' in page


def test_nothing_still_asks_for_the_partition_module():
    """Calamares refuses to start ("Module bootloader requires partition before
    it in sequence") when a module.desc names one that is not in the sequence.
    Seen on the real thing: only bootloader and unpackfs have requiredModules,
    and unpackfs asks for mount. Ours must be the one found first."""
    text = (ETC / "settings.conf").read_text()
    search = re.search(r"^modules-search: \[(.*)\]$", text, re.M).group(1).split(",")
    assert search[0].strip() == "/usr/lib/calamares/modules", search
    ours = (JOB.parent / "bootloader/module.desc").read_text()
    code = re.sub(r"^#.*$", "", ours, flags=re.M)
    assert "requiredModules" not in code
    assert re.search(r'^name:\s+"bootloader"$', ours, re.M)
    script = re.search(r'^script:\s+"(.*)"$', ours, re.M).group(1)
    assert script.startswith("/") and script.endswith("/bootloader/main.py")
