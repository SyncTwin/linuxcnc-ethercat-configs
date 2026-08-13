# Wecon VD3E — open source LinuxCNC driver

An EtherCAT driver for the **Wecon VD3E** servo drive, written for
`linuxcnc-ethercat` (the component that connects EtherCAT devices to LinuxCNC).
Free software, GPL v2, same license as the project it belongs to.

> **Status, 2026-08-13.** The driver is written, it compiles, and the device
> facts below were confirmed against the vendor ESI and against a real drive on
> our bench. It has **not yet been run to `OP` state with this driver** — the
> same drive does reach `OP` through the generic `basic_cia402` path. This page
> is updated the moment that changes. We would rather publish an honest status
> than a claim.

## Why this driver exists

`linuxcnc-ethercat` supports 272 devices from nine vendors. **209 of them are
Beckhoff** — 77 percent of the catalog. Only four families of servo drives are
in there at all.

Wecon is not in the catalog. Neither is Inovance, Mitsubishi, Schneider,
Yaskawa, Siemens, Panasonic, Estun, Veichi, Sanyo Denki or Fanuc.

This is nobody's fault. An open hardware catalog contains what somebody once
sat down and added. We had eight EtherCAT devices from five vendors on one
bench, used this project for over a year, and had contributed nothing back.

Without a driver the drive still runs — through `generic` or `basic_cia402` —
but you write the PDO map by hand:

```xml
<slave idx="0" type="generic" vid="00000eff" pid="0d3e0001" configPdos="true">
  <syncManager idx="2" dir="out">
    <pdo idx="1701">
      <pdoEntry idx="6040" subIdx="00" bitLen="16" halPin="controlword" halType="u32"/>
      ... thirty more lines ...
```

With the driver:

```xml
<slave idx="0" type="VD3E" name="x"/>
```

## What we established about this drive

Facts, with how each was obtained. Nothing here is guessed.

| fact | value | source |
|---|---|---|
| Vendor ID | `0x00000eff` | live bus, `ethercat slaves -v` |
| Product code | `0x0d3e0001` | live bus |
| Revision | `0x00000073` | live bus, matches ESI V1.15.0 |
| Mailbox protocols | CoE only — no FoE, no EoE | live bus |
| PDO assignment | exactly **one** RxPDO and **one** TxPDO (`0x1c12`/`0x1c13` hold a single entry, default `0x1701`/`0x1b01`) | ESI |
| Mapping limit | **10 entries** per mapping object (subindex 0 default `0x0a`) | ESI |
| Available mappings | out: `0x1600`, `0x1701`, `0x1702` · in: `0x1a00`, `0x1b01` | ESI |
| Distributed Clocks | `AssignActivate 0x300`, sync0 = master period; Free Run also offered | ESI |
| Object dictionary | 109 objects, readable over the bus (SDO-Info works) | live bus, matches ESI exactly |
| Modes | pp, pv, tq, hm, csp, csv, cst | vendor manual |
| `0x608f`, `0x6092` | **do not exist** — "object does not exist" | live bus |
| Encoder resolution | 8388608 counts/rev (23-bit absolute, multi-turn) | measured by hand, see below |
| Complete access on SDO write | **rejected** by this drive (a Mitsubishi MR-J4 on the same bus accepts it) | live bus |

### How the encoder resolution was measured

Since `0x608f` does not exist, the resolution cannot be read from the bus at
all. We measured it physically: torque off, mark on the shaft, five full turns
by hand, counting the increments of `0x6064`.

| `0x6091` gear ratio | increment over 5 turns | per turn | deviation from 2²³ |
|---|---|---|---|
| 1:1 | 42 203 264 | 8 440 653 | +0.6% |
| 2:1 | 20 787 053 | 4 157 411 | −0.9% |

The ratio between the two rows is 2.03, so `0x6091` divides position exactly as
the standard says, and the resolution is 8388608 counts per revolution.

Standstill noise: ±7 counts out of 8.4 million.

### One thing we do not understand

At very low speed in Profile Velocity mode the instantaneous velocity oscillates:
**±12% at 0.01 rev/s**, about ±5% at 0.2 rev/s, with a period of roughly 2
seconds. The average velocity is correct to within 0.01%, so this is not a
scaling problem. We do not know whether this is normal cogging at low speed or a
tuning issue. We have asked the manufacturer.

## Installing

Headers must match the installed runtime version. A header from a different
build is worse than a missing one.

```bash
sudo apt-get install -y build-essential pkg-config git libexpat1-dev \
    libethercat-dev linuxcnc-uspace-dev

git clone -b feat/wecon-vd3e https://github.com/SyncTwin/linuxcnc-ethercat.git
cd linuxcnc-ethercat
make configure && make build && sudo make install
```

**Stop LinuxCNC first.** Replacing `lcec.so` under a running machine fails in a
way that looks like a configuration problem.

Verify that the module really contains the driver — checking the package version
is not enough, because `dpkg` ranks a snapshot suffix above a normal version and
a different package can win silently:

```bash
strings /usr/lib/linuxcnc/modules/lcec.so | grep -x VD3E
```

## Using

```xml
<masters>
  <master idx="0" appTimePeriod="1000000" refClockSyncCycles="1">
    <slave idx="0" type="VD3E" name="x"/>
  </master>
</masters>
```

`appTimePeriod` must equal the LinuxCNC servo thread period. `name` determines
the HAL pin names.

```hal
net x-pos-cmd  joint.0.motor-pos-cmd        => lcec.0.x.srv-target-position
net x-pos-fb   lcec.0.x.srv-actual-position => joint.0.motor-pos-fb
```

Useful pins: `srv-actual-torque`, `srv-actual-following-error`, `srv-error-code`,
`srv-opmode-display` (8 = CSP), `slave-state-op`.

**Set the scale by hand.** The drive cannot report its encoder resolution — see
above. Use 8388608 counts/rev together with your ballscrew pitch.

### Not enabled on purpose

Touch probe (`0x60b8`..`0x60bd`) exists on this drive and `0x60b8` is even in the
factory RxPDO, but it is not enabled in the driver: we have not run it on
hardware, and a wrong mapping costs the transition to `OP`. An empty slot is
more honest than an untested line.

### VD5 and VD5L

Not supported. They share product code `0x0d510001` and differ only by revision,
so they need revision matching rather than a second product code — and neither
has been on our bench. If you have one, see below.

## Help us fill the catalog

The reason most drives are missing is not difficulty. A vendor driver is about
twenty meaningful lines; the `cia402` class in the upstream project does the
real work. What is missing is **information about the device** — and that lives
with the people who own the hardware.

If you run a drive that is not in the catalog, four commands cover almost
everything a driver needs:

```bash
ethercat slaves -v            # identity, mailbox protocols, current state
ethercat pdos -p<N>           # which PDOs are assigned by default
ethercat sdos -p<N> | wc -l   # is the dictionary readable over the bus?
ethercat sdos -p<N> | grep 6502   # which modes the drive claims
```

That last count is more interesting than it sounds. On our bench three drives
answered **809**, **109** and **zero** objects. A drive that reports nothing has
to be described by hand, and that is exactly where an ESI file becomes the only
source of truth.

So: **send us the ESI file and those four outputs**, and we will write the
driver and submit it upstream with your name on the report. Open an issue in
this repository, or in the upstream project directly.

Device registry with identities and known traps: <https://synctwin.ru/ethercat/>

## License and credit

GPL v2, matching `linuxcnc-ethercat`. The driver was developed by SyncTwin
against a drive purchased through normal channels; no vendor documentation under
NDA was used. If the manufacturer's engineers want to review or correct anything
here, we will credit them in the commit.
