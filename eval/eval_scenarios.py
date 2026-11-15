"""Eval B: end-to-end multi-turn scenarios, scored on DB STATE not on wording.
Run inside container: python -m eval.eval_scenarios
"""
import asyncio
import json
import shutil
import uuid
from pathlib import Path

from sqlalchemy import select

from app import agent
from app.db import Invoice, Note, Profile, User, init_db, session

R = "/srv/eval/receipts"
SCENARIOS = [
    {"name": "บันทึกบิลตรงๆ", "turns": [("img", f"{R}/02_coffee.png"), "ยืนยัน"],
     "check": {"confirmed": 1, "total_sum": 300.0}},
    {"name": "แก้ยอดก่อนยืนยัน", "turns": [("img", f"{R}/02_coffee.png"), "ยอดจริงๆ 350 นะ", "โอเค บันทึก"],
     "check": {"confirmed": 1, "total_sum": 350.0}},
    {"name": "ปฏิเสธไม่บันทึก", "turns": [("img", f"{R}/02_coffee.png"), "ไม่เอา ยกเลิก"],
     "check": {"confirmed": 0}},
    {"name": "บิลผิดโปรไฟล์ → ย้าย", "turns": ["สร้างโปรไฟล์ทริปหัวหิน", "สลับกลับโปรไฟล์ส่วนตัว", ("img", f"{R}/08_hotel.png"),
                                          "อันนี้ของทริปหัวหินนะ ไม่ใช่ส่วนตัว", "ยืนยันบันทึก"],
     "check": {"confirmed": 1, "profile_of_last": "ทริปหัวหิน"}},
    {"name": "บันทึกแล้วลบแล้วกู้", "turns": [("img", f"{R}/05_grab.png"), "ยืนยัน", "ลบบิลเมื่อกี้", "เฮ้ย ไม่ใช่ เอาคืนมา"],
     "check": {"confirmed": 1, "deleted": 0}},
    {"name": "ถามยอดหลังบันทึก 2 ใบ", "turns": [("img", f"{R}/02_coffee.png"), "ยืนยัน", ("img", f"{R}/05_grab.png"), "ยืนยัน", "รวมทั้งหมดเท่าไหร่"],
     "check": {"confirmed": 2, "reply_contains_number": 384.0}},
    {"name": "บิลซ้ำ → ไม่บันทึกซ้ำ", "turns": [("img", f"{R}/01_7eleven.png"), "ยืนยัน", ("img", f"{R}/01_7eleven.png"), "อ๋อ ซ้ำเหรอ งั้นไม่เอา"],
     "check": {"confirmed": 1}},
    {"name": "จำงบ + เตือนเมื่อเกิน", "turns": ["จำไว้ว่างบเดือนนี้ 100 บาท", ("img", f"{R}/02_coffee.png"), "ยืนยัน"],
     "check": {"notes": 1, "confirmed": 1, "last_reply_mentions_budget": True}},
    {"name": "ติ๊กเบิกแล้ว + รายงานเฉพาะยังไม่เบิก", "turns": [("img", f"{R}/02_coffee.png"), "ยืนยัน", ("img", f"{R}/05_grab.png"), "ยืนยัน",
                                                    "บิลกาแฟเบิกแล้ว", "ยืนยัน", "ขอ PDF เฉพาะที่ยังไม่ได้เบิก"],
     "check": {"reimbursed": 1, "files": 1}},
    {"name": "สองใบ ยืนยันครั้งเดียว → ต้องไม่มีใบค้าง", "turns": [("img", f"{R}/02_coffee.png"), ("img", f"{R}/05_grab.png"), "ยืนยัน บันทึกเลย"],
     "check": {"confirmed": 2, "drafts": 0, "total_sum": 384.0}},
    {"name": "รูปไม่ใช่บิล", "turns": [("img", "/srv/eval/non_receipts/01_landscape.png"), "บันทึกให้หน่อยสิ"],
     "check": {"confirmed": 0, "drafts": 0}},
]


async def run(sc):
    ext = f"evalB:{uuid.uuid4().hex[:6]}"
    agent.get_user(ext)
    last, files = None, 0
    for t in sc["turns"]:
        if isinstance(t, tuple):
            dst = Path("/data/uploads") / f"evalB-{uuid.uuid4().hex[:8]}{Path(t[1]).suffix}"
            shutil.copy(t[1], dst)
            last = await agent.run_turn(ext, image_path=str(dst))
        else:
            last = await agent.run_turn(ext, text=t)
        files += len(last["files"])
    c = sc["check"]
    with session() as s:
        u = s.scalars(select(User).where(User.line_user_id == ext)).first()
        q = select(Invoice).join(Profile).where(Profile.user_id == u.id)
        invs = list(s.scalars(q))
        live = [i for i in invs if i.deleted_at is None]
        conf = [i for i in live if i.status == "confirmed"]
        got = {"confirmed": len(conf), "drafts": len([i for i in live if i.status == "draft"]),
               "deleted": len([i for i in invs if i.deleted_at is not None]),
               "total_sum": round(sum(i.total_thb or 0 for i in conf), 2),
               "reimbursed": len([i for i in conf if i.reimbursed_at]),
               "notes": len(list(s.scalars(select(Note).where(Note.user_id == u.id)))), "files": files,
               "profile_of_last": s.get(Profile, conf[-1].profile_id).name if conf else None,
               "reply_contains_number": any(f"{c.get('reply_contains_number', -1):,.2f}".rstrip("0").rstrip(".") in last["reply"].replace(",", "")
                                            or f"{c.get('reply_contains_number', -1):,.2f}" in last["reply"] for _ in [0]),
               "last_reply_mentions_budget": any(w in last["reply"] for w in ("งบ", "เกิน"))}
    fails = [f"{k}: want {v} got {got.get(k)}" for k, v in c.items()
             if (got.get(k) != v if k != "reply_contains_number" else not got[k])]
    return {"name": sc["name"], "ok": not fails, "fails": fails, "last": last["reply"][:100]}


async def main():
    init_db()
    res = []
    import os
    todo = [sc for sc in SCENARIOS if not os.environ.get('SCENARIO') or os.environ['SCENARIO'] in sc['name']]
    for sc in todo:
        r = await run(sc)
        res.append(r)
        print(f"{'✓' if r['ok'] else '✗'} {r['name']}  {r['fails'] or ''}", flush=True)
    print(f"\nTASK SUCCESS: {sum(r['ok'] for r in res)}/{len(res)}")
    Path("/data/logs/evalB" + ("_subset" if os.environ.get("SCENARIO") else "") + ".json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
