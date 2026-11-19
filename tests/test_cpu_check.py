# SPDX-License-Identifier: GPL-3.0-or-later
"""raye-cpu-check: whether this PC's processor runs Raye, from /proc/cpuinfo."""
import pathlib
import subprocess

import pytest

REPO = pathlib.Path(__file__).parent.parent
CHECK = REPO / "usr/libexec/raye-cpu-check"

BASE = "fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 syscall nx lm"
# qemu -cpu core2duo: 64-bit, SSSE3, but no SSE4 and no POPCNT
CORE2 = BASE + " constant_tsc nopl pni ssse3 cx16 hypervisor"
NEHALEM = CORE2 + " lahf_lm sse4_1 sse4_2 popcnt"
HASWELL = NEHALEM + " avx avx2 bmi1 bmi2 fma f16c abm movbe xsave"
ZEN4 = HASWELL + " avx512f avx512bw avx512cd avx512dq avx512vl"
PENTIUM4 = "fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2"


def cpuinfo(tmp_path, *flag_lines, extra=""):
    blocks = [f"processor\t: {i}\nvendor_id\t: GenuineIntel\nflags\t\t: {flags}\n{extra}"
              for i, flags in enumerate(flag_lines)]
    path = tmp_path / "cpuinfo"
    path.write_text("\n".join(blocks) + "\n")
    return path


def check(path):
    done = subprocess.run(["python3", str(CHECK), str(path)], capture_output=True, text=True, check=True)
    return dict(line.split(" ", 1) if " " in line else (line, "") for line in done.stdout.splitlines())


def test_recent_processor_is_fine(tmp_path):
    assert check(cpuinfo(tmp_path, HASWELL)) == {"level": "3", "verdict": "ok"}
    assert check(cpuinfo(tmp_path, ZEN4))["level"] == "4"


def test_nehalem_era_is_fine(tmp_path):
    assert check(cpuinfo(tmp_path, NEHALEM)) == {"level": "2", "verdict": "ok"}


def test_core2_runs_but_is_old(tmp_path):
    found = check(cpuinfo(tmp_path, CORE2))
    assert found["level"] == "1" and found["verdict"] == "old"
    assert found["missing"].split() == ["lahf_lm", "popcnt", "sse4_1", "sse4_2"]


def test_32_bit_only_processor_is_too_old(tmp_path):
    found = check(cpuinfo(tmp_path, PENTIUM4))
    assert found["level"] == "0" and found["verdict"] == "too-old"
    assert found["missing"] == "lm"


def test_every_core_counts(tmp_path):
    # the weakest core decides: a flag one core lacks is not there
    found = check(cpuinfo(tmp_path, HASWELL, NEHALEM))
    assert found["level"] == "2"


@pytest.mark.parametrize("text", [
    "",
    "processor\t: 0\nFeatures\t: fp asimd evtstrm aes pmull sha1 sha2 crc32\n",
    "processor\t: 0\nvendor_id\t: GenuineIntel\n",
])
def test_unreadable_says_nothing(tmp_path, text):
    path = tmp_path / "cpuinfo"
    path.write_text(text)
    assert check(path) == {"verdict": "unknown"}


def test_missing_file_says_nothing(tmp_path):
    assert check(tmp_path / "nope") == {"verdict": "unknown"}


def test_reads_proc_by_default():
    assert "/proc/cpuinfo" in CHECK.read_text()
    first = CHECK.read_text().splitlines()[0]
    assert first == "#!/usr/bin/python3"


def test_setup_leaves_the_answer_for_the_pages():
    run = (REPO / "usr/libexec/raye-setup-run").read_text()
    assert '/usr/libexec/raye-cpu-check > "$dir/cpu"' in run
    # read by the pages, so no root needed and it happens before Calamares
    line = next(line for line in run.splitlines() if "raye-cpu-check" in line)
    assert "sudo" not in line
    assert run.index("raye-cpu-check") < run.index("while :; do")
