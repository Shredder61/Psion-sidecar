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

The Sidecar dictionary interface is independent of the lexicon format. No commercial tournament list or third-party repository resource is bundled.

A word list must have documented redistribution terms before it is included in a public Sidecar release. The English lexicon must also be chosen deliberately: British English expectations and the intended Scrabble word authority need to be agreed before final game validation.

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


## Selected lexicon target: Collins Scrabble Words

The project target is **Collins Scrabble Words 2024 (CSW24)**, the seventh edition. It is the WESPA-endorsed lexicon effective for tournament and club play from 1 January 2025. The published list contains more than 280,000 permissible words and includes World English variants and inflected forms.

Official reference:
- Collins Official SCRABBLE Words, seventh edition, ISBN 978-0-00-866072-7.
- Collins product page: https://collins.co.uk/products/9780008660727
- Collins Zyzzyva terms: https://scrabble.collinsdictionary.com/tools/

### Licensing restriction

CSW24 is a proprietary HarperCollins word list. Collins' published Zyzzyva terms state that the word lists are copyright material and prohibit copying, editing, disseminating, reverse-engineering or using them beyond the permitted private, non-commercial use. The free Zyzzyva software being GPL does not make the embedded Collins word lists GPL or open data.

Consequently:
- CSW24 is the rules/validation target, not a word list we can bundle in the public Sidecar repository.
- Do not scrape, extract, convert, reconstruct or redistribute the list from Zyzzyva, the printed book or another application.
- A public Sidecar release needs explicit written permission/licensing from HarperCollins for the intended digital use and distribution, or a separately licensed lexicon with clearly disclosed differences.
- The current WordDictionary interface can load a word list supplied by a user who has the appropriate rights, but this does not itself grant permission to redistribute that list.
- Do not claim the game is CSW24-compliant until it is tested against an authorised CSW24 data source.
