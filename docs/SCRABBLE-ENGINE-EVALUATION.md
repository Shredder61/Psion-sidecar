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

The Sidecar dictionary interface is independent of the lexicon format. A word list must have documented redistribution terms before it is included in a public Sidecar release.

### Selected initial lexicon: ENABLE2K

The selected initial dictionary is **ENABLE2K** (Enhanced North American Benchmark LExicon, revised millennial edition).

- The original ENABLE2K documentation states that WORD.LST is in the public domain and may be used and distributed freely.
- The original documentation explicitly describes it as a gift to the Scrabble community and says game designers may incorporate it.
- The original revised edition reports 173,528 entries.
- It is an older, primarily North American alternative lexicon, not a current Collins/WESPA tournament list.
- The original documentation asks that the source and compilers be credited.
- Reference copy and README: https://github.com/BartMassey/wordlists (see README-enable2k.txt).
- Original documentation mirrored by Debian: https://sources.debian.org/src/scowl/6-2/r/enable/README

The repository may include the ENABLE2K data only with its provenance and public-domain notice preserved. Before bundling, verify the exact source file, compare its contents with the published ENABLE2K distribution, record a checksum and document the normalisation/filtering applied for the game.

**Dictionary identity:** label the game dictionary “ENABLE2K”, not “Collins”, “CSW”, “SOWPODS” or “tournament legal”. Do not claim CSW24 compatibility.

A later British-English option can be considered separately, but only after its word-list provenance and redistribution rights have been checked. Do not silently merge unrelated lists or describe a hybrid as ENABLE2K.

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
