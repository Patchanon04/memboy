"""Keyword ontology vs embedding vs Gemma — vendor name → category, on names the keywords were NOT written from.

Names: eval/ontology_names.json if it exists (written by a person who has not read app/ontology.py), else Gemma is asked
to invent them (it has never seen our keyword list → blind to the rule; but they are AI-invented, not real shops).
Embedding: bge-m3 on the same Ollama server (OpenAI-standard /v1/embeddings); every keyword + subcategory name is a labelled point, a vendor goes to the category of
its most similar point (kNN, k=1). Embedding only "claims" a name above a similarity threshold, like the keyword rule.

    python -m eval.eval_embedding   (inside the app container)   → eval/logs/EMBEDDING.md"""
import asyncio
import json
import os
import re
from pathlib import Path

import httpx
import numpy as np

from app import ontology

from app import llm

EMB = os.environ.get("EMBED_MODEL", "bge-m3")
GEN = llm.MODEL
EVAL = Path("/srv/eval")
CATS = list(ontology.TREE)
HUMAN = EVAL / "ontology_names.json"
INVENTED = EVAL / "ontology_names_llm.json"


async def gen(c, prompt, temperature):
    return await llm.generate([{"role": "user", "parts": [{"text": prompt}]}], temperature=temperature)


def json_in(text):
    return json.loads(re.search(r"[\[{].*[\]}]", text, re.S).group(0))


async def invent_names(c):
    """Gemma writes realistic receipt-header shop names per category. It never saw app/ontology.py."""
    hints = {"อาหาร": "ร้านอาหาร คาเฟ่ ร้านข้าว ร้านขนม เดลิเวอรี", "เดินทาง": "ปั๊มน้ำมัน แท็กซี่ รถโดยสาร สายการบิน ทางด่วน ที่จอดรถ",
             "ที่พัก": "โรงแรม รีสอร์ท โฮสเทล หอพักรายวัน แพลตฟอร์มจองที่พัก", "อุปกรณ์": "ร้านไอที ร้านเครื่องเขียน ร้านถ่ายเอกสาร ร้านวัสดุก่อสร้าง ร้านอะไหล่",
             "สุขภาพ": "ร้านยา คลินิก โรงพยาบาล ร้านนวด สปา ฟิตเนส", "ของใช้": "ซูเปอร์มาร์เก็ต มินิมาร์ท ร้านโชห่วย ตลาด ร้านของใช้ในบ้าน"}
    out = []
    for cat in CATS:
        text = await gen(c, f"เขียนชื่อร้านค้าในประเทศไทยที่พิมพ์อยู่หัวใบเสร็จ 20 ชื่อ หมวด '{cat}' ({hints[cat]}). "
                            "ผสมร้านเล็กท้องถิ่นและเครือใหญ่ ภาษาไทยและอังกฤษ ไม่ซ้ำกัน ห้ามมีคำอธิบาย "
                            'ตอบเป็น JSON array ของ string อย่างเดียว', 0.9)
        out += [{"vendor": n.strip(), "category": cat} for n in json_in(text) if isinstance(n, str) and n.strip()]
    seen, uniq = set(), []
    for r in out:
        if r["vendor"].lower() not in seen:
            seen.add(r["vendor"].lower())
            uniq.append(r)
    INVENTED.write_text(json.dumps(uniq, ensure_ascii=False, indent=1), encoding="utf-8")
    return uniq


async def embed(c, texts):
    vecs = []
    for i in range(0, len(texts), 50):
        r = await c.post(f"{llm.BASE_URL}/embeddings", headers={"Authorization": f"Bearer {llm.API_KEY}"} if llm.API_KEY else {},
                         json={"model": EMB, "input": texts[i:i + 50]})
        if r.status_code != 200:
            raise RuntimeError(f"embedding http {r.status_code}")
        vecs += [e["embedding"] for e in sorted(r.json()["data"], key=lambda e: e["index"])]
    m = np.array(vecs, dtype=np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


async def llm_classify(c, names):
    out = {}
    for i in range(0, len(names), 30):
        chunk = names[i:i + 30]
        text = await gen(c, "จัดหมวดค่าใช้จ่ายของแต่ละร้านจากชื่อร้านในใบเสร็จ เลือกจาก " + ", ".join(CATS) +
                            ' ตอบ JSON object {"ชื่อร้าน": "หมวด"} อย่างเดียว\n' + "\n".join(chunk), 0.0)
        got = json_in(text)
        out.update({n: got.get(n) for n in chunk})
    return out


async def main():
    async with httpx.AsyncClient(timeout=300) as c:
        rows = json.loads(HUMAN.read_text(encoding="utf-8")) if HUMAN.exists() else (
            json.loads(INVENTED.read_text(encoding="utf-8")) if INVENTED.exists() else await invent_names(c))
        source = "written by a person who has not read ontology.py" if HUMAN.exists() else f"invented by {GEN} (never saw the keywords)"
        names = [r["vendor"] for r in rows]
        gold = [r["category"] for r in rows]

        points = [(kw, ontology.PARENT[sub]) for subs in ontology.TREE.values() for sub, kws in subs.items() for kw in kws]
        points += [(sub, cat) for cat, subs in ontology.TREE.items() for sub in subs]
        P = await embed(c, [p[0] for p in points])
        V = await embed(c, names)
        sim = V @ P.T
        best = sim.argmax(1)
        emb_cat = [points[j][1] for j in best]
        emb_sim = sim.max(1)
        cls = await llm_classify(c, names)

    n = len(rows)
    kw = [ontology.classify(x) for x in names]
    kw_claim = [i for i in range(n) if kw[i]]
    kw_right = sum(kw[i][0] == gold[i] for i in kw_claim)
    emb_right_all = sum(emb_cat[i] == gold[i] for i in range(n))
    llm_right = sum(cls.get(names[i]) == gold[i] for i in range(n))
    # the systems as they would run: keyword first, then the fallback for names the keywords don't know
    sys_now = sum((kw[i][0] if kw[i] else cls.get(names[i])) == gold[i] for i in range(n))
    sys_emb = sum((kw[i][0] if kw[i] else emb_cat[i]) == gold[i] for i in range(n))
    curve = []
    for t in (0.60, 0.65, 0.70, 0.75, 0.80):
        claim = [i for i in range(n) if emb_sim[i] >= t]
        curve.append(f"| {t:.2f} | {len(claim)}/{n} | {sum(emb_cat[i] == gold[i] for i in claim)}/{len(claim) or 1} |")
    miss = [i for i in range(n) if not kw[i]]
    lines = ["# Keyword vs embedding vs Gemma — vendor name → category", "",
             f"{n} names, {source}. Category only (6 classes), name only (no image).", "",
             "| method | coverage | correct |", "|---|---|---|",
             f"| keyword ontology (current) | {len(kw_claim)}/{n} | {kw_right}/{len(kw_claim)} of those it claims |",
             f"| embedding kNN ({EMB}) | {n}/{n} | {emb_right_all}/{n} |",
             f"| Gemma picks the category | {n}/{n} | {llm_right}/{n} |",
             f"| **keyword → Gemma (what runs now)** | {n}/{n} | **{sys_now}/{n}** |",
             f"| **keyword → embedding** | {n}/{n} | **{sys_emb}/{n}** |", "",
             f"On the {len(miss)} names the keywords don't know: Gemma {sum(cls.get(names[i]) == gold[i] for i in miss)}/{len(miss)} · "
             f"embedding {sum(emb_cat[i] == gold[i] for i in miss)}/{len(miss)}", "",
             "Embedding with a similarity threshold (claim only when sure):", "", "| threshold | claimed | correct |", "|---|---|---|",
             *curve, "", "Wrong answers (name: gold | keyword | embedding | gemma):"]
    for i in range(n):
        k = kw[i][0] if kw[i] else "-"
        if (kw[i] and k != gold[i]) or emb_cat[i] != gold[i] or cls.get(names[i]) != gold[i]:
            lines.append(f"- {names[i]}: {gold[i]} | {k} | {emb_cat[i]} ({emb_sim[i]:.2f}) | {cls.get(names[i])}")
    (EVAL / "logs" / "EMBEDDING.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    asyncio.run(main())
