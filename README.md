# redline

A writing checker for the mistakes I actually make. It runs entirely on my machine and works in any Windows app: select text, press `Ctrl+Alt+R`, and a popup lists what to fix.

It is not a Grammarly replacement. Below is how it compares with LanguageTool and Harper, including where it loses.

## What it checks

| Check | How | Why |
|---|---|---|
| **Style** | Rules: em-dashes, my filler words ("things", "basically"...), AI-sounding phrases | These are my own rules. No general tool knows them. Edit `src/redline/rules.toml`. |
| **Grammar** | A small local correction model ([Unbabel/gec-t5_small](https://hf.co/Unbabel/gec-t5_small)) rewrites each sentence; the differences become flags | General grammar and spelling |
| **Meaning flip** | `redline compare original.txt rewrite.txt`: pairs each rewritten sentence with the one it came from, then asks an NLI model whether they contradict | When I reword a draft, negations and directions flip without me noticing. A case study I submitted said a brand "has a defined positioning" where the draft said "no clear positioning". It read fine, so I missed it. |

## Results

### Grammar: compared with LanguageTool and Harper

Detection F0.5 (precision weighted), with 95% bootstrap intervals. All three run locally on the same detokenised sentences.

| Test set | Sentences | redline | Harper | LanguageTool |
|---|---|---|---|---|
| **Native-speaker essays** (LOCNESS, BEA-2019 dev) | 988 | 0.52 [0.48, 0.55] | **0.52** [0.48, 0.57] | 0.45 [0.40, 0.48] |
| Learner essays, all levels (BEA-2019 dev) | 4,384 | **0.68** [0.67, 0.69] | 0.41 [0.38, 0.43] | 0.39 [0.37, 0.41] |
| Learner essays (CoNLL-2014 test) | 1,312 | **0.74** [0.72, 0.75] | 0.53 [0.49, 0.57] | 0.44 [0.41, 0.46] |

**Read the first row first.** The other two are learner essays, which is what the grammar model was trained on, and LanguageTool and Harper are tuned for native writers who make fewer, different mistakes. On native writing, which is what I write, redline is level with Harper, not ahead. A clear lead on learner text plus a tie on native text says more about where each tool was built for than about which is "better".

Where redline falls short, on the native set:

- **Precision is 0.52.** About half its flags are not errors the annotators marked. Harper is at 0.59.
- **Spelling recall is 0.65**, against 0.97 for LanguageTool and 1.00 for Harper. A rewrite model sometimes leaves a misspelling alone; a dictionary never does. Adding a dictionary pass is the obvious next step.
- **It does better on punctuation and prepositions** (punctuation recall 0.44 vs 0.24 Harper, 0.12 LanguageTool), the errors the rule-based tools mostly leave alone.

A second, larger model (vennify/t5-base) scored lower than gec-t5_small on CoNLL-2014 (F0.5 0.69 vs 0.74, measured before the long-sentence fix) and was dropped from the full comparison to save memory.

### Meaning flip

| Set | Result |
|---|---|
| **Real rewrites** (my submitted case study) | Caught **2 of 2** flips; did not flag the third rewrite, which was garbled but kept its meaning. n = 3, so this is a sanity check, not a rate. |
| Synthetic pairs from BEA-2019 sentences (one cue flipped vs a meaning-preserving edit, balanced) | F0.5 0.99 [0.99, 1.00], n = 910 held out. Threshold picked on a separate dev half. |

The synthetic number is near perfect because the task is easy: one negation or direction word changed, against simple synonym swaps. It shows the pipeline works, not that it catches every real flip. Real reworded pairs are rare because drafts usually get overwritten; collecting more is the work that would make this number mean something.

### Style rules

Pending: scored against my own labels of my own sentences (`redline label`), which I haven't finished. The tools don't check for these rules at all, so the useful number here is whether the rules flag what I actually want flagged.

## How it works

```
check     style rules (instant) + grammar model per sentence -> flags with character spans
compare   split both texts -> pair sentences by embedding similarity (all-MiniLM-L6-v2)
          -> NLI contradiction score (nli-deberta-v3-small, both directions) -> flag above threshold
app       global hotkey -> copy selection (clipboard restored) -> popup; style first, grammar after
eval      the same functions as the app, scored against gold spans
```

Design choices worth knowing:

- **Detection, not correction, is scored.** A flag counts if it overlaps a gold error span; a missing-word error counts if the flag touches the gap. This compares tools that only flag (Harper, LanguageTool) with one that rewrites (redline) on equal terms.
- **Tools see normal text.** The test sets are tokenised ("do n't", "word ."). They are detokenised before checking, with gold spans mapped to characters, so LanguageTool isn't penalised for flagging spaces that real text wouldn't have.
- **F0.5, not F1.** Precision counts double: a checker that cries wolf gets switched off.
- **Every number has n and a 95% bootstrap interval.** Resampled by sentence, 1,000 times.
- **Run-on sentences are chunked** at clause boundaries before the model sees them, so its fixed output length can't truncate a sentence into fake errors.
- **Private by design.** Nothing leaves the machine. My own writing used for the personal evals stays in `data/personal/`, outside git; only aggregate numbers are published.

## Run it

```bash
uv sync --extra dev
uv run redline check notes.txt              # style + grammar
uv run redline check - --no-grammar         # style only, from stdin, instant
uv run redline compare draft.txt final.txt  # meaning flips
uv run redline app                          # hotkey app (Ctrl+Alt+R)
```

Models (about 500 MB in total) download on first use.

Reproduce the eval:

```bash
uv run redline data                          # CoNLL-2014 test, BEA-2019 dev (check their terms)
npm install                                  # Harper baseline (harper.js 3.0.0)
uv run redline eval grammar --dataset conll14
uv run redline eval grammar --dataset bea19dev
uv run redline eval grammar --dataset bea19native
uv run redline build-sets --public-flips && uv run redline eval flip
uv run redline label                         # label your own sentences, then:
uv run redline eval style
uv run pytest                                # 65 tests; add -m model for the ones that load models
```

LanguageTool runs locally through `language_tool_python`; if Java is missing, a JRE is downloaded once into `~/.cache/redline/jdk`.

## Licences

Code: MIT. Models keep their own licences: gec-t5_small and nli-deberta-v3-small are Apache 2.0; the second grammar model tried in the eval, vennify/t5-base-grammar-correction, is CC BY-NC-SA 4.0. The test sets are not redistributed here: CoNLL-2014 (NUS) and W&I+LOCNESS (BEA-2019) each have their own research terms.
