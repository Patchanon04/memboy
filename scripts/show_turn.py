"""For the live demo: print the latest turn exactly as the agent saw it, split into
what the user sent / what the model asked for / CONTEXT returned by the tool / FINAL ANSWER.
Run inside the container right after sending a message in LINE (or the web test page):
    python -m scripts.show_turn            # the most recently active user
    python -m scripts.show_turn 3          # the last 3 turns
The user is shown by pseudonym (app/privacy.py), never by LINE id.
"""
import json
import sys
import textwrap

from sqlalchemy import select

from app import privacy
from app.db import Conversation, User, init_db, session

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1


def is_user_msg(r):
    t = r.content.get("text") or ""
    return r.role == "user" and not t.startswith(("TOOL_RESULT", "SYSTEM"))


def short(s, n=900):
    return s if len(s) <= n else s[:n] + f" ... (+{len(s) - n} ตัวอักษร)"


def main():
    init_db()
    with session() as s:
        last = s.scalars(select(Conversation).order_by(Conversation.id.desc()).limit(1)).first()
        if not last:
            print("ยังไม่มีบทสนทนา")
            return
        user = s.get(User, last.user_id)
        rows = s.scalars(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.id)).all()
    starts = [i for i, r in enumerate(rows) if is_user_msg(r)][-N:]
    print(f"ผู้ใช้: {privacy.pseudonym(user.line_user_id)}\n")
    for k, st in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(rows)
        u = rows[st].content
        print("=" * 70)
        print("ผู้ใช้ส่ง:", (u.get("text") or "").strip() or "(รูป)", "[มีรูป]" if u.get("image") else "")
        for r in rows[st + 1:end]:
            t = r.content.get("text") or ""
            if r.role == "model":
                try:
                    act = json.loads(t)
                except ValueError:
                    print("\nโมเดลตอบ (ไม่ใช่ JSON, ระบบขอใหม่):", short(t, 200))
                    continue
                if "tool" in act:
                    print(f"\nโมเดลขอเรียก tool: {act['tool']}  argument: {json.dumps(act.get('args', {}), ensure_ascii=False)}")
                else:
                    print("\n>>> FINAL ANSWER (ข้อความที่ส่งกลับ LINE):")
                    print(textwrap.indent(str(act.get("reply", "")), "    "))
            elif t.startswith("TOOL_RESULT"):
                name, _, payload = t[len("TOOL_RESULT "):].partition(": ")
                print(f"\n>>> CONTEXT จาก tool {name} (ส่งกลับเข้า complete prompt):")
                print(textwrap.indent(short(payload), "    "))
            elif t.startswith("SYSTEM"):
                print("\nระบบแทรก:", short(t, 200))
        print()


if __name__ == "__main__":
    main()
