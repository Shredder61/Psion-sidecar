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

Use the **English Speller Database (ESDB)** maintained by the en-wl project, release `rel-2026.02.25`, as the source for the first British-English game lexicon.

- ESDB explicitly supports British spelling code `B` (British `-ise`) and `Z` (British `-ize` / Oxford spelling).
- The upstream README gives the extraction form `./scowl word-list 60 B,Z 5` for a British list including both spelling families and variants.
- ESDB size 80 is described by its maintainer as including unusual but generally valid current words of the sort used in word games such as Scrabble. Size 85 includes valid words that may no longer be used in modern English, so do not include size 85.
- The project describes its combined work as available under an MIT-like licence, with third-party source notices in its `Copyright` file.
- Upstream release: https://github.com/en-wl/wordlist/releases/tag/rel-2026.02.25
- Upstream repository and extraction documentation: https://github.com/en-wl/wordlist

**Proposed game-list profile:** ESDB size 80; spellings `B,Z`; variant level 5; exclude abbreviations, proper names, Roman numerals, non-word entries, multi-word entries, and any entry that cannot be represented as a single A-Z tile word of 2–15 letters. Preserve both British `-ise` and `-ize` forms. Do not include American-only `A`, Canadian `C` or Australian `D` spellings. The precise extraction/filter command must be tested against the pinned release before the list is generated.

This is a **British-English Scrabble-style lexicon**, not an official Collins or WESPA tournament list. ESDB is primarily a spelling database; size 80 is a candidate vocabulary threshold, not proof that every resulting entry is accepted in CSW24. The generated word count, exclusions, source revision, command, checksum and all applicable notices must be recorded. Keep the generated list replaceable so another authorised British lexicon can be added later.

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

1. Confirm the intended English word authority and identify a redistributable word list.
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

The game must be described as using ENABLE2K unless a different authorised dictionary is explicitly selected. It must not be described as CSW24-compliant or tournament legal.
