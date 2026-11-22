#!/usr/bin/env python3
"""Apply the warp-transfer wait fix to generated C.

Run this after recomp/gen.py and before tools/build_game.py:

    python tools/apply_warp_wait_fix.py --gen generated/v327680

The fix is idempotent: when the marker is already present the file is left
untouched and the script exits successfully. If the generated code has changed
so the expected call site is missing, the script fails instead of guessing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

MARKER = "Warp fix: phase 0xe / state 1 waits forever"

OLD = (
    "    c->x[30] = 0x700018de3cull; c->x[8] = x8; c->x[9] = x9; "
    "c->x[19] = x19; c->sp = sp_; f_700045c630(c); "
    "x8 = c->x[8]; x9 = c->x[9]; x10 = c->x[10]; x11 = c->x[11];\n"
)

NEW = (
    "    { uint64_t chk_h = c->x[1], chk_key = c->x[2]; "
    "c->x[30] = 0x700018de3cull; c->x[8] = x8; c->x[9] = x9; "
    "c->x[19] = x19; c->sp = sp_; f_700045c630(c);\n"
    "      /* Warp fix: phase 0xe / state 1 waits forever on this -1-keyed presentation task.\n"
    "         Its leaf completion check never turns over on the PC recomp, so treat the wait as\n"
    "         satisfied for this handle signature and let the phase machine advance. */\n"
    "      if (((uint32_t)chk_h) == 0xffffffffu && chk_key == 0 && c->x[0] != 0) c->x[0] = 0;\n"
    "      x8 = c->x[8]; x9 = c->x[9]; x10 = c->x[10]; x11 = c->x[11]; }\n"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", type=Path, default=Path("generated/v327680"),
                    help="generated C directory (default: generated/v327680)")
    args = ap.parse_args()

    path = args.gen / "main" / "main_0010.c"
    if not path.is_file():
        print(f"apply_warp_wait_fix: {path} not found", file=sys.stderr)
        return 1

    with path.open("r", encoding="utf-8", newline="") as f:
        text = f.read()
    if MARKER in text:
        print(f"apply_warp_wait_fix: already applied in {path}")
        return 0

    nl = "\r\n" if "\r\n" in text else "\n"
    old = OLD.replace("\n", nl)
    new = NEW.replace("\n", nl)
    count = text.count(old)
    if count != 1:
        print(f"apply_warp_wait_fix: expected one call site, found {count} in {path}",
              file=sys.stderr)
        return 1

    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(text.replace(old, new, 1))
    print(f"apply_warp_wait_fix: patched {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
