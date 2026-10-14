import urllib.request,time
hdr={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
u="https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202401689"
req=urllib.request.Request(u,headers=hdr)
with urllib.request.urlopen(req,timeout=60) as r:
    print("HEADERS:",dict(r.headers))
    print(r.read()[:2000].decode("utf-8","replace"))
print("="*60)
# CELLAR
for cu,acc in [("http://publications.europa.eu/resource/celex/32024R1689","application/xhtml+xml"),
               ("http://publications.europa.eu/resource/celex/32024R1689","text/html")]:
    try:
        req=urllib.request.Request(cu,headers={**hdr,"Accept":acc})
        with urllib.request.urlopen(req,timeout=90) as r:
            d=r.read()
            print(cu,acc,"status",r.status,"len",len(d))
            if len(d)>200000:
                open(r"H:\Hiive\ai_act_official.html","wb").write(d); print("saved")
                break
    except Exception as e:
        print(cu,acc,"ERR",type(e).__name__,e)
    time.sleep(2)
