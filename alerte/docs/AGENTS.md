# What the agents really do

## Three kinds of "who speaks"

| What | Who produces it | In which mode |
| --- | --- | --- |
| The events (the flood, the false alarm, the vendor's offer) and **HydroSense**'s outputs | **Scripted**: written in the scenario file. HydroSense is the fictional AI under test; it fails on cue and never calls a model. | always |
| What each institution (MET, DPC, OPS, ART, ANTIC) decides and says | **Rule engine**: fixed rules and sentence templates filled from the who-does-what table. No AI. | `offline` |
| | **AI model**: an open language model writes the decision and its own words, from the institution's role card, perspective, powers, inbox and the retrieved passages. | `llm` |
| Gap detection, citation checking, the readiness table | **Code**: deliberately not AI, so every finding can be audited and replayed. | both |

So yes: in `offline` mode the agents do not think. They look up their powers and fill a template, which is why the sentences look alike.
That mode exists for fast, reproducible tests and as a safety net. It is labelled everywhere ("rule engine, no AI"). **To see agents
reason, discuss and disagree, run the AI mode.**

## What the AI mode does

For every event, each recipient seat is a separate model call with its own prompt:

1. **Role card and perspective**: mission, what it fears, what it can and cannot do, its priorities and its voice (`data/scenarios/roles/*.yaml`).
2. **Its own powers and duties** from the who-does-what map, **its private inbox**, the event, and **passages retrieved from the library** that it may cite.
3. The model answers with a decision, a first-person **statement** to the others, what it knows and does not know, the options it
   weighed, its legal basis (quote copied from a passage) or "no legal basis found", and any requests to other institutions.
4. **Requests** go to the other institution's own model call, which accepts, refuses or says "not our role", citing its own powers.
5. **Discussion round**: each seat reads what the others decided (with whether their citations were verified) and agrees, objects (with a
   concrete reason) or asks for clarification. These appear on the board and as arrows in the arena.
6. A seat that finds no legal basis can **ask the Legal Adviser**, another model call that answers from the national texts and examples elsewhere.
7. Citations are **checked in code** against the library. An unverified quote is flagged and the seat is asked once to correct it.

Limits that keep it honest: at most `ALERTE_LLM_BUDGET` model calls per drill (default 150, decisions first, discussion with what is left);
when a call fails or the budget is gone, that decision falls back to the rule engine and is **labelled "AI failed: rules used"**, never passed off as AI.

## Checking it yourself

* **Decisions page > "How was this decided?"** shows, for an AI decision, the exact prompt and the model's raw answer from the logbook;
  for a rule-engine decision it says no AI was involved and shows the mandate line it used.
* Every decision and board message carries a tag: rule engine (no AI), AI model, AI failed: rules used, scripted, human.
* The end-of-drill summary and `python -m alerte run ... ` print who wrote the decisions and how many model calls and discussion messages there were.
* Two seats answering the same event in AI mode should differ in wording, priorities and objections. If they do not, the model is too small,
  or its prompt is ignored: look at the raw answers.

## Run a real model for free

The simulator speaks the OpenAI-compatible chat protocol, so it works with any server that does.

**Local, free: Ollama.** Install from ollama.com, then:
```bash
ollama pull qwen2.5:7b-instruct      # weaker computer: qwen2.5:3b-instruct
ollama serve                          # if it is not already running
```
In `.env` set `ALERTE_BRAIN=llm` (the other defaults already point to Ollama on `http://localhost:11434/v1`), then
`python -m alerte doctor --check-llm` and start the interface: the Live exercise page shows "AI model reachable" and defaults to it.

**Hosted, with a free tier.** Several providers offer an OpenAI-compatible endpoint with a free tier. Set in `.env`:
`ALERTE_LLM_BASE_URL` (their `/v1` address), `ALERTE_LLM_API_KEY` (your key, keep it private) and `ALERTE_LLM_MODEL` (a model name from their list).
Free tiers, rate limits and model names change often, so check the provider's current terms; I have not tested any hosted provider.
The drill content is fictional, but do not send real personal data.

**ITU sandbox.** Selected teams get cloud credits; point the same three variables at the sandbox model server.

## What I could and could not verify

* Verified here: the plumbing, with a mock server that answers differently per institution: prompts, labelling, discussion round, call budget,
  fallback, logbook, interface.
* **Not verified: the quality of a real model's reasoning.** My environment cannot reach any model host, so I have not run a real model.
  Expect to tune: small models may produce weak JSON or generic statements; a 7B model is the practical minimum, and on a CPU each call can take
  many seconds, so a full drill is slow (reduce `ALERTE_LLM_BUDGET`, use a smaller model, or run on a GPU or the sandbox).
