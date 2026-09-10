"""Confirmation gate — the one rule the model cannot talk its way past.

Saving a draft, editing a confirmed invoice and deleting are irreversible-ish; the professor's requirement is that
"confirm before save/edit/delete" is enforced by the program, not by the prompt. So a gated tool call is never
executed on the turn the model makes it: it is parked as the user's pending_action and the model gets a preview
to show. It runs only when the *next* user message is a confirmation — matched here, in code, by regex.
A user turn that itself starts with a confirmation word ("ยืนยัน", after the agent showed a draft preview) counts
as consent for that turn, so the normal draft -> "ยืนยัน" -> save flow stays one round trip.
"""
import datetime
import re

from app import tools

GATED = {"save_invoice", "update_invoice", "delete_invoice"}
# Thai has no word boundaries ("ยืนยันบันทึก" is one run), so \b only guards the Latin words.
CONFIRM = re.compile(r"^\s*(ยืนยัน|บันทึกเลย|ตกลง|โอเค|(?:ok|okay|yes|confirm)\b)", re.I)
CANCEL = re.compile(r"^\s*(ยกเลิก|ไม่บันทึก|ไม่เอา|(?:cancel|no)\b)", re.I)
TTL = datetime.timedelta(minutes=10)   # a stale preview must not be confirmable an hour later


def is_confirm(text: str | None) -> bool:
    return bool(text and CONFIRM.match(text))


def is_cancel(text: str | None) -> bool:
    return bool(text and CANCEL.match(text))


def needs_gate(user, s, tool: str, args: dict) -> bool:
    if tool not in GATED:
        return False
    if tool == "update_invoice":  # correcting a draft is part of the preview loop; only saved data is gated
        try:
            return tools._own_invoice(user, s, args.get("invoice_id")).status != "draft"
        except tools.ToolError:
            return False  # unknown id: let the tool raise its own message
    return True


def preview(user, s, tool: str, args: dict) -> dict:
    """What the user is about to confirm — from the database, not from the model's memory."""
    if tool == "save_invoice" and str(args.get("draft_id")).lower() == "all":
        return {"drafts": tools._pending_drafts(user, s)}
    iv = tools._own_invoice(user, s, args.get("draft_id") or args.get("invoice_id"))  # raises ToolError if not ours
    d = tools._inv_dict(iv)
    if tool == "update_invoice":
        d["changes"] = args.get("fields")
    return d


def park(user, s, tool: str, args: dict):
    user.pending_action = {"tool": tool, "args": args}
    user.pending_at = datetime.datetime.utcnow()
    s.commit()


def peek(user) -> dict | None:
    if user.pending_action and user.pending_at and datetime.datetime.utcnow() - user.pending_at < TTL:
        return dict(user.pending_action)
    return None


def clear(user, s):
    user.pending_action = None
    user.pending_at = None
    s.commit()


if __name__ == "__main__":  # python -m app.gate — the regex is the security boundary, so it has its own check
    for s_, want in [("ยืนยันบันทึก", True), ("ยืนยัน บันทึกเลย", True), ("โอเค บันทึก", True), ("okay", True), ("ok", True),
                     ("ยอดจริง 350", False), ("ไม่เอา ยกเลิก", False), ("confirmation?", False)]:
        assert is_confirm(s_) is want, (s_, want)
    for s_, want in [("ไม่เอา ยกเลิก", True), ("ยกเลิก", True), ("note", False), ("no", True), ("now", False), ("ยืนยัน", False)]:
        assert is_cancel(s_) is want, (s_, want)
    print("gate regex ok")
