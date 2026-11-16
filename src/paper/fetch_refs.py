"""fetch_refs.py - ambil metadata primer (Crossref / arXiv) ke sources/.
Tidak memakai hasil mesin pencari. python fetch_refs.py
"""
import json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources")
os.makedirs(SRC, exist_ok=True)
UA = {"User-Agent": "research-reference-check/1.0 (academic use)"}

DOIS = {
 "northcutt2021_confidentlearning": "10.1613/jair.1.12125",
 "frenay2014_labelnoise": "10.1109/TNNLS.2013.2292894",
 "song2023_noisylabels": "10.1109/TNNLS.2022.3152527",
 "geirhos2020_shortcut": "10.1038/s42256-020-00257-z",
 "kapoor2023_leakage": "10.1016/j.patter.2023.100804",
 "sommer2010_closedworld": "10.1109/SP.2010.25",
 "ahmad2018_5gsecurity": "10.1109/MCOMSTD.2018.1700063",
 "sharafaldin2018_cicids2017": "10.5220/0006639801080116",
 "moustafa2015_unswnb15": "10.1109/MilCIS.2015.7348942",
 "neto2023_ciciot2023": "10.3390/s23135941",
 "booij2022_toniot": "10.1109/JIOT.2021.3085194",
 "sarhan2022_standardfeature": "10.1007/s11036-021-01843-0",
 "virtanen2020_scipy": "10.1038/s41592-019-0686-2",
 "wilcoxon1945_ranking": "10.2307/3001968",
 "mcnemar1947_sampling": "10.1007/BF02295996",
 "lanvin2022_errors_cicids": "10.1007/978-3-031-31108-6_2",
 "flood2024_badsmells": "10.1109/EuroSP60621.2024.00042",
 "saranya2025_ibertroa": "10.1038/s41598-025-19156-7",
 "moubayed2024_eda_pipeline": "10.3390/fi16090331",
 "lassoued2026_supervised_5gnidd": "10.3390/computers15060362",
 "engelen2021_troubleshooting": "10.1109/SPW53761.2021.00009",
 "liu2022_errorprevalence": "10.1109/CNS56114.2022.9947235",
 "goldschmidt2025_survey": "10.1016/j.cose.2025.104510",
}
ARXIV = {
 "qu2025_tabicl": "2502.05564",
 "samarakoon2022_5gnidd": "2212.01298",
 "uccello2026_featureattr": "2509.10206",
 "ilias2024_cnnmoe": "2412.03483",
 "jerabek2025_simplemodel": "2506.08655",
 "galal2026_edgeiiotset": "2608.15761",
 "roy2026_shortcut": "2609.28725",
 "northcutt2021_labelerrors": "2103.14749",
 "arp2022_dosdonts": "2010.09470",
 "luay2025_temporal": "2503.04404",
 "chen2021_duplicates": "2105.10041",
}

def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 200:
        return True, "cache"
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            d = r.read()
        open(path, "wb").write(d)
        time.sleep(0.4)
        return True, "ok"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

rep = []
for k, doi in DOIS.items():
    ok, how = get("https://api.crossref.org/works/" + urllib.parse.quote(doi),
                  os.path.join(SRC, f"crossref_{k}.json"))
    rep.append((k, "crossref", doi, "OK" if ok else how, how))
    print(f"{k:38} crossref {doi:42} {'OK' if ok else how}", flush=True)
for k, aid in ARXIV.items():
    ok, how = get("https://export.arxiv.org/api/query?id_list=" + aid,
                  os.path.join(SRC, f"arxiv_{k}.xml"))
    print(f"{k:38} arxiv    {aid:42} {'OK' if ok else how}", flush=True)
json.dump({"dois": DOIS, "arxiv": ARXIV}, open(os.path.join(HERE, "sources_index.json"), "w"), indent=1)
