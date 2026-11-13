"""W3 tool contracts, no LLM: profiles, find/summarize/compare, notes, reimbursed, categories, split, report/csv, restore.
Run: docker compose run -T --rm app python -m tests.test_w3
"""
import uuid
from pathlib import Path

from app import agent, tools
from app.db import Invoice, User, init_db, session


def user():
    ext = f"test3:{uuid.uuid4().hex[:6]}"
    return ext, agent.get_user(ext)


def add(u, s, **kw):
    d = dict(vendor="ร้าน", invoice_date="2026-08-10", subtotal=100.0, vat=0.0, total=100.0, category="อาหาร", status="confirmed")
    d.update(kw)
    iv = Invoice(profile_id=tools._active_profile(u, s).id, total_thb=d["total"], **d)
    s.add(iv)
    s.commit()
    return iv.id


def main():
    init_db()
    _, uid = user()
    with session() as s:
        u = s.get(User, uid)
        a = add(u, s, vendor="กาแฟบ้านสวน", total=65.0, invoice_date="2026-08-05", items=[{"name": "ลาเต้", "qty": 1, "price": 65}])
        b = add(u, s, vendor="โรงแรมริมน้ำ", total=1850.0, category="ที่พัก", invoice_date="2026-08-12")
        c = add(u, s, vendor="แท็กซี่", total=180.0, category="เดินทาง", invoice_date="2026-07-20")

        # profiles: create switches active; list; switch back; invoice moves via update(profile)
        assert tools.manage_profile(u, s, action="create", name="ทริปหัวหิน")["active"]
        assert [p["name"] for p in tools.manage_profile(u, s, action="list")["profiles"] if p["active"]] == ["ทริปหัวหิน"]
        assert tools.find_invoices(u, s)["count"] == 0                       # new profile is empty
        assert tools.find_invoices(u, s, profile="all")["count"] == 3
        assert tools.find_invoices(u, s, profile="all")["total"] == tools.summarize_expenses(u, s, profile="all")["total"]  # sum from code, not the model
        assert tools.summarize_expenses(u, s, vendor="กาแฟ", profile="all")["total"] == 65.0     # vendor filter is honoured
        for bad in (("summarize_expenses", {"sort": "total"}), ("find_invoices", {"desc": False})):
            try:
                agent.check_args(*bad)
                raise AssertionError(f"unknown arg accepted: {bad}")
            except tools.ToolError as e:
                assert "ใช้ได้" in str(e)
        agent.check_args("summarize_expenses", {"vendor": "x", "date_from": "2026-08-01"})   # valid args pass
        tools.update_invoice(u, s, invoice_id=b, fields={"profile": "ทริปหัวหิน"})
        assert tools.find_invoices(u, s)["count"] == 1
        tools.manage_profile(u, s, action="switch", name="ส่วนตัว")
        try:
            tools.manage_profile(u, s, action="switch", name="ไม่มีจริง")
            raise AssertionError("bad profile must raise")
        except tools.ToolError:
            pass

        # summarize + compare (money from SQL)
        t = tools.summarize_expenses(u, s, date_from="2026-08-01", date_to="2026-08-31", profile="all")
        assert t["total"] == 1915.0 and t["by_category"]["ที่พัก"] == 1850.0, t
        t2 = tools.summarize_expenses(u, s, date_from="2026-08-01", date_to="2026-08-31", profile="all",
                                      compare_to={"date_from": "2026-07-01", "date_to": "2026-07-31"})
        assert t2["compare_to"]["total"] == 180.0 and t2["compare_to"]["diff"] == 1735.0, t2

        # ontology (app/ontology.py): alias → category, subcategory filter, roll-down, rule over the model's guess
        assert tools.summarize_expenses(u, s, category="ค่าเดินทาง", profile="all")["total"] == 180.0
        assert tools.find_invoices(u, s, category="เรียกรถ", profile="all")["count"] == 1      # แท็กซี่ is_a เรียกรถ
        assert tools.find_invoices(u, s, category="ค่าน้ำมัน", profile="all")["count"] == 0
        assert tools.summarize_expenses(u, s, profile="all")["by_subcategory"]["เดินทาง › เรียกรถ"] == 180.0
        g = tools._make_draft(u, s, {"vendor": "Grab", "date": "2026-08-20", "total": 120, "vat": 0, "subtotal": 120,
                                     "category": "อาหาร"}, Path("/tmp/none.png"), None)
        assert g["category"] == "เดินทาง" and g["subcategory"] == "เรียกรถ", g        # model said อาหาร; the rule knows Grab

        # find by item / vendor / reimbursed
        assert tools.find_invoices(u, s, item="ลาเต้")["count"] == 1
        assert tools.find_invoices(u, s, vendor="กาแฟ")["count"] == 1
        tools.mark_reimbursed(u, s, invoice_ids=[a])
        assert tools.find_invoices(u, s, reimbursed=True)["count"] == 1
        tools.mark_reimbursed(u, s, invoice_ids=a, undo=True)
        assert tools.find_invoices(u, s, reimbursed=True)["count"] == 0

        # notes
        n = tools.remember_note(u, s, action="save", text="งบเดือนละ 5000")["saved"]
        assert len(tools.remember_note(u, s, action="list")["notes"]) == 1
        tools.remember_note(u, s, action="delete", note_id=n)
        assert tools.remember_note(u, s, action="list")["notes"] == []

        # categories: add, use, reject unknown, cap, rename cascades, default undeletable
        tools.manage_category(u, s, action="add", name="ค่าเลี้ยงลูกค้า")
        tools.update_invoice(u, s, invoice_id=a, fields={"category": "ค่าเลี้ยงลูกค้า"})
        try:
            tools.update_invoice(u, s, invoice_id=a, fields={"category": "ไม่มีหมวดนี้"})
            raise AssertionError("unknown category must raise")
        except tools.ToolError:
            pass
        tools.manage_category(u, s, action="rename", name="ค่าเลี้ยงลูกค้า", new_name="รับรองลูกค้า")
        assert s.get(Invoice, a).category == "รับรองลูกค้า"
        try:
            tools.manage_category(u, s, action="remove", name="อาหาร")
            raise AssertionError("default category must not be removable")
        except tools.ToolError:
            pass

        # split bill: assigned item + even share of the rest
        d = add(u, s, vendor="หมูกระทะ", total=1200.0, items=[{"name": "บุฟเฟ่ต์", "qty": 4, "price": 259}, {"name": "เบียร์", "qty": 2, "price": 79}])
        sp = tools.split_bill(u, s, invoice_id=d, people=["โบ๊ท", "นัท"], assignments={"เบียร์": "โบ๊ท"})
        assert abs(sum(sp["split"].values()) - 1200.0) < 0.05 and sp["split"]["โบ๊ท"] - sp["split"]["นัท"] == 158.0, sp

        # report + csv produce files; restore after delete; tax id checksum
        r = tools.generate_report(u, s, date_from="2026-01-01", date_to="2026-12-31", profile="all")
        assert Path(r["_file"]).exists() and r["count"] == 4
        cv = tools.export_csv(u, s, date_from="2026-01-01", date_to="2026-12-31", profile="all")
        assert Path(cv["_file"]).read_text(encoding="utf-8-sig").count("\n") == 5
        tools.delete_invoice(u, s, invoice_id=c)
        assert tools.find_invoices(u, s, profile="all")["count"] == 3
        tools.restore_invoice(u, s, invoice_id=c)
        assert tools.find_invoices(u, s, profile="all")["count"] == 4
        assert tools.valid_thai_tax_id("0105558123456") in (True, False) and tools.valid_thai_tax_id("1234567890120") is False
        assert tools.valid_thai_tax_id(None) is None
    # learned preferences: correcting a vendor's category/profile is remembered and applied to the next draft
    with session() as s:
        u = s.get(User, uid)
        x = add(u, s, vendor="ปั๊ม บางจาก สาขาร่มเกล้า", total=800.0, category="เดินทาง")
        r = tools.update_invoice(u, s, invoice_id=x, fields={"category": "อุปกรณ์"})
        assert r["learned"]["category"] == "อุปกรณ์", r
        pref = tools.get_pref(u, s, "ปั๊มบางจาก สาขาร่มเกล้า")  # spacing differences normalize to the same key
        assert pref and pref.category == "อุปกรณ์"
        tools.manage_profile(u, s, action="create", name="รถบริษัท")
        tools.update_invoice(u, s, invoice_id=x, fields={"profile": "รถบริษัท"})
        pref = tools.get_pref(u, s, "ปั๊มบางจาก สาขาร่มเกล้า")
        assert pref.profile_id == tools._profile_ids(u, s, "รถบริษัท")[0]
        d = tools._make_draft(u, s, {"vendor": "ปั๊มบางจาก สาขาร่มเกล้า", "date": "2026-09-01", "total": 500, "vat": 0, "subtotal": 500, "category": "เดินทาง"}, Path("/tmp/none.png"), None)
        assert d["category"] == "อุปกรณ์" and d["learned_from_past_corrections"]["profile"] == "รถบริษัท", d
    print("ALL W3 TOOL TESTS PASSED")


if __name__ == "__main__":
    main()
