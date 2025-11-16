import os
import time
import json
import threading
from obswebsocket import obsws, requests

# === CONFIG ===
# Broadcast info file
BROADCAST_FILE_PATH = r"D:\\SteamLibrary\\steamapps\\common\\SlapshotRebound\\Slapshot_Data\\broadcastinfo.txt"
POLL_INTERVAL_BROADCAST = 0.1  # seconds
INTERMISSION_DELAY = 3  # seconds

# Stats JSON files
SLAPSHOT_LOGS_PATH = r"D:\\SteamLibrary\\steamapps\\common\\SlapshotRebound\\Slapshot_Data\\Matches"
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(BASE_PATH, "stats")
SLEEP_INTERVAL_STATS = 2

# OBS WebSocket settings
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = "your_password_here"

# === REPLAY CONFIG ===
# REPLAY settings
REPEAT_THRESHOLD = 13  # number of consecutive same time reads to trigger replay
REPLAY_COOLDOWN_SECONDS = 6

# FACEOFF settings
FACEOFF_COOLDOWN_SECONDS = 4

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

# === NORMALIZATION FUNCTIONS ===
def normalize(value):
    if not value:
        return ""
    v = value.strip().upper()
    v = v.replace("–", "-").replace("—", "-")
    return v

def is_dash(x):
    return normalize(x) == "-"

def is_faceoff(x):
    return normalize(x) == "FACEOFF"

def is_time_format(x):
    x = normalize(x)
    if x.startswith("+"):
        x = x[1:]  # Remove leading '+' when the match is in overtime.
    if ":" not in x:
        return False
    parts = x.split(":")
    return len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()

def convert_to_seconds(t):
    """Convert 4:51 into total seconds (291). Handles + prefixes."""
    if not t or ":" not in t:
        return None
    t = t.lstrip("+")
    parts = t.split(":")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return None
    return int(parts[0]) * 60 + int(parts[1])

# === PERIOD WATCHER EVENTS ===
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

# === EVENTS ===
def switch_scene(scene_name):
    if ws:
        try:
            ws.call(requests.SetCurrentProgramScene(sceneName=scene_name))
            print(f"[OBS] Switched to scene: {scene_name}")
        except Exception as e:
            print(f"OBS error: {e}")

def on_replay_trigger():
    print("[EVENT] REPLAY TRIGGERED")
    switch_scene("REPLAY")

def on_live_trigger():
    print("[EVENT] LIVE TRIGGERED")
    switch_scene("LIVE")

# === PERIOD WATCHER LOOP ===
prev_value = None
repeat_count = 0
last_replay_time = 0
last_faceoff_time = 0

def read_broadcast_value():
    try:
        if os.path.exists(BROADCAST_FILE_PATH):
            with open(BROADCAST_FILE_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        print(f"Error reading broadcast file: {e}")
    return None

def watcher_loop():
    global prev_value, repeat_count, last_replay_time, last_faceoff_time
    print("Slapshot Period Watcher Running...")

    while True:
        current_raw = read_broadcast_value()
        current = normalize(current_raw)
        prev_norm = normalize(prev_value) if prev_value else None

        if current is None:
            time.sleep(POLL_INTERVAL_BROADCAST)
            continue

        # === REPEAT TIME DETECTION ===
        if is_time_format(current):
            if current == prev_norm:
                repeat_count += 1
            else:
                repeat_count = 1  # reset
        else:
            repeat_count = 0

        now = time.time()

        # Trigger REPLAY if threshold met and cooldown passed
        if repeat_count == REPEAT_THRESHOLD and (now - last_replay_time) >= REPLAY_COOLDOWN_SECONDS:
            on_replay_trigger()
            last_replay_time = now

        # === FACEOFF DETECTION ===
        if is_faceoff(current) and (now - last_faceoff_time) >= FACEOFF_COOLDOWN_SECONDS:
            on_live_trigger()
            last_faceoff_time = now

        # === INTERMISSION DETECTION ===
        if is_time_format(prev_norm) and is_dash(current):
            print("Intermission detected... delaying transition...")
            time.sleep(INTERMISSION_DELAY)
            on_intermission_start()

        prev_value = current_raw
        time.sleep(POLL_INTERVAL_BROADCAST)

# === STATS GENERATOR FUNCTIONS ===
DEFAULT_STATS = [
    "score","goals","assists","shots","passes","turnovers","post_hits",
    "blocks","saves","faceoffs_won","faceoffs_lost","takeaways",
    "possession_time_sec","games_played","conceded_goals","contributed_goals",
    "primary_assists","secondary_assists","wins","losses","game_winning_goals","post_hits"
]

CALCULATED_STATS = {
    "faceoffs_total": lambda s: s.faceoffs_won + s.faceoffs_lost,
    "faceoff_win_percent": lambda s: str(round(100 * s.faceoffs_won / s.faceoffs_total)) + "%" if s.faceoffs_total > 0 else "-",
    "posession_time_friendly": lambda s: time.strftime("%M:%S", time.gmtime(s.possession_time_sec)),
    "points": lambda s: s.goals + s.assists,
    "impact_rating": lambda s: round((s.goals)+(s.primary_assists*0.75)+(s.shots*0.1)+(s.saves*0.25)+(s.secondary_assists*0.25)+(s.faceoffs_won*0.05)-(s.faceoffs_lost*0.05)-(s.turnovers*0.1)+(s.takeaways*0.1)+(s.possession_time_sec*0.005)+(s.game_winning_goals+0.25),2)
}

ALL_STATS = DEFAULT_STATS + list(CALCULATED_STATS.keys())

class Stats(object):
    def __init__(self):
        for stat in ALL_STATS:
            setattr(self, stat, "-")

class Player(object):
    def __init__(self, game_user_id, username, team, stats=Stats()):
        self.game_user_id = game_user_id
        self.username = username
        self.team = team
        self.stats = stats

def write_output_file(filename, value):
    outF = open(os.path.join(OUTPUT_PATH, filename), "w+", encoding="UTF-8")
    outF.write(str(value))
    outF.close()

def write_stats(home_stats, away_stats, players, generic_info):
    if not os.path.exists(OUTPUT_PATH):
        os.mkdir(OUTPUT_PATH)

    for stat in ALL_STATS:
        write_output_file(f"home_{stat}.txt", getattr(home_stats, stat))
        write_output_file(f"away_{stat}.txt", getattr(away_stats, stat))

    sorted_players = sorted(players, key=lambda p: p.game_user_id)
    home_players = [p for p in sorted_players if p.team == "home"]
    away_players = [p for p in sorted_players if p.team == "away"]

    for idx, player in enumerate(home_players):
        write_output_file(f"home_player_{idx}_username.txt", player.username)
        for stat in ALL_STATS:
            write_output_file(f"home_player_{idx}_{stat}.txt", getattr(player.stats, stat))

    for idx, player in enumerate(away_players):
        write_output_file(f"away_player_{idx}_username.txt", player.username)
        for stat in ALL_STATS:
            write_output_file(f"away_player_{idx}_{stat}.txt", getattr(player.stats, stat))

    for data in generic_info.keys():
        write_output_file(f"{data}.txt", generic_info[data])

    print(f"Wrote new stats files to: {OUTPUT_PATH}")

# === STATS GENERATOR LOOP ===
def stats_loop():
    _latest_log_file = None
    try:
        while True:
            files = sorted(os.listdir(SLAPSHOT_LOGS_PATH), reverse=True)
            match = {}
            newest_file = None
            for file in files:
                with open(os.path.join(SLAPSHOT_LOGS_PATH, file), "r", encoding="UTF-8") as f:
                    match = json.load(f)
                if match.get("periods_enabled") == "True":
                    newest_file = file
                    break

            if not newest_file:
                print(f"No period-based stat files detected, sleeping for {SLEEP_INTERVAL_STATS} seconds")
                time.sleep(SLEEP_INTERVAL_STATS)
                continue

            if _latest_log_file is None or _latest_log_file != newest_file:
                print("New stat file detected:", newest_file)
                _latest_log_file = newest_file

                raw_players = match.get("players", [])
                home_stats = Stats()
                away_stats = Stats()
                players = []

                for p in raw_players:
                    stats = Stats()
                    for stat in DEFAULT_STATS:
                        setattr(stats, stat, round(p["stats"].get(stat, 0)))
                    players.append(Player(p["game_user_id"], p["username"], p["team"], stats))

                for stat in DEFAULT_STATS:
                    setattr(home_stats, stat, sum(getattr(p.stats, stat, 0) for p in players if p.team=="home"))
                    setattr(away_stats, stat, sum(getattr(p.stats, stat, 0) for p in players if p.team=="away"))

                for stat, calculator in CALCULATED_STATS.items():
                    for player in players:
                        setattr(player.stats, stat, calculator(player.stats))
                    setattr(home_stats, stat, calculator(home_stats))
                    setattr(away_stats, stat, calculator(away_stats))

                generic_info = {}
                current_period = match.get("current_period")
                if current_period == "2":
                    game_state = "Second Intermission"
                elif current_period == "1":
                    game_state = "First Intermission"
                else:
                    game_state = "Final"
                generic_info["game_state"] = game_state

                write_stats(home_stats, away_stats, players, generic_info)
            else:
                print(f"No new stat file detected, sleeping for {SLEEP_INTERVAL_STATS} seconds")

            time.sleep(SLEEP_INTERVAL_STATS)
    except KeyboardInterrupt:
        pass

# === MAIN ===
if __name__ == "__main__":
    connect_obs()
    threading.Thread(target=watcher_loop, daemon=True).start()
    threading.Thread(target=stats_loop, daemon=True).start()

    print("Slapshot watcher + stats generator running...")
    while True:
        time.sleep(1)
