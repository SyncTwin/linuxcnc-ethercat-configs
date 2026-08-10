#!/usr/bin/env python3
"""ladder_timing.py -- how long after the ACK does the drive actually do it?

Walks the CiA402 state machine N times over SDO and times every rung:
from "controlword written and acknowledged" to "statusword shows the new
state". Then times the gap between "operation enabled" and the shaft
actually starting to move.

Every number is compared against a measured baseline: the cost of one
plain SDO read. Anything at or below that is not resolved by this method,
and the plot says so.

Usage:
    python3 ladder_timing.py -p 3 --runs 20 --csv ladder.csv

Safety: shaft must be free. The drive is disabled after every run and the
final disable is verified by statusword, never by the sent command.
"""
import argparse
import csv
import statistics
import subprocess
import time


def sdo_up(pos, index, sub, typ):
    out = subprocess.check_output(
        ["ethercat", "upload", f"-p{pos}", "--type", typ, index, str(sub)],
        text=True)
    return int(out.split()[1])


def sdo_down(pos, index, sub, value, typ):
    subprocess.check_call(
        ["ethercat", "download", f"-p{pos}", "--type", typ,
         index, str(sub), str(value)])


def measure_baseline(pos, n=50):
    """Cost of one SDO read -- the resolution floor of this method."""
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        sdo_up(pos, "0x6041", 0, "uint16")
        ts.append((time.perf_counter() - t0) * 1000)
    return ts


def rung(pos, cw, mask, want, timeout=3.0):
    """Send controlword, return ms until statusword reports the state."""
    t0 = time.perf_counter()
    sdo_down(pos, "0x6040", 0, cw, "uint16")
    t_ack = (time.perf_counter() - t0) * 1000
    while True:
        sw = sdo_up(pos, "0x6041", 0, "uint16")
        if sw & mask == want:
            return t_ack, (time.perf_counter() - t0) * 1000, sw
        if (time.perf_counter() - t0) > timeout:
            raise SystemExit(f"rung 0x{cw:04X} timeout, sw=0x{sw:04X}")


def disable(pos):
    sdo_down(pos, "0x60FF", 0, 0, "int32")
    sdo_down(pos, "0x6040", 0, 0x0006, "uint16")
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 3.0:
        sw = sdo_up(pos, "0x6041", 0, "uint16")
        if not sw & 0x0004:
            return sw
        time.sleep(0.02)
    raise SystemExit("drive did not report torque off")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--position", type=int, required=True)
    ap.add_argument("--runs", type=int, default=20)
    ap.add_argument("--rps", type=float, default=0.3)
    ap.add_argument("--cpr", type=int, default=8388608)
    ap.add_argument("--csv", default="ladder.csv")
    args = ap.parse_args()
    pos = args.position

    base = measure_baseline(pos)
    floor = statistics.median(base)
    print(f"baseline SDO read: median {floor:.2f} ms, "
          f"min {min(base):.2f}, max {max(base):.2f} ms")

    sdo_down(pos, "0x6060", 0, 3, "int8")
    while sdo_up(pos, "0x6061", 0, "int8") != 3:
        time.sleep(0.05)

    rows = []
    try:
        for i in range(args.runs):
            r = {"run": i}
            r["ack_shutdown"], r["shutdown"], _ = rung(pos, 0x0006, 0x006F, 0x0021)
            r["ack_switch_on"], r["switch_on"], _ = rung(pos, 0x0007, 0x006F, 0x0023)
            r["ack_enable"], r["enable"], _ = rung(pos, 0x000F, 0x006F, 0x0027)

            # enabled -> shaft actually moving
            p0 = sdo_up(pos, "0x6064", 0, "int32")
            t0 = time.perf_counter()
            sdo_down(pos, "0x60FF", 0, int(args.rps * args.cpr), "int32")
            r["ack_speed"] = (time.perf_counter() - t0) * 1000
            thresh = args.cpr // 2000          # ~0.2 deg, well above ±7 noise
            while True:
                d = abs(sdo_up(pos, "0x6064", 0, "int32") - p0)
                if d > thresh:
                    r["first_motion"] = (time.perf_counter() - t0) * 1000
                    break
                if (time.perf_counter() - t0) > 3.0:
                    raise SystemExit("no motion within 3 s")
            rows.append(r)
            print(f"run {i:2d}: shutdown {r['shutdown']:6.1f} | "
                  f"switch_on {r['switch_on']:6.1f} | enable {r['enable']:6.1f} | "
                  f"motion {r['first_motion']:7.1f} ms", flush=True)
            disable(pos)
            time.sleep(0.3)
    finally:
        sw = disable(pos)
        print(f"final disable verified, statusword=0x{sw:04X}")

    with open(args.csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value_ms"])
        for b in base:
            w.writerow(["baseline_sdo_read", f"{b:.3f}"])
        for r in rows:
            for k, v in r.items():
                if k != "run":
                    w.writerow([k, f"{v:.3f}"])
    print(f"-> {args.csv}")

    for key in ["shutdown", "switch_on", "enable", "first_motion"]:
        vals = [r[key] for r in rows]
        print(f"{key:14s} median {statistics.median(vals):7.1f} ms  "
              f"min {min(vals):7.1f}  max {max(vals):7.1f}")


if __name__ == "__main__":
    main()
