# LED and DPI protocol of the ROCCAT Burst Pro Air

Worked out on 2026-09-03 from USB captures of ROCCAT Swarm 1.9481 running in a
VMware VM while `usbmon` recorded on the Linux host. Every claim here was checked
against three independent captures, and the rebuilt packets come out
byte-identical to Swarm's.

## Devices

| USB ID | Device | Lighting controllable |
|---|---|---|
| `1e7d:2cab` | Burst Pro Air, wired | **yes**, see below |
| `1e7d:2ca6` | Burst Pro Air dongle | no, it does not accept these packets |
| `1e7d:3a56` | Torch microphone | not investigated |

The mouse exposes three HID interfaces (`input0`, `input1`, `input2`).
Configuration goes over **interface 2**.

## Transport

Every command is a HID **feature report `0x06`** to interface 2, always exactly
**30 bytes** (`SET_REPORT`, `bmRequestType=0x21`, `bRequest=0x09`,
`wValue=0x0306`, `wIndex=2`, `wLength=30`).

After **every** command Swarm reads the status, and the mouse insists on it:

```
write:  06 00 44 07 00 …
read:   06 00 44 08 06 01 00 5a ff 67 0b 05 05 05 05 4b … 7e …   (battery level among others)
```

Without that handshake the mouse drops the commands, silently and without an
error.

## Battery level

The status answer carries the charge, so no extra command is needed:

```
06 00 44 08 06 01 00 5a ff 76 0b …
                     ^^    ^^^^^
                     |     byte 9/10: cell voltage, 16 bit little endian
                     byte 7: charge in percent
```

Byte 7 was read as `0x64` = 100 and `0x5a` = 90, matching what Swarm displays at
the same moment. Byte 9/10 tracks the charge: 3021 at 100 percent, 2919 and 2934
at 90 percent, which reads as millivolts.

This works **wired only**. The dongle answers the same handshake with an empty
`06 00 44 0c 00 …` on every one of its interfaces. Over Bluetooth the mouse
offers the standard **GATT Battery Service** (`0x180f`) instead, and it reports
the same number.

Over Bluetooth the mouse **pushes the charge every 9.8 seconds**. The Battery
Level characteristic `0x2a19` is declared `read, notify`, and notify is not a
broadcast: the device sends only once a client has set the notification bit, and
the subscription drops when that client goes away. Subscribed over a connection
held open, 80 notifications arrived in 30 minutes, every one of them carrying the
same value of 90, so the interval does not depend on a change. 69 of the gaps
were 9.8 seconds. The outliers are sleep: pauses of 54.6, 66.3, 90.5 and once
870.1 seconds with nothing at all, and after **every** such pause the next
notification came 4.9 seconds later, half a step, before the grid resumed. So the
mouse reports every ten seconds while awake, goes completely silent asleep, and
sends immediately on waking. With nobody subscribed nothing is sent at all.

### Over the dongle

Worked out on 2026-09-05 from a `usbmon` capture of Swarm running in a VM with
the dongle passed through, then replayed on Linux, where both routes answer.

```
write:  06 01 44 07 00 …
read:   06 01 44 08 06 01 01 5a ff 2a 0b …
                          ^^    ^^^^^
                          |     byte 9/10: cell voltage in mV
                          byte 7: charge in percent
```

Same layout as the wired answer. The single difference is **byte 1**: `01`
addresses the mouse behind the dongle, `00` addresses the dongle itself. Swarm
uses `00` for dongle commands (`13`, `25`, `00`) and `01` for everything meant
for the mouse (`35`, `43`, `44`, `45`, `46`, `47`, `49`, `4b`, `4e`, `4f`).

A second route has the value pushed on the interrupt endpoint of interface 2,
where it arrives as report `0x08` without a further request:

```
write:  06 01 49 06 01 04 …
report: 08 00 53 29 0b 01 5a 01 ff 03 …
                 ^^^^^    ^^
                 mV, 16 bit LE
                          charge in percent
```

That is one report per command, not a subscription: four commands produced three
reports and never more. Swarm itself polls about every 69 seconds.

### One command unlocks it

Freshly plugged in, the dongle answers the battery command with the empty
`06 01 44 0c 00 …`. **One command changes that, and it has to come first:**

```
06 00 00 04        once per plug cycle, addressed to the dongle itself
06 01 44 07 00     any number of times after that
```

Checked on 2026-09-05 across three plug cycles, each one conclusive on its own.
First: bare command empty, Swarm's full preamble made it answer, and the bare
command answered afterwards too, so the unlock lives in the dongle until it is
unplugged. Second: the preamble sent one command at a time, `06 00 13 07 02`
changed nothing, `06 00 00 04` flipped it. Third: `06 00 00 04` on its own is
enough.

The command is addressed to the dongle, not to the mouse, and its own answer is
empty. Swarm repeats it together with `06 00 00 05` for as long as it runs, 140
times in seven minutes. The voltages read back move from call to call (2846 to
2866 mV at a steady 90 percent), so the value is live rather than a stored copy.

### Configuration can be read back over the dongle

Unlike the wired path, the stored pages come back:

```
write:  06 01 46 06 02 <page> <profile>
write:  06 01 46 07 02 <page> <profile>
read:   06 01 46 08 19 06 3f 01 06 06 07 02 20 03 c4 09 ea 0b …   the DPI block
read:   06 01 46 08 19 80 0c 00 00 03 01 06 54 0f 00 00 …         the lighting block
```

Two fields in the dongle's own reports look like candidates but are not the
charge: the five vendor bytes of the mouse report (`01 ab 2c 62 00`, usage
`0xf1`, interface 0) and bytes 8/9 of the DPI button reports (`3e 03`). Both
stayed byte-identical across a drop from 100 to 90 percent.

Two ways further into the dongle were tried on 2026-09-05, both dead ends. Byte 1
of the handshake is **not a device address**: swept over `00` to `07` and `ff` on
all three interfaces, the dongle echoes the value back and still answers
`06 <byte 1> 44 0c 00 …`, where a real device index would have rejected the
unknown ones. And input report `0x0c`, declared with 63 bytes in the descriptor
of interface 2 but never sent by the device, is **not a second channel**: fetched
with `HIDIOCGINPUT` it returns whatever was last exchanged on any of the three
interfaces, which is to say all three read from one buffer inside the device.

**The dongle's feature channel cannot be probed at all.** OpenRGB's dongle
driver uses the same transport as the wired one, feature report `0x06` over 30
bytes, but the header `06 01 4c 06 …`: address `01` and command `4c` where the
wire uses `00` and `46`. If writing maps `46` to `4c`, reading should map `44` to
`4a`, so `06 01 4a 07 00`, `06 01 4c 07 00` and `06 01 44 07 00` were sent on
interfaces 0 and 2, with `06 00 44 07 00` as the control. The dongle echoes
**every** header back and stamps byte 3 with `0c`, always answering
`06 <address> <command> 0c 00 …`. Wired, that byte reads `08` and data follows.
Byte 3 is a state, not a length, and `0c` means "nothing for that". So sweeping
the command space over this channel cannot find anything: no answer differs from
any other, and a hit would not be recognisable as one.

One path on interface 2 is still untested: the pair of **output report `0x09`**
(29 bytes) and **input report `0x0c`** (63 bytes), both declared in the
descriptor, neither ever used. Unlike the feature channel that one is
distinguishable, since an answer would arrive as its own 63-byte report.

## The apply sequence

```
06 00 46 06 02 00 01                    select page 0
06 00 46 06 19 06 3f 01 06 06 07 …      write the DPI block (26 bytes)
06 00 46 06 02 01 01                    select page 1
06 00 46 06 19 80 0c  + block[0:23]     lighting, part A
06 00 46 06 02 02 01                    select page 2
06 00 46 06 0d        + block[23:48]    lighting, part B
06 00 4e 06 04 01 00 00 ff              apply (write into the profile)
```

Swarm leaves about 80 ms between commands.

**The sequence is mandatory.** Checked on the device: page 0 followed by the
apply is discarded without a word, the DPI stages stay as they were. Only with
pages 1 and 2 in the same run does the mouse take the DPI block. If you want to
change the DPI alone, you still have to write the lighting with it.

## Lighting block (48 bytes)

```
byte  0.. 8   header, never changes:  00 00 03 01 06 54 0f 00 00
byte  9..28   four zone entries, 5 bytes each: zone, brightness, R, G, B
byte 29..33   trailer:                01 64 ff ff ff
byte 34..35   checksum, 16 bit little endian
byte 36..47   zeroes
```

Zone numbers: **1 = scroll wheel, 2 = left button, 3 = right button, 4 = palm
rest.** Brightness `0x00` is 0 %, `0xff` is 100 %.

### Checksum

```
checksum = (sum of all 48 block bytes with the checksum bytes at 0, + 0x0619) & 0xFFFF
```

The start value `0x0619` comes out of the difference across three captures:

| Capture | Sum without checksum bytes | Stored value | Difference |
|---|---|---|---|
| left button only | `0x0ee6` | `0x14ff` | `0x0619` |
| all four zones set | `0x0e59` | `0x1472` | `0x0619` |
| everything white | `0x0fcd` | `0x15e6` | `0x0619` |

## DPI block (26 bytes)

Measured on the device on 2026-09-03: values written, result read back from the
reports the mouse sends (see below).

```
byte  0      19          length of the 25 bytes that follow
byte  1.. 5  06 3f 01 06 06   header, taken over unchanged
byte  6      stage mask
byte  7      start stage, counted from 0 (0 = first stage)
byte  8..25  nine values, 16 bit little endian each
```

The nine values are **six stage slots** and **three fixed values** (800, 1200,
1600) that stayed the same across all captures and did nothing when changed.

### Stage mask

Not a free bit field but a **thermometer code**: `mask = (1 << stages) - 1`.

| Mask | Stages | Checked |
|---|---|---|
| `0x01` | 1 | yes |
| `0x07` | 3 | yes, the state the mouse ships in |
| `0x1f` | 5 | yes |
| `0x21` | n/a | yes: **invalid**, the mouse falls back to **one** stage |

As a free bitmask `0x21` would mean slot 1 and slot 6 and should have given two
stages. Exactly one was left, which is what makes it a thermometer code.

Unused slots are filled anyway; their content does not matter.

### Start stage (byte 7)

The stage the mouse currently sits on. Measured by writing `2` into byte 7 and
then pressing the DPI button once: the mouse reported stage 1, so it had been on
stage **3**. The value counts **from 0**.

The byte lives in the stored profile and **survives sleep**: written with start
stage 3, the mouse was left to fall asleep and woke up on stage 3. Written with
`0` it always wakes on the first stage, no matter which one was picked at the
button before. That is what made the DPI "reset itself every now and then".

### No checksum

The DPI block has none, unlike the lighting block. Shown by `3f 01` staying
unchanged while all nine values and the mask varied, with the mouse accepting
every block.

## The mouse reports its DPI stage

On **interface 2** (the `hidraw` node belonging to `/input2`) the mouse sends
report `0x08` on its own every time the DPI button is pressed:

```
08 00 ef 67 …                      start
08 00 b0 <stage> …                 stage number, counted from 1
08 00 52 01 20 <DPI 16 bit LE> 00  current DPI value
08 00 52 01 00 <DPI 16 bit LE> 00
08 00 ef e7 …                      end
```

This is the measuring tool the DPI block was worked out with: whatever you wrote
comes back here. It is not a way to **read** the stored configuration, the report
only appears on a button press. To watch it:

```bash
python3 -c "
import os, select
fd = os.open('/dev/hidraw2', os.O_RDONLY | os.O_NONBLOCK)   # the node for /input2
while True:
    if select.select([fd], [], [], 30)[0]:
        b = os.read(fd, 64)
        if b[2] == 0xb0: print('stage', b[3])
        elif b[2] == 0x52 and b[4] == 0x20: print('  DPI', int.from_bytes(b[5:7], 'little'))
"
```

## What cannot be read back

Four kinds of read command (`00 44 06 …` with and without page selection, page
selection through `46` followed by a `GET_FEATURE`) all return the same status
packet `06 00 44 08 …` and never configuration data. Colours and DPI stages
cannot be pulled out of the mouse, which is why the tool stores its own copy.

## What does not work

* **OpenRGB's driver** (`RoccatBurstProAirController`, 2022) only knows the
  dongle `2ca6` and uses the header `06 01 4c …` instead of `06 00 46 …`. On this
  firmware it does nothing, tested wired **and** wireless.
* **Eruption** knows neither `2cab` nor `2ca6`; the device table in
  `eruption/src/hwdevices/mod.rs` lists neither ID, and the fallback
  `generic_mouse` driver has an empty LED function.
* OpenRGB issue #5063 reported this exact wired ID and was closed without a
  solution for lack of a capture.

## Capturing it yourself

```bash
sudo modprobe usbmon
lsusb | grep -i roccat          # find the bus the mouse sits on
sudo tcpdump -i usbmon1 -s 256 -U -w capture.pcap
```

Then let Swarm set the colours in a VM with the mouse passed through, and read
the feature reports out of the capture.
