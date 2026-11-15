#!/usr/bin/env python3
"""Build the HomeView iPad panel.

Reads   homeview/config.yaml   (your entity IDs)
        homeview/base.yaml     (button-card design system + plugin settings)
        homeview/dotmatrix.js  (dot-matrix + label helpers injected into templates)
Writes  dist/homeview_dashboard.yaml  -> paste into the dashboard's Raw configuration editor
        dist/homeview_package.yaml    -> copy to /config/packages/homeview.yaml
                                         (helpers, weather/clock sensors, music script,
                                          camera-alert automations)

The single-screen layout is sized for an iPad Air 2 in landscape
(1024 x 768 CSS px) with kiosk mode hiding the Home Assistant header.

Usage:  python3 homeview/build_dashboard.py [--config path] [--out dir]
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import re
import sys

import yaml

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent

# --- geometry: 20-column grid on 1024 x 768 ----------------------------------
COLS = 20
H_TOP, H_MUSIC, H_DEVICES, H_CAMS = 188, 104, 160, 220

SCREENSAVER = "input_boolean.homeview_screensaver"
MINUTE_SENSOR = "sensor.homeview_minute"
DATE_SENSOR = "sensor.homeview_date"
WEATHER_SENSOR = "sensor.homeview_weather_today"
PLAY_SCRIPT = "script.homeview_play_pause"
POPUP_STYLE = {"bg_color": "#111113", "bg_opacity": "94", "bg_blur": "0"}


# --- helpers -----------------------------------------------------------------
def bc(template, **kw) -> dict:
    card = {"type": "custom:button-card", "template": template}
    card.update({k: v for k, v in kw.items() if v is not None})
    return card


def height(px: int) -> dict:
    return {"card": [{"height": f"{px}px"}]}


def layout(areas: list[str], columns: str, rows: str, fields: dict, padding: str | None = None) -> dict:
    styles = {
        "grid": [
            {"grid-template-areas": " ".join(f'"{r}"' for r in areas)},
            {"grid-template-columns": columns},
            {"grid-template-rows": rows},
        ],
        "custom_fields": {k: [{"min-width": "0"}, {"min-height": "0"}] for k in fields},
    }
    if padding is not None:
        styles["card"] = [{"padding": padding}]
    return bc("hv_layout", styles=styles, custom_fields={k: {"card": v} for k, v in fields.items()})


def popup(hash_: str, name: str, icon: str, cards: list, width: str = "640px", **extra) -> dict:
    head = {"type": "custom:bubble-card", "card_type": "pop-up", "hash": hash_, "name": name,
            "icon": icon, "width_desktop": width, **POPUP_STYLE, **extra}
    return {"type": "vertical-stack", "cards": [head, *cards]}


def action(service: str, entity_id: str, **data) -> dict:
    a = {"action": "perform-action", "perform_action": service, "target": {"entity_id": entity_id}}
    if data:
        a["data"] = data
    return a


def row(names_and_spans: list[tuple[str, int]]) -> str:
    cells = []
    for name, n in names_and_spans:
        cells += [name] * n
    assert len(cells) == COLS, names_and_spans
    return " ".join(cells)


# --- cards -------------------------------------------------------------------
def clock_card() -> dict:
    return bc("hv_clock", styles=height(H_TOP))


def weather_card(cfg) -> dict:
    w = cfg["weather"]["entity"]
    return bc("hv_weather", entity=w, variables={"forecast": WEATHER_SENSOR},
              triggers_update=[w, WEATHER_SENSOR], styles=height(H_TOP))


def calendar_card(cfg) -> dict:
    cals = cfg["calendars"]
    return bc("hv_calendar", variables={"calendars": cals, "max": 3},
              triggers_update=[c["entity"] for c in cals] + [DATE_SENSOR], styles=height(H_TOP))


def device_card(spec, main_tpl: str, dot_tpl: str, default_icon: str, dots: int) -> dict:
    """Fan or light: a bright-when-on container with a toggle and a row of level dots."""
    ent = spec["entity"]
    fields = {"main": bc(main_tpl, entity=ent, name=spec.get("name"), icon=spec.get("icon", default_icon))}
    for i in range(1, dots + 1):
        fields[f"d{i}"] = bc(dot_tpl, entity=ent, variables={"i": i})
    return bc("hv_device", entity=ent, styles={
        "card": [{"height": f"{H_DEVICES}px"}],
        "custom_fields": {k: [{"min-width": "0"}] for k in fields},
    }, custom_fields={k: {"card": v} for k, v in fields.items()})


def fan_card(spec) -> dict:
    return device_card(spec, "hv_fan_main", "hv_speed_dot", "mdi:fan", 6)


def light_card(spec) -> dict:
    return device_card(spec, "hv_light_main", "hv_bright_dot", "mdi:lightbulb", 5)


def camera_tile(i: int, cam) -> dict:
    return bc("hv_camera", entity=cam["snapshot"], variables={"name": cam.get("name", "")},
              tap_action={"action": "navigate", "navigation_path": f"#cam-{i}"},
              styles=height(H_CAMS))


def music_cards(cfg) -> dict:
    p = cfg["music"]["player"]
    return {
        "np": bc("hv_nowplaying", entity=p, styles=height(H_MUSIC)),
        "prev": bc("hv_transport", entity=p, name="Prev", icon="mdi:skip-previous",
                   tap_action=action("media_player.media_previous_track", p), styles=height(H_MUSIC)),
        "play": bc(["hv_transport", "hv_bright_when_on"], entity=p,
                   name="[[[ return entity && entity.state === 'playing' ? 'Pause' : 'Play' ]]]",
                   icon="[[[ return entity && entity.state === 'playing' ? 'mdi:pause' : 'mdi:play' ]]]",
                   tap_action={"action": "perform-action", "perform_action": PLAY_SCRIPT, "haptic": "medium"},
                   styles=height(H_MUSIC)),
        "next": bc("hv_transport", entity=p, name="Next", icon="mdi:skip-next",
                   tap_action=action("media_player.media_next_track", p), styles=height(H_MUSIC)),
        "vol": bc("hv_volume", entity=p, styles=height(H_MUSIC), custom_fields={
            "minus": {"card": bc("hv_round_button", entity=p, icon="mdi:minus",
                                 tap_action=action("media_player.volume_down", p))},
            "plus": {"card": bc("hv_round_button", entity=p, icon="mdi:plus",
                                tap_action=action("media_player.volume_up", p))},
        }),
    }


# --- pop-ups -----------------------------------------------------------------
def weather_popup(cfg) -> dict:
    w = cfg["weather"]["entity"]
    return popup("#weather", "Weather", "mdi:weather-partly-cloudy", [
        {"type": "weather-forecast", "entity": w, "forecast_type": "hourly", "show_current": True, "show_forecast": True},
        {"type": "weather-forecast", "entity": w, "forecast_type": "daily", "show_current": False, "show_forecast": True},
    ])


def calendar_popup(cfg) -> dict:
    return popup("#calendar", "This week", "mdi:calendar-month", [
        {"type": "calendar", "initial_view": "listWeek", "entities": [c["entity"] for c in cfg["calendars"]]},
    ], width="760px")


def camera_popups(cfg) -> list:
    cams = cfg["cameras"]
    n = len(cams)
    out = []
    for i, cam in enumerate(cams, start=1):
        live = {"type": "picture-entity", "entity": cam.get("live") or cam["snapshot"], "camera_view": "live",
                "show_state": False, "show_name": bool(cam.get("name")),
                "tap_action": {"action": "none"}, "hold_action": {"action": "none"}}
        if cam.get("name"):
            live["name"] = cam["name"]
        cards = [live]
        if n > 1:
            nxt = i % n + 1
            prv = (i - 2) % n + 1
            pills = [bc("hv_pill", name="Next camera", icon="mdi:chevron-right",
                        tap_action={"action": "navigate", "navigation_path": f"#cam-{nxt}"})]
            if n > 2:
                pills.insert(0, bc("hv_pill", name="Previous", icon="mdi:chevron-left",
                                   tap_action={"action": "navigate", "navigation_path": f"#cam-{prv}"}))
            cards.append({"type": "horizontal-stack", "cards": pills})
        extra = {}
        if cam.get("alert_sensor"):
            extra = {"trigger": [{"condition": "state", "entity": f"input_boolean.homeview_cam_{i}_alert", "state": "on"}],
                     "trigger_close": True, "auto_close": "30000"}
        out.append(popup(f"#cam-{i}", cam.get("name") or f"Camera {i}", "mdi:cctv", cards, width="900px", **extra))
    return out


# --- the view ----------------------------------------------------------------
def home_view(cfg, warnings: list) -> dict:
    fields: dict = {}
    areas: list[str] = []
    rows: list[int] = []

    # Row 1: clock | weather | calendar
    top = [("clock", 7)]
    fields["clock"] = clock_card()
    has_w, has_c = bool(cfg.get("weather")), bool(cfg.get("calendars"))
    if has_w and has_c:
        top += [("weather", 7), ("cal", 6)]
    elif has_w:
        top += [("weather", 13)]
    elif has_c:
        top += [("cal", 13)]
    else:
        top = [("clock", COLS)]
    if has_w:
        fields["weather"] = weather_card(cfg)
    if has_c:
        fields["cal"] = calendar_card(cfg)
    areas.append(row(top)); rows.append(H_TOP)

    # Row 2: now playing | prev | play | next | volume
    if cfg.get("music"):
        fields.update(music_cards(cfg))
        areas.append(row([("np", 7), ("prev", 2), ("play", 2), ("next", 2), ("vol", 7)])); rows.append(H_MUSIC)

    # Row 3: fans + lights, equal widths
    devices = [fan_card(f) for f in cfg.get("fans") or []] + [light_card(l) for l in cfg.get("lights") or []]
    if devices:
        if len(devices) > 6:
            warnings.append(f"{len(devices)} fans+lights on one row get narrow; 6 or fewer fits best.")
        dev_fields = {f"x{i}": c for i, c in enumerate(devices, start=1)}
        fields["devices"] = layout([" ".join(dev_fields)], f"repeat({len(devices)}, 1fr)", f"{H_DEVICES}px",
                                   dev_fields, padding="0px")
        areas.append(row([("devices", COLS)])); rows.append(H_DEVICES)

    # Row 4: camera snapshots
    cams = cfg.get("cameras") or []
    if cams:
        cam_fields = {f"c{i}": camera_tile(i, c) for i, c in enumerate(cams, start=1)}
        fields["cams"] = layout([" ".join(cam_fields)], f"repeat({len(cams)}, 1fr)", f"{H_CAMS}px",
                                cam_fields, padding="0px")
        areas.append(row([("cams", COLS)])); rows.append(H_CAMS)

    total = sum(rows) + 12 * (len(rows) - 1) + 28
    if total > 736:
        warnings.append(f"Layout is {total}px tall; the iPad shows ~736px without scrolling.")

    cards = [layout(areas, f"repeat({COLS}, 1fr)", " ".join(f"{h}px" for h in rows), fields)]
    if has_w:
        cards.append(weather_popup(cfg))
    if has_c:
        cards.append(calendar_popup(cfg))
    cards += camera_popups(cfg) if cams else []
    return {"title": "Home", "path": "home", "icon": "mdi:home", "type": "panel",
            "background": cfg["dashboard"]["background"],
            "cards": [{"type": "vertical-stack", "cards": cards}]}


# --- Home Assistant package (helpers, sensors, script, automations) ----------
def package(cfg) -> dict:
    pkg: dict = {
        "input_boolean": {
            "homeview_screensaver": {"name": "HomeView Screensaver", "icon": "mdi:monitor-shimmer"},
            "homeview_kiosk": {"name": "HomeView Kiosk", "icon": "mdi:fullscreen"},
        },
        "template": [{
            "triggers": [{"trigger": "time_pattern", "minutes": "/1"},
                         {"trigger": "homeassistant", "event": "start"}],
            "sensor": [
                {"name": "HomeView Minute", "unique_id": "homeview_minute",
                 "icon": "mdi:clock-outline", "state": "{{ now().strftime('%H:%M') }}"},
                {"name": "HomeView Date", "unique_id": "homeview_date",
                 "icon": "mdi:calendar-today", "state": "{{ now().date() | string }}"},
            ],
        }],
    }
    w = (cfg.get("weather") or {}).get("entity")
    if w:
        f = f"(fc['{w}'].forecast | default([]) | first | default({{}}, true))"
        pkg["template"].append({
            "triggers": [{"trigger": "time_pattern", "minutes": "/30"},
                         {"trigger": "homeassistant", "event": "start"}],
            "actions": [{"action": "weather.get_forecasts", "target": {"entity_id": w},
                         "data": {"type": "daily"}, "response_variable": "fc"}],
            "sensor": [{
                "name": "HomeView Weather Today", "unique_id": "homeview_weather_today",
                "icon": "mdi:weather-partly-cloudy",
                "state": f"{{{{ {f}.condition | default('unknown') }}}}",
                "attributes": {
                    "high": f"{{{{ {f}.temperature | default(none) }}}}",
                    "low": f"{{{{ {f}.templow | default(none) }}}}",
                    "rain_chance": f"{{{{ {f}.precipitation_probability | default(none) }}}}",
                    "rain_mm": f"{{{{ {f}.precipitation | default(none) }}}}",
                },
            }],
        })

    m = cfg.get("music")
    if m:
        p, spk = m["player"], m["speaker"]
        spk_jinja = json.dumps(spk)  # double-quoted Jinja string, safe for apostrophes
        pkg["script"] = {"homeview_play_pause": {
            "alias": "HomeView - Play / pause music",
            "description": "Pauses Spotify, or starts it on the Echo if it isn't playing there yet.",
            "mode": "single",
            "icon": "mdi:play-pause",
            "sequence": [{
                "if": [{"condition": "state", "entity_id": p, "state": "playing"}],
                "then": [{"action": "media_player.media_pause", "target": {"entity_id": p}}],
                "else": [
                    {"if": [{"condition": "template",
                             "value_template": f"{{{{ state_attr('{p}', 'source') != {spk_jinja} }}}}"}],
                     "then": [
                         {"action": "media_player.select_source", "target": {"entity_id": p},
                          "data": {"source": spk}, "continue_on_error": True},
                         {"delay": {"seconds": 2}},
                     ]},
                    {"if": [{"condition": "not", "conditions": [
                        {"condition": "state", "entity_id": p, "state": "playing"}]}],
                     "then": [{"action": "media_player.media_play", "target": {"entity_id": p},
                               "continue_on_error": True}]},
                ],
            }],
        }}

    autos = []
    for i, cam in enumerate(cfg.get("cameras") or [], start=1):
        if not cam.get("alert_sensor"):
            continue
        flag = f"input_boolean.homeview_cam_{i}_alert"
        pkg["input_boolean"][f"homeview_cam_{i}_alert"] = {"name": f"HomeView Camera {i} Alert", "icon": "mdi:cctv"}
        autos.append({
            "id": f"homeview_camera_{i}_alert",
            "alias": f"HomeView - Camera {i} alert on iPad",
            "description": "Wakes the iPad and shows this camera live for 30 seconds.",
            "mode": "restart",
            "triggers": [{"trigger": "state", "entity_id": cam["alert_sensor"], "from": "off", "to": "on"}],
            "actions": [
                {"action": "input_boolean.turn_off", "target": {"entity_id": SCREENSAVER}},
                {"action": "input_boolean.turn_on", "target": {"entity_id": flag}},
                {"delay": {"seconds": 30}},
                {"action": "input_boolean.turn_off", "target": {"entity_id": flag}},
            ],
        })
    if autos:
        pkg["automation"] = autos
    return pkg


# --- post-processing & output --------------------------------------------------
def walk(node):
    yield node
    if isinstance(node, dict):
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def map_strings(node, fn):
    if isinstance(node, dict):
        return {k: map_strings(v, fn) for k, v in node.items()}
    if isinstance(node, list):
        return [map_strings(v, fn) for v in node]
    return fn(node) if isinstance(node, str) else node


def strip_blur(node):
    if isinstance(node, dict):
        for v in node.values():
            strip_blur(v)
    elif isinstance(node, list):
        node[:] = [x for x in node if not (isinstance(x, dict) and len(x) == 1 and
                                           next(iter(x)) in ("backdrop-filter", "-webkit-backdrop-filter"))]
        for x in node:
            strip_blur(x)


def check_hashes(dash) -> list[str]:
    errors = []
    for v in dash["views"]:
        defined = {n["hash"] for n in walk(v) if isinstance(n, dict) and n.get("card_type") == "pop-up"}
        used = {n["navigation_path"] for n in walk(v)
                if isinstance(n, dict) and str(n.get("navigation_path", "")).startswith("#")}
        errors += [f"view '{v['path']}' links to {h} but has no pop-up with that hash" for h in sorted(used - defined)]
    return errors


class Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def _str(dumper, s):
    style = "|" if "\n" in s else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", s, style=style)


Dumper.add_representer(str, _str)


def dump(data) -> str:
    return yaml.dump(data, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=4096, indent=2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=HERE / "config.yaml", type=pathlib.Path)
    ap.add_argument("--out", default=REPO / "dist", type=pathlib.Path)
    args = ap.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    accent = cfg["dashboard"].get("accent", "#FF3B30")
    helpers_js = (HERE / "dotmatrix.js").read_text().replace("__ACCENT__", accent)
    helpers_js = "\n".join(l for l in helpers_js.splitlines() if not l.lstrip().startswith("//"))
    base = yaml.safe_load((HERE / "base.yaml").read_text().replace("__ACCENT__", accent))
    base = map_strings(base, lambda s: s.replace("/*DOTMATRIX*/", helpers_js.strip())
                       .replace("sensor.time", MINUTE_SENSOR).replace("sensor.date", DATE_SENSOR))

    url = cfg["dashboard"]["url_path"].strip("/")
    warnings: list[str] = []
    dash = copy.deepcopy(base)
    dash["wallpanel"]["screensaver_stop_navigation_path"] = f"/{url}/home"
    dash["views"] = [home_view(cfg, warnings)]
    if not cfg["dashboard"].get("glass_blur", True):
        strip_blur(dash)
    errors = check_hashes(dash)

    args.out.mkdir(parents=True, exist_ok=True)
    dash_text = ("# HomeView iPad panel - GENERATED by homeview/build_dashboard.py, don't edit by hand.\n"
                 f"# Paste into: Settings > Dashboards > (dashboard at /{url}) > pencil > three dots >\n"
                 "#             Raw configuration editor  (replace everything, then Save).\n" + dump(dash))
    (args.out / "homeview_dashboard.yaml").write_text(dash_text)
    pkg_text = ("# HomeView package - GENERATED by homeview/build_dashboard.py.\n"
                "# Copy to /config/packages/homeview.yaml, then Developer tools > YAML > Check configuration\n"
                "# and restart Home Assistant. (Packages must be enabled once, see docs/SETUP.md.)\n"
                + dump(package(cfg)))
    (args.out / "homeview_package.yaml").write_text(pkg_text)

    placeholders = sorted(set(re.findall(r"\b[a-z_]+\.your_[a-z0-9_]+", dash_text + pkg_text)))
    if "Your Echo Name" in pkg_text:
        placeholders.append('music.speaker: "Your Echo Name"')
    print(f"Wrote {args.out / 'homeview_dashboard.yaml'} ({len(dash_text.splitlines())} lines) "
          f"and {args.out / 'homeview_package.yaml'}")
    for w in warnings:
        print("WARNING:", w)
    if placeholders:
        print(f"\n{len(placeholders)} placeholders still need real values in {args.config.name}:")
        for p in placeholders:
            print("  -", p)
    for e in errors:
        print("ERROR:", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
