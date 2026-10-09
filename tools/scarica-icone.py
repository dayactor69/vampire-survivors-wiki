#!/usr/bin/env python3
"""Scarica in icons/ gli sprite di armi, passivi ed evoluzioni usati da index.html.

Fonte: Vampire Survivors Wiki (https://vampire.survivors.wiki), pagina /w/Evolution
e immagini /images/Sprite-<Nome>.png. Rispetta robots.txt (verificato: /images/ e
/w/Evolution non sono vietati per User-agent: *), una richiesta alla volta con pausa.

Uso:  python3 tools/scarica-icone.py          (dalla radice del repo)
Ogni file e' salvato come icons/<slug>.png, dove <slug> e' slug(nome) come in index.html:
minuscolo, senza accenti, caratteri non alfanumerici sostituiti da "-".
Alla fine stampa la riga "var IC=..." da incollare in index.html e l'elenco dei mancanti.
"""
import json, re, subprocess, sys, time, unicodedata, urllib.parse, urllib.request, urllib.robotparser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://vampire.survivors.wiki"
UA = "vs-wiki-icons/1.0 (script una tantum per mini-wiki non ufficiale; igor.riefoli@gmail.com)"
PAUSA = 1.0  # secondi tra una richiesta e l'altra

# Nome nel nostro dataset -> nome del file sul wiki (senza "Sprite-" e ".png"), solo dove non coincide.
# (il confronto ignora maiuscole, accenti e punteggiatura, quindi es. Tirajisu/Carrello/Carréllo si risolvono da soli;
# aggiungi qui solo i nomi che il wiki scrive in modo davvero diverso)
ALIAS = {}


def slug(n):
    n = unicodedata.normalize("NFD", n)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")


def chiave(n):
    return re.sub(r"[^a-z0-9]", "", slug(n))


def nomi_dataset():
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    m = re.search(r"(var BASE=.*?var D=\[.*?\n\];)", src, re.S)
    js = m.group(1) + "\nconsole.log(JSON.stringify(D))"
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout
    nomi = set()
    for exp, tipo, ris, ric, *_ in json.loads(out):
        nomi.add(ris)
        for p in ric.split(" + "):
            p = re.sub(r"\s*\([^)]*\)", "", p).strip()
            if re.search(r"forziere|passivi|evoluzioni", p, re.I):
                continue
            nomi.add(p)
    return sorted(nomi)


rp = urllib.robotparser.RobotFileParser()
rp.parse(urllib.request.urlopen(urllib.request.Request(BASE + "/robots.txt", headers={"User-Agent": UA}), timeout=30)
         .read().decode("utf-8").splitlines())


def get(url):
    if not rp.can_fetch(UA, url):
        raise SystemExit("robots.txt vieta " + url)
    time.sleep(PAUSA)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=30).read()


def main():
    nomi = nomi_dataset()
    html = get(BASE + "/w/Evolution").decode("utf-8")
    sul_wiki = {}  # chiave normalizzata -> nome file (decodificato, con underscore)
    for f in set(re.findall(r"/images/(?:thumb/)?Sprite-([^\"?/ ]+?)\.png", html)):
        f = urllib.parse.unquote(f)
        sul_wiki.setdefault(chiave(f), f)
    (ROOT / "icons").mkdir(exist_ok=True)
    trovati, mancanti = [], []
    for n in nomi:
        f = ALIAS.get(n) or sul_wiki.get(chiave(n))
        dest = ROOT / "icons" / (slug(n) + ".png")
        if not f:
            f = n.replace(" ", "_")  # ultimo tentativo: indirizzo diretto
        url = BASE + "/images/Sprite-" + urllib.parse.quote(f.replace(" ", "_"), safe="_-") + ".png"
        try:
            dati = dest.read_bytes() if dest.exists() else get(url)
            if not dati.startswith(b"\x89PNG"):
                raise ValueError("non e' un PNG")
            dest.write_bytes(dati)
            trovati.append(slug(n))
        except Exception as e:
            print("MANCA %-35s %s (%s)" % (n, url, e), file=sys.stderr)
            mancanti.append(n)
    print("\nTrovate %d/%d icone" % (len(trovati), len(nomi)))
    print("Mancanti (%d): %s" % (len(mancanti), ", ".join(mancanti)))
    print('\nvar IC="%s".split(" ");' % " ".join(sorted(trovati)))


main()
