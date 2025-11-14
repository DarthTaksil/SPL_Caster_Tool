import time
import os
from obswebsocket import obsws, requests

# === CONFIG ===
FILE_PATH = r"D:\SteamLibrary\steamapps\common\SlapshotRebound\Slapshot_Data\broadcastinfo.txt"
POLL_INTERVAL = 0.1  # seconds
INTERMISSION_DELAY = 3  # seconds

# OBS WebSocket settings
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = "your_password_here"

# === OBS CONNECTION ===
ws = None

def connect_obs():
    global ws
    try:
        ws = obsws(OBS_HOST, OBS_PORT, OBS_PASSWORD)
        ws.connect()
        print("Connected to OBS WebSocket.")
    except Exception as e:
        print(f"Failed to connect to OBS: {e}")

# === INPUT NORMALIZATION ===
def normalize(value):
    if not value:
        return ""
    v = value.strip().upper()
    # Replace Unicode dashes with ASCII dash
    v = v.replace("–", "-").replace("—", "-")
    return v

def is_dash(x):
    return normalize(x) == "-"

def is_faceoff(x):
    return normalize(x) == "FACEOFF"

def is_time_format(x):
    x = normalize(x)
    if ":" not in x:
        return False
    parts = x.split(":")
    return len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()

# === EVENTS ===
def on_period_start():
    print("[EVENT] PERIOD START DETECTED — switching to LIVE scene")
    if ws:
        try:
            ws.call(requests.SetCurrentProgramScene(sceneName="LIVE"))
        except Exception as e:
            print(f"OBS error: {e}")


def on_intermission_start():
    print("[EVENT] INTERMISSION START DETECTED — switching to INTERMISSION scene")
    if ws:
        try:
            ws.call(requests.SetCurrentProgramScene(sceneName="INTERMISSION"))
        except Exception as e:
            print(f"OBS error: {e}")

# === INTERNAL STATE TRACKING ===
prev_value = None

def read_value():
    try:
        if os.path.exists(FILE_PATH):
            with open(FILE_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        print(f"Error reading file: {e}")
    return None

# === MAIN LOOP ===
def watcher_loop():
    global prev_value
    print("Slapshot Period Watcher Running...")

    while True:
        current_raw = read_value()
        current = normalize(current_raw)
        prev_norm = normalize(prev_value) if prev_value else None

        # Debug output
        print(f"DEBUG: prev='{prev_norm}'  current='{current}' raw='{current_raw}'")

        if current is None:
            time.sleep(POLL_INTERVAL)
            continue

        # Detect period start: '-' → 'FACEOFF'
        if prev_norm == "-" and current == "FACEOFF":
            on_period_start()

        # Detect intermission: time → dash
        if is_time_format(prev_norm) and is_dash(current):
            print("Intermission detected... delaying transition...")
            time.sleep(INTERMISSION_DELAY)
            on_intermission_start()

        prev_value = current_raw
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    connect_obs()
    watcher_loop()
