"""Worker ordering + history windowing, no LLM. Run: docker compose run -T --rm app python -m tests.test_concurrency"""
import asyncio
import json
import time
import uuid

from app import agent, line_io, llm, worker
from app.db import init_db, session


async def _no_line(*a, **k):  # this test is about ordering, not LINE — never hit api.line.me
    return {}


line_io._post = _no_line


def ev(uid, i):
    return {"type": "message", "replyToken": "t", "source": {"userId": uid}, "message": {"type": "text", "id": f"{uid}-{uuid.uuid4().hex[:6]}", "text": f"msg #{i}"}}


def main():
    init_db()
    order = []

    async def fake(contents, temperature=0.0, model=None):
        tag = contents[-1]["parts"][-1]["text"][-2:]
        order.append(("start", tag))
        await asyncio.sleep(0.3)
        order.append(("end", tag))
        return json.dumps({"reply": "ok"})
    llm.generate = fake

    async def run(evs):
        await asyncio.gather(*(worker.process_event({"job_try": 1}, e) for e in evs))

    u = f"U-conc-{uuid.uuid4().hex[:4]}"
    t0 = time.time()
    asyncio.run(run([ev(u, i) for i in range(3)]))
    assert all(order[i][0] == "start" and order[i + 1] == ("end", order[i][1]) for i in range(0, 6, 2)), order  # strictly serial per user
    assert time.time() - t0 >= 0.85
    order.clear()
    t0 = time.time()
    asyncio.run(run([ev(f"U-par-{uuid.uuid4().hex[:4]}", i) for i in range(3)]))
    assert time.time() - t0 < 0.7, "different users must run in parallel"

    uid = agent.get_user(f"hist:{uuid.uuid4().hex[:6]}")
    with session() as s:
        for i in range(45):
            agent._store(s, uid, "user" if i % 2 == 0 else "model", {"text": f"m{i}", "image": "/srv/eval/receipts/01_7eleven.png" if i % 8 == 0 else None})
        c = agent._history_contents(s, uid)
    assert len(c) <= agent.HISTORY_LIMIT and sum(1 for t in c for p in t["parts"] if "inline_data" in p) <= 3
    print("ALL CONCURRENCY/HISTORY TESTS PASSED")


if __name__ == "__main__":
    main()
