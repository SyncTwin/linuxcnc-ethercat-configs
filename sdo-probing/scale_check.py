#!/usr/bin/env python3
"""scale_check.py -- measure a CiA402 drive's velocity scale via SDO only.

Spins the motor in Profile Velocity mode using nothing but the `ethercat`
CLI (IgH master): no PDO cycle, no realtime, no vendor software.
Measured speed is derived from the raw position counter (0x6064) vs wall
clock -- deliberately NOT from 0x606C, which goes through the very scale
we are checking.

Usage:
    python3 scale_check.py -p 3 --rps 0.5 --seconds 4 [--cpr 8388608] [--csv out.csv]

Safety: the shaft must be free. Ctrl-C or any error disables the drive
(controlword 0x0006) and the script verifies "operation enabled" is gone
from the statusword before exiting -- sent commands are not trusted.
"""
import argparse
import csv
import subprocess
import sys
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


def wait_status(pos, mask, want, timeout=3.0):
    """Wait until (statusword & mask) == want. Trust bits, not sent commands."""
    deadline = time.time() + timeout
    sw = -1
    while time.time() < deadline:
        sw = sdo_up(pos, "0x6041", 0, "uint16")
        if sw & 0x0008:
            raise SystemExit(f"drive FAULT, statusword=0x{sw:04X}")
        if sw & mask == want:
            return sw
        time.sleep(0.05)
    raise SystemExit(f"timeout: statusword=0x{sw:04X}, "
                     f"wanted &0x{mask:04X}==0x{want:04X}")


def disable(pos):
    """Shutdown and verify by statusword that torque is actually gone."""
    sdo_down(pos, "0x60FF", 0, 0, "int32")
    sdo_down(pos, "0x6040", 0, 0x0006, "uint16")
    sw = wait_status(pos, 0x0004, 0x0000, timeout=3.0)  # op-enabled bit off
    print(f"disabled, statusword=0x{sw:04X} (operation-enabled bit clear)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--position", type=int, required=True)
    ap.add_argument("--rps", type=float, default=0.5, help="target rev/s")
    ap.add_argument("--seconds", type=float, default=4.0)
    ap.add_argument("--cpr", type=int, default=8388608,
                    help="encoder counts per revolution (23-bit default)")
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()
    pos = args.position

    # -- mode: request in 0x6060, confirm in 0x6061 (ack is not done) --
    sdo_down(pos, "0x6060", 0, 3, "int8")            # Profile Velocity
    t0 = time.time()
    while sdo_up(pos, "0x6061", 0, "int8") != 3:
        if time.time() - t0 > 2.0:
            raise SystemExit("0x6060 write acked, but 0x6061 never showed 3")
        time.sleep(0.05)
    print(f"mode PV confirmed by 0x6061 after {time.time() - t0:.3f}s")

    # -- CiA402 ladder: each rung confirmed by statusword bits --
    try:
        sdo_down(pos, "0x6040", 0, 0x0006, "uint16")  # shutdown
        wait_status(pos, 0x006F, 0x0021)              # ready to switch on
        sdo_down(pos, "0x6040", 0, 0x0007, "uint16")  # switch on
        wait_status(pos, 0x006F, 0x0023)              # switched on
        sdo_down(pos, "0x6040", 0, 0x000F, "uint16")  # enable operation
        wait_status(pos, 0x006F, 0x0027)              # operation enabled
        print("operation enabled (confirmed by statusword)")

        target = int(args.rps * args.cpr)
        sdo_down(pos, "0x60FF", 0, target, "int32")
        print(f"target 0x60FF = {target} counts/s ({args.rps} rev/s)")

        samples = []
        t_start = time.time()
        while time.time() - t_start < args.seconds:
            t = time.time() - t_start
            raw = sdo_up(pos, "0x6064", 0, "int32")
            samples.append((t, raw))
            time.sleep(0.1)
    finally:
        disable(pos)

    # -- velocity from raw counter, wrap-safe successive diffs --
    total = 0
    for (t_a, p_a), (t_b, p_b) in zip(samples, samples[1:]):
        d = (p_b - p_a + 2**31) % 2**32 - 2**31
        total += d
    dt = samples[-1][0] - samples[0][0]
    meas_rps = total / dt / args.cpr
    err = (meas_rps - args.rps) / args.rps * 100
    print(f"measured: {meas_rps:.4f} rev/s vs target {args.rps} "
          f"({err:+.2f}%) over {dt:.2f}s, {len(samples)} samples")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_s", "pos_counts"])
            w.writerows(samples)
        print(f"samples -> {args.csv}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted -- disabling")
        disable(int(sys.argv[sys.argv.index("-p") + 1]))
        raise
