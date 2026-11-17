# Sidecar Scrabble — development plan

## Objective

Add a self-hosted English-language Scrabble game as an independent Sidecar module. The same Python implementation must run on Raspberry Pi OS and Android/Termux, with the Psion Series 7 as a primary browser client.

The existing crossword downloader and catalogue must remain unchanged while Scrabble is developed.

## Hosting and interface decisions

- Reuse the existing Sidecar HTTP server and its standard-library-only deployment model initially.
- Implement the game as an isolated package under `scrabble/`; do not add game rules to `sidecar_web.py`.
- Use server-rendered, conservative HTML and small amounts of vanilla JavaScript/CSS. Avoid Flask, PyTorch, Pygame, Node build steps and other runtime dependencies.
- Keep game state and saved games on the host. The browser is a client, not the authority for scoring or legality.
- Keep routes, templates, static assets and storage separate from crossword/catalogue routes.
- Make the game usable on a modern browser and degrade gracefully on older EPOC browsers.

## Game rules and scope

### First playable release

- Standard 15 × 15 English Scrabble board and premium squares.
- Standard English tile distribution (100 tiles) and letter values.
- Seven-tile racks and blank tiles.
- First move covers the centre; subsequent moves connect to existing tiles.
- Validate main and cross-words against the generated British ESDB size-70 lexicon (both British -ise and -ize forms; clearly identified as a non-tournament alternative, not CSW24).
- Correct letter/word multipliers, bingo bonus, tile replenishment and end-game scoring.
- Human versus computer, with a legal move generator.
- Pass, exchange, new game, save and resume.
- A "show best move" action that suggests without committing the computer's turn.

### Later releases

- Adjustable AI strategy/strength, challenge rules, turn history and multiple local players.
- Optional LAN multiplayer.
- Additional dictionary choices only where licensing permits.

## Engine evaluation

Do not commit to an external engine before a reproducible comparison on the Pi. Evaluate:

1. A compact DAWG approach (including the Skrafl implementation as a technical reference).
2. A GADDAG approach (including astralcai/scrabbler as a technical reference).
3. Correctness against hand-built positions and a trusted reference implementation.

Measure dictionary build/load time, resident memory, rack move-generation time, full-board move-generation time, blank handling and legal-move completeness. Repeat on the HiBy/Termux after the Pi baseline.

External repositories are research references, not automatically dependencies. Review each source licence and all dictionary/vocabulary terms before copying or bundling code or word lists. British ESDB is the selected initial lexicon source: start at size 70 with B and Z spellings, preserve all applicable upstream notices, pin the source release, record the extraction recipe and checksums, and identify it accurately. Do not bundle a commercial tournament lexicon.

## Architecture boundaries

- `rules.py`: tile distribution, premiums, scoring and turn validation.
- `board.py`: immutable/serialisable board representation and placements.
- `dictionary.py`: dictionary interface; implementation selected after benchmarking.
- `moves.py`: legal move generation and validation.
- `game.py`: bag, racks, players, turns, scoring and end-game.
- `ai.py`: move selection; initially score-based, later strategic.
- `storage.py`: versioned JSON save/load.
- `web.py`: HTTP route adapter called by Sidecar, not a second server.
- `templates/` and `static/`: accessible, low-bandwidth interface.

Game rules must be testable without starting the web server. The server must never trust a score or move legality supplied by the browser.

## Interface priorities

Target the Series 7 640 × 480 display first:

- Board remains legible and fits the viewport without horizontal scrolling where possible.
- Large, high-contrast tile letters and clear premium-square distinctions.
- Select a rack tile, then select a board square; do not require drag-and-drop.
- Provide explicit orientation, submit, undo, exchange and pass controls.
- Keep score, current player, rack and bag count visible.
- Offer a text/list alternative for move suggestions and status.
- No reliance on modern CSS layout features or JavaScript frameworks.

## Deployment

The game must use the same source on Raspberry Pi and Termux. Platform-specific service/startup configuration remains separate. Scrabble data must live in a dedicated writable data directory; source files and dictionaries remain read-only at runtime.

## Initial acceptance criteria

- Existing Sidecar homepage, catalogue and crossword tests continue to pass.
- A fresh game has the correct 100-tile English distribution.
- Board premium squares and scoring match published standard rules.
- Invalid, disconnected, out-of-bounds and malformed moves are rejected server-side.
- Cross-words are checked, blanks score zero, and premium squares are used only on newly placed tiles.
- Save/load round-trips a game without changing board, bag, racks, scores or turn.
- The same engine tests pass on Raspberry Pi OS and Termux.
- No third-party Python package is required for the first release.

## Immediate next work

1. Add the isolated package and a test harness.
2. Implement and test the tile set, board geometry and scoring independently of AI.
3. Benchmark DAWG and GADDAG candidates on the Pi before selecting the production move generator.
4. Add the Series 7-oriented interface after the rules engine is stable.
