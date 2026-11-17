"""Item catalog search (PR3) — id / name / kind, light VN normalization."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from ktt112026.game.content.loader import catalog_by_id

KIND_LABEL = {
    "danduoc": "Đan dược",
    "linhthu": "Linh thú",
    "congphap": "Công pháp",
    "vukhi": "Vũ khí",
    "phapbao": "Pháp bảo",
    "herb": "Linh thảo",
}


def strip_accents(text: str) -> str:
    s = unicodedata.normalize("NFD", text or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def norm(text: str) -> str:
    t = strip_accents(str(text).lower().strip())
    t = re.sub(r"\s+", " ", t)
    return t


def search_items(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    cat = catalog_by_id()
    qn = norm(q)
    # exact id
    if q.lower() in cat:
        return [cat[q.lower()]]
    scored: list[tuple[int, dict[str, Any]]] = []
    for iid, it in cat.items():
        name = str(it.get("name") or "")
        kind = str(it.get("kind") or "")
        nn = norm(name)
        ni = norm(iid)
        score = 0
        if qn == ni or qn == nn:
            score = 100
        elif qn in ni:
            score = 80
        elif qn in nn:
            score = 70
        elif ni.startswith(qn) or nn.startswith(qn):
            score = 60
        else:
            # token overlap
            tokens = [t for t in qn.split(" ") if t]
            if tokens and all(t in nn or t in ni for t in tokens):
                score = 50
        if score:
            # mild boost if kind keyword
            if qn in KIND_LABEL or qn in norm(KIND_LABEL.get(kind, "")):
                score += 5
            row = dict(it)
            row["_score"] = score
            scored.append((score, row))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("name") or "")))
    return [r for _, r in scored[: max(1, min(20, limit))]]


def format_item_brief(it: dict[str, Any]) -> str:
    kind = KIND_LABEL.get(str(it.get("kind") or ""), str(it.get("kind") or "?"))
    name = str(it.get("name") or it.get("id"))
    iid = str(it.get("id") or "")
    price = it.get("price")
    price_s = f" · giá {price}" if price not in (None, "") else ""
    desc = str(it.get("desc") or "").strip()
    if len(desc) > 60:
        desc = desc[:57] + "…"
    desc_s = f" — {desc}" if desc else ""
    return f"`{iid}` **{name}** [{kind}]{price_s}{desc_s}"
