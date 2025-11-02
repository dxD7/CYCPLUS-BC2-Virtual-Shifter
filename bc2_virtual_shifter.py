import asyncio
import time
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
import pyautogui
import platform

# --- Configuration (Check and Adjust as needed) ---
DEVICE_NAME = "BC2"
DEBOUNCE_MS = 100            # Minimum time (ms) between two simulated keypresses
UART_NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

# Key Map
SHIFT_KEYS = {
    6: 'k', # Key for Upshift (Index 6)
    7: 'i', # Key for Downshift (Index 7)
}
# The bytes that signal a shift is active (0x01, 0x02, and 0x03 observed)
PRESSED_VALUES = {0x01, 0x02, 0x03}
# The value that indicates the button is RELEASED/Inactive
RELEASE_VALUE = 0x00

# --- State Variables ---
last_press_time = 0

# Independent state for each index: Stores the last *non-zero* byte seen at that index.
# When a new, different non-zero byte arrives, a shift is registered.
last_shift_state = {
    6: RELEASE_VALUE, # Last non-zero state seen at index 6
    7: RELEASE_VALUE  # Last non-zero state seen at index 7
}

# --- Core Logic: Notification Handler Function ---
def handle_notify(sender: BleakGATTCharacteristic, data: bytearray):
    """
    Independent state machine for each shift index (6 and 7).
    Resets to 0x00 instantly after a successful shift or button release.
    """
    global last_press_time, last_shift_state
    
    # Log the incoming data
    # print(f"📨 Data from {sender.uuid}: {data.hex()}")
    
    now = time.time() * 1000

    # Process Index 6 (Upshift) and Index 7 (Downshift) independently
    for index in [6, 7]:
        if len(data) > index:
            current_byte = data[index]
            last_byte = last_shift_state[index]
            key = SHIFT_KEYS.get(index)

            # --- State Machine Logic for the Current Index ---

            # 1. NEW SHIFT DETECTED (State change from one PRESSED_VALUE to another)
            if current_byte in PRESSED_VALUES and last_byte in PRESSED_VALUES and current_byte != last_byte:
                
                if now - last_press_time > DEBOUNCE_MS:
                    pyautogui.press(key)
                    last_press_time = now
                    print(f"↕ **SHIFT DETECTED** (Index: {index}, {hex(last_byte)}->{hex(current_byte)}) → **{key.upper()}**")
                    
                    # IMMEDIATELY reset state for this index after a successful press
                    last_shift_state[index] = RELEASE_VALUE 
                else:
                    # Debounce hit, but still a valid state change. Reset state to allow next shift.
                    print(f"🟡 Shift detected at index {index}, but ignored due to debounce.")
                    last_shift_state[index] = RELEASE_VALUE 
                    
            # 2. SHIFT INITIATION (First PRESSED_VALUE after RELEASE_VALUE)
            elif current_byte in PRESSED_VALUES and last_byte == RELEASE_VALUE:
                # Lock the new non-zero state. Now we wait for 0x00 or a different PRESSED_VALUE.
                last_shift_state[index] = current_byte
                # print(f"➖ Initial signal captured at index {index}: {hex(current_byte)}")

            # 3. BUTTON RELEASE (Non-zero state returns to 0x00)
            elif current_byte == RELEASE_VALUE and last_byte in PRESSED_VALUES:
                # The button was pressed (last_byte was non-zero) and is now released (current_byte is 0x00).
                # Reset state to allow a new shift sequence. No keypress happens here.
                last_shift_state[index] = RELEASE_VALUE
                # print(f"✅ Button released detected at index {index}. State reset.")

            # 4. Noise/No Change/Other Cases (e.g., 0x00 to 0x00, or same non-zero value repeated)
            else:
                # Update state if a noise packet contains a repeating non-zero value, 
                # but only if it's currently 0x00. This is a subtle nuance 
                # but helps handle device noise patterns.
                if current_byte in PRESSED_VALUES and last_byte != current_byte:
                    last_shift_state[index] = current_byte
                pass
                
# --- Main Connection Logic (Unchanged) ---
async def main():
    if platform.system() == "Linux":
        import os
        os.environ["BLESSED_NO_DANGER_RISK"] = "1"
        
    print(f"🔍 Scanning for {DEVICE_NAME}... (waiting for connection)")

    def filter_device(d, ad):
        return d.name and DEVICE_NAME.lower() in d.name.lower()

    device = await BleakScanner.find_device_by_filter(filter_device, timeout=20.0)
    if not device:
        print(f"❌ Device '{DEVICE_NAME}' not found. Make sure it's powered on and near your PC.")
        return

    print(f"✅ Found device: {device.name or 'Unnamed'} ({device.address})")

    try:
        async with BleakClient(device.address) as client:
            print(f"🔗 Connected to {device.name or 'Unnamed'}")
            print("🔍 Discovering services...")
            print("✅ Services discovered, subscribing to notifications...")
            
            try:
                await client.start_notify(UART_NOTIFY_UUID, handle_notify)
                print(f"📡 Subscribed to {UART_NOTIFY_UUID}")
            except Exception as e:
                print(f"❌ FAILED to subscribe to notification UUID: {e}. Check device pairing status.")
                return

            print(f"\n🎧 Listening for shift signals... (Mapped to '{SHIFT_KEYS[6].upper()}' and '{SHIFT_KEYS[7].upper()}')")
            print("Press Ctrl+C to stop.")
            
            while client.is_connected:
                await asyncio.sleep(0.1)

    except Exception as e:
        print(f"\n🛑 An error occurred: {e}")
    finally:
        print("\n🛑 Disconnected. Stopping listener.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Stopped by user.")
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
             print(f"\n🛑 Runtime Error: {e}")