## 🚴‍♂️ BC2 Virtual Shifter Bridge

A small windowed Python app that turns the CYCPLUS BC2 Bluetooth controller into a working virtual shifter for MyWhoosh.

It connects to the BC2 over Bluetooth Low Energy, listens for the upshift and downshift buttons, and sends the matching keyboard presses MyWhoosh uses for its built-in virtual shifting. Everything runs in a tidy little window — no terminal, no console spam.

Perfect for setups like a Saris H3 or any trainer that doesn’t have built-in shifting.

## 🧩 Features

- One-click Start / Stop button
- Live status indicator: gray = stopped, orange = searching / retrying, green = connected
- Remappable keys — upshift defaults to `k`, downshift to `i` (MyWhoosh defaults), editable live in the window
- Activity log showing the last 5 events with timestamps
- Auto-retry: if it can’t find the BC2 or the connection drops, it keeps scanning and reconnecting on its own
- 100 ms debounce to keep rapid shifts clean
- Dark or light theme (flip `THEME` at the top of the file)

## ⚙️ Requirements

- Python 3.9+
- A Bluetooth Low Energy (BLE) adapter
- Two Python packages:

  `py -m pip install bleak pyautogui`

## 🚀 How to Use

1. Wake the shifter: hold both the UP (+) and DOWN (−) buttons simultaneously for about 5 seconds.
2. Double-click `bc2_virtual_shifter_gui.pyw`.
3. The app starts searching automatically. When the status dot turns green it’s connected and listening for shifts — if it can’t find the BC2 it tells you to hold + and − again and retries every few seconds.
4. Open MyWhoosh (or your preferred app) and ride.

Use the Stop button to pause, Start to jump back in. Closing the window stops everything cleanly.

## 🔧 Configuration

The shift keys are changed right in the window — no code needed. Anything else lives in the constants at the top of the file:

- `DEVICE_NAME` — the BLE name to look for (default: `BC2`)
- `DEBOUNCE_MS` — minimum gap between simulated keypresses (default: 100)
- `SCAN_TIMEOUT` — how long each scan lasts (default: 10 s)
- `RETRY_DELAY` — pause between connection attempts (default: 3 s)
- `THEME` — `"dark"` or `"light"`

## 💡 Notes

- Tested on Windows 11 with Python 3.13.9 and MyWhoosh using a Saris H3.

## 🧠 Background

I bought the BC2 thinking it would just work for virtual shifting in MyWhoosh with my Saris H3 — turns out, it didn’t.
Nothing fancy, but it does exactly what I needed — so I’m sharing it in case it helps someone else.
