# Running ALERTE in the ITU AI for Good sandbox (or any GPU cloud)

ALERTE runs in three settings with the same code; only the `.env` changes.

| Setting | Brain | What you need |
| --- | --- | --- |
| Laptop, offline | `ALERTE_BRAIN=offline` | Python only |
| Laptop with a local model | `ALERTE_BRAIN=llm` + Ollama | 16 GB RAM for a 7B model |
| Sandbox / GPU cloud | `ALERTE_BRAIN=llm` + vLLM | One GPU (16 GB or more) |

## 1. Start a model server in the sandbox

Option A, vLLM (fastest on a GPU):

```bash
bash sandbox/serve_vllm.sh                      # serves Qwen/Qwen2.5-7B-Instruct on port 8000
```

Option B, Ollama (simplest):

```bash
curl -fsSL https://ollama.com/install.sh | sh   # on Ubuntu you may first need: sudo apt-get install -y zstd
ollama serve &
ollama pull qwen2.5:7b-instruct
ollama pull bge-m3                              # multilingual embeddings (French, English, Arabic)
```

## 2. Run ALERTE against it

```bash
pip install -r requirements.txt
export ALERTE_BRAIN=llm
export ALERTE_LLM_BASE_URL=http://localhost:8000/v1       # vLLM; for Ollama: http://localhost:11434/v1
export ALERTE_LLM_MODEL=Qwen/Qwen2.5-7B-Instruct          # for Ollama: qwen2.5:7b-instruct
python -m alerte doctor --check-llm
python -m alerte ingest --embed ollama                      # optional: meaning-based search
python -m alerte eval --brain llm --repeats 3               # targets T1, T2, T3, T5, T6
python -m alerte ui --headless --port 8501                  # web interface
```

If the model server fails or answers badly, ALERTE falls back to its offline rules for that step and records
the failure in the logbook, so a drill always finishes.

## 3. Fine-tune with the sandbox credits

```bash
python -m alerte export-sft --out sandbox/alerte_sft.jsonl --runs runs/demo-cm01 runs/demo-ae01
pip install "transformers>=4.44" "peft>=0.11" "accelerate>=0.33" datasets bitsandbytes
python sandbox/finetune_lora.py --data sandbox/alerte_sft.jsonl --model Qwen/Qwen2.5-7B-Instruct --4bit
LORA=sandbox/alerte-lora bash sandbox/serve_vllm.sh
export ALERTE_LLM_MODEL=alerte                               # the LoRA name served by vLLM
python -m alerte eval --brain llm --repeats 3                # compare with the base model
```

The dataset teaches the model the habits judged by the hackathon: cite exact passages, answer
"no legal basis found" rather than invent a law, and stay in role.

## 4. Contribute the knowledge base to the AI for Good Lab

```bash
pip install -r requirements-full.txt
python -m alerte export-chroma --collection alerte_kb --embed ollama --embed-model nomic-embed-text
```

This writes a ChromaDB collection in the format of the ITU reference code
(`simulation/server/knowledge/kb.py`), next to its own `kb_main` collection.

## Notebook

`alerte_sandbox.ipynb` does all of the above in Jupyter or Google Colab (free GPU).
