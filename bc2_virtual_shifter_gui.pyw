"""
BC2 Virtual Shifter Bridge - windowed version (no console)

Based on dxD7/CYCPLUS-BC2-Virtual-Shifter (GPL-3.0).
Double-click this .pyw file to run it without a terminal window.

Requirements:  py -m pip install bleak pyautogui
"""
import asyncio
import queue
import threading
import time
import tkinter as tk
import tkinter.font as tkfont

import pyautogui
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic

# --- Configuration ---------------------------------------------------------
DEVICE_NAME = "BC2"
DEBOUNCE_MS = 100            # Minimum time (ms) between two simulated keypresses
SCAN_TIMEOUT = 10.0          # Seconds to scan before trying again
RETRY_DELAY = 3.0            # Seconds to wait between attempts
UART_NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

SHIFT_KEYS = {6: "k", 7: "i"}   # packet index -> key (editable in the window)

PRESSED_VALUES = {0x01, 0x02, 0x03}
RELEASE_VALUE = 0x00

# --- Look ------------------------------------------------------------------
THEME = "dark"   # "light" or "dark"

PALETTES = {
    "light": dict(BG="#f2f2f7", CARD="#ffffff", TEXT="#1c1c1e", MUTED="#8e8e93",
                  DIVIDER="#e5e5ea", FILL="#f2f2f7", ACCENT="#007aff",
                  ACCENT_HOVER="#0a6fe0", SECONDARY="#e5e5ea", SECONDARY_HOVER="#d8d8de"),
    "dark": dict(BG="#1c1c1e", CARD="#2c2c2e", TEXT="#f2f2f7", MUTED="#98989f",
                 DIVIDER="#3a3a3c", FILL="#3a3a3c", ACCENT="#0a84ff",
                 ACCENT_HOVER="#3d9bff", SECONDARY="#3a3a3c", SECONDARY_HOVER="#48484a"),
}
globals().update(PALETTES[THEME])

GREEN, ORANGE, GRAY = "#34c759", "#ff9f0a", "#8e8e93"
FONT = "Segoe UI"            # replaced at startup by the best available font
CARD_W = 312
MAX_EVENTS = 5


# --- BLE worker (own thread, own asyncio loop) -----------------------------
class BridgeWorker(threading.Thread):
    def __init__(self, ui_queue: queue.Queue):
        super().__init__(daemon=True)
        self.q = ui_queue
        self.loop = None
        self.stop_event = None
        self.last_press_time = 0.0
        self.last_shift_state = {6: RELEASE_VALUE, 7: RELEASE_VALUE}

    def log(self, msg, kind="info"):
        self.q.put(("log", msg, kind))

    def status(self, text, color, detail=""):
        self.q.put(("status", text, color, detail))

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.stop_event = asyncio.Event()
        try:
            self.loop.run_until_complete(self.main())
        finally:
            self.loop.close()
            self.q.put(("done",))

    def stop(self):
        if self.loop and self.stop_event and not self.loop.is_closed():
            try:
                self.loop.call_soon_threadsafe(self.stop_event.set)
            except RuntimeError:
                pass  # loop already closed, nothing left to stop

    async def interruptible_sleep(self, seconds):
        try:
            await asyncio.wait_for(self.stop_event.wait(), seconds)
        except asyncio.TimeoutError:
            pass

    async def main(self):
        while not self.stop_event.is_set():
            missing = False
            try:
                missing = await self.session() == "missing"
            except Exception as e:  # never exit on an error, just retry
                self.log(f"Error: {str(e)[:40]}")

            if self.stop_event.is_set():
                break
            detail = ("Not found. Hold + and \u2212 for 5 seconds" if missing
                      else f"Trying again in {RETRY_DELAY:.0f} seconds")
            self.status("Waiting to retry", ORANGE, detail)
            await self.interruptible_sleep(RETRY_DELAY)

        self.status("Stopped", GRAY, "Press Start to connect")
        self.log("Stopped")

    async def session(self):
        self.status("Searching", ORANGE, f"Looking for {DEVICE_NAME}")
        self.log("Searching")

        device = await BleakScanner.find_device_by_filter(
            lambda d, ad: bool(d.name) and DEVICE_NAME.lower() in d.name.lower(),
            timeout=SCAN_TIMEOUT,
        )
        if self.stop_event.is_set():
            return None
        if not device:
            self.log("Not found")
            return "missing"

        self.status("Connecting", ORANGE, device.name or DEVICE_NAME)

        disconnected = asyncio.Event()
        loop = asyncio.get_running_loop()
        self.last_shift_state = {6: RELEASE_VALUE, 7: RELEASE_VALUE}

        def on_disconnect(_client):
            loop.call_soon_threadsafe(disconnected.set)

        async with BleakClient(device, disconnected_callback=on_disconnect) as client:
            await client.start_notify(UART_NOTIFY_UUID, self.handle_notify)
            self.status("Connected", GREEN, "Listening for shifts")
            self.log("Connected")

            waiters = [
                asyncio.ensure_future(disconnected.wait()),
                asyncio.ensure_future(self.stop_event.wait()),
            ]
            await asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED)
            for w in waiters:
                w.cancel()

        if not self.stop_event.is_set():
            self.log("Connection lost")
        return None

    # Same state machine as the original script
    def handle_notify(self, sender: BleakGATTCharacteristic, data: bytearray):
        now = time.time() * 1000

        for index in (6, 7):
            if len(data) <= index:
                continue

            current_byte = data[index]
            last_byte = self.last_shift_state[index]
            key = SHIFT_KEYS.get(index)

            if (current_byte in PRESSED_VALUES and last_byte in PRESSED_VALUES
                    and current_byte != last_byte):
                if now - self.last_press_time > DEBOUNCE_MS and key:
                    pyautogui.press(key)
                    self.last_press_time = now
                    self.log("Upshift" if index == 6 else "Downshift", "shift")
                self.last_shift_state[index] = RELEASE_VALUE

            elif current_byte in PRESSED_VALUES and last_byte == RELEASE_VALUE:
                self.last_shift_state[index] = current_byte

            elif current_byte == RELEASE_VALUE and last_byte in PRESSED_VALUES:
                self.last_shift_state[index] = RELEASE_VALUE

            else:
                if current_byte in PRESSED_VALUES and last_byte != current_byte:
                    self.last_shift_state[index] = current_byte


# --- Small custom widgets --------------------------------------------------
def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class Card(tk.Canvas):
    """Rounded white panel with an inner frame to put widgets in."""

    def __init__(self, parent, width, height, pad_x=16, pad_y=0, radius=12):
        super().__init__(parent, width=width, height=height, bg=BG, highlightthickness=0)
        round_rect(self, 1, 1, width - 1, height - 1, radius, fill=CARD, outline="")
        self.inner = tk.Frame(self, bg=CARD)
        self.create_window(pad_x, pad_y, window=self.inner, anchor="nw",
                           width=width - 2 * pad_x, height=height - 2 * pad_y)


class PillButton(tk.Canvas):
    def __init__(self, parent, command, width=132, height=36):
        super().__init__(parent, width=width, height=height, bg=BG, highlightthickness=0)
        self.bw, self.bh, self.command = width, height, command
        self.label, self.fill, self.hover_fill = "", ACCENT, ACCENT_HOVER
        self.fg, self.enabled, self.hovering = "#ffffff", True, False
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))

    def set_look(self, label, fill, hover_fill, fg, enabled=True):
        self.label, self.fill, self.hover_fill = label, fill, hover_fill
        self.fg, self.enabled = fg, enabled
        self.config(cursor="hand2" if enabled else "arrow")
        self.render()

    def render(self):
        self.delete("all")
        fill = self.hover_fill if (self.hovering and self.enabled) else self.fill
        round_rect(self, 1, 1, self.bw - 1, self.bh - 1, self.bh // 2, fill=fill, outline="")
        self.create_text(self.bw / 2, self.bh / 2, text=self.label, fill=self.fg,
                         font=(FONT, 11, "bold"))

    def _hover(self, on):
        self.hovering = on
        self.render()

    def _click(self, _event):
        if self.enabled:
            self.command()


# --- Window ----------------------------------------------------------------
class App:
    def __init__(self, root: tk.Tk):
        global FONT
        self.root = root
        self.q = queue.Queue()
        self.worker = None
        self.events = []   # newest first: (time string, text)

        available = set(tkfont.families(root))
        for name in ("SF Pro Display", "Helvetica Neue", "Segoe UI Variable Display", "Segoe UI"):
            if name in available:
                FONT = name
                break

        root.title("BC2 shifter")
        root.configure(bg=BG)
        root.resizable(False, False)

        outer = tk.Frame(root, bg=BG, padx=24, pady=28)
        outer.pack()

        # Status (centered)
        row = tk.Frame(outer, bg=BG)
        row.pack()
        self.dot = tk.Canvas(row, width=12, height=12, bg=BG, highlightthickness=0)
        self.dot_item = self.dot.create_oval(1, 1, 11, 11, fill=GRAY, outline="")
        self.dot.pack(side="left", padx=(0, 10), pady=(4, 0))
        self.status_lbl = tk.Label(row, text="Stopped", bg=BG, fg=TEXT,
                                   font=(FONT, 22, "bold"))
        self.status_lbl.pack(side="left")
        self.detail_lbl = tk.Label(outer, text="", bg=BG, fg=MUTED, font=(FONT, 10),
                                   wraplength=CARD_W, justify="center")
        self.detail_lbl.pack(pady=(2, 0))

        self.btn = PillButton(outer, self.toggle)
        self.btn.pack(pady=(18, 24))

        # Keys card
        keys = Card(outer, CARD_W, 93)
        keys.pack(pady=(0, 14))
        self.up_var = tk.StringVar(value=SHIFT_KEYS[6])
        self.down_var = tk.StringVar(value=SHIFT_KEYS[7])
        self._key_row(keys.inner, "Upshift key", self.up_var, 6)
        tk.Frame(keys.inner, bg=DIVIDER, height=1).pack(fill="x")
        self._key_row(keys.inner, "Downshift key", self.down_var, 7)

        # Activity card
        row_h, pad_y = 28, 10
        activity = Card(outer, CARD_W, MAX_EVENTS * row_h + 2 * pad_y, pad_y=pad_y)
        activity.pack()
        self.rows = []
        for _ in range(MAX_EVENTS):
            r = tk.Frame(activity.inner, bg=CARD, height=row_h)
            r.pack(fill="x")
            r.pack_propagate(False)
            name = tk.Label(r, text="", bg=CARD, fg=MUTED, font=(FONT, 10))
            name.pack(side="left")
            when = tk.Label(r, text="", bg=CARD, fg=MUTED, font=(FONT, 10))
            when.pack(side="right")
            self.rows.append((name, when))
        self.render_events()

        self.set_button("wait")
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(100, self.poll_queue)
        self.start()

    def _key_row(self, parent, label, var, index):
        row = tk.Frame(parent, bg=CARD, height=46)
        row.pack(fill="x")
        row.pack_propagate(False)
        tk.Label(row, text=label, bg=CARD, fg=TEXT, font=(FONT, 11)).pack(side="left")
        tk.Entry(row, textvariable=var, width=5, justify="center", bg=FILL, fg=ACCENT,
                 insertbackground=ACCENT, relief="flat", bd=0, font=(FONT, 11, "bold"),
                 highlightthickness=1, highlightbackground=FILL,
                 highlightcolor=ACCENT).pack(side="right", ipady=4)
        var.trace_add("write", lambda *_: self.update_key(index, var))

    @staticmethod
    def update_key(index, var):
        value = var.get().strip()
        if value:
            SHIFT_KEYS[index] = value

    def set_button(self, mode):
        if mode == "start":
            self.btn.set_look("Start", ACCENT, ACCENT_HOVER, "#ffffff")
        elif mode == "stop":
            self.btn.set_look("Stop", SECONDARY, SECONDARY_HOVER, TEXT)
        else:
            self.btn.set_look("Stopping", SECONDARY, SECONDARY, MUTED, enabled=False)

    def add_event(self, text, kind):
        stamp = time.strftime("%H:%M:%S")
        if kind != "shift" and self.events and self.events[0][1] == text:
            self.events[0] = (stamp, text)          # repeated message: just refresh the time
        else:
            self.events.insert(0, (stamp, text))
            del self.events[MAX_EVENTS:]
        self.render_events()

    def render_events(self):
        for i, (name, when) in enumerate(self.rows):
            if i < len(self.events):
                stamp, text = self.events[i]
                name.config(text=text, fg=TEXT if i == 0 else MUTED)
                when.config(text=stamp)
            else:
                name.config(text="No activity yet" if i == 0 and not self.events else "")
                when.config(text="")

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        self.worker = BridgeWorker(self.q)
        self.worker.start()
        self.set_button("stop")

    def toggle(self):
        if self.worker and self.worker.is_alive():
            self.worker.stop()
            self.set_button("wait")
        else:
            self.start()

    def poll_queue(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item[0] == "log":
                    self.add_event(item[1], item[2])
                elif item[0] == "status":
                    self.status_lbl.config(text=item[1])
                    self.detail_lbl.config(text=item[3])
                    self.dot.itemconfigure(self.dot_item, fill=item[2])
                elif item[0] == "done":
                    self.set_button("start")
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)

    def on_close(self):
        try:
            if self.worker and self.worker.is_alive():
                self.worker.stop()
        finally:
            self.root.destroy()


if __name__ == "__main__":
    try:  # sharper text on high-DPI Windows displays
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()
