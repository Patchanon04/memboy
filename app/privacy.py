"""Pseudonymization of the people in our logs.

The turn log is kept for evaluation (Eval C, harness checks, error analysis). It needs "same person → same id" so
metrics can count per user — it does not need *who* the person is. So a LINE userId / web login name is replaced by a
keyed hash before it is written:

    Ue6b14f75…  →  line:3f9a0c1d2b7e4a55

Same input + same key → same pseudonym (per-user metrics still work). Without PSEUDONYM_KEY nobody can walk it back,
not even from a list of candidate LINE ids (that is why it is an HMAC and not a bare SHA-256). The real id lives in one
place only: users.line_user_id, which the bot needs to reply. This is pseudonymization, not anonymization: whoever
holds the key *and* the users table can re-link — by design, so a user's data can still be found and deleted.

Keep PSEUDONYM_KEY stable: rotating it splits one person into two pseudonyms across the change. It is separate from
LINE_CHANNEL_SECRET for exactly that reason (that one gets rotated).

    python -m app.privacy FILE.jsonl …   # rewrite old logs in place (idempotent)"""
import hashlib
import hmac
import json
import os
import re
import sys
from pathlib import Path

KEY = (os.environ.get("PSEUDONYM_KEY") or os.environ.get("LINE_CHANNEL_SECRET") or "dev-only").encode()
_LINE_ID = re.compile(r"U[0-9a-f]{32}")
_DONE = re.compile(r"[A-Za-z][A-Za-z0-9]*:[0-9a-f]{16}")
_KIND = re.compile(r"[A-Za-z][A-Za-z0-9]*")


def pseudonym(external_id: str) -> str:
    if _DONE.fullmatch(external_id or ""):
        return external_id  # already a pseudonym — idempotent, safe to rerun the migration
    # the label before the hash says *what kind* of account, never who: line / web / test / harness / evalA …
    # (Eval C excludes test traffic by this label, so it has to survive pseudonymization)
    kind = "line" if _LINE_ID.fullmatch(external_id or "") else ((m := _KIND.match(external_id or "")) and m.group(0)) or "dev"
    return f"{kind}:{hmac.new(KEY, external_id.encode(), hashlib.sha256).hexdigest()[:16]}"


def rewrite(path: Path) -> int:
    """Replace the user field of every row; a raw LINE id that leaked into free text is masked too."""
    out, n = [], 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if "user" in row and row["user"] != (p := pseudonym(str(row["user"]))):
            row["user"], n = p, n + 1
        text = json.dumps(row, ensure_ascii=False)
        out.append(_LINE_ID.sub(lambda m: pseudonym(m.group(0)), text))
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return n


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for f in sys.argv[1:]:
            print(f, "rows pseudonymized:", rewrite(Path(f)))
        sys.exit()
    real = "U" + "ab" * 16
    p = pseudonym(real)
    assert p.startswith("line:") and real not in p and len(p) == 21
    assert pseudonym(real) == p, "stable: per-user metrics must still group"
    assert pseudonym("web:somchai").startswith("web:") and "somchai" not in pseudonym("web:somchai")
    assert pseudonym(p) == p, "idempotent"
    assert pseudonym("U-test-1").startswith("U:"), "test ids are not mistaken for LINE users"
    assert pseudonym("harness-d5").startswith("harness:") and pseudonym("usage:x").startswith("usage:"), "Eval C filters"
    print("privacy ok:", real[:8] + "…", "→", p)
