"""fetch_abstracts.py - ambil abstrak dari sumber PRIMER (repositori penulis,
HAL, arXiv, penerbit terbuka). Hanya mengunduh; tidak menjalankan apa pun."""
import os, time, urllib.request
HERE=os.path.dirname(os.path.abspath(__file__)); SRC=os.path.join(HERE,"sources")
UA={"User-Agent":"Mozilla/5.0 (research reference check; academic use)"}
T={
 "engelen2021_troubleshooting":"https://lirias.kuleuven.be/retrieve/713070",
 "flood2024_badsmells":"https://detlearsom.github.io/pubs/BadSmells-EuroSP24-finaldraft.pdf",
 "lanvin2022_errors_cicids":"https://hal.science/hal-03775466",
 "sommer2010_closedworld":"https://www.icir.org/vern/papers/anomaly-detection.oakland10.pdf",
 "sarhan2022_standardfeature":"https://export.arxiv.org/api/query?id_list=2011.09144",
 "geirhos2020_shortcut":"https://export.arxiv.org/api/query?id_list=2004.07780",
 "song2023_noisylabels":"https://export.arxiv.org/api/query?id_list=2007.08199",
 "kapoor2023_leakage":"https://export.arxiv.org/api/query?id_list=2207.07048",
 "frenay2014_labelnoise":"https://export.arxiv.org/api/query?id_list=1902.00232",
}
for k,u in T.items():
    ext=".xml" if "arxiv" in u else (".pdf" if u.endswith(".pdf") else ".html")
    p=os.path.join(SRC,f"primary_{k}{ext}")
    if os.path.exists(p) and os.path.getsize(p)>500: print(k,"cache"); continue
    try:
        with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=40) as r:
            d=r.read()
        open(p,"wb").write(d); print(f"{k:34} OK {len(d)} byte -> {os.path.basename(p)}")
        time.sleep(0.5)
    except Exception as e:
        print(f"{k:34} GAGAL {type(e).__name__}: {str(e)[:70]}")
