# Pawn Wars

Welcome to OPEN DAY at the Department of Computer Science and Automation, IISc!
Pawn Wars is a reinforcement-learning-powered pawn-only chess variant with two playable versions:

- `3x3` board (root app)
- `4x4` board (`4by4/` app)

Each version includes:

- A training board UI (`/`) that can run AI-vs-AI games and visualize candidate moves and move history.
- A play mode (`/play`) where a human plays against the AI via drag-and-drop.
- A Q-table policy store (`q_table.json`) that is updated from game outcomes.

---

## 1. How the Game Works

### 1.1 Board Setup

- White pawns start on rank `1`.
- Black pawns start on the last rank:
  - `3x3`: rank `3`
  - `4x4`: rank `4`

### 1.2 Move Rules

For both variants:

- Forward move by 1 square if empty.
- Diagonal capture by 1 square.
- No en passant, no promotion, no other pieces.

### 1.3 Win Conditions

A game ends when:

- A white pawn reaches the top rank, or
- A black pawn reaches rank `1`, or
- The current player has no legal moves (that player loses).

---

## 2. Reinforcement Learning Logic

### 2.1 State Representation

State key format:

`<player>|<sorted_board_positions>`

Example shape:

`W|a1:W,b1:W,c1:W,a3:B,b3:B,c3:B`

### 2.2 Action Selection

- For each state, all legal actions are stored in the Q-table.
- New unseen actions start with value `20`.
- Action is sampled probabilistically with weights proportional to Q-values.

### 2.3 Learning Update

After game ends:

- For each recorded state-action:
  - `+1` if it belongs to winner
  - `-1` if it belongs to loser

The table is persisted to `q_table.json`.

---

## 3. Repository Structure

```text
simple-games-rl/
  app.py                    # 3x3 Flask app
  fast_train.py             # 3x3 offline trainer
  q_table.json              # 3x3 (or active cwd) Q-table
  templates/
    index.html              # 3x3 training UI
    play.html               # 3x3 human-vs-AI UI
  static/
    img/iisc-logo.png

  4by4/
    app.py                  # 4x4 Flask app
    fast_train.py           # 4x4 offline trainer
    q_table.json            # 4x4 Q-table (when run from 4by4 cwd)
    templates/
      index.html            # 4x4 training UI
      play.html             # 4x4 human-vs-AI UI
    static/
      img/iisc-logo.png
```

---

## 4. Prerequisites

- Python 3.10+ recommended
- pip

Install dependencies:

```bash
pip install flask tqdm
```

`tqdm` is only required by `4by4/fast_train.py`.

---

## 5. Run the Applications

### 5.1 Run 3x3 App

From repository root:

```bash
python app.py
```

Open:

- `http://127.0.0.1:5000/` (training UI)
- `http://127.0.0.1:5000/play` (play mode)

### 5.2 Run 4x4 App

Recommended: run from inside `4by4` so it uses `4by4/q_table.json`.

```bash
cd 4by4
python app.py
```

Open:

- `http://127.0.0.1:5001/` (training UI)
- `http://127.0.0.1:5001/play` (play mode)

Note: `Q_TABLE_FILE = "q_table.json"` is relative to current working directory.

---

## 6. API Endpoints

Both apps expose the same endpoint pattern.

### 6.1 `POST /start`

Start AI-vs-AI session and make the first White move.

Request JSON:

```json
{
  "gameID": "optional-existing-id"
}
```

Response includes:

- `gameID`
- `player` (`white` for first move)
- `from`, `to`
- `qvalues.actions`, `qvalues.values`
- optional `message`, `winner` on game over

### 6.2 `POST /continue`

Continue current AI-vs-AI game.

Request JSON:

```json
{
  "gameID": "required-id"
}
```

Response shape similar to `/start`.

### 6.3 `POST /play_drag/start`

Start human-vs-AI drag mode.

Request JSON:

```json
{
  "player_side": "W"
}
```

`player_side` can be `"W"` or `"B"`.

If user chooses Black, computer (White) may make the first move.

### 6.4 `POST /play_drag/move`

Submit human move.

Request JSON:

```json
{
  "gameID": "required-id",
  "from": "a1",
  "to": "a2"
}
```

Response includes updated board, status message, and optional `winner`.

### 6.5 UI Routes

- `GET /` -> `index.html` (training board + candidate move previews + history)
- `GET /play` -> `play.html` (drag-and-drop human-vs-AI)

---

## 7. Offline Training Scripts

### 7.1 3x3 Training

From repository root:

```bash
python fast_train.py
```

Defaults:

- `NUM_GAMES = 10000`
- Saves updated table to root `q_table.json`

### 7.2 4x4 Training

From `4by4` directory:

```bash
python fast_train.py
```

Defaults:

- `NUM_GAMES = 10000000` (very large)
- Uses progress bar via `tqdm`
- Saves to `4by4/q_table.json` if run from `4by4`

Tip: reduce `NUM_GAMES` before quick experiments.

---

## 8. UI Notes

Both 3x3 and 4x4 templates now include:

- Pawn Wars branding
- Vibrant animated gradient theme
- Candidate move mini-board previews with arrows
- White/Black move history panes in horizontal layout
- Responsive layout and drag-and-drop play screen

---

## 9. Recent Fixes

- Fixed 4x4 Black-side start bug where White's opening move could leave 5 White pawns.
  - Correct behavior now keeps White pawn count at 4 after initial computer move.

---

## 10. Troubleshooting

### 10.1 App starts but wrong Q-table is loaded

Cause:

- Running from an unexpected current working directory.

Fix:

- Run `python app.py` from the intended app directory:
  - root for 3x3
  - `4by4/` for 4x4

### 10.2 Port already in use

Default ports:

- 3x3: `5000`
- 4x4: `5001`

Stop the conflicting process or change port in `app.run(...)`.

### 10.3 UI does not reflect recent CSS/JS changes

- Hard refresh browser (`Ctrl+F5`).

---

## 11. Suggested Workflow

1. Train policy quickly with small `NUM_GAMES`.
2. Run app and inspect candidate move distributions.
3. Play against AI and observe move-history and Q-value behavior.
4. Increase training games and compare policy quality over time.

