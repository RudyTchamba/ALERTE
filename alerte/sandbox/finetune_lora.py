"""Fine-tune a small open model with LoRA on the ALERTE dataset (run on a GPU: ITU sandbox, Colab, Kaggle).

1. Build the dataset (any computer):
     python -m alerte export-sft --out sandbox/alerte_sft.jsonl --runs runs/demo-cm01 runs/demo-ae01
2. On a GPU machine:
     pip install "transformers>=4.44" "peft>=0.11" "accelerate>=0.33" datasets bitsandbytes
     python sandbox/finetune_lora.py --data sandbox/alerte_sft.jsonl --model Qwen/Qwen2.5-7B-Instruct --4bit
3. Serve the result with vLLM (see serve_vllm.sh) and point ALERTE to it (ALERTE_BRAIN=llm).

Check the dataset without a GPU:   python sandbox/finetune_lora.py --data sandbox/alerte_sft.jsonl --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_rows(path: Path) -> list[dict]:
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        r = json.loads(line)
        msgs = r.get("messages")
        if not msgs or msgs[-1]["role"] != "assistant" or any(m["role"] not in ("system", "user", "assistant") for m in msgs):
            raise ValueError(f"line {i}: each row needs messages ending with an assistant turn")
        rows.append(r)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct", help="any chat model on Hugging Face (open weights)")
    ap.add_argument("--out", default="sandbox/alerte-lora")
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--max-len", type=int, default=2048)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--4bit", dest="four_bit", action="store_true", help="QLoRA: fits a 7B model on a 16 GB GPU")
    ap.add_argument("--merge", action="store_true", help="also save merged full weights (for vLLM / GGUF conversion)")
    ap.add_argument("--dry-run", action="store_true", help="only check the dataset")
    args = ap.parse_args()

    rows = load_rows(Path(args.data))
    by_src: dict[str, int] = {}
    for r in rows:
        by_src[r.get("source", "?")] = by_src.get(r.get("source", "?"), 0) + 1
    print(f"{len(rows)} examples {by_src}")
    if args.dry_run:
        return 0

    try:
        import torch
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, DataCollatorForSeq2Seq,
                                  Trainer, TrainingArguments)
    except ImportError as e:
        print(f"Missing training libraries ({e}). See the install line at the top of this file.")
        return 1
    if not torch.cuda.is_available():
        print("No GPU found. Run this in the ITU sandbox, Colab or Kaggle with a GPU.")
        return 1

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
                               bnb_4bit_compute_dtype=torch.bfloat16) if args.four_bit else None
    model = AutoModelForCausalLM.from_pretrained(args.model, quantization_config=quant, torch_dtype=torch.bfloat16,
                                                 device_map="auto")
    if args.four_bit:
        model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LoraConfig(r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05,
                                             target_modules="all-linear", task_type="CAUSAL_LM"))
    model.print_trainable_parameters()

    def encode(r: dict) -> dict:
        prompt = tok.apply_chat_template(r["messages"][:-1], tokenize=False, add_generation_prompt=True)
        full = tok.apply_chat_template(r["messages"], tokenize=False)
        p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
        ids = tok(full, add_special_tokens=False, truncation=True, max_length=args.max_len)["input_ids"]
        labels = [-100] * min(len(p_ids), len(ids)) + ids[len(p_ids):]   # learn only the assistant answer
        return {"input_ids": ids, "attention_mask": [1] * len(ids), "labels": labels[:len(ids)]}

    data = [encode(r) for r in rows]
    data = [d for d in data if any(x != -100 for x in d["labels"])]
    split = max(1, len(data) // 10)
    train, evals = data[split:], data[:split]

    targs = TrainingArguments(output_dir=args.out, num_train_epochs=args.epochs, learning_rate=args.lr,
                              per_device_train_batch_size=args.batch, gradient_accumulation_steps=args.grad_accum,
                              per_device_eval_batch_size=args.batch, bf16=True, logging_steps=5, save_strategy="epoch",
                              eval_strategy="epoch", lr_scheduler_type="cosine", warmup_ratio=0.05, report_to=[])
    trainer = Trainer(model=model, args=targs, train_dataset=train, eval_dataset=evals,
                      data_collator=DataCollatorForSeq2Seq(tok, padding=True, label_pad_token_id=-100))
    trainer.train()
    model.save_pretrained(args.out)
    tok.save_pretrained(args.out)
    print(f"LoRA adapter saved in {args.out}")
    if args.merge:
        merged = model.merge_and_unload()
        merged.save_pretrained(args.out + "-merged")
        tok.save_pretrained(args.out + "-merged")
        print(f"Merged model saved in {args.out}-merged (serve with vLLM, or convert to GGUF for Ollama)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
