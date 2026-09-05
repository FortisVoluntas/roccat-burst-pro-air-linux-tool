# Burst Pro Air

Lighting and DPI control for the ROCCAT Burst Pro Air on Linux.

![The application window](docs/screenshot.png)

ROCCAT never shipped Swarm for Linux, and the two tools that would normally step
in do not reach this mouse. OpenRGB's driver was written for the wireless dongle
and sends a packet header that the current firmware ignores; Eruption does not
know either device ID. So I recorded the USB traffic with `usbmon` while Swarm
was setting colours inside a VM, and rebuilt the protocol from the captures. The
packets this sends are byte-identical to Swarm's.

Everything goes into the profile stored inside the mouse, so the colours and the
DPI stages survive a reboot and stay in place over the dongle.

## Requirements

* Python 3 and PyQt6 (`python3-pyqt6` on Fedora, Nobara, Debian and Ubuntu,
  `python-pyqt6` on Arch). The command line tool needs Python alone.
* The mouse plugged in **by cable** (`1e7d:2cab`). The dongle (`1e7d:2ca6`) will
  not accept these packets, so plug the cable in to change something and unplug
  it afterwards.

Written on Nobara 44 with KDE, Python 3.14 and PyQt6 6.11.

## Install

```
git clone https://github.com/FortisVoluntas/roccat-burst-pro-air-linux-tool.git
cd roccat-burst-pro-air-linux-tool
./install.sh
```

The script does two things: it writes a menu entry pointing back at the folder
you cloned into, and it installs the udev rule, which is the step that asks for
your password. The tool stays where it is and runs from there, so keep the
folder.

To undo it, delete `~/.local/share/applications/burst-pro-air.desktop` and
`/etc/udev/rules.d/99-roccat-burst-pro-air.rules`, then remove the folder.

Doing it by hand works as well, see Use and Permissions.

## Use

The window, with a drawn top view of the mouse. Click a colour patch to pick the
colour of that zone, the slider next to it sets the brightness:

```
./burst-pro-air
```

Or from a shell, one argument per zone in the order scroll wheel, left button,
right button, palm rest:

```
./bpa_led.py 000000:0 FFFFFF FFFFFF FFFFFF          # wheel off, the rest white
./bpa_led.py D8E04A FF9D2E FF9D2E 3FD23F            # a colour per zone
./bpa_led.py FFFFFF FFFFFF FFFFFF FFFFFF 800,2500,3050:3
```

A zone is `RRGGBB` or `RRGGBB:brightness` with brightness in percent. The last
argument holds one to six DPI stages, optionally followed by `:startstage`, the
stage the mouse wakes up on.

The charge is readable on both connections, wired and over the 2.4 GHz dongle:

```
./bpa_led.py akku
Akku 90 Prozent, Zellspannung 2854 mV
```

`install.sh` puts the desktop entry in place. By hand, copy
`burst-pro-air.desktop` to `~/.local/share/applications/` and write the real path
into `Exec=`, in quotes if it contains spaces.

## Battery icon in the panel

`bpa_tray.py` puts a mouse next to the clock. Its colour carries the charge in
steps of 25 percent, green, yellow, orange, red, and hovering over it shows the
exact percentage and the cell voltage. It looks once a minute, the first time a
minute after login so the mouse is certainly enumerated by then.

It shows itself only while the mouse is reachable over USB, wired or through the
dongle. Over Bluetooth it stays hidden: there the desktop already tracks the
charge through UPower, and there would be two icons for one mouse.

`install.sh` writes the autostart entry. By hand, copy
`burst-pro-air-tray.desktop` to `~/.config/autostart/` and write the real path
into `Exec=`, in quotes if it contains spaces.

**It needs a panel that speaks StatusNotifierItem.** KDE Plasma, XFCE, Cinnamon,
MATE, LXQt and Budgie do. **GNOME Shell does not:** it dropped the tray area and
needs the extension *AppIndicator and KStatusNotifierItem Support*, without which
the icon never appears and says nothing about why. Written and tested on KDE
Plasma under Wayland; the other environments follow from the protocol, they were
not tried here.

## Permissions

The tool writes to `/dev/hidraw*`. If OpenRGB is installed its udev rule already
opens that up; otherwise install the rule shipped here:

```
sudo cp udev/99-roccat-burst-pro-air.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger
```

Then replug the cable.

## What it cannot do

* Read the current settings back. The mouse answers every read command with the
  same status packet and never with configuration data, so the tool keeps its
  own copy in `~/.config/burst-pro-air/zonen.json`.
* Write colours without DPI. The mouse only accepts the DPI block together with
  the lighting pages, so applying always writes both. If you change the stages
  in Swarm later, the next apply puts the stored ones back.

## Protocol

[docs/protocol.md](docs/protocol.md) has the whole thing: transport, the command
sequence, both block layouts, the checksum and its start value, and the reports
the mouse sends when you press its DPI button. Enough to add the device to
another tool.

## License

GPL-3.0-or-later.
