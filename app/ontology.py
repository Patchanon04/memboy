"""Expense ontology — what the bot knows about spending, written down instead of left to the model's guess.

Three relations, shared by extraction, queries and reports:

  is_a         subcategory ⊂ category                ("เรียกรถ" is_a "เดินทาง")
  instance_of  vendor-name keyword → subcategory     ("บางจาก" → "เชื้อเพลิง")
  alias        what people say → a node              ("ค่าน้ำมัน" → "เชื้อเพลิง")

What it buys:
- "ค่าเดินทางเดือนนี้" rolls up Grab + ปั๊ม + BTS without the model listing them (alias → category).
- "ค่าน้ำมันเท่าไหร่" filters a subcategory that is not a stored column (instance_of over the vendor).
- a vendor the keywords know is classified by rule, not by the model's guess (beats the LLM on misread names).

ponytail: plain dicts, not OWL/RDF — the bot needs roll-up, lookup and synonyms, not a reasoner. Keyword match is the
instance_of test; swap for embedding lookup only if vendors outgrow keywords. Top-level categories match
tools.CATS_DEFAULT on purpose: stored invoices keep one category, the subcategory is derived (no schema change)."""
import re

TREE: dict[str, dict[str, list[str]]] = {
    "อาหาร": {
        "คาเฟ่": ["กาแฟ", "คาเฟ่", "coffee", "café", "cafe", "starbucks", "bakery", "เบเกอรี่"],
        "ร้านอาหาร": ["ก๋วยเตี๋ยว", "ข้าวแกง", "ข้าวมันไก่", "ข้าวขาหมู", "ข้าวต้ม", "ร้านข้าว", "ครัว", "ส้มตำ",
                      "หมูทอด", "หมูกระทะ", "โจ๊ก", "ชาบู", "บุฟเฟ่ต์", "ภัตตาคาร", "noodle", "burger", "pizza",
                      "restaurant", "kitchen", "salad", "grill", "sushi", "ramen", "kfc", "mcdonald"],
        "เดลิเวอรี": ["grabfood", "grab food", "lineman", "line man", "foodpanda", "robinhood"],
    },
    "เดินทาง": {
        "เชื้อเพลิง": ["ปั๊ม", "บางจาก", "ปตท", "เชลล์", "คาลเท็กซ์", "น้ำมันเชื้อเพลิง", "bangchak", "ptt", "shell",
                       "esso", "caltex", "susco", "fuel", "gas station"],
        "เรียกรถ": ["แท็กซี่", "วินมอเตอร์ไซค์", "มอเตอร์ไซค์รับจ้าง", "taxi", "cab", "grab", "bolt"],
        "ขนส่งสาธารณะ": ["รถไฟฟ้า", "รถไฟ", "รถตู้", "รถเมล์", "ขสมก", "บขส", "เรือด่วน", "ท่าเรือ", "bts", "mrt",
                         "airport rail", "railway", "ferry", "bus"],
        "ตั๋วเครื่องบิน": ["การบินไทย", "นกแอร์", "สายการบิน", "airasia", "air asia", "thai airways", "nok air",
                           "lion air", "airline", "airways"],
        "ทางด่วน/ที่จอดรถ": ["ทางด่วน", "ที่จอดรถ", "easy pass", "m-flow", "parking"],
    },
    "ที่พัก": {
        "โรงแรม/ที่พัก": ["โรงแรม", "รีสอร์ท", "โฮสเทล", "เกสต์เฮาส์", "hotel", "resort", "hostel", "guesthouse",
                          "agoda", "booking.com", "airbnb"],
    },
    "อุปกรณ์": {
        "ไอที": ["ไอที", "คอมพิวเตอร์", "it city", "advice", "banana", "jib", "power buy", "gadget", "tech", "computer"],
        "เครื่องเขียน/สิ่งพิมพ์": ["เครื่องเขียน", "ถ่ายเอกสาร", "ศึกษาภัณฑ์", "office", "print", "stationery", "copy",
                                   "b2s", "officemate"],
        "อะไหล่/เครื่องมือ": ["อะไหล่", "ฮาร์ดแวร์", "เครื่องมือช่าง", "โฮมโปร", "ไทวัสดุ", "hardware", "homepro",
                              "global house"],
    },
    "สุขภาพ": {
        "ร้านยา": ["ร้านยา", "ฟาร์มาซี", "เภสัช", "pharmacy", "boots", "watsons"],
        "โรงพยาบาล/คลินิก": ["โรงพยาบาล", "คลินิก", "ทันตกรรม", "hospital", "clinic", "dental"],
        "สปา/นวด": ["สปา", "นวด", "spa", "massage"],
    },
    "ของใช้": {
        "ซูเปอร์มาร์เก็ต/มินิมาร์ท": ["ซุปเปอร์", "ซูเปอร์", "มินิมาร์ท", "โลตัส", "บิ๊กซี", "แม็คโคร", "เซเว่น",
                                      "supermarket", "minimart", "mini mart", "lotus", "big c", "tops", "makro",
                                      "7-eleven", "family mart", "cj more"],
        "ตลาด": ["ตลาดสด", "ตลาดนัด", "ตลาดน้ำ"],
        "ร้านทุกอย่าง": ["ยี่สิบบาท", "20 บาท", "ร้านทุกอย่าง", "daiso", "ไดโซะ", "moshi"],
    },
}

ALIAS = {
    "ค่าอาหาร": "อาหาร", "ค่ากิน": "อาหาร", "ของกิน": "อาหาร", "food": "อาหาร", "meal": "อาหาร",
    "กาแฟ": "คาเฟ่", "ค่ากาแฟ": "คาเฟ่", "coffee": "คาเฟ่",
    "ค่าเดินทาง": "เดินทาง", "ค่ารถ": "เดินทาง", "travel": "เดินทาง", "transport": "เดินทาง",
    "transportation": "เดินทาง",
    "ค่าน้ำมัน": "เชื้อเพลิง", "น้ำมัน": "เชื้อเพลิง", "fuel": "เชื้อเพลิง", "gas": "เชื้อเพลิง",
    "แท็กซี่": "เรียกรถ", "ค่าแท็กซี่": "เรียกรถ", "taxi": "เรียกรถ", "grab": "เรียกรถ",
    "รถไฟฟ้า": "ขนส่งสาธารณะ", "bts": "ขนส่งสาธารณะ", "mrt": "ขนส่งสาธารณะ",
    "ค่าตั๋วเครื่องบิน": "ตั๋วเครื่องบิน", "เครื่องบิน": "ตั๋วเครื่องบิน", "flight": "ตั๋วเครื่องบิน",
    "ค่าทางด่วน": "ทางด่วน/ที่จอดรถ", "ค่าที่จอดรถ": "ทางด่วน/ที่จอดรถ",
    "ค่าที่พัก": "ที่พัก", "ค่าโรงแรม": "ที่พัก", "โรงแรม": "ที่พัก", "hotel": "ที่พัก", "accommodation": "ที่พัก",
    "ค่ายา": "ร้านยา", "ยา": "ร้านยา",
    "ค่าหมอ": "โรงพยาบาล/คลินิก", "ค่ารักษา": "โรงพยาบาล/คลินิก", "ค่ารักษาพยาบาล": "โรงพยาบาล/คลินิก",
    "medical": "สุขภาพ", "health": "สุขภาพ",
    "เครื่องเขียน": "เครื่องเขียน/สิ่งพิมพ์", "ค่าถ่ายเอกสาร": "เครื่องเขียน/สิ่งพิมพ์", "ไอที": "ไอที",
    "equipment": "อุปกรณ์", "ของใช้ในบ้าน": "ของใช้", "supplies": "ของใช้",
    "ซูเปอร์": "ซูเปอร์มาร์เก็ต/มินิมาร์ท", "ซุปเปอร์": "ซูเปอร์มาร์เก็ต/มินิมาร์ท",
}

PARENT = {sub: cat for cat, subs in TREE.items() for sub in subs}
_KEYWORDS = sorted(((kw.lower(), sub) for subs in TREE.values() for sub, kws in subs.items() for kw in kws),
                   key=lambda t: -len(t[0]))  # longest first: "grabfood" must beat "grab", "ก๋วยเตี๋ยว" beat "เรือ"


def _hit(kw: str, text: str) -> bool:
    if re.search(r"[a-z0-9]", kw):  # Latin needs word edges ("cab" ≠ "cabinet"); Thai has none, substring it is
        return re.search(rf"(?<![a-z]){re.escape(kw)}(?![a-z])", text) is not None
    return kw in text


def sub_of(vendor: str | None) -> str | None:
    """instance_of: the subcategory a vendor name belongs to, or None when no keyword knows it."""
    text = (vendor or "").lower()
    return next((sub for kw, sub in _KEYWORDS if _hit(kw, text)), None) if text else None


def classify(vendor: str | None) -> tuple[str, str] | None:
    sub = sub_of(vendor)
    return (PARENT[sub], sub) if sub else None


def sub_within(vendor: str | None, category: str | None) -> str | None:
    """The subcategory only when it agrees with the stored category (a user correction can move a vendor elsewhere;
    then we don't claim "อาหาร › เชื้อเพลิง")."""
    sub = sub_of(vendor)
    return sub if sub and PARENT[sub] == category else None


def resolve(term: str | None) -> tuple[str, str | None] | None:
    """A word the user or the model used for a category filter → (category, subcategory|None). None = not ours
    (a custom category, compared as-is)."""
    t = (term or "").strip()
    for _ in range(3):  # alias → alias → node, never deeper
        if t in TREE:
            return t, None
        if t in PARENT:
            return PARENT[t], t
        t = ALIAS.get(t, ALIAS.get(t.lower(), ""))
        if not t:
            return None
    return None


def describe() -> str:
    """One line for the system prompt: the tree the category filter understands."""
    return " · ".join(f"{cat}({', '.join(subs)})" for cat, subs in TREE.items())


if __name__ == "__main__":  # the relations the queries depend on
    assert classify("Grab") == ("เดินทาง", "เรียกรถ")
    assert classify("GrabFood เดลิเวอรี") == ("อาหาร", "เดลิเวอรี")       # longest keyword wins
    assert classify("ก๋วยเตี๋ยวเรือรุ่งเรือง") == ("อาหาร", "ร้านอาหาร")   # not a boat
    assert classify("ปั๊มบางจาก สาขาร่มเกล้า") == ("เดินทาง", "เชื้อเพลิง")
    assert classify("Metro Fuel Station") == ("เดินทาง", "เชื้อเพลิง")
    assert classify("Cabinet Furniture") is None                           # word edge: cab ≠ cabinet
    assert classify("ร้านลุงสมชาย") is None                                 # unknown stays unknown → LLM decides
    assert sub_within("Grab", "เดินทาง") == "เรียกรถ" and sub_within("Grab", "อาหาร") is None
    assert resolve("ค่าเดินทาง") == ("เดินทาง", None)
    assert resolve("ค่าน้ำมัน") == ("เดินทาง", "เชื้อเพลิง")
    assert resolve("เรียกรถ") == ("เดินทาง", "เรียกรถ")
    assert resolve("Hotel") == ("ที่พัก", None)
    assert resolve("หมวดที่ user สร้างเอง") is None
    assert all(PARENT[s] in TREE for s in PARENT) and all(resolve(a) for a in ALIAS), "every alias must land on a node"
    print("ontology ok:", len(TREE), "categories,", len(PARENT), "subcategories,", len(_KEYWORDS), "keywords,",
          len(ALIAS), "aliases")
