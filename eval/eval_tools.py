"""Eval A + D: tool-selection benchmark. Each case = seeded DB state + prior context + one message.
Scores the FIRST tool the agent calls (+ arg subset), forbidden tools, and reply constraints.
Run inside the container:  GEMMA_MODEL=gemma-4-26b-a4b-it python -m eval.eval_tools [cases.json]
"""
import asyncio
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

from sqlalchemy import select

from app import agent, tools
from app.db import Invoice, Note, Profile, User, init_db, session

CASES = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("cases_tool_selection.json"))
LOG = Path("/data/logs/turns.jsonl")


def seed(ext: str, spec: dict) -> dict:
    """Create user + rows; returns {"ids": [invoice ids in seed order]}."""
    uid = agent.get_user(ext)
    ids = []
    with session() as s:
        u = s.get(User, uid)
        for name in spec.get("profiles", []):
            s.add(Profile(user_id=u.id, name=name))
        s.commit()
        for kind in ("confirmed", "drafts"):
            for d in spec.get(kind, []):
                iv = Invoice(profile_id=tools._active_profile(u, s).id, status="confirmed" if kind == "confirmed" else "draft",
                             vendor=d.get("vendor"), invoice_date=d.get("date", "2026-08-20"), total=d.get("total"),
                             subtotal=d.get("subtotal", d.get("total")), vat=d.get("vat", 0.0), category=d.get("category", "อาหาร"),
                             currency=d.get("currency", "THB"), total_thb=d.get("total_thb", d.get("total")) if d.get("currency", "THB") == "THB" else d.get("total_thb"),
                             items=d.get("items"))
                if d.get("reimbursed"):
                    import datetime
                    iv.reimbursed_at = datetime.datetime.utcnow()
                s.add(iv)
                s.commit()
                ids.append(iv.id)
                # realistic history: every seeded invoice came through analyze (+ save) with its id visible in TOOL_RESULT
                agent._store(s, u.id, "user", {"text": f"[image id=seed{iv.id}]"})
                agent._store(s, u.id, "model", {"text": json.dumps({"tool": "analyze_receipt", "args": {"image_id": f"seed{iv.id}"}}, ensure_ascii=False)})
                agent._store(s, u.id, "user", {"text": "TOOL_RESULT analyze_receipt: " + json.dumps({"draft_id": iv.id, "vendor": iv.vendor, "date": iv.invoice_date, "total": iv.total, "vat": iv.vat, "currency": iv.currency, "category": iv.category, "items": iv.items, "warnings": [] if iv.currency == "THB" else [f"บิลสกุล {iv.currency} — เรียก convert_currency(draft_id={iv.id})"]}, ensure_ascii=False)})
                if kind == "confirmed":
                    agent._store(s, u.id, "model", {"text": json.dumps({"reply": f"สรุปบิล {iv.vendor} {iv.total} บาท ถูกต้องไหมครับ?"}, ensure_ascii=False)})
                    agent._store(s, u.id, "user", {"text": "ยืนยัน"})
                    agent._store(s, u.id, "model", {"text": json.dumps({"tool": "save_invoice", "args": {"draft_id": iv.id}}, ensure_ascii=False)})
                    agent._store(s, u.id, "user", {"text": "TOOL_RESULT save_invoice: " + json.dumps({"saved": iv.id, "vendor": iv.vendor, "total": iv.total}, ensure_ascii=False)})
        for t in spec.get("notes", []):
            s.add(Note(user_id=u.id, text=t))
        s.commit()
    return {"uid": uid, "ids": ids}


def inject_context(uid: int, lines: list[str], ids: list[int]):
    with session() as s:
        for line in lines:
            role, _, text = line.partition(":")
            for i, v in enumerate(ids):
                text = text.replace(f"$ID{i}", str(v))
            agent._store(s, uid, role, {"text": text})


def subset(expected, actual) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(subset(v, actual.get(k)) for k, v in expected.items())
    if isinstance(expected, bool) or actual is None:
        return str(expected).lower() == str(actual).lower()
    try:  # 95 == 95.0 == "95.00"
        return abs(float(str(expected).replace(",", "")) - float(str(actual).replace(",", ""))) < 0.01
    except ValueError:
        return str(expected).strip().lower() == str(actual).strip().lower()


def score(case: dict, steps: list[dict], reply: str) -> tuple[bool, str]:
    exp = case["expect"]
    calls = [s for s in steps if "tool" in s]
    first = calls[0]["tool"] if calls else None
    names = [c["tool"] for c in calls]
    if "tool" in exp and exp["tool"] != first:
        return False, f"first tool {first!r} != {exp['tool']!r}"
    if "tool_any" in exp and first not in exp["tool_any"]:
        return False, f"first tool {first!r} not in {exp['tool_any']}"
    if "args_contains" in exp and calls and not subset(exp["args_contains"], calls[0].get("args", {})):
        return False, f"args {calls[0].get('args')} missing {exp['args_contains']}"
    if "args_has_keys" in exp and calls and not all(k in calls[0].get("args", {}) for k in exp["args_has_keys"]):
        return False, f"args {calls[0].get('args')} lacks keys {exp['args_has_keys']}"
    if "args_any" in exp and calls and not any(subset(a, calls[0].get("args", {})) for a in exp["args_any"]):
        return False, f"args {calls[0].get('args')} matches none of {exp['args_any']}"
    for f in exp.get("forbid", []):
        if f in names:
            return False, f"forbidden tool {f} called"
    for k, n in exp.get("max_calls", {}).items():
        if names.count(k) > n:
            return False, f"{k} called {names.count(k)}x > {n}"
    for bad in exp.get("reply_not_contains", []):
        if bad in reply:
            return False, f"reply contains {bad!r}"
    if "reply_contains_any" in exp and not any(w in reply for w in exp["reply_contains_any"]):
        return False, f"reply lacks any of {exp['reply_contains_any']}"
    for t in exp.get("tools_contains", []):
        if t not in names:
            return False, f"tool chain {names} lacks {t}"
    if "tool_any_after" in exp and not any(t in names[1:] for t in exp["tool_any_after"]):
        return False, f"chain {names} has none of {exp['tool_any_after']} after the first call"
    if "min_tools" in exp and len(names) < exp["min_tools"]:
        return False, f"chain length {len(names)} < {exp['min_tools']}"
    return True, "ok"


async def run_case(case: dict) -> dict:
    ext = f"evalA:{case['id']}:{uuid.uuid4().hex[:6]}"
    st = seed(ext, case.get("seed", {}))
    inject_context(st["uid"], case.get("context", []), st["ids"])
    img = None
    if case.get("image"):
        src = Path(case["image"])
        dst = Path("/data/uploads") / f"evalA-{uuid.uuid4().hex[:8]}{src.suffix}"
        shutil.copy(src, dst)
        img = str(dst)
    out = await agent.run_turn(ext, text=case.get("message"), image_path=img)
    last = json.loads(LOG.read_text(encoding="utf-8").splitlines()[-1])
    ok, why = score(case, last["steps"], out["reply"])
    return {"id": case["id"], "group": case["group"], "ok": ok, "why": why,
            "tools": [s["tool"] for s in last["steps"] if "tool" in s], "reply": out["reply"][:120]}


async def main():
    init_db()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    if os.environ.get("CASE_IDS"):  # rerun a subset, e.g. CASE_IDS=4,12,27
        want = {int(x) for x in os.environ["CASE_IDS"].split(",")}
        cases = [c for c in cases if c["id"] in want]
    results = []
    for c in cases:
        r = await run_case(c)
        results.append(r)
        print(f"{'✓' if r['ok'] else '✗'} #{r['id']:<3} {r['group']:<16} {r['tools']}  {'' if r['ok'] else '← ' + r['why']}", flush=True)
    groups = {}
    for r in results:
        g = groups.setdefault(r["group"].split("-")[0], [0, 0])
        g[0] += r["ok"]
        g[1] += 1
    print("\nMODEL:", os.environ.get("GEMMA_MODEL", "gemma-4-26b-a4b-it"))
    for g, (a, b) in groups.items():
        print(f"  {g}: {a}/{b} = {a / b:.0%}")
    print(f"  ALL: {sum(r['ok'] for r in results)}/{len(results)} = {sum(r['ok'] for r in results) / len(results):.0%}")
    out = Path("/data/logs") / f"evalA_{os.environ.get('GEMMA_MODEL', 'gemma-4-26b-a4b-it')}{'_subset' if os.environ.get('CASE_IDS') else ''}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
