# term-slots

## Controls

Keybinds are contextual depending on the current game state. Cheatsheet below.

Slot view:
- `[Tab]` Switch to hand view
- `[Enter]` Spin slots
- `[Left/Right]` Column navigation

Hand view:
- `[Tab]` Switch to slot view
- `[Enter]` Spin slots / Accept selected card / Confirm card burning
- `[Left/Right]` Card in hand navigation
- `[Up/Down]` Select/Deselect card
- `[x]` Sort hand cards by rank
- `[c]` Sort hand cards by suit
- `[b]` Toggle card burning mode (On/Off)


## How to run (for the time being)

1. Clone the repo
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

**:ON WINDOWS:**

3. Open **Windows Terminal** (or any modern GPU accelerated terminal, powershell and cmd won't work well)
4. cd into the repo dir
5. Sync uv using `uv sync`
6. Run the program with `.\run_ext.ps1`
