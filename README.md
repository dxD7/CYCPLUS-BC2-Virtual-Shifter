# CYCPLUS-BC2-Virtual-Shifter
Turn your CYCPLUS BC2 into a working virtual shifter for MyWhoosh.

🚴‍♂️ BC2 Virtual Shifter Bridge

A small Python script that turns the CYCPLUS BC2 Bluetooth controller into a working virtual shifter for MyWhoosh.

It connects to the BC2 over Bluetooth, listens for the upshift and downshift buttons, and sends keyboard presses which match MyWhoosh’s built-in virtual shifting controls.

Perfect for setups like a Saris H3 or any trainer that doesn’t have built-in shifting.

🧩 Features

Automatically connects to the BC2 via Bluetooth

Maps upshift → K, downshift → I (MyWhoosh defaults)

⚙️ Requirements

You’ll need:

Python 3.9+

A Bluetooth Low Energy (BLE) adapter

The following Python packages:

pip install bleak pyautogui

🚀 How to Use

Run the script first:

python bc2_virtual_shifter.py


When you see:

🔍 Scanning for BC2... (waiting for connection)


then connect your BC2 — it will get detected automatically.

Wait for:

✅ Found device: CYCPLUS BC2 ...
🔗 Connected
🎧 Listening for shift signals...


Open MyWhoosh.

Shift away using the BC2:

Upshift → presses K

Downshift → presses I

🛠️ Customization

Change which keys are sent:

SHIFT_KEYS = {
    6: 'k',  # Upshift
    7: 'i',  # Downshift
}


Adjust debounce time (in milliseconds):

DEBOUNCE_MS = 100

💡 Notes

Start the script before connecting the BC2 in Bluetooth settings — that’s how it’s discovered properly.

Tested on Windows 11 with Python 3.13.9 and MyWhoosh.

Works great with the Saris H3 trainer.

🧠 Background

I bought the BC2 thinking it would just work for virtual shifting in MyWhoosh with my Saris H3 — turns out, it didn’t.
After a lot of trial and error (and some help from ChatGPT and Gemini), I wrote this little script to make it all work properly.

Nothing fancy, but it does exactly what I needed — so I’m sharing it in case it helps someone else.
