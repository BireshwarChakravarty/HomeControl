# Master Blueprint & Raw YAML: DIY Apple "HomeView" Dashboard for Home Assistant (iPad)

**Reference Source:** Shane Whatley – *"I Built My Own Apple HomeView… Using an iPad!"* (`https://www.youtube.com/watch?v=hcNzvX3JZbo`)

---

## 1. Role & Objective for Claude

You are acting as a **Home Assistant Frontend & Automation Architect**. Your objective is to help the user build, customize, or maintain a 3-view wall-mounted iPad dashboard in Home Assistant that replicates Apple's **HomeView** smart home display aesthetic and functionality, using the reference architecture and master YAML template embedded in **Section 8** of this document.

If you are connected to the user's Home Assistant instance via **HA-MCP (Model Context Protocol)**, follow these safety and workflow rules:

1. **Inspect Before Writing:** Query the user's existing entity registry (`light.*`, `camera.*`, `weather.*`, `calendar.*`, `lock.*`, `cover.*`, `switch.*`, `scene.*`, `vacuum.*`) before generating or modifying YAML.
2. **Require Confirmation:** Always summarize proposed dashboard or automation changes and ask for explicit user confirmation before writing changes to Home Assistant.
3. **Preserve Performance on Older iPads:** Never place 9 simultaneous live video streams on a single view. Use periodic snapshot refreshes (`camera_view: auto`) for camera grids and reserve live WebRTC/RTSP streams (`camera_view: live`) for individual popups or a single primary doorbell preview.

---

## 2. Project Overview & Architecture

The project turns a standard iPad (mounted in landscape orientation running the **Home Assistant Companion App**) into an Apple HomeView alternative powered by a Home Assistant server and connected to Claude via **HA-MCP** and **Home Assistant Cloud (Nabu Casa)**.

### Core Capabilities

* **3 Swipable Views:**
  1. **Widgets View (`/home-widget/widgets`):** StandBy-style always-on display featuring a large date, analog clock, auto-rotating photo slideshow (2-minute interval), dual-calendar upcoming events, and detailed weather forecast.
  2. **Home View (`/home-widget/home`):** Primary control center with Apple glassmorphism ("glass tiles") for lights, scenes, locks, garage doors, ceiling fans, curtain light groups, a live doorbell preview, and interactive popups for weather, calendar, doorbell events, and robot vacuum controls.
  3. **Cameras View (`/home-widget/cameras`):** A $3 \times 3$ grid of up to 9 cameras using low-overhead medium-resolution snapshots that refresh every few seconds. Tapping any camera opens a high-resolution live feed popup with contextual action buttons (e.g., Front Door Lock, Garage Door, Previous/Next camera navigation, and Close).
* **Idle Clock Screensaver & Motion Wake:** Uses `WallPanel` to display a full-screen analog clock when idle (120 seconds), paired with an `input_boolean` helper and a motion/presence sensor automation to wake the screen when someone approaches.
* **Automatic Doorbell Popup:** Triggers a 45-second live popup modal whenever the doorbell ring event fires.

---

## 3. Prerequisites & Dependencies

### 3.1 Required HACS Frontend Modules

Before deploying the dashboard YAML, ensure the following frontend resources are installed via **HACS (Home Assistant Community Store)**:

| HACS Module | Purpose in Dashboard | Views Using It |
| :--- | :--- | :--- |
| **`button-card`** | Renders every tile, custom widget, analog clock, and popup action button via `button_card_templates`. | All (`Widgets`, `Home`, `Cameras`) |
| **`Bubble Card`** | Powers modal popups (weather details, calendar, live camera views, doorbell popup, vacuum controls). | `Home`, `Cameras` |
| **`WallPanel`** | Manages the full-screen idle clock screensaver and the photo slideshow card. | `Widgets`, `Home`, `Cameras` |
| **`Kiosk Mode`** | Hides the Home Assistant top header and left sidebar (toggled by long-pressing the analog clock tile). | `Home`, Global |
| **`Swipe Navigation`** | Enables horizontal touch swiping between the 3 views on the iPad. | Full Dashboard |

### 3.2 Required Media & Helper Entities

1. **Dashboard URL Slug:** Must be created as a Storage-mode dashboard from scratch at URL path `home-widget` (Settings $\rightarrow$ Dashboards $\rightarrow$ Add Dashboard).
   * *Note:* Popup close buttons route to `/home-widget/...`. If the user wants a different URL slug, update all internal navigation paths accordingly.
2. **Helper Entities (Settings $\rightarrow$ Devices & Services $\rightarrow$ Helpers):**
   * `input_boolean.your_screensaver_toggle`: Turning this entity `off` wakes the WallPanel screensaver.
   * `input_boolean.kiosk_mode_toggle`: Toggled by holding the analog clock to show/hide the Home Assistant header and sidebar.
   * `light.your_curtain_lights`: Light Group helper combining multiple curtain or accent lights (optional).
3. **Local Media Files (`Media -> My media`):**
   * `glass.jpg`: Background image uploaded to `/local/media/glass.jpg` to give the Apple HomeView frosted glass look.
   * `Photo Slideshow/`: A folder in `My media` containing `.jpg` or `.png` photos, cycled every 120 seconds by the photo widget.

---

## 4. Reusable Design System (`button_card_templates`)

The dashboard YAML starts at the root level (zero indentation) with global plugins and `button_card_templates:`. When generating or editing cards for this dashboard, adhere to these core template patterns:

* **`glass_tile`:** Frosted glass aesthetic (`backdrop-filter: blur(24px)`, semi-transparent background, rounded corners) for device controls. Displays icon, device name, and state, with distinct visual highlights for `on`, `unlocked`, and `open` states.
* **`fan_tile`:** Inherits `glass_tile`. When `switch.your_ceiling_fan` is `on`, applies a continuous CSS rotation animation to the fan icon.
* **`scene_tile`:** Stateless pill-shaped tile that triggers `scene.turn_on` on tap.
* **`analog_clock` & `analog_clock_screensaver`:** Custom SVG analog clock face with an Apple Watch-style orange second hand. Configured with a `hold_action` to toggle `input_boolean.kiosk_mode_toggle`.
* **`weather_widget`:** Custom weather summary card pulling temperature, condition, UV index, and forecast data, opening `#weather-popup` on tap.
* **`calendar_widget`:** Displays upcoming events from two distinct calendar entities color-coded with **orange** (`#FF9500`) and **green** (`#34C759`) indicator dots, opening `#calendar-popup` on tap.
* **`camera_tile`:** Styled container for camera snapshots. Supports standard $16:9$ landscape cameras and tall $9:16$ portrait cameras (specifically slots 6 and 9).
* **`vacuum_tile`:** Robot vacuum status tile that displays a `Refill Water` alert badge when `binary_sensor.your_vacuum_water_low` is `on`.

---

## 5. Entity Mapping & Placeholders Reference

When adapting the YAML in **Section 8** to a user's specific Home Assistant setup, map the following standard placeholders to the user's real entity IDs:

| Placeholder Entity ID | Target Device / Integration | Implementation Notes |
| :--- | :--- | :--- |
| `weather.your_weather` | Primary Weather Integration (e.g., NWS) | Uses `twice_daily` forecast service. Also replace hardcoded `"Your City"` text in `weather_widget`. |
| `weather.forecast_home` | Met.no (Default HA Weather) | Used specifically for UV Index attribute (`attributes.uv_index`). |
| `calendar.your_calendar_1` | Primary Calendar Entity | Displayed with an orange dot. Update label `'Calendar 1'`. |
| `calendar.your_calendar_2` | Secondary Calendar Entity | Displayed with a green dot. Update label `'Calendar 2'`. |
| `lock.your_front_door_lock` | Smart Lock Entity | Displayed on Home view AND inside live camera popups for quick locking/unlocking. |
| `cover.your_garage_door` | Garage Door Opener | Displayed on Home view AND inside live camera popups. |
| `light.your_porch_light` | Front Porch Light | Mapped to `"Lights · Front Porch"` glass tile and Doorbell popup. |
| `light.your_room_lights` | Primary Room / Studio Lights | Mapped to `"Lights · Studio"` glass tile. |
| `light.your_curtain_lights` | Light Group Helper | Mapped to `"Curtain Lights"` tile. |
| `switch.your_ceiling_fan` | Ceiling Fan Switch | Uses `fan_tile` spinning icon animation when state is `on`. |
| `scene.your_good_night_scene` | Good Night Scene | Mapped to `"Good Night"` scene pill tile. |
| `scene.your_lights_off_scene` | Room Off Scene | Mapped to `"Studio Off"` scene pill tile. |
| `input_boolean.your_screensaver_toggle` | Screensaver Wake Helper | Toggled by motion sensor automation to wake iPad from clock screensaver. |
| `input_boolean.kiosk_mode_toggle` | Kiosk Mode Helper | Toggled by long-pressing the analog clock. |
| `event.your_doorbell_ring` | Doorbell Ring Event | Triggers `#doorbell-popup` on the iPad for 45 seconds (`auto_close: '45000'`). |
| `camera.your_doorbell_high` | Doorbell High-Res Stream | Used inside `#doorbell-popup` and `#cam-1-popup`. |
| `camera.your_doorbell_medium` | Doorbell Med-Res Stream | Used on the Home view preview and Camera grid slot 1. |
| `camera.your_package_camera` | Doorbell Package Camera | Secondary downward-facing doorbell camera feed (Slot 2 & Doorbell popup). |
| `camera.your_camera_3_medium` to `_9_medium` | Grid Cameras 3–9 (Med-Res) | Used in the $3 \times 3$ snapshot grid. Slots 6 & 9 are styled for tall ($9:16$) aspect ratios. |
| `camera.your_camera_3_high` to `_9_high` | Grid Cameras 3–9 (High-Res) | Opened in `#cam-3-popup` through `#cam-9-popup` when a grid snapshot is tapped. |
| `vacuum.your_vacuum_entity` | Robot Vacuum Entity | Mapped to `vacuum_tile` and `#vacuum-popup` (alongside mode select, dock button, and water sensor). |

---

## 6. Supporting Home Assistant Automations

When the user asks you to set up the supporting automations for this dashboard, deploy or adapt these YAML automations:

### 6.1 Motion-Activated Screensaver Wake Automation

```yaml
alias: "HomeView iPad - Wake Screensaver on Motion"
description: "Turns off the WallPanel screensaver toggle when presence/motion is detected near the iPad."
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.your_motion_or_presence_sensor
    to: "on"
condition:
  - condition: state
    entity_id: input_boolean.your_screensaver_toggle
    state: "on"
action:
  - service: input_boolean.turn_off
    target:
      entity_id: input_boolean.your_screensaver_toggle
```

### 6.2 Doorbell Ring Wake & Auto-Popup Automation

*(Note: Bubble Card natively supports `trigger_entity: event.your_doorbell_ring` and `auto_close: '45000'`, which is already configured in the dashboard YAML below. This companion automation ensures the WallPanel screensaver wakes up immediately when the doorbell rings).*

```yaml
alias: "HomeView iPad - Wake on Doorbell Ring"
description: "Wakes the iPad screensaver when the doorbell rings so the Bubble Card popup is visible."
mode: restart
trigger:
  - platform: state
    entity_id: event.your_doorbell_ring
action:
  - service: input_boolean.turn_off
    target:
      entity_id: input_boolean.your_screensaver_toggle
```

---

## 7. Step-by-Step Workflow for Claude

When the user asks you to build or customize this dashboard for their setup:

1. **Discovery Phase:**
   * Query the user's entities via HA-MCP (or ask the user) to identify their lights, locks, covers, switches, scenes, calendars, weather integrations, cameras, and vacuum entities.
2. **Customization Phase:**
   * Take the **Complete Reference Dashboard YAML** in **Section 8** and replace every `your_*` placeholder with the user's verified entity IDs.
   * **Weather Check:** If their weather provider does not support `twice_daily` forecasts (e.g., standard Met.no instead of NWS), change `forecast_type: twice_daily` to `daily` or `hourly` in `#weather-popup`.
   * **Camera Count Check:** If they have fewer than 9 cameras, adjust the `columns:` count on the `Cameras` view grid (e.g., `columns: 2`), remove unused camera tiles, and update the `Prev` / `Next` navigation hashes inside the `#cam-X-popup` blocks so they loop cleanly.
   * **Camera Popups Expansion:** In Section 8, `#cam-1-popup` is fully written out as the pattern for the camera grid popups. Replicate that `vertical-stack` popup block for each active camera the user has (`#cam-2-popup` through `#cam-N-popup`), linking each `Prev` and `Next` button to the adjacent camera hash.
3. **Deployment & Cache Reset:**
   * Write the configuration to the `/home-widget` dashboard (or instruct the user to paste it into the **Raw Configuration Editor** with `kiosk_mode:` on Line 1 at zero indentation).
   * Remind the user to set `/home-widget/home` as the default dashboard on their iPad Companion App and run **Settings $\rightarrow$ Companion App $\rightarrow$ Debugging $\rightarrow$ Reset frontend cache** if styles do not immediately load.

---

## 8. Complete Reference Dashboard YAML (`shane_homeview_dashboard.yaml`)

Below is the complete, self-contained dashboard configuration. Paste this into the Home Assistant **Raw Configuration Editor** after swapping the placeholders:

```yaml
# ==============================================================================
# SHANE WHATLEY - DIY APPLE HOMEVIEW IPAD DASHBOARD (HOME ASSISTANT)
# ==============================================================================
# TARGET URL: /home-widget (Open /home-widget/home on iPad Companion App)
# ORIENTATION: iPad Landscape (1024x768 / 1180x820 / 1366x1024)
# ==============================================================================

# ------------------------------------------------------------------------------
# GLOBAL PLUGINS: KIOSK MODE, SWIPE NAVIGATION & WALLPANEL SCREENSAVER
# ------------------------------------------------------------------------------
kiosk_mode:
  non_admin_settings:
    hide_header: true
    hide_sidebar: true
  entity_settings:
    - entity:
        input_boolean.kiosk_mode_toggle: 'on'
      hide_header: true
      hide_sidebar: true

swipe_nav:
  wrap: false
  animate: swipe
  prevent_default: true
  swipe_amount: 15

wallpanel:
  enabled: true
  hide_toolbar: false
  hide_sidebar: false
  fullscreen: false
  idle_time: 120
  keep_screen_on_time: 0
  black_screen_after_time: 0
  control_reactivation_time: 1
  screensaver_stop_navigation_path: /home-widget/home
  screensaver_entity: input_boolean.your_screensaver_toggle
  style:
    wallpanel-screensaver-container:
      background: 'rgba(10, 12, 18, 0.92)'
      backdrop-filter: 'blur(30px)'
    wallpanel-screensaver-info-box:
      '--wp-card-width': '420px'
      display: flex
      justify-content: center
      align-items: center
  cards:
    - type: custom:button-card
      template: analog_clock_screensaver

# ------------------------------------------------------------------------------
# REUSABLE BUTTON CARD TEMPLATES (button_card_templates)
# ------------------------------------------------------------------------------
button_card_templates:

  # 1. BASE GLASSMORPHISM TILE (Used for Lights, Scenes, Locks, Covers, Fans)
  glass_tile:
    aspect_ratio: 1/1
    show_state: true
    show_icon: true
    show_name: true
    tap_action:
      action: toggle
      haptic: light
    styles:
      card:
        - background: 'rgba(255, 255, 255, 0.12)'
        - backdrop-filter: 'blur(24px) saturate(180%)'
        - -webkit-backdrop-filter: 'blur(24px) saturate(180%)'
        - border: '1px solid rgba(255, 255, 255, 0.22)'
        - border-radius: '24px'
        - padding: '16px'
        - box-shadow: '0 8px 32px 0 rgba(0, 0, 0, 0.25)'
        - transition: 'all 0.25s cubic-bezier(0.25, 0.8, 0.25, 1)'
      grid:
        - grid-template-areas: '"i ." "n n" "s s"'
        - grid-template-columns: '1fr 1fr'
        - grid-template-rows: '1fr min-content min-content'
      icon:
        - width: '38px'
        - height: '38px'
        - color: 'rgba(255, 255, 255, 0.75)'
        - justify-self: start
        - align-self: start
      name:
        - color: '#FFFFFF'
        - font-size: '15px'
        - font-weight: '600'
        - justify-self: start
        - text-align: left
        - padding-top: '8px'
      state:
        - color: 'rgba(255, 255, 255, 0.60)'
        - font-size: '13px'
        - font-weight: '500'
        - justify-self: start
        - text-align: left
        - text-transform: capitalize
    state:
      - value: 'on'
        styles:
          card:
            - background: 'rgba(255, 255, 255, 0.88)'
            - border: '1px solid rgba(255, 255, 255, 0.95)'
          icon:
            - color: '#F59E0B'
          name:
            - color: '#111827'
          state:
            - color: '#4B5563'
      - value: 'unlocked'
        styles:
          card:
            - background: 'rgba(239, 68, 68, 0.28)'
            - border: '1px solid rgba(239, 68, 68, 0.55)'
          icon:
            - color: '#EF4444'
      - value: 'open'
        styles:
          card:
            - background: 'rgba(245, 158, 11, 0.28)'
            - border: '1px solid rgba(245, 158, 11, 0.55)'
          icon:
            - color: '#F59E0B'

  # 2. FAN GLASS TILE (Includes CSS keyframe spin animation when 'on')
  fan_tile:
    template: glass_tile
    icon: mdi:fan
    state:
      - value: 'on'
        styles:
          card:
            - background: 'rgba(255, 255, 255, 0.88)'
          icon:
            - color: '#3B82F6'
            - animation: 'rotating 1.8s linear infinite'
          name:
            - color: '#111827'
          state:
            - color: '#4B5563'

  # 3. SCENE GLASS TILE (Stateless trigger pill)
  scene_tile:
    template: glass_tile
    aspect_ratio: 2.2/1
    show_state: false
    tap_action:
      action: call-service
      service: scene.turn_on
      service_data:
        entity_id: '[[[ return entity.entity_id ]]]'
    styles:
      grid:
        - grid-template-areas: '"i n"'
        - grid-template-columns: 'min-content 1fr'
        - grid-template-rows: '1fr'
        - align-items: center
        - column-gap: '12px'
      name:
        - padding-top: '0px'
        - font-size: '15px'

  # 4. ANALOG CLOCK TILE (Long-press toggles Kiosk Mode)
  analog_clock:
    show_icon: false
    show_name: false
    show_state: false
    aspect_ratio: 1/1
    hold_action:
      action: call-service
      service: input_boolean.toggle
      service_data:
        entity_id: input_boolean.kiosk_mode_toggle
      haptic: heavy
    styles:
      card:
        - background: 'rgba(255, 255, 255, 0.14)'
        - backdrop-filter: 'blur(24px)'
        - border-radius: '28px'
        - border: '1px solid rgba(255, 255, 255, 0.22)'
        - padding: '12px'
    custom_fields:
      clock_svg: |
        [[[
          const now = new Date();
          const sec = now.getSeconds();
          const min = now.getMinutes() + sec / 60;
          const hr = (now.getHours() % 12) + min / 60;
          const secDeg = sec * 6;
          const minDeg = min * 6;
          const hrDeg = hr * 30;
          return `
            <svg viewBox="0 0 200 200" width="100%" height="100%">
              <circle cx="100" cy="100" r="92" fill="rgba(0,0,0,0.25)" stroke="rgba(255,255,255,0.25)" stroke-width="3"/>
              <!-- Hour Hand -->
              <line x1="100" y1="100" x2="100" y2="48" stroke="#FFFFFF" stroke-width="6" stroke-linecap="round"
                    transform="rotate(${hrDeg} 100 100)" />
              <!-- Minute Hand -->
              <line x1="100" y1="100" x2="100" y2="28" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round"
                    transform="rotate(${minDeg} 100 100)" />
              <!-- Second Hand (Apple Watch Orange) -->
              <line x1="100" y1="115" x2="100" y2="22" stroke="#FF9500" stroke-width="2" stroke-linecap="round"
                    transform="rotate(${secDeg} 100 100)" />
              <circle cx="100" cy="100" r="5" fill="#FF9500"/>
            </svg>
          `;
        ]]]

  # 5. ANALOG CLOCK SCREENSAVER (Large WallPanel Clock Face)
  analog_clock_screensaver:
    template: analog_clock
    styles:
      card:
        - width: '360px'
        - height: '360px'
        - background: 'transparent'
        - border: 'none'
        - box-shadow: 'none'

  # 6. WEATHER WIDGET TILE (Uses NWS twice_daily + Met.no UV/Dew Point)
  weather_widget:
    entity: weather.your_weather
    show_icon: true
    show_name: false
    show_state: false
    tap_action:
      action: navigate
      navigation_path: '#weather-popup'
    styles:
      card:
        - background: 'linear-gradient(145deg, rgba(30, 64, 175, 0.45), rgba(15, 23, 42, 0.55))'
        - backdrop-filter: 'blur(24px)'
        - border-radius: '28px'
        - border: '1px solid rgba(255, 255, 255, 0.22)'
        - padding: '20px'
        - color: '#FFFFFF'
      grid:
        - grid-template-areas: '"city icon" "temp temp" "cond hl"'
        - grid-template-columns: '1fr auto'
        - grid-template-rows: 'min-content 1fr min-content'
    custom_fields:
      city: |
        [[[ return `<div style="font-size:16px;font-weight:600;text-align:left;">Your City</div>`; ]]]
      temp: |
        [[[
          const t = entity?.attributes?.temperature ?? '--';
          return `<div style="font-size:48px;font-weight:300;text-align:left;line-height:1;">${t}°</div>`;
        ]]]
      cond: |
        [[[
          const s = entity?.state ?? 'Unknown';
          return `<div style="font-size:14px;opacity:0.8;text-align:left;text-transform:capitalize;">${s}</div>`;
        ]]]
      hl: |
        [[[
          const uv = states['weather.forecast_home']?.attributes?.uv_index ?? '-';
          return `<div style="font-size:13px;opacity:0.75;text-align:right;">UV: ${uv}</div>`;
        ]]]

  # 7. DUAL CALENDAR WIDGET TILE (Orange & Green Indicator Dots)
  calendar_widget:
    show_icon: false
    show_name: false
    show_state: false
    tap_action:
      action: navigate
      navigation_path: '#calendar-popup'
    styles:
      card:
        - background: 'rgba(255, 255, 255, 0.12)'
        - backdrop-filter: 'blur(24px)'
        - border-radius: '24px'
        - border: '1px solid rgba(255, 255, 255, 0.22)'
        - padding: '16px 20px'
        - text-align: left
    custom_fields:
      events: |
        [[[
          const c1 = states['calendar.your_calendar_1'];
          const c2 = states['calendar.your_calendar_2'];
          const e1Title = c1?.attributes?.message ?? 'No upcoming events';
          const e1Time  = c1?.attributes?.start_time ?? '';
          const e2Title = c2?.attributes?.message ?? 'No upcoming events';
          const e2Time  = c2?.attributes?.start_time ?? '';
          return `
            <div style="display:flex;flex-direction:column;gap:8px;color:#FFF;">
              <div style="font-size:12px;font-weight:700;letter-spacing:0.06em;opacity:0.65;text-transform:uppercase;">Upcoming Schedule</div>
              <div style="display:flex;align-items:center;gap:10px;">
                <span style="width:10px;height:10px;border-radius:50%;background:#FF9500;display:inline-block;"></span>
                <span style="font-size:14px;font-weight:600;">Calendar 1: ${e1Title}</span>
                <span style="font-size:12px;opacity:0.65;margin-left:auto;">${e1Time}</span>
              </div>
              <div style="display:flex;align-items:center;gap:10px;">
                <span style="width:10px;height:10px;border-radius:50%;background:#34C759;display:inline-block;"></span>
                <span style="font-size:14px;font-weight:600;">Calendar 2: ${e2Title}</span>
                <span style="font-size:12px;opacity:0.65;margin-left:auto;">${e2Time}</span>
              </div>
            </div>
          `;
        ]]]

  # 8. CAMERA SNAPSHOT GRID TILE (Medium-res snapshot -> High-res live popup)
  camera_tile:
    show_icon: false
    show_state: false
    show_name: true
    live_stream: false
    show_live_stream: false
    styles:
      card:
        - border-radius: '22px'
        - overflow: 'hidden'
        - border: '1px solid rgba(255, 255, 255, 0.20)'
        - background: 'rgba(0, 0, 0, 0.45)'
        - padding: '0px'
        - height: '210px'
      name:
        - position: 'absolute'
        - bottom: '10px'
        - left: '14px'
        - background: 'rgba(0, 0, 0, 0.55)'
        - backdrop-filter: 'blur(10px)'
        - padding: '4px 10px'
        - border-radius: '12px'
        - color: '#FFFFFF'
        - font-size: '13px'
        - font-weight: '600'

  # 9. NARWAL VACUUM TILE (Status + Refill Water Prompt)
  vacuum_tile:
    template: glass_tile
    icon: mdi:robot-vacuum
    tap_action:
      action: navigate
      navigation_path: '#vacuum-popup'
    custom_fields:
      water_alert: |
        [[[
          const water = states['binary_sensor.your_vacuum_water_low']?.state;
          if (water === 'on') {
            return `<div style="color:#38BDF8;font-size:11px;font-weight:700;">💧 Refill Water</div>`;
          }
          return '';
        ]]]

# ==============================================================================
# DASHBOARD VIEWS (3 VIEWS: WIDGETS, HOME, CAMERAS)
# ==============================================================================
views:

  # ----------------------------------------------------------------------------
  # VIEW 1: WIDGETS (Modular / StandBy Face - Always On, No Screensaver)
  # ----------------------------------------------------------------------------
  - title: Widgets
    path: widgets
    type: panel
    background: center / cover no-repeat url("/local/media/glass.jpg") fixed
    cards:
      - type: vertical-stack
        cards:
          - type: horizontal-stack
            cards:
              # Big Date & Analog Clock Column
              - type: vertical-stack
                cards:
                  - type: custom:button-card
                    name: >
                      [[[
                        const d = new Date();
                        return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
                      ]]]
                    styles:
                      card:
                        - background: 'rgba(255,255,255,0.12)'
                        - backdrop-filter: 'blur(24px)'
                        - border-radius: '24px'
                        - padding: '18px'
                      name:
                        - font-size: '34px'
                        - font-weight: '800'
                        - color: '#FF3B30'
                  - type: custom:button-card
                    template: analog_clock
              # Photo Slideshow Widget (Cycles /media/local/Photo Slideshow every 2 mins)
              - type: custom:wallpanel-card
                image_url: media-source://media_source/local/Photo Slideshow
                image_order: random
                idle_time: 0
                display_time: 120
              # Weather & Upcoming Calendar Column
              - type: vertical-stack
                cards:
                  - type: custom:button-card
                    template: weather_widget
                  - type: custom:button-card
                    template: calendar_widget

  # ----------------------------------------------------------------------------
  # VIEW 2: HOME (Main Smart Home Face - Default Landing View: /home-widget/home)
  # ----------------------------------------------------------------------------
  - title: Home
    path: home
    type: panel
    background: center / cover no-repeat url("/local/media/glass.jpg") fixed
    cards:
      - type: vertical-stack
        cards:
          # TOP ROW: Clock, Weather Widget, Live Porch/Doorbell Snapshot
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                template: analog_clock
              - type: custom:button-card
                template: weather_widget
              - type: picture-entity
                entity: camera.your_doorbell_medium
                name: Front Porch
                show_state: false
                tap_action:
                  action: navigate
                  navigation_path: '#doorbell-popup'

          # MIDDLE GRID: Glass Accessory & Scene Tiles
          - type: grid
            columns: 4
            square: false
            cards:
              - type: custom:button-card
                template: glass_tile
                entity: lock.your_front_door_lock
                name: Front Door
                icon: mdi:lock
              - type: custom:button-card
                template: glass_tile
                entity: cover.your_garage_door
                name: Garage Door
                icon: mdi:garage
              - type: custom:button-card
                template: glass_tile
                entity: light.your_porch_light
                name: Lights · Front Porch
                icon: mdi:outdoor-lamp
              - type: custom:button-card
                template: glass_tile
                entity: light.your_room_lights
                name: Lights · Studio
                icon: mdi:lightbulb-group
              - type: custom:button-card
                template: glass_tile
                entity: light.your_curtain_lights
                name: Curtain Lights
                icon: mdi:string-lights
              - type: custom:button-card
                template: fan_tile
                entity: switch.your_ceiling_fan
                name: Ceiling Fan
              - type: custom:button-card
                template: vacuum_tile
                entity: vacuum.your_vacuum_entity
                name: Narwal Vacuum
              - type: vertical-stack
                cards:
                  - type: custom:button-card
                    template: scene_tile
                    entity: scene.your_good_night_scene
                    name: Good Night
                    icon: mdi:weather-night
                  - type: custom:button-card
                    template: scene_tile
                    entity: scene.your_lights_off_scene
                    name: Studio Off
                    icon: mdi:power

          # BOTTOM BAR: Family Calendar Bar (Next events + Full week popup)
          - type: custom:button-card
            template: calendar_widget

          # ====================================================================
          # BUBBLE CARD MODAL POPUPS (HOME VIEW)
          # ====================================================================

          # POPUP 1: Doorbell Live Feed + Package Cam + Lock/Garage Controls
          # Automatically opens for 45s when event.your_doorbell_ring fires
          - type: vertical-stack
            cards:
              - type: custom:bubble-card
                card_type: pop-up
                hash: '#doorbell-popup'
                name: Front Doorbell
                icon: mdi:doorbell-video
                auto_close: '45000'
                trigger_entity: event.your_doorbell_ring
              - type: picture-glance
                title: Live Feed (High Res)
                camera_image: camera.your_doorbell_high
                camera_view: live
                entities:
                  - entity: lock.your_front_door_lock
                  - entity: cover.your_garage_door
                  - entity: light.your_porch_light
              - type: picture-entity
                entity: camera.your_package_camera
                name: Package Camera
                camera_view: live
              - type: custom:button-card
                name: Close
                icon: mdi:close
                tap_action:
                  action: navigate
                  navigation_path: /home-widget/home

          # POPUP 2: Detailed Weather Forecast Popup
          - type: vertical-stack
            cards:
              - type: custom:bubble-card
                card_type: pop-up
                hash: '#weather-popup'
                name: Detailed Weather Forecast
                icon: mdi:weather-partly-cloudy
              - type: weather-forecast
                entity: weather.your_weather
                forecast_type: twice_daily
                show_current: true
                show_forecast: true
              - type: custom:button-card
                name: Close
                icon: mdi:close
                tap_action:
                  action: navigate
                  navigation_path: /home-widget/home

          # POPUP 3: Full-Week Calendar Popup
          - type: vertical-stack
            cards:
              - type: custom:bubble-card
                card_type: pop-up
                hash: '#calendar-popup'
                name: Family Schedule (7-Day View)
                icon: mdi:calendar-month
              - type: calendar
                initial_view: listWeek
                entities:
                  - calendar.your_calendar_1
                  - calendar.your_calendar_2
              - type: custom:button-card
                name: Close
                icon: mdi:close
                tap_action:
                  action: navigate
                  navigation_path: /home-widget/home

          # POPUP 4: Narwal Flow 2 Robot Vacuum Controller Popup
          - type: vertical-stack
            cards:
              - type: custom:bubble-card
                card_type: pop-up
                hash: '#vacuum-popup'
                name: Narwal Flow 2 Controller
                icon: mdi:robot-vacuum
              - type: entities
                title: Vacuum Controls & Rooms
                entities:
                  - entity: vacuum.your_vacuum_entity
                  - entity: select.your_vacuum_cleaning_mode
                  - entity: button.your_vacuum_return_to_dock
                  - entity: binary_sensor.your_vacuum_water_low
              - type: custom:button-card
                name: Close
                icon: mdi:close
                tap_action:
                  action: navigate
                  navigation_path: /home-widget/home

  # ----------------------------------------------------------------------------
  # VIEW 3: CAMERAS (3x3 Snapshot Grid + High-Res Live Stream Popups)
  # ----------------------------------------------------------------------------
  - title: Cameras
    path: cameras
    type: panel
    background: center / cover no-repeat url("/local/media/glass.jpg") fixed
    cards:
      - type: vertical-stack
        cards:
          # 3x3 Camera Snapshot Grid (Uses _medium resolution entities for smooth FPS)
          # Note: Cameras 6 (Right Yard) and 9 (Left Yard) support tall 9:16 aspect ratios
          - type: grid
            columns: 3
            square: false
            cards:
              # Tile 1: Doorbell
              - type: picture-entity
                entity: camera.your_doorbell_medium
                name: 1 · Doorbell
                camera_view: auto
                tap_action:
                  action: navigate
                  navigation_path: '#cam-1-popup'
              # Tile 2: Package Camera
              - type: picture-entity
                entity: camera.your_package_camera
                name: 2 · Package Cam
                camera_view: auto
                tap_action:
                  action: navigate
                  navigation_path: '#cam-2-popup'
              # Tile 3: Front Porch
              - type: picture-entity
                entity: camera.your_camera_3_medium
                name: 3 · Front Porch
                camera_view: auto
                tap_action:
                  action: navigate
                  navigation_path: '#cam-3-popup'
              # Tile 4: Driveway
              - type: picture-entity
                entity: camera.your_camera_4_medium
                name: 4 · Driveway
                camera_view: auto
                tap_action:
                  action: navigate
                  navigation_path: '#cam-4-popup'
              # Tile 5: Garage
              - type: picture-entity
                entity: camera.your_camera_5_medium
                name: 5 · Garage
                camera_view: auto
                tap_action:
                  action: navigate
                  navigation_path: '#cam-5-popup'
              # Tile 6: Right Yard (Tall 9:16)
              - type: picture-entity
                entity: camera.your_camera_6_medium
                name: 6 · Right Yard (9:16)
                aspect_ratio: '9:16'
                camera_view: auto
                tap_action:
                  action: navigate
                  navigation_path: '#cam-6-popup'
              # Tile 7: Backyard
              - type: picture-entity
                entity: camera.your_camera_7_medium
                name: 7 · Backyard
                camera_view: auto
                tap_action:
                  action: navigate
                  navigation_path: '#cam-7-popup'
              # Tile 8: Back Porch
              - type: picture-entity
                entity: camera.your_camera_8_medium
                name: 8 · Back Porch
                camera_view: auto
                tap_action:
                  action: navigate
                  navigation_path: '#cam-8-popup'
              # Tile 9: Left Yard (Tall 9:16)
              - type: picture-entity
                entity: camera.your_camera_9_medium
                name: 9 · Left Yard (9:16)
                aspect_ratio: '9:16'
                camera_view: auto
                tap_action:
                  action: navigate
                  navigation_path: '#cam-9-popup'

          # ====================================================================
          # CAMERA LIVE STREAM POPUPS (High-Res + Lock, Garage, Prev/Next, Close)
          # Pattern shown for Cam 1..9 so Claude can replicate for each camera
          # ====================================================================
          - type: vertical-stack
            cards:
              - type: custom:bubble-card
                card_type: pop-up
                hash: '#cam-1-popup'
                name: Doorbell (Live High-Res)
                icon: mdi:cctv
              - type: picture-entity
                entity: camera.your_doorbell_high
                camera_view: live
              - type: horizontal-stack
                cards:
                  - type: custom:button-card
                    template: glass_tile
                    entity: lock.your_front_door_lock
                    name: Lock
                    aspect_ratio: 2/1
                  - type: custom:button-card
                    template: glass_tile
                    entity: cover.your_garage_door
                    name: Garage
                    aspect_ratio: 2/1
                  - type: custom:button-card
                    name: Prev
                    icon: mdi:chevron-left
                    tap_action:
                      action: navigate
                      navigation_path: '#cam-9-popup'
                  - type: custom:button-card
                    name: Next
                    icon: mdi:chevron-right
                    tap_action:
                      action: navigate
                      navigation_path: '#cam-2-popup'
                  - type: custom:button-card
                    name: Close
                    icon: mdi:close
                    tap_action:
                      action: navigate
                      navigation_path: /home-widget/cameras
```