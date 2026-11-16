"""Phase 1 baseline: send each question in a JSONL file to api /ask and save the answers."""
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = "http://localhost:8000/ask"
DATASET = Path("evals/datasets/baseline_phase1.jsonl")
OUT_DIR = Path("evals/reports")


def ask(question: str) -> dict:
    body = json.dumps({"question": question}).encode()
    req = urllib.request.Request(API_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:  # 422 / 502 / 503 from our API
        return {"error": e.code, "detail": e.read().decode()}


def main() -> None:
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    jsonl_path = OUT_DIR / f"baseline_no_rag_{stamp}.jsonl"
    md_path = OUT_DIR / f"baseline_no_rag_{stamp}.md"

    total_cost, md = 0.0, [f"# Baseline without RAG ({stamp} UTC)\n"]
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in rows:
            res = ask(row["question"])
            f.write(json.dumps({**row, "response": res}, ensure_ascii=False) + "\n")

            status = res.get("status", f"ERROR {res.get('error')}")
            sources = [c["title"] for c in res.get("citations", [])] or ["(none)"]
            total_cost += res.get("meta", {}).get("cost_usd", 0.0)
            md.append(
                f"## {row['id']} · {row['category']} · {status}\n\n"
                f"**Q:** {row['question']}\n\n{res.get('answer', res.get('detail'))}\n\n"
                + "**Sources:**\n" + "".join(f"- {s}\n" for s in sources)
            )
            print(f"[{row['id']}] {row['category']:<14} -> {status}")

    md_path.write_text("\n".join(md), encoding="utf-8")
    print(f"\nSaved: {jsonl_path} and {md_path} | total cost ~${total_cost:.6f}")


if __name__ == "__main__":
    main()