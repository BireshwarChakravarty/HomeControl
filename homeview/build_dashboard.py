#!/usr/bin/env python3
"""Build the HomeView iPad dashboard and its automations.

Reads   homeview/config.yaml  (your entity IDs)
      + homeview/base.yaml    (plugin settings + button-card design system)
Writes  dist/homeview_dashboard.yaml   -> paste into the dashboard's Raw configuration editor
        dist/automations/*.yaml        -> paste each into a new automation (Edit in YAML)

Layout is computed for an iPad Air 2 in landscape (1024 x 768 CSS px) with kiosk
mode hiding the HA header. With the header showing (while you edit) the page
just scrolls a little.

Usage:  python3 homeview/build_dashboard.py [--config path] [--out dir]
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import pathlib
import re
import sys

import yaml

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent

# --- iPad Air 2 landscape geometry (CSS px) ----------------------------------
USABLE_H = 736          # 768 - iPadOS status bar (24) - safety margin; kiosk mode hides the HA header
PAD = 14                # hv_layout padding
GAP = 12                # hv_layout gap
HOME_TOP_H = 220
HOME_CAL_H = 88
TILE_H_MAX = 176
COLS = 4

HELPER_SCREENSAVER = "input_boolean.homeview_screensaver"
HELPER_DOORBELL = "input_boolean.homeview_doorbell_popup"

POPUP_STYLE = {"bg_opacity": "94", "bg_blur": "0"}   # no extra blur layer on the A8X GPU


# --- small helpers -----------------------------------------------------------
def domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0]


def bc(template, **kw) -> dict:
    """A custom:button-card using one or more templates."""
    card = {"type": "custom:button-card", "template": template}
    card.update({k: v for k, v in kw.items() if v is not None})
    return card


def height(px: int) -> dict:
    return {"card": [{"height": f"{px}px"}]}


def layout(areas: list[str], columns: str, rows: str, fields: dict) -> dict:
    """An hv_layout container: a CSS grid whose named cells hold other cards."""
    return bc(
        "hv_layout",
        styles={
            "grid": [
                {"grid-template-areas": " ".join(f'"{r}"' for r in areas)},
                {"grid-template-columns": columns},
                {"grid-template-rows": rows},
            ],
            "custom_fields": {k: [{"min-width": "0"}, {"min-height": "0"}] for k in fields},
        },
        custom_fields={k: {"card": v} for k, v in fields.items()},
    )


def popup(hash_: str, name: str, icon: str, cards: list, width: str = "640px", **extra) -> dict:
    head = {
        "type": "custom:bubble-card",
        "card_type": "pop-up",
        "hash": hash_,
        "name": name,
        "icon": icon,
        "width_desktop": width,
        **POPUP_STYLE,
        **extra,
    }
    return {"type": "vertical-stack", "cards": [head, *cards]}


def confirm_text(name: str | None, entity_id: str) -> str:
    """JS template for the confirmation dialog, e.g. 'Unlock Front Door?'."""
    d = domain(entity_id)
    if d == "lock":
        verb = "entity.state === 'locked' ? 'Unlock' : 'Lock'"
    elif d == "cover":
        verb = "entity.state === 'closed' ? 'Open' : 'Close'"
    else:
        verb = "'Toggle'"
    who = json.dumps(f" {name}?") if name else "' ' + entity.attributes.friendly_name + '?'"
    return f"[[[ return ({verb}) + {who}; ]]]"


def tile(spec, small: bool = False) -> dict:
    if isinstance(spec, str):
        spec = {"entity": spec}
    ent = spec["entity"]
    kind = spec.get("type") or ("fan" if domain(ent) == "fan" else "tile")
    tpl = "hv_fan_tile" if kind == "fan" else "hv_tile"
    card = bc([tpl, "hv_tile_small"] if small else tpl, entity=ent,
              name=spec.get("name"), icon=spec.get("icon"))
    confirm = spec.get("confirm", domain(ent) in ("lock", "cover"))
    if confirm:
        card["tap_action"] = {
            "action": "toggle",
            "haptic": "light",
            "confirmation": {"text": confirm_text(spec.get("name"), ent)},
        }
    return card


def control_row(entities: list, extra: list | None = None) -> dict:
    cards = [tile(e, small=True) for e in entities] + (extra or [])
    return {"type": "grid", "columns": max(1, len(cards)), "square": False, "cards": cards}


# --- pop-ups -----------------------------------------------------------------
def weather_popup(cfg) -> dict:
    w = cfg["weather"]
    cards = [
        {"type": "weather-forecast", "entity": w["entity"], "forecast_type": "hourly",
         "show_current": True, "show_forecast": True},
    ]
    if w.get("forecast_type", "daily") != "hourly":
        cards.append({"type": "weather-forecast", "entity": w["entity"],
                      "forecast_type": w.get("forecast_type", "daily"),
                      "show_current": False, "show_forecast": True})
    return popup("#weather", "Weather", "mdi:weather-partly-cloudy", cards)


def calendar_popup(cfg) -> dict:
    return popup("#calendar", "Upcoming week", "mdi:calendar-month", [
        {"type": "calendar", "initial_view": "listWeek",
         "entities": [c["entity"] for c in cfg["calendars"]]},
    ], width="760px")


def vacuum_popup(cfg) -> dict:
    v = cfg["vacuum"]
    cards = [{
        "type": "tile",
        "entity": v["entity"],
        "name": v.get("name"),
        "features": [{"type": "vacuum-commands",
                      "commands": ["start_pause", "stop", "return_home", "locate"]}],
    }]
    extras = [e for e in [v.get("water_low"), *(v.get("extra_entities") or [])] if e]
    if extras:
        cards.append({"type": "entities", "entities": extras})
    return popup("#vacuum", v.get("name", "Vacuum"), "mdi:robot-vacuum", cards)


def doorbell_popup(cfg) -> dict:
    db = cfg["doorbell"]
    live = {"type": "picture-entity", "entity": db.get("live") or db["preview"],
            "camera_view": "live", "show_name": False, "show_state": False,
            "tap_action": {"action": "none"}, "hold_action": {"action": "none"}}
    if db.get("package"):
        # Only ONE live stream per pop-up: the package cam uses refreshing snapshots.
        pkg = {"type": "picture-entity", "entity": db["package"], "camera_view": "auto",
               "name": "Package", "show_state": False,
               "tap_action": {"action": "none"}, "hold_action": {"action": "none"}}
        media = {"type": "horizontal-stack", "cards": [live, pkg]}
    else:
        media = live
    cards = [media]
    if db.get("controls"):
        cards.append(control_row(db["controls"]))
    extra = {}
    if db.get("ring_event"):
        extra = {
            "trigger": [{"condition": "state", "entity": HELPER_DOORBELL, "state": "on"}],
            "trigger_close": True,
            "auto_close": "45000",
        }
    return popup("#doorbell", "Front door", "mdi:doorbell-video", cards, width="900px", **extra)


def camera_popups(cfg) -> list:
    cams = cfg["cameras"]["list"]
    controls = cfg["cameras"].get("controls") or []
    n = len(cams)
    out = []
    for i, cam in enumerate(cams, start=1):
        prev_i = (i - 2) % n + 1
        next_i = i % n + 1
        nav = []
        if n > 1:
            nav = [
                bc("hv_pill", name="Prev", icon="mdi:chevron-left",
                   tap_action={"action": "navigate", "navigation_path": f"#cam-{prev_i}"}),
                bc("hv_pill", name="Next", icon="mdi:chevron-right",
                   tap_action={"action": "navigate", "navigation_path": f"#cam-{next_i}"}),
            ]
        cards = [{"type": "picture-entity", "entity": cam.get("live") or cam["snapshot"],
                  "camera_view": "live", "show_name": False, "show_state": False,
                  "tap_action": {"action": "none"}, "hold_action": {"action": "none"}}]
        if controls or nav:
            cards.append(control_row(controls, nav))
        out.append(popup(f"#cam-{i}", cam["name"], "mdi:cctv", cards, width="900px"))
    return out


# --- views -------------------------------------------------------------------
def view(title: str, path: str, icon: str, cfg, cards: list) -> dict:
    return {
        "title": title,
        "path": path,
        "icon": icon,
        "type": "panel",
        "background": cfg["dashboard"]["background"],
        "cards": [{"type": "vertical-stack", "cards": cards}],
    }


def weather_card(cfg, h: int) -> dict:
    w = cfg["weather"]
    return bc("hv_weather", entity=w["entity"],
              variables={"city": cfg["dashboard"].get("city", ""), "uv_entity": w.get("uv_entity", "")},
              styles=height(h))


def calendar_card(cfg, h: int, detail: bool, max_rows: int = 0) -> dict:
    cals = cfg["calendars"]
    return bc("hv_calendar",
              variables={"calendars": cals, "detail": detail, "max": max_rows},
              triggers_update=[c["entity"] for c in cals] + ["sensor.date"],
              styles=height(h))


def widgets_view(cfg) -> dict:
    has_w, has_c = bool(cfg.get("weather")), bool(cfg.get("calendars"))
    p = cfg.get("photos") or {}
    fields = {
        "date": bc("hv_date", styles=height(125)),
        "clock": bc("hv_clock", variables={"size": 270}, styles=height(310)),
        "photo": bc("hv_photo", variables={"folder": p.get("folder", "/local/homeview/slideshow"),
                                           "count": p.get("count", 1),
                                           "minutes": p.get("minutes", 2)},
                    styles=height(125 + GAP + 310)),
    }
    if has_w and has_c:
        bottom = "wx cal"
    elif has_w:
        bottom = "wx wx"
    elif has_c:
        bottom = "cal cal"
    else:
        bottom = None
    if has_w:
        fields["wx"] = weather_card(cfg, 245)
    if has_c:
        fields["cal"] = calendar_card(cfg, 245, detail=True, max_rows=3)
    areas = ["date photo", "clock photo"] + ([bottom] if bottom else [])
    rows = "125px 310px" + (" 245px" if bottom else "")
    cards = [layout(areas, "300px 1fr", rows, fields)]
    if has_w:
        cards.append(weather_popup(cfg))
    if has_c:
        cards.append(calendar_popup(cfg))
    if cfg.get("doorbell"):
        cards.append(doorbell_popup(cfg))
    return view("Widgets", "widgets", "mdi:view-dashboard-variant", cfg, cards)


def home_slots(cfg) -> list:
    slots = [tile(t) for t in cfg.get("tiles") or []]
    v = cfg.get("vacuum")
    if v:
        trig = [v["entity"]] + ([v["water_low"]] if v.get("water_low") else [])
        slots.append(bc("hv_vacuum_tile", entity=v["entity"], name=v.get("name"),
                        variables={"water_low": v.get("water_low", "")},
                        triggers_update=trig))
    scenes = cfg.get("scenes") or []
    for i in range(0, len(scenes), 2):
        chunk = scenes[i:i + 2]
        slots.append(("scenes", chunk))
    return slots


def home_view(cfg, warnings: list) -> dict:
    has_w, has_c, db = bool(cfg.get("weather")), bool(cfg.get("calendars")), cfg.get("doorbell")
    slots = home_slots(cfg)
    rows_n = max(1, math.ceil(len(slots) / COLS))
    bottom_bar = bool(db) and has_c
    fixed = 2 * PAD + HOME_TOP_H + (HOME_CAL_H + GAP if bottom_bar else 0) + GAP * rows_n
    tile_h = min(TILE_H_MAX, (USABLE_H - fixed) // rows_n)
    if tile_h < 100:
        warnings.append(f"Home view has {len(slots)} tile slots ({rows_n} rows); tiles shrink to "
                        f"{tile_h}px. Consider moving some to a second view.")

    fields = {"clock": bc("hv_clock", variables={"size": 180}, styles=height(HOME_TOP_H))}
    top = ["clock"]
    if has_w:
        fields["weather"] = weather_card(cfg, HOME_TOP_H)
        top.append("weather")
    if db:
        fields["door"] = {"type": "picture-entity", "entity": db["preview"], "name": "Front door",
                          "show_state": False, "camera_view": "auto", "aspect_ratio": "9:4",            # ~492 x 220 px
                          "fit_mode": "cover",
                          "tap_action": {"action": "navigate", "navigation_path": "#doorbell"}}
        top += ["door"] * (COLS - len(top))
    elif has_c:
        fields["cal"] = calendar_card(cfg, HOME_TOP_H, detail=True, max_rows=3)
        top += ["cal"] * (COLS - len(top))
    top += [top[-1]] * (COLS - len(top))

    areas = [" ".join(top)]
    names = []
    for i, slot in enumerate(slots, start=1):
        key = f"t{i}"
        names.append(key)
        if isinstance(slot, tuple):           # scene pills stacked in one slot
            chunk = slot[1]
            pill_h = tile_h if len(chunk) == 1 else (tile_h - 8) // 2
            fields[key] = {"type": "vertical-stack", "cards": [
                bc("hv_scene", entity=s["entity"], name=s.get("name"), icon=s.get("icon"),
                   styles=height(pill_h)) for s in chunk]}
        else:
            slot.setdefault("styles", {})
            slot["styles"]["card"] = [{"height": f"{tile_h}px"}]
            fields[key] = slot
    names += ["."] * (rows_n * COLS - len(names))
    for r in range(rows_n):
        areas.append(" ".join(names[r * COLS:(r + 1) * COLS]))
    rows = f"{HOME_TOP_H}px " + " ".join([f"{tile_h}px"] * rows_n)
    if bottom_bar:
        fields["cal"] = calendar_card(cfg, HOME_CAL_H, detail=False, max_rows=2)
        areas.append(" ".join(["cal"] * COLS))
        rows += f" {HOME_CAL_H}px"

    cards = [layout(areas, f"repeat({COLS}, 1fr)", rows, fields)]
    if db:
        cards.append(doorbell_popup(cfg))
    if has_w:
        cards.append(weather_popup(cfg))
    if has_c:
        cards.append(calendar_popup(cfg))
    if cfg.get("vacuum"):
        cards.append(vacuum_popup(cfg))
    return view("Home", "home", "mdi:home", cfg, cards)


def cameras_view(cfg) -> dict:
    cams = cfg["cameras"]["list"][:9]
    n = len(cams)
    cols = 1 if n == 1 else 2 if n <= 4 else 3
    grid = {"type": "grid", "columns": cols, "square": False, "cards": [
        {"type": "picture-entity", "entity": c["snapshot"], "name": f"{i} · {c['name']}",
         "show_state": False, "camera_view": "auto", "aspect_ratio": "16:9", "fit_mode": "cover",
         "tap_action": {"action": "navigate", "navigation_path": f"#cam-{i}"}}
        for i, c in enumerate(cams, start=1)]}
    cards = [layout(["cams"], "1fr", "auto", {"cams": grid})]
    cards += camera_popups({"cameras": {**cfg["cameras"], "list": cams}})
    if cfg.get("doorbell"):
        cards.append(doorbell_popup(cfg))
    return view("Cameras", "cameras", "mdi:cctv", cfg, cards)


# --- automations -------------------------------------------------------------
def automations(cfg) -> dict[str, dict]:
    out = {}
    wake = (cfg.get("wake") or {}).get("motion_sensor")
    if wake:
        out["homeview_wake_on_motion"] = {
            "alias": "HomeView iPad - Wake screensaver on motion",
            "description": "Stops the WallPanel clock screensaver when someone walks up to the iPad.",
            "mode": "single",
            "triggers": [{"trigger": "state", "entity_id": wake, "to": "on"}],
            "conditions": [{"condition": "state", "entity_id": HELPER_SCREENSAVER, "state": "on"}],
            "actions": [{"action": "input_boolean.turn_off", "target": {"entity_id": HELPER_SCREENSAVER}}],
        }
    ring = (cfg.get("doorbell") or {}).get("ring_event")
    if ring:
        out["homeview_doorbell_popup"] = {
            "alias": "HomeView iPad - Doorbell pop-up",
            "description": "Wakes the iPad and opens the doorbell pop-up for 45 seconds on every ring.",
            "mode": "restart",
            "triggers": [{"trigger": "state", "entity_id": ring,
                          "not_from": ["unavailable", "unknown"],
                          "not_to": ["unavailable", "unknown"]}],
            "actions": [
                {"action": "input_boolean.turn_off", "target": {"entity_id": HELPER_SCREENSAVER}},
                {"action": "input_boolean.turn_on", "target": {"entity_id": HELPER_DOORBELL}},
                {"delay": {"seconds": 45}},
                {"action": "input_boolean.turn_off", "target": {"entity_id": HELPER_DOORBELL}},
            ],
        }
    ch = cfg.get("charging")
    if ch:
        out["homeview_ipad_charging"] = {
            "alias": "HomeView iPad - Keep battery between %d%% and %d%%" % (ch.get("low", 30), ch.get("high", 80)),
            "description": "Cycles the iPad charger plug so the old battery doesn't sit at 100% around the clock.",
            "mode": "single",
            "triggers": [
                {"trigger": "numeric_state", "entity_id": ch["battery_sensor"], "below": ch.get("low", 30), "id": "low"},
                {"trigger": "numeric_state", "entity_id": ch["battery_sensor"], "above": ch.get("high", 80), "id": "high"},
            ],
            "actions": [{"choose": [
                {"conditions": [{"condition": "trigger", "id": "low"}],
                 "sequence": [{"action": "switch.turn_on", "target": {"entity_id": ch["charger_switch"]}}]},
                {"conditions": [{"condition": "trigger", "id": "high"}],
                 "sequence": [{"action": "switch.turn_off", "target": {"entity_id": ch["charger_switch"]}}]},
            ]}],
        }
    return out


# --- post-processing & checks ------------------------------------------------
def strip_blur(node):
    if isinstance(node, dict):
        for v in node.values():
            strip_blur(v)
    elif isinstance(node, list):
        node[:] = [x for x in node if not (isinstance(x, dict) and len(x) == 1 and
                                           next(iter(x)) in ("backdrop-filter", "-webkit-backdrop-filter"))]
        for x in node:
            strip_blur(x)


def walk(node):
    yield node
    if isinstance(node, dict):
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def check_hashes(dash) -> list[str]:
    errors = []
    for v in dash["views"]:
        defined = {n["hash"] for n in walk(v) if isinstance(n, dict) and n.get("card_type") == "pop-up"}
        used = {n["navigation_path"] for n in walk(v)
                if isinstance(n, dict) and str(n.get("navigation_path", "")).startswith("#")}
        for h in sorted(used - defined):
            errors.append(f"view '{v['path']}' links to {h} but has no pop-up with that hash")
    return errors


class Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def _str(dumper, s):
    if "\n" in s:
        return dumper.represent_scalar("tag:yaml.org,2002:str", s, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", s)


Dumper.add_representer(str, _str)


def dump(data) -> str:
    return yaml.dump(data, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=4096, indent=2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=HERE / "config.yaml", type=pathlib.Path)
    ap.add_argument("--out", default=REPO / "dist", type=pathlib.Path)
    args = ap.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    base = yaml.safe_load((HERE / "base.yaml").read_text())
    url = cfg["dashboard"]["url_path"].strip("/")
    warnings: list[str] = []

    dash = copy.deepcopy(base)
    dash["wallpanel"]["screensaver_stop_navigation_path"] = f"/{url}/home"
    views = [widgets_view(cfg), home_view(cfg, warnings)]
    if (cfg.get("cameras") or {}).get("list"):
        views.append(cameras_view(cfg))
    else:
        dash["wallpanel"]["enabled_on_tabs"] = ["home"]
    dash["views"] = views
    if not cfg["dashboard"].get("glass_blur", True):
        strip_blur(dash)

    errors = check_hashes(dash)

    header = (
        "# HomeView iPad dashboard - GENERATED by homeview/build_dashboard.py, don't edit by hand.\n"
        f"# Paste into: Settings > Dashboards > (dashboard at /{url}) > pencil > three dots >\n"
        "#             Raw configuration editor  (replace everything, then Save).\n"
    )
    args.out.mkdir(parents=True, exist_ok=True)
    text = header + dump(dash)
    (args.out / "homeview_dashboard.yaml").write_text(text)

    auto_dir = args.out / "automations"
    auto_dir.mkdir(exist_ok=True)
    for old in auto_dir.glob("*.yaml"):
        old.unlink()
    autos = automations(cfg)
    for name, a in autos.items():
        (auto_dir / f"{name}.yaml").write_text(
            "# Settings > Automations > Create automation > three dots > Edit in YAML > paste > Save\n" + dump(a))
    all_text = text + "".join(dump(a) for a in autos.values())

    placeholders = sorted(set(re.findall(r"\b[a-z_]+\.your_[a-z0-9_]+", all_text)))
    print(f"Wrote {args.out / 'homeview_dashboard.yaml'} ({len(text.splitlines())} lines, "
          f"{len(views)} views) and {len(autos)} automation(s) in {auto_dir}")
    for w in warnings:
        print("WARNING:", w)
    if placeholders:
        print(f"\n{len(placeholders)} placeholder entity IDs still need real values in {args.config.name}:")
        for p in placeholders:
            print("  -", p)
    for e in errors:
        print("ERROR:", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
