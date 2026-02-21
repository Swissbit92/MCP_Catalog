"""
HTML + JSON reporter for comprehensive persona test results.

Produces:
  - results/comprehensive_results.json  — full machine-readable data
  - results/comprehensive_report.html   — self-contained visual report
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

# ANSI codes (Windows 10+ / ANSI terminal)
_R = "\033[0m"
_BOLD = "\033[1m"
_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_DIM = "\033[2m"


def _ansi(text: str, *codes: str) -> str:
    return "".join(codes) + text + _R


def print_progress(current: int, total: int, test: dict, result: dict | None = None) -> None:
    """Print one-line progress indicator."""
    cat = test.get("category", "?")
    persona = test.get("persona", "?")
    q = test.get("question", "")[:55]
    prefix = f"[{current:03d}/{total}]"
    if result is None:
        print(f"{_DIM}{prefix}{_R} ({cat}) {_CYAN}{persona}{_R}: {q}...", end="", flush=True)
    else:
        score = result.get("score", 0)
        passed = result.get("passed", False)
        grade = result.get("grade", "?")
        source = result.get("source", "?")
        elapsed = result.get("elapsed", 0)
        status = _ansi(f"{'PASS' if passed else 'FAIL'}", _GREEN if passed else _RED, _BOLD)
        print(f"\r{_DIM}{prefix}{_R} ({cat}) {_CYAN}{persona}{_R}: {q:<55} "
              f"{status} {grade} {score:.2f} [{source}] {elapsed:.1f}s")


def print_summary(aggregate: dict, verbose: bool = False) -> None:
    """Print terminal summary with ANSI colour."""
    if not aggregate:
        print("No results to summarise.")
        return

    pr = aggregate["pass_rate"]
    colour = _GREEN if pr >= 0.80 else (_YELLOW if pr >= 0.60 else _RED)

    print(f"\n{'═' * 80}")
    print(_ansi("  NEPHILIM PERSONA TEST SUMMARY", _BOLD, _CYAN))
    print(f"{'═' * 80}")
    print(f"  Total:      {aggregate['total']}")
    print(f"  Passed:     {_ansi(str(aggregate['passed']), _GREEN, _BOLD)}")
    print(f"  Failed:     {_ansi(str(aggregate['failed']), _RED, _BOLD)}")
    print(f"  Pass rate:  {_ansi(f'{pr*100:.1f}%', colour, _BOLD)}")
    print(f"  Avg score:  {aggregate['avg_score']:.3f}")

    gd = aggregate.get("grade_distribution", {})
    dist = "  ".join(f"{g}:{gd.get(g,0)}" for g in ["A", "B", "C", "D", "F"])
    print(f"  Grades:     {dist}")

    print(f"\n  {'DIMENSION':<22} AVG SCORE")
    print(f"  {'─' * 35}")
    for dim, val in aggregate.get("by_dimension", {}).items():
        bar = "█" * int(val * 20)
        dc = _GREEN if val >= 0.80 else (_YELLOW if val >= 0.60 else _RED)
        print(f"  {dim:<22} {_ansi(f'{val:.3f}', dc)} {_DIM}{bar}{_R}")

    print(f"\n  {'PERSONA':<26} PASS%   AVG SCORE   TOTAL")
    print(f"  {'─' * 58}")
    for persona, d in aggregate.get("by_persona", {}).items():
        pr_p = d["pass_rate"]
        pc = _GREEN if pr_p >= 0.80 else (_YELLOW if pr_p >= 0.60 else _RED)
        print(f"  {persona:<26} {_ansi(f'{pr_p*100:5.1f}%', pc)}   "
              f"{d['avg_score']:.3f}       {d['total']}")

    if verbose:
        print(f"\n  {'CATEGORY':<26} PASS%   AVG SCORE   TOTAL")
        print(f"  {'─' * 58}")
        for cat, d in sorted(aggregate.get("by_category", {}).items()):
            pr_c = d["pass_rate"]
            cc = _GREEN if pr_c >= 0.80 else (_YELLOW if pr_c >= 0.60 else _RED)
            print(f"  {cat:<26} {_ansi(f'{pr_c*100:5.1f}%', cc)}   "
                  f"{d['avg_score']:.3f}       {d['total']}")

    print(f"{'═' * 80}\n")


def save_json(results: list[dict], path: str) -> None:
    """Save full results to JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  JSON saved → {path}")


def save_html(results: list[dict], aggregate: dict, path: str) -> None:
    """Generate a self-contained dark-themed HTML report."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pr = aggregate.get("pass_rate", 0)
    pr_color = "#00ff88" if pr >= 0.80 else ("#ffd700" if pr >= 0.60 else "#ff4455")
    gd = aggregate.get("grade_distribution", {})

    # ── Row building ──────────────────────────────────────────────────────────
    rows_html = ""
    for i, r in enumerate(results, 1):
        passed = r.get("passed", False)
        score = r.get("score", 0)
        grade = r.get("grade", "?")
        row_cls = "pass-row" if passed else "fail-row"
        flags = "; ".join(r.get("flags", [])[:2]) or "—"
        dims = r.get("dimensions", {})
        dim_cells = "".join(
            f'<td class="dim-cell" title="{d}">{dims.get(d, 0):.2f}</td>'
            for d in ["mcp_routing", "persona_voice", "no_leak", "safety",
                       "factual_anchor", "response_quality", "emotional_fit"]
        )
        status_badge = (
            '<span class="badge pass">PASS</span>' if passed
            else '<span class="badge fail">FAIL</span>'
        )
        q_short = r.get("question", "")[:65].replace("<", "&lt;").replace(">", "&gt;")
        answer_preview = (r.get("answer", "") or "")[:200].replace("<", "&lt;").replace(">", "&gt;")
        rows_html += f"""
        <tr class="{row_cls}">
          <td class="num">{i}</td>
          <td class="persona-cell">{r.get("persona","")}</td>
          <td class="cat-cell">{r.get("category","")}</td>
          <td class="q-cell" title="{r.get('question','').replace('"','&quot;')}">{q_short}</td>
          <td>{r.get("source","?")}</td>
          <td>{r.get("elapsed",0):.1f}s</td>
          <td class="score-cell">{score:.3f}</td>
          <td class="grade-{grade.lower()}">{grade}</td>
          {dim_cells}
          <td>{status_badge}</td>
          <td class="flags-cell" title="{flags}">{flags[:60]}</td>
          <td class="answer-cell" title="{answer_preview}">{answer_preview[:80]}…</td>
        </tr>"""

    # ── Persona table ──────────────────────────────────────────────────────────
    persona_rows = ""
    for p, d in aggregate.get("by_persona", {}).items():
        pr_p = d["pass_rate"]
        pc = "#00ff88" if pr_p >= 0.80 else ("#ffd700" if pr_p >= 0.60 else "#ff4455")
        avg_dims = d.get("avg_dimensions", {})
        dim_cells = "".join(
            f'<td class="dim-cell">{avg_dims.get(dim,0):.2f}</td>'
            for dim in ["mcp_routing", "persona_voice", "no_leak", "safety",
                         "factual_anchor", "response_quality", "emotional_fit"]
        )
        persona_rows += f"""
        <tr>
          <td class="persona-cell">{p}</td>
          <td>{d['total']}</td>
          <td style="color:{pc}"><b>{pr_p*100:.1f}%</b></td>
          <td>{d['avg_score']:.3f}</td>
          {dim_cells}
        </tr>"""

    # ── Category table ─────────────────────────────────────────────────────────
    cat_rows = ""
    for cat, d in sorted(aggregate.get("by_category", {}).items()):
        pr_c = d["pass_rate"]
        pc = "#00ff88" if pr_c >= 0.80 else ("#ffd700" if pr_c >= 0.60 else "#ff4455")
        cat_rows += f"""
        <tr>
          <td>{cat}</td>
          <td>{d['total']}</td>
          <td style="color:{pc}"><b>{pr_c*100:.1f}%</b></td>
          <td>{d['avg_score']:.3f}</td>
        </tr>"""

    # ── Dimension global bars ─────────────────────────────────────────────────
    dim_bars = ""
    for dim, val in aggregate.get("by_dimension", {}).items():
        bar_color = "#00ff88" if val >= 0.80 else ("#ffd700" if val >= 0.60 else "#ff4455")
        dim_bars += f"""
        <div class="dim-row">
          <span class="dim-label">{dim}</span>
          <div class="bar-track"><div class="bar-fill" style="width:{val*100:.1f}%;background:{bar_color}"></div></div>
          <span class="dim-val">{val:.3f}</span>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEPHILIM Persona Test Report — {ts}</title>
<style>
  :root {{
    --void: #0B0B0D; --surface: #111116; --surface2: #1a1a22;
    --cyan: #00ffff; --magenta: #ff00ff; --gold: #ffd700;
    --text: #e8e8f0; --dim: #666680; --border: #2a2a38;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--void); color: var(--text); font-family: 'Manrope',sans-serif; font-size: 13px; }}
  h1 {{ font-size: 1.8rem; color: var(--cyan); letter-spacing: 2px; }}
  h2 {{ font-size: 1rem; color: var(--magenta); margin: 1.5rem 0 0.5rem; letter-spacing: 1px; text-transform: uppercase; }}
  .header {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 1.5rem 2rem; }}
  .subtitle {{ color: var(--dim); margin-top: 0.3rem; font-size: 0.85rem; }}
  .main {{ padding: 1.5rem 2rem; }}

  /* Summary cards */
  .cards {{ display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0 1.5rem; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
           padding: 1rem 1.5rem; min-width: 120px; }}
  .card .val {{ font-size: 2rem; font-weight: 700; }}
  .card .lbl {{ color: var(--dim); font-size: 0.75rem; margin-top: 0.2rem; }}
  .grade-card {{ display: flex; gap: 1.5rem; align-items: center; }}
  .grade-a {{ color: #00ff88; }} .grade-b {{ color: #7fffff; }}
  .grade-c {{ color: #ffd700; }} .grade-d {{ color: #ff9944; }} .grade-f {{ color: #ff4455; }}

  /* Dimension bars */
  .dim-row {{ display: flex; align-items: center; gap: 0.8rem; margin: 0.3rem 0; }}
  .dim-label {{ width: 160px; color: var(--dim); font-size: 0.8rem; }}
  .bar-track {{ flex: 1; height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 4px; transition: width 0.3s; }}
  .dim-val {{ width: 45px; text-align: right; font-size: 0.8rem; }}

  /* Tables */
  table {{ width: 100%; border-collapse: collapse; margin: 0.5rem 0 1.5rem; font-size: 0.75rem; }}
  th {{ background: var(--surface2); color: var(--cyan); padding: 6px 8px; text-align: left;
        border-bottom: 2px solid var(--border); position: sticky; top: 0; }}
  td {{ padding: 5px 8px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  tr:hover td {{ background: var(--surface2); }}
  .pass-row {{ border-left: 3px solid #00ff88; }}
  .fail-row {{ border-left: 3px solid #ff4455; }}
  .num {{ color: var(--dim); width: 30px; }}
  .persona-cell {{ color: var(--cyan); font-weight: 600; }}
  .cat-cell {{ color: var(--magenta); font-size: 0.7rem; }}
  .q-cell {{ max-width: 200px; }}
  .score-cell {{ font-weight: 700; }}
  .flags-cell {{ color: #ff9944; font-size: 0.7rem; max-width: 160px; }}
  .answer-cell {{ color: var(--dim); font-size: 0.7rem; max-width: 200px;
                  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .dim-cell {{ font-size: 0.7rem; text-align: center; color: var(--dim); }}
  .badge {{ padding: 2px 6px; border-radius: 3px; font-weight: 700; font-size: 0.7rem; }}
  .badge.pass {{ background: #00441b; color: #00ff88; }}
  .badge.fail {{ background: #440011; color: #ff4455; }}
  .grade-a {{ color: #00ff88; font-weight: 700; }}
  .grade-b {{ color: #7fffff; font-weight: 700; }}
  .grade-c {{ color: #ffd700; font-weight: 700; }}
  .grade-d {{ color: #ff9944; font-weight: 700; }}
  .grade-f {{ color: #ff4455; font-weight: 700; }}

  /* Search/filter */
  .controls {{ display: flex; gap: 0.8rem; margin: 0.5rem 0; flex-wrap: wrap; }}
  input[type=text], select {{ background: var(--surface); border: 1px solid var(--border);
    color: var(--text); padding: 5px 10px; border-radius: 4px; font-size: 0.8rem; }}
  input[type=text]:focus, select:focus {{ outline: none; border-color: var(--cyan); }}
  .overflow-x {{ overflow-x: auto; }}
</style>
</head>
<body>
<div class="header">
  <h1>⬡ NEPHILIM PERSONA TEST REPORT</h1>
  <div class="subtitle">Generated {ts} · {aggregate.get("total",0)} tests across all personas</div>
</div>
<div class="main">

<h2>Overall Summary</h2>
<div class="cards">
  <div class="card"><div class="val">{aggregate.get('total',0)}</div><div class="lbl">TOTAL TESTS</div></div>
  <div class="card"><div class="val" style="color:#00ff88">{aggregate.get('passed',0)}</div><div class="lbl">PASSED</div></div>
  <div class="card"><div class="val" style="color:#ff4455">{aggregate.get('failed',0)}</div><div class="lbl">FAILED</div></div>
  <div class="card"><div class="val" style="color:{pr_color}">{pr*100:.1f}%</div><div class="lbl">PASS RATE</div></div>
  <div class="card"><div class="val">{aggregate.get('avg_score',0):.3f}</div><div class="lbl">AVG SCORE</div></div>
  <div class="card">
    <div class="grade-card">
      <div><span class="grade-a">A:{gd.get('A',0)}</span></div>
      <div><span class="grade-b">B:{gd.get('B',0)}</span></div>
      <div><span class="grade-c">C:{gd.get('C',0)}</span></div>
      <div><span class="grade-d">D:{gd.get('D',0)}</span></div>
      <div><span class="grade-f">F:{gd.get('F',0)}</span></div>
    </div>
    <div class="lbl">GRADE DISTRIBUTION</div>
  </div>
</div>

<h2>Scoring Dimensions</h2>
{dim_bars}

<h2>Per-Persona Breakdown</h2>
<div class="overflow-x">
<table>
<thead><tr>
  <th>Persona</th><th>Tests</th><th>Pass%</th><th>Avg Score</th>
  <th title="mcp_routing">Routing</th>
  <th title="persona_voice">Voice</th>
  <th title="no_leak">No Leak</th>
  <th title="safety">Safety</th>
  <th title="factual_anchor">Factual</th>
  <th title="response_quality">Quality</th>
  <th title="emotional_fit">Emotion</th>
</tr></thead>
<tbody>{persona_rows}</tbody>
</table>
</div>

<h2>Per-Category Breakdown</h2>
<table>
<thead><tr><th>Category</th><th>Tests</th><th>Pass%</th><th>Avg Score</th></tr></thead>
<tbody>{cat_rows}</tbody>
</table>

<h2>Full Test Results</h2>
<div class="controls">
  <input type="text" id="search" placeholder="Filter question/persona/category..." oninput="filterTable()">
  <select id="statusFilter" onchange="filterTable()">
    <option value="">All</option>
    <option value="pass">Pass only</option>
    <option value="fail">Fail only</option>
  </select>
  <select id="personaFilter" onchange="filterTable()">
    <option value="">All personas</option>
  </select>
</div>
<div class="overflow-x">
<table id="resultsTable">
<thead><tr>
  <th>#</th><th>Persona</th><th>Category</th><th>Question</th><th>Source</th><th>Time</th>
  <th>Score</th><th>Grade</th>
  <th title="mcp_routing">Rt</th>
  <th title="persona_voice">Vo</th>
  <th title="no_leak">Lk</th>
  <th title="safety">Sf</th>
  <th title="factual_anchor">Fc</th>
  <th title="response_quality">Qu</th>
  <th title="emotional_fit">Em</th>
  <th>Status</th><th>Flags</th><th>Answer Preview</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
</div>

</div>
<script>
function filterTable() {{
  const search = document.getElementById('search').value.toLowerCase();
  const status = document.getElementById('statusFilter').value;
  const persona = document.getElementById('personaFilter').value.toLowerCase();
  const rows = document.querySelectorAll('#resultsTable tbody tr');
  rows.forEach(row => {{
    const text = row.innerText.toLowerCase();
    const isPass = row.classList.contains('pass-row');
    const matchSearch = !search || text.includes(search);
    const matchStatus = !status || (status==='pass'&&isPass) || (status==='fail'&&!isPass);
    const matchPersona = !persona || text.includes(persona);
    row.style.display = matchSearch && matchStatus && matchPersona ? '' : 'none';
  }});
}}
// Populate persona filter
(function() {{
  const sel = document.getElementById('personaFilter');
  const personas = [...new Set([...document.querySelectorAll('#resultsTable .persona-cell')].map(c=>c.innerText))];
  personas.sort().forEach(p => {{
    const opt = document.createElement('option');
    opt.value = p; opt.textContent = p; sel.appendChild(opt);
  }});
}})();
</script>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  HTML saved → {path}")
