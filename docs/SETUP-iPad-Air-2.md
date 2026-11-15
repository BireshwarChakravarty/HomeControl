# HomeView on an iPad Air 2 (iPadOS 15.8): setup guide

This guide covers the whole job, from checking the iPad to a wall-mounted HomeView panel.
Steps 1 to 5 happen in Home Assistant, from any computer. Step 6 happens on the iPad.

---

## 0. Will an iPad Air 2 still work? Yes, with three caveats

| Piece | Status for iPad Air 2 / iPadOS 15.8.6 |
|---|---|
| **Home Assistant web UI** | Works. HA 2026.11 set the minimum to **Safari/iOS 15.4**. iPadOS 15.8 ships Safari 15.6, so this iPad is above the line. The devices that were dropped are the iPad Air 1 and iPad mini 2/3. |
| **HA Companion app** | Version 2026.8.0 and later need iOS 16.4. The **last version for iPadOS 15 is 2026.7.1**. The App Store offers it as "Download the last compatible version". |
| **Known breakage** | HA **2026.6.0 and 2026.6.1** hung on the splash screen on iPadOS 15, including the iPad Air 2. **2026.6.2 fixed it.** Stay on 2026.6.2 or newer. |

What to do about it:

1. On the iPad, go to **Settings → General → Software Update** and install the newest 15.8.x release.
2. Before you update the HA *server*, read the release notes' **Breaking changes** and search for "Safari", "iOS" or "browser". A future release could raise the minimum above iOS 15. That would retire this iPad as a panel, and no browser on iPadOS 15 can work around it.
3. If the Companion app ever misbehaves, use the web app instead. Open your HA URL in Safari, then **Share → Add to Home Screen**. It runs full-screen and everything here works the same.

---

## 1. Install the frontend plugins (HACS)

Install [HACS](https://hacs.xyz) first if you don't have it. Then go to **HACS → search** and install each of these. They're all "Dashboard" type plugins:

| Plugin | What it does here |
|---|---|
| **button-card** | Draws every tile, the clock, the date, weather, calendar and photo frame |
| **Bubble Card** | The pop-ups: weather, calendar, vacuum, doorbell and live cameras |
| **WallPanel** | Shows the clock screensaver after 2 minutes idle |
| **Kiosk Mode** | Hides the HA header and sidebar |
| **Swipe Navigation** | Swipes left and right between the three views |

When they're installed, hard-refresh your browser.

## 2. Create the helpers and sensors HomeView uses

**Time and date sensors.** These keep the clock, date, calendar labels and photo frame in sync.
Go to Settings → Devices & services → **Add integration → Time & Date** and pick **Time**. Add the integration a second time and pick **Date**.
Check that `sensor.time` and `sensor.date` exist.

**Three toggle helpers.** Go to Settings → Devices & services → Helpers → **Create helper → Toggle**. Use exactly these names, so HA generates the entity IDs below:

| Name | Entity ID | Purpose |
|---|---|---|
| HomeView Screensaver | `input_boolean.homeview_screensaver` | WallPanel turns it on while the clock screensaver shows. An automation turns it off to wake the screen. |
| HomeView Kiosk | `input_boolean.homeview_kiosk` | Hold the clock to hide or show the HA header for admin users. |
| HomeView Doorbell Popup | `input_boolean.homeview_doorbell_popup` | Opens the doorbell pop-up for 45 s when someone rings. |

**A dedicated iPad user.** Go to Settings → People → **Add person**, for example "iPad Panel". Turn on *Allow login* and leave **Administrator off**.
Kiosk Mode always hides the header and sidebar for non-admin users, and it keeps the panel's login separate from yours.

## 3. Map your devices

There are two ways to do this:

- **Easiest:** send me your entity list and I'll fill everything in. In HA, go to **Developer tools → Template**, paste the template below, and copy the output back to me:

  ```jinja
  {% for s in states
     if s.domain in ['light','switch','fan','lock','cover','scene','script','camera',
                     'weather','calendar','vacuum','event','select']
     or (s.domain == 'binary_sensor'
         and s.attributes.device_class in ['motion','occupancy','presence','problem']) %}
  {{ s.entity_id }} | {{ s.name }}
  {% endfor %}
  ```

- **Yourself:** edit [`homeview/config.yaml`](../homeview/config.yaml). Replace each `your_…` value, and delete any section you don't have, such as the vacuum, doorbell or cameras. Then run:

  ```bash
  python3 homeview/build_dashboard.py
  ```

  It rewrites `dist/`, adapts the layout to however many tiles and cameras you have, and lists any placeholders you missed.

## 4. Create the dashboard

1. Go to Settings → Dashboards → **Add dashboard → New dashboard from scratch**. Set the title to `HomeView` and the URL to `home-widget`. If you use another URL, set `dashboard.url_path` in `config.yaml` and rebuild.
2. Open the dashboard, then click the **pencil → ⋮ → Raw configuration editor**.
3. Select everything in the editor and replace it with the contents of [`dist/homeview_dashboard.yaml`](../dist/homeview_dashboard.yaml). Click **Save**.

## 5. Add the automations

Each file in [`dist/automations/`](../dist/automations/) is one automation. For each file: go to Settings → Automations → **Create automation → ⋮ → Edit in YAML**, paste the file, and click **Save**.

| File | Does |
|---|---|
| `homeview_wake_on_motion.yaml` | Wakes the screensaver when your motion or presence sensor sees someone |
| `homeview_doorbell_popup.yaml` | When the doorbell rings: wakes the screen and opens the doorbell pop-up with live video for 45 s |
| `homeview_ipad_charging.yaml` | *(optional)* Only appears if you fill in `charging:` in the config. It toggles a smart plug so the old battery stays between 30 and 80 % instead of sitting at 100 % all the time. |

**Photo frame (Widgets view).** Run this on your computer:

```bash
python3 tools/prepare_slideshow.py ~/Pictures/ForThePanel ./slideshow --limit 80 --shuffle
```

Copy the resulting `slideshow` folder to **`/config/www/homeview/slideshow`** on the HA server. You can use the Samba share, File editor or Studio Code Server add-on.
Set `photos.count` in the config to the number the script printed, then rebuild.
If `/config/www` didn't exist before, restart HA once so `/local/` starts serving it.
The script shrinks photos to about 1400 px. Full-size iPhone photos are the quickest way to make a 2 GB iPad stutter.

## 6. Set up the iPad

1. **App:** install **Home Assistant 2026.7.1** (the last compatible version). Sign in as the **iPad Panel** user.
2. **Default dashboard:** in the app, tap the **profile** (bottom of the sidebar) → **Dashboard → HomeView**. While you're there, set **Theme → Dark**.
3. **Never sleep:** go to Settings → Display & Brightness → **Auto-Lock → Never**.
4. **No interruptions:** turn on a **Focus / Do Not Disturb** that's always on, and turn off notification banners for other apps.
5. **Lock it to the app:** go to Settings → Accessibility → **Guided Access → On** and set a passcode. Open the HA app and **triple-click the Home button → Start**. This stops anyone leaving the app, and iPadOS won't kill it in the background.
6. **Landscape:** rotate the iPad to landscape. Swipe down from the top-right corner and tap **rotation lock**.
7. **If styles look stale or broken** after a change: in the app, go to Settings → Companion App → **Debugging → Reset frontend cache**, then pull down to reload.

---

## Using it

- **Swipe** left and right between **Widgets** (StandBy-style clock, photo, weather, agenda), **Home** (controls) and **Cameras**.
- **Tiles:** tap to toggle. **Hold** a tile for HA's detail dialog with brightness, colour and so on. Locks and the garage door **ask before** they unlock or open.
- **Hold the clock** about 1 s to show or hide the HA header. This only matters for admin logins, because the iPad Panel user never sees the header.
  To get out of kiosk mode completely, add `?disable_km` to the URL.
- **Screensaver:** after 2 minutes idle on Home or Cameras, a large clock appears. Tap it, or walk past the motion sensor, to wake it.
  The Widgets view never shows the screensaver, so you can leave the iPad on it as an always-on display.
- **Doorbell:** a ring opens the live doorbell pop-up on whichever view is showing, and closes it after 45 s.
- **Cameras:** the grid shows snapshots that refresh about every 10 s, which is cheap. Tap a camera for its live stream with **Prev / Next** buttons and lock/garage controls.
  Bubble Card unloads a pop-up's contents when it closes, so only one live stream runs at a time.

## If the iPad feels slow

In order of impact:

1. Set `dashboard.glass_blur: false` in the config and rebuild. This removes the frosted blur, which is the heaviest GPU effect on the A8X.
2. Use the **lower-resolution** camera stream (often called "medium", "sub" or "fluent") as `snapshot:` for the grid tiles.
3. Keep the photo count under about 100 and run them through `prepare_slideshow.py`.
4. Once a week, end Guided Access, swipe the app away and reopen it. Old iPads leak memory over days.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Stuck on the HA logo / "Unable to connect" after an HA update | This usually means a frontend regression on iPadOS 15. Check the [HA frontend issues](https://github.com/home-assistant/frontend/issues) for "iPadOS 15". Restore the backup HA takes before updating, or wait for the patch release. |
| A tile shows a red "Custom element doesn't exist" | That HACS plugin isn't installed or loaded. Reinstall it and reset the frontend cache (step 6.7). |
| Clock, date or photo never change | `sensor.time` or `sensor.date` is missing (step 2). |
| Doorbell pop-up doesn't open | Check that the automation turns `input_boolean.homeview_doorbell_popup` on. Older Bubble Card releases use `trigger_entity` / `trigger_state` instead of the `trigger:` list, so update Bubble Card. |
| Camera tile is black | The camera entity has no snapshot support, or its stream is H.265 or another codec Safari 15 can't play. Use the camera's H.264 sub-stream. |
| Photo frame is empty | Open `http://<ha>:8123/local/homeview/slideshow/photo001.jpg` in a browser. If you get a 404, check the folder location and restart HA once. |

## What changed from the original YAML

The reference files are in [`reference/`](../reference/). These changes adapt them to the iPad Air 2 and fix bugs:

1. **Frosted glass didn't render.** Safari before 18 only understands `-webkit-backdrop-filter`. Every blur now has both versions, and the blur radius is halved for the A8X.
2. **The analog clock didn't tick.** button-card only re-renders when an entity changes. The hands are now CSS-animated from the correct angle and re-sync every minute.
3. **The photo slideshow card:** `custom:wallpanel-card` isn't a card that WallPanel documents. It's replaced with a button-card photo frame that reads numbered files.
4. **The doorbell auto pop-up never fired.** An `event.*` entity's state is a timestamp, so `trigger_entity` never matched. A helper boolean and an automation now drive it.
5. **Weather and calendar taps on the Widgets view did nothing.** Bubble pop-ups only exist on the view that contains them. Each view now has the pop-ups it links to, and the doorbell pop-up is on every view.
6. **Two live streams in the doorbell pop-up** are now one live stream plus the package camera as refreshing snapshots.
7. **The 9:16 camera tiles** made the 3×3 grid about 1,000 px tall on a 768 px screen. Every tile is now a uniform, cropped 16:9.
8. **Square tiles overflowed the screen.** Every view now uses an exact grid sized for 1024×768 with kiosk mode on. The build script resizes it when you have more or fewer tiles.
9. **Unlocking the front door or opening the garage was a single accidental tap.** Both now ask for confirmation.
10. **Smaller fixes:**
    - The weather grid referenced a nonexistent `icon` area.
    - Calendar times were raw strings; they now read like "Today · 3:00 PM".
    - `twice_daily` forecasts only work with NWS; the default is now hourly plus daily.
    - The scene tiles now use `perform-action`.
    - The Close buttons jumped between views; Bubble Card's own close is used instead.
    - The WallPanel screensaver is now off on the Widgets view.
    - The unused `camera_tile` template is removed.

### Not yet tested on real hardware

The YAML is generated and checked automatically:

- every pop-up link has a matching pop-up;
- all 14 JavaScript templates run against mock data;
- the layout was rendered in a mock at 1024×768.

It has **not** run in a live Home Assistant with the real plugins yet.

A few plugin options come from those projects' documentation rather than a live test:

- WallPanel `enabled_on_tabs`;
- Bubble Card `trigger`, `width_desktop` and `bg_blur`;
- picture-entity `fit_mode`.

If one of them behaves differently, tell me what you see and I'll adjust the generator.
