#!/usr/bin/env python3
"""
build_combined.py — generate the deployed Legion Toolkit dispatchers.

The toolkit ships as TWO codebases:
  * custom/   – the Lenovo LOQ 83SC-specific dashboard GUI / power CLI
  * upstream/ – the unmodified upstream Legion Linux GUI / CLI

This script wraps each custom module behind a model-gate dispatcher and embeds
the upstream module as base64 (self-contained, single-file deploy). It produces:

  legion-gui.py   (runs custom GUI on 83SC, upstream GUI otherwise)
  legion-cli.py   (runs custom CLI on 83SC, upstream CLI otherwise)

Edit the sources under custom/ and upstream/ — never hand-edit the generated
files. Run:  python3 tools/build_combined.py
"""
from pathlib import Path
import base64

ROOT = Path(__file__).resolve().parent.parent          # .../legion-toolkit-src
UPSTREAM_VERSION = "LenovoLegionLinux (legion_linux.legion_gui / legion_cli)"


def model_gate_header(kind: str) -> str:
    """Top-of-file dispatcher prefix shared by GUI and CLI."""
    return f'''#!/usr/bin/env python3
"""
Legion Linux Toolkit — {kind} launcher (generated dispatcher, do not edit by hand).

This entry point detects the host laptop model and loads the matching codebase:

  * Lenovo LOQ 83SC  (DMI product_name "83SC", BIOS version "SECN*")
        -> the 83SC-specific custom {kind}   (custom/legion-{kind.split()[0]}.py)
  * any other model -> the upstream Legion Linux {kind}   (embedded as base64)

Upstream source: {UPSTREAM_VERSION}
Regenerate with: tools/build_combined.py
"""
import base64
from pathlib import Path


def _read_dmi(field):
    try:
        return Path(f"/sys/class/dmi/id/{{field}}").read_text().strip()
    except OSError:
        return ""


def _detect_loq_83sc():
    """True only for the Lenovo LOQ 83SC this custom build targets."""
    vendor = _read_dmi("sys_vendor").upper()
    product = _read_dmi("product_name").strip()
    bios = _read_dmi("bios_version").strip()
    return vendor == "LENOVO" and product == "83SC" and bios.upper().startswith("SECN")


# Model gate: 83SC -> custom build, everything else -> upstream build.
_is_custom = _detect_loq_83sc()

if _is_custom:
'''


def indent(text: str) -> str:
    out = []
    for ln in text.split("\n"):
        out.append(("    " + ln) if ln.strip() else ln)
    return "\n".join(out)


def build(name: str, kind: str):
    custom_src = (ROOT / "custom" / name).read_text()
    upstream_src = (ROOT / "upstream" / name).read_text()
    blob = base64.b64encode(upstream_src.encode()).decode()

    out = (
        model_gate_header(kind)
        + indent(custom_src)
        + "\n\nelse:\n"
        + '    # ── UPSTREAM CODE (any other model) ──\n'
        + f'    _upstream_code = base64.b64decode("{blob}")\n'
        + '    exec(compile(_upstream_code, __file__, "exec"))\n'
    )
    (ROOT / name).write_text(out)
    print(f"built {name}: {len(out)} bytes "
          f"(custom {len(custom_src)} B, upstream blob {len(blob)} B)")


if __name__ == "__main__":
    build("legion-gui.py", "GUI")
    build("legion-cli.py", "CLI")
