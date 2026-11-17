# Sidecar Scrabble

This directory is reserved for the independent Scrabble module. It is intentionally separate from the existing crossword and software-catalogue code.

The first implementation will be pure Python and use the Python standard library only. The game will be hosted by the existing Sidecar HTTP server; it will not start a second server or introduce Flask/Pygame dependencies.

See [the development plan](../docs/SCRABBLE-PLAN.md) for scope, architecture, engine evaluation and acceptance criteria.

## Planned modules

- `rules.py` — English tile set, board premiums and scoring.
- `board.py` — board state and tile placement.
- `dictionary.py` — replaceable, file-loaded word-list interface (no lexicon bundled).
- `moves.py` — move validation and scoring; move generation will be added separately.
- `game.py` — bag, racks, turns and game state.
- `ai.py` — computer move selection.
- `storage.py` — JSON save/resume.
- `web.py` — route adapter for Sidecar.

No dictionary is bundled yet. Dictionary licensing and the choice between DAWG and GADDAG are part of the initial evaluation.
