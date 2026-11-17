# Scrabble move-engine evaluation

## Decision status

No third-party move engine has been selected or incorporated. The production engine must run on Raspberry Pi OS and Android/Termux using a small Python footprint.

## Candidate review

### GADDAG: astralcai/scrabbler

Repository: https://github.com/astralcai/scrabbler

- The repository includes an MIT licence for its software.
- It implements Gordon's GADDAG move-generation approach in Python.
- Its README describes standard Scrabble and Words With Friends board support.
- It constructs a GADDAG from a plain-text list and can persist the structure using gzip and Python pickle.
- The code and licence may be evaluated as a candidate implementation.
- The licence for any bundled or separately sourced word list must be established independently.
- Pickle files must be treated as trusted local data only; never load user-supplied or downloaded pickle files.

### DAWG: vthorsteinsson/Skrafl

Repository: https://github.com/vthorsteinsson/Skrafl

- The README describes a compact DAWG with wildcard lookup and rack permutation.
- The README reports 178,691 TWL06 words represented by a 772 KB graph and 30–70 ms rack permutation timings on the author's desktop using CPython.
- These are upstream-reported figures, not Sidecar or Raspberry Pi benchmarks.
- The inspected repository files carry Miðeind ehf. copyright notices. No clear repository-wide licence granting redistribution or modification rights was identified in this review.
- Treat this implementation as a technical reference only. Do not copy or bundle its code unless its licence is clarified by the rights holder.

## Dictionary policy

The Sidecar dictionary must be British English, independently replaceable, and redistributable with the public project. It must not be described as Collins/CSW24 or as an official tournament lexicon.

### Selected candidate: British ESDB (formerly SCOWL)

Use the **English Speller Database (ESDB)** maintained by the en-wl project, pinned to release `rel-2026.02.25`, as the source for the first British-English game lexicon.

- ESDB supports British spelling code `B` (British `-ise`) and `Z` (British `-ize` / Oxford spelling).
- Upstream documents `./scowl word-list 60 B,Z 5` as the way to extract a British list including both spelling families and variants.
- Upstream says size 60 is its vetted default and size 70 should also be usable; larger lists are less carefully checked and may contain misspelled or invalid words. Therefore start at size 70, not 80.
- The upstream `Copyright` file grants permission to use, copy, modify, distribute and sell SCOWLv2 or word lists created from it, provided its copyright and permission notice are reproduced in copies and supporting documentation. It also describes additional notices that apply to certain data combinations. Our extraction uses only British `B,Z`, not Australian `D`, and must remain no larger than size 80 to avoid the stated UKACD notice for lists larger than 80.
- Release: https://github.com/en-wl/wordlist/releases/tag/rel-2026.02.25
- Source and extraction documentation: https://github.com/en-wl/wordlist
- Exact release copyright notice: https://github.com/en-wl/wordlist/blob/rel-2026.02.25/Copyright

**Initial extraction profile:** size 70; spellings `B,Z`; variant level 5; exclude special categories, abbreviations, and diacritical marks; then retain only single-token A-Z entries of 2–15 letters. The upstream command to test from the root of the pinned checkout is:

```sh
./scowl word-list 70 B,Z 5 --categories= --wo-poses=abbr --deaccent > british_esdb_raw.txt
```

The final filtering step must be a small reproducible script, not an undocumented manual edit. It should uppercase entries, keep only ASCII A-Z words of 2–15 letters, remove duplicates, sort deterministically, and write `british_esdb.txt`. Preserve `british_esdb_raw.txt` only as a build artifact if needed; do not commit it unless its provenance and notices are included. Record the exact raw and final word counts, SHA-256 checksums, source tag, command, filter-script version and all required notices.

This is a **British-English Scrabble-style lexicon**, not an official Collins or WESPA tournament list. ESDB is a spelling database, not a Scrabble rules authority. Size 70 is a conservative starting vocabulary level, not proof that every entry is valid under CSW24. We must audit sample words and known exclusions, and must not claim CSW24 compatibility.

Do not use ENABLE2K as the default game list: it is predominantly North American. Do not silently mix it into the British ESDB output.

## Benchmark protocol

Run candidates on the same hardware and the same legally usable test lexicon. Record:

1. Device model, OS, Python version and available memory.
2. Lexicon word count and source/licence.
3. Build time from plain text.
4. Persisted graph size on disk.
5. Load time from persisted data.
6. Peak resident memory if a reliable measurement is available.
7. Exact lookup throughput.
8. Rack move-generation time for representative 7-tile racks.
9. Rack move-generation time with one and two blanks.
10. Full-board move-generation time on fixed mid-game positions.
11. Number of moves returned and best move score.
12. Correctness against hand-checked positions, including cross-checks and existing board letters.

Use repeated runs and report median timings. Keep build time separate from normal game-start load time. Do not compare engines using different lexicons or different board positions.

## Next engineering steps

1. Generate and audit the pinned British ESDB-derived word list.
2. Create a reproducible benchmark fixture with fixed racks and board positions.
3. Evaluate the MIT GADDAG candidate in an isolated test checkout, without copying it into Sidecar yet.
4. Establish DAWG implementation licensing or select a separately licensed DAWG implementation.
5. Run the same benchmark on the Raspberry Pi, then repeat on the HiBy R5/Termux.
6. Select an engine only after correctness, memory and latency are compared.

## Safety and portability

- Keep all engine evaluation code isolated from the live Sidecar server.
- Do not introduce Flask, Pygame, PyTorch or a native build dependency.
- Do not load untrusted pickle data.
- Preserve the standard-library-only core and the existing crossword/catalogue routes.


## Collins Scrabble Words reference and restriction

CSW24 remains a useful comparison point for the intended international/UK Scrabble experience, but it is **not** the bundled dictionary and we will not seek a licence.

Official reference:
- Collins Official SCRABBLE Words, seventh edition, ISBN 978-0-00-866072-7.
- Collins product page: https://collins.co.uk/products/9780008660727
- Collins Zyzzyva terms: https://scrabble.collinsdictionary.com/tools/

CSW24 is proprietary HarperCollins material. The published Zyzzyva terms restrict use of the word lists. Do not scrape, extract, convert, reconstruct or redistribute the list from Zyzzyva, the printed book or another application.

The game must be described as using the British ESDB-derived lexicon unless a different authorised dictionary is explicitly selected. It must not be described as CSW24-compliant or tournament legal.
