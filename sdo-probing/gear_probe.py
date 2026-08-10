#!/usr/bin/env python3
"""gear_probe.py -- does 0x6091 (gear ratio) touch position feedback?

The motor stays disabled: you turn the shaft BY HAND, the script only
watches the raw position counter (0x6064). Run it once per gear setting,
turning the shaft the same number of marked revolutions each time.

If 0x6091 scales feedback, the counts-per-hand-revolution will differ
between the two runs. If it does not, they stay equal.

Usage:
    python3 gear_probe.py -p 3 --seconds 25 --turns 5
"""
import argparse
import subprocess
import time


def sdo_up(pos, index, sub, typ):
    out = subprocess.check_output(
        ["ethercat", "upload", f"-p{pos}", "--type", typ, index, str(sub)],
        text=True)
    return int(out.split()[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--position", type=int, required=True)
    ap.add_argument("--seconds", type=float, default=25.0)
    ap.add_argument("--turns", type=float, default=5.0,
                    help="how many hand revolutions you will make")
    ap.add_argument("--cpr", type=int, default=8388608)
    args = ap.parse_args()
    pos = args.position

    gear_n = sdo_up(pos, "0x6091", 1, "uint32")
    gear_d = sdo_up(pos, "0x6091", 2, "uint32")
    sw = sdo_up(pos, "0x6041", 0, "uint16")
    torque_on = bool(sw & 0x0004)
    print(f"0x6091 = {gear_n}:{gear_d} | statusword=0x{sw:04X} "
          f"| torque {'ON -- STOP, do not touch' if torque_on else 'off (shaft free)'}")
    if torque_on:
        raise SystemExit("drive is enabled; refusing to ask for a hand turn")

    start = sdo_up(pos, "0x6064", 0, "int32")
    print(f"start counter = {start}")
    print(f">>> TURN THE SHAFT {args.turns} REVOLUTIONS BY HAND NOW "
          f"({args.seconds:.0f}s) <<<", flush=True)

    t0 = time.time()
    last_print = 0.0
    while time.time() - t0 < args.seconds:
        time.sleep(0.3)
        now = sdo_up(pos, "0x6064", 0, "int32")
        d = (now - start + 2**31) % 2**32 - 2**31
        if time.time() - t0 - last_print >= 3.0:
            last_print = time.time() - t0
            print(f"  t={last_print:4.1f}s  delta={d:>12}  "
                  f"= {d / args.cpr:+.3f} rev", flush=True)

    end = sdo_up(pos, "0x6064", 0, "int32")
    delta = (end - start + 2**31) % 2**32 - 2**31
    print(f"end counter   = {end}")
    print(f"delta         = {delta} counts = {delta / args.cpr:+.4f} rev "
          f"(nominal cpr {args.cpr})")
    if args.turns:
        print(f"counts per hand revolution = {delta / args.turns:,.0f} "
              f"(you said {args.turns} turns)")


if __name__ == "__main__":
    main()
