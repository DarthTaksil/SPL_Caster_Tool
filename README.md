# SPL_Caster_Tool
A tool for the Broadcasters of the Slapshot Premier League

## Downloading / Installing
Click the Green `Code` dropdown and then `Download ZIP`.

After you get the files. Move `main.py` into it's own folder.  Double-click to run it. If you dont have Python installed, you can do so [here](https://www.python.org/downloads/release/python-31210/).

## SET UP / CONFIG

### OBS SCENES
This will switch between three scenes. And they must be named accordingly: (yes they are case sensitive)
- `LIVE` - Scene for the live gameplay.
- `INTERMISSION` - Scene for intermission Stats.
- `REPLAY` - Scene for Goal Replays.

#### Scene Cont.
- `LIVE` should display the whole game capture with a scorebug.
- `INTERMISSION` should display the current score ( `away_goals.txt` and `home_goals.txt` ), the `game-state.txt`, and Team Names associated with the graphic. What metrics you choose to display is up to your descretion. Every metric is made available in the `stats` folder.
- `REPLAY` should only display the game capture (with the exception of a few watermarks in the upper right and upper left of the screen.)

Transition Overrides are expected to be used. (I use `Time` as my `Transition Point Type`.)
- `TRANSITION TO LIVE` should have a transitional point of 0ms
- `TRANSITION TO REPLAY` should have a transitional point of 2800ms

#### Making Transitions
If your making a transition in Adobe Premiere Pro, when you export your video make sure there is Alpha compatibility. My personal export preference is:
- Export Settings
- - Format: `Quicktime`
- Basic Video Settings
- - Video Codec: `Animation`
- - Depth: `8-bpc + alpha`
This should export a `.mov` file.

### PYTHON DOWNLOAD
You WILL need Python to run this.
Download it [here](https://www.python.org/downloads/release/python-31210/).  I use 3.12.10 but you may find success with other versions.

### CONFIG
Then Open main.py with Notepad and set your directories to the `broadcastinfo.txt` and `Matches` folder.

To get to these files:
- Open Steam
- Right Click `Slapshot: Rebound`
- Click `Properties` (bottom option in dropdown)
- Click  `Installed Files` (3rd option from the top in the left nav-bar)
- On the top right click `Browse...`
- Open `Slapshot_Data`
- You will see `broadcastinfo.txt` under `boot.config`
- - If you don't see this file, open the game, press tilde, and use the command `broadcasterinfo on`. You may need to play a bot match via Practice for the file to generate.
- Towards the top you will also see your `Matches` folder.
Make sure you have // in the URL. Don't ask me why it needs to be `//` instead of just `/`. We don't ask questions, we're just going with the flow here.

And set your OBS_PASSWORD.
To get your OBS_PASSWORD:
- Open OBS
- Click `Tools`
- Click `obs-websocket settings`
- - Click the box next to `Enable WebSocket server`
- - make sure the Server Port is `4455`.  If it's different make sure the main.py reflects that change.
- - Under the Server Password, click `Show Connect Info`
- - Copy `Server Password` and paste it in `main.py` inside the quotations for `OBS_PASSWORD`

Alternatively, you can choose to uncheck the `Enable Authentication`. If you do this, you dont have to worry about setting the password in `main.py`