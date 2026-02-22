"""
Emergency log scraper — extracts scored results from run.log and saves checkpoint JSON.
Use this if the background run crashes before completing a persona.

Usage:
  python tests/manual/scrape_log.py
  python tests/manual/scrape_log.py --watch   # re-scrape every 60s
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
import argparse

LOG = os.path.join(os.path.dirname(__file__), "results", "run.log")
OUT = os.path.join(os.path.dirname(__file__), "results", "scraped_checkpoint.json")

# Matches:  [001/1045] (ADVERSARIAL) nephilim_eeva: question text   PASS A 0.96 [llm] 16.4s
_LINE_RE = re.compile(
    r"\[(\d+)/(\d+)\]\s+\((\w+)\)\s+([\w]+):\s+(.+?)\s+"
    r"(PASS|FAIL)\s+([A-F])\s+([\d.]+)\s+\[([^\]]+)\]\s+([\d.]+)s"
)

# Strip ANSI codes
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def scrape(log_path: str) -> list[dict]:
    results = []
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except FileNotFoundError:
        print(f"Log not found: {log_path}")
        return []

    clean = _ANSI.sub("", raw)
    for line in clean.splitlines():
        m = _LINE_RE.search(line)
        if not m:
            continue
        idx, total, category, persona, question, status, grade, score, source, elapsed = m.groups()
        results.append({
            "num": int(idx),
            "total": int(total),
            "category": category,
            "persona": persona,
            "question": question.strip(),
            "passed": status == "PASS",
            "grade": grade,
            "score": float(score),
            "source": source,
            "elapsed": float(elapsed),
        })
    # Deduplicate by num (keep last occurrence — most complete)
    seen: dict[int, dict] = {}
    for r in results:
        seen[r["num"]] = r
    return sorted(seen.values(), key=lambda r: r["num"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="Re-scrape every 60s")
    parser.add_argument("--log", default=LOG)
    parser.add_argument("--out", default=OUT)
    args = parser.parse_args()

    while True:
        results = scrape(args.log)
        if results:
            total = len(results)
            passed = sum(1 for r in results if r["passed"])
            avg = sum(r["score"] for r in results) / total
            by_persona: dict[str, dict] = {}
            for r in results:
                p = r["persona"]
                if p not in by_persona:
                    by_persona[p] = {"total": 0, "passed": 0}
                by_persona[p]["total"] += 1
                by_persona[p]["passed"] += int(r["passed"])

            with open(args.out, "w", encoding="utf-8") as f:
                json.dump({"scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                           "count": total, "results": results}, f, indent=2)

            print(f"[{time.strftime('%H:%M:%S')}] Scraped {total} results | "
                  f"{passed}/{total} pass | avg score {avg:.3f}")
            for p, d in by_persona.items():
                print(f"  {p:<26} {d['passed']}/{d['total']}")
            print(f"  -> saved to {args.out}")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] No results parsed yet from {args.log}")

        if not args.watch:
            break
        print(f"  Next scrape in 60s (Ctrl-C to stop)...\n")
        try:
            time.sleep(60)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
