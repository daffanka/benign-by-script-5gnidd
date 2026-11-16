"""prior_art_search.py — pencarian karya terdahulu untuk klaim kebaruan (S1b).

(i)  sitasi-maju makalah 5G-NIDD lewat OpenAlex (filter cites:<id>)
(ii) kueri kata kunci ke arXiv API dan Crossref
(iii) unduh paparan Khalil 2026 bila bisa

Semua respons mentah disimpan di sources/prior_art/. Tidak ada ringkasan mesin
pencari yang dipakai sebagai bukti.
python prior_art_search.py
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "sources", "prior_art")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "prior-art-check/1.0 (academic use; mailto:anonymous@example.org)"}
KEYWORDS = ["label", "mislabel", "mislabelled", "mislabeled", "error", "noise",
            "leakage", "shortcut", "duplicate", "audit", "quality", "artifact"]


def get(url, name, binary=False):
    p = os.path.join(OUT, name)
    if os.path.exists(p) and os.path.getsize(p) > 100:
        return open(p, "rb").read() if binary else open(p, encoding="utf-8").read()
    req = urllib.request.Request(url, headers=UA)
    d = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                d = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(20 * (attempt + 1))
                continue
            raise
    open(p, "wb").write(d)
    time.sleep(0.4)
    return d if binary else d.decode("utf-8", "replace")


def main():
    log = {"date": "2026-11-16", "queries": []}

    # ---------- (i) OpenAlex: temukan rekaman 5G-NIDD, lalu penyitasinya
    q1 = "https://api.openalex.org/works?filter=doi:10.48550/arxiv.2212.01298"
    try:
        d = json.loads(get(q1, "openalex_seed.json"))
        res = d.get("results", [])
    except Exception as e:
        res = []
        log["queries"].append({"q": q1, "error": str(e)})
    if not res:
        q1b = ("https://api.openalex.org/works?search="
               + urllib.parse.quote("5G-NIDD comprehensive network intrusion detection dataset"))
        d = json.loads(get(q1b, "openalex_seed_search.json"))
        res = d.get("results", [])
        log["queries"].append({"q": q1b, "n": len(res)})
    else:
        log["queries"].append({"q": q1, "n": len(res)})
    seed = None
    for w in res:
        if "5g-nidd" in (w.get("title") or "").lower():
            seed = w
            break
    if seed is None and res:
        seed = res[0]
    log["seed"] = {"id": seed.get("id"), "title": seed.get("title"),
                   "cited_by_count": seed.get("cited_by_count"),
                   "doi": seed.get("doi")} if seed else None
    print("seed:", log["seed"])

    citers = []
    if seed:
        sid = seed["id"].rsplit("/", 1)[-1]
        page, cursor = 0, "*"
        while True:
            q = (f"https://api.openalex.org/works?filter=cites:{sid}"
                 f"&per-page=200&cursor={cursor}")
            d = json.loads(get(q, f"openalex_citers_{page}.json"))
            citers += d.get("results", [])
            cursor = d.get("meta", {}).get("next_cursor")
            page += 1
            log["queries"].append({"q": q, "n": len(d.get("results", []))})
            if not cursor or page > 12 or not d.get("results"):
                break
    log["n_citers"] = len(citers)
    print("penyitasi:", len(citers))

    def inv_abs(w):
        inv = w.get("abstract_inverted_index") or {}
        if not inv:
            return ""
        pos = {}
        for word, idxs in inv.items():
            for i in idxs:
                pos[i] = word
        return " ".join(pos[k] for k in sorted(pos))

    flagged = []
    for w in citers:
        txt = ((w.get("title") or "") + " " + inv_abs(w)).lower()
        hit = sorted({k for k in KEYWORDS if re.search(rf"\b{k}", txt)})
        if hit:
            flagged.append({"id": w.get("id"), "title": w.get("title"),
                            "year": w.get("publication_year"),
                            "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
                            "doi": w.get("doi"), "keywords_hit": hit,
                            "abstract_present": bool(inv_abs(w))})
    log["n_flagged"] = len(flagged)
    log["flagged"] = flagged
    json.dump({"citers": [{"id": w.get("id"), "title": w.get("title"),
                           "year": w.get("publication_year"), "doi": w.get("doi")}
                          for w in citers]},
              open(os.path.join(OUT, "citers_list.json"), "w", encoding="utf-8"), indent=1)
    print("lolos saringan kata kunci:", len(flagged))

    # ---------- (ii) kueri kata kunci
    ax = ('https://export.arxiv.org/api/query?search_query='
          + urllib.parse.quote('all:"5G-NIDD"') + "&max_results=100")
    t = get(ax, "arxiv_5gnidd.xml")
    n_ax = len(re.findall(r"<entry>", t))
    log["queries"].append({"q": ax, "n": n_ax})
    print("arXiv all:\"5G-NIDD\":", n_ax, "entri")
    ax_titles = [re.sub(r"\s+", " ", x).strip()
                 for x in re.findall(r"<entry>.*?<title>(.*?)</title>", t, re.S)]
    ax_abs = re.findall(r"<summary>(.*?)</summary>", t, re.S)
    ax_flag = []
    for ti, ab in zip(ax_titles, ax_abs + [""] * len(ax_titles)):
        low = (ti + " " + ab).lower()
        hit = sorted({k for k in KEYWORDS if re.search(rf"\b{k}", low)})
        if hit:
            ax_flag.append({"title": ti, "keywords_hit": hit})
    log["arxiv_flagged"] = ax_flag
    print("arXiv lolos saringan:", len(ax_flag))

    cr = ("https://api.crossref.org/works?rows=100&query.bibliographic="
          + urllib.parse.quote("5G-NIDD label error leakage shortcut duplicate audit quality"))
    d = json.loads(get(cr, "crossref_5gnidd_keywords.json"))["message"]
    log["queries"].append({"q": cr, "total_results": d.get("total-results"),
                           "rows_returned": len(d.get("items", []))})
    cr_flag = []
    for it in d.get("items", []):
        ti = (it.get("title") or [""])[0]
        if "5g-nidd" in ti.lower() or "5g nidd" in ti.lower():
            cr_flag.append({"title": ti, "doi": it.get("DOI"),
                            "year": (it.get("issued", {}).get("date-parts", [[None]])[0] or [None])[0]})
    log["crossref_title_hits"] = cr_flag
    print("Crossref judul memuat 5G-NIDD:", len(cr_flag))

    # ---------- (iii) paparan Khalil
    url = ("https://sola.kau.se/swits/wp-content/uploads/sites/257/2026/06/"
           "2026_Karim_Khalil.pdf")
    try:
        raw = get(url, "khalil2026.pdf", binary=True)
        log["khalil"] = {"url": url, "bytes": len(raw), "status": "downloaded"}
        print("Khalil PDF:", len(raw), "byte")
    except Exception as e:
        log["khalil"] = {"url": url, "status": f"FAILED {type(e).__name__}: {e}"}
        print("Khalil PDF GAGAL:", e)

    json.dump(log, open(os.path.join(HERE, "prior_art_log.json"), "w", encoding="utf-8"),
              indent=1)
    print("tulis prior_art_log.json")


if __name__ == "__main__":
    main()
