# HomeControl: HomeView wall panel for Home Assistant

This repo makes a three-view, Apple HomeView-style Home Assistant dashboard for a wall-mounted **iPad Air 2 (iPadOS 15.8)** in landscape.
It's based on Shane Whatley's DIY HomeView design and adapted to the iPad Air 2's older Safari and 2 GB of RAM.

| View | What's on it |
|---|---|
| **Widgets** | StandBy-style date, analog clock, photo frame, weather and upcoming events. Always on, no screensaver. |
| **Home** | Clock, weather, doorbell preview, glass tiles for locks, garage, lights, fan and vacuum, scene pills and an agenda bar |
| **Cameras** | Snapshot grid of 1–9 cameras. Tap one for a live pop-up with Prev / Next and lock/garage controls. |

It also includes an idle clock screensaver, motion wake, an automatic doorbell pop-up, and optional battery-saving charging.

**→ Start with [docs/SETUP-iPad-Air-2.md](docs/SETUP-iPad-Air-2.md).**

## Layout

```
homeview/config.yaml           <- the only file you edit (your entity IDs)
homeview/base.yaml             design system: button-card templates + plugin settings
homeview/build_dashboard.py    generates dist/ from the two files above
dist/homeview_dashboard.yaml   paste into the dashboard's Raw configuration editor
dist/automations/*.yaml        paste each into a new automation (Edit in YAML)
tools/prepare_slideshow.py     resizes + numbers photos for the photo frame
reference/                     the original blueprint and YAML this is based on
```

## Rebuild after editing the config

```bash
pip install pyyaml
```

```bash
python3 homeview/build_dashboard.py
```

The build lists any `your_…` placeholders that still need a real entity ID, and it fails if a pop-up link has no matching pop-up.
