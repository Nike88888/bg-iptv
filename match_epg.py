#!/usr/bin/env python3
"""
Сверява tvg-id в iptv-org M3U с channel id от open-epg XML и записва нов M3U.

Употреба:
  python match_epg.py
  python match_epg.py --m3u bg.m3u --epg bulgaria2.xml --out bg_epg.m3u
(--m3u и --epg приемат URL или локален файл)
"""
import argparse, difflib, re, sys, urllib.request
import xml.etree.ElementTree as ET

M3U_URL = "https://iptv-org.github.io/iptv/countries/bg.m3u"
EPG_URL = "https://www.open-epg.com/files/bulgaria2.xml"

# Ръчни съответствия (tvg-id от плейлиста -> channel id от EPG),
# за канали, чиито имена се различават твърде много
ALIASES = {
    "CineStarActionBulgaria.bg@SD": "CineStar A&T HD.bg",
    "DisneyChannel.bg@SD": "Disney.bg",
    "H2.bg@SD": "History 2.bg",
    "NationalGeographic.bg@SD": "Nat Geo HD.bg",
    "NationalGeographicWild.bg@SD": "NG Wild HD.bg",
    "TV1000.bg@SD": "TV 1000.bg",
    "DiscoveryChannel.bg@SD": "Discovery HD.bg",
    "HitMixMusic.bg@SD": "Hit Mix HD.bg",
}

CYR = dict(zip("абвгдежзийклмнопрстуфхцчшщъьюя",
               ["a","b","v","g","d","e","zh","z","i","y","k","l","m","n","o","p",
                "r","s","t","u","f","h","c","ch","sh","sht","a","","yu","ya"]))


def read(src):
    if src.startswith("http"):
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=60).read()
    return open(src, "rb").read()


def norm(s):
    s = s.lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", " ", s)          # (1080p), [Not 24/7]
    s = s.split("@")[0]                              # BNT1.bg@SD -> bnt1.bg
    s = re.sub(r"\.(bg|bgr)$", "", s)
    s = "".join(CYR.get(c, c) for c in s)
    s = re.sub(r"\b(hd|sd|fhd|uhd|tv|bg|bulgaria)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def load_epg(src):
    root = ET.fromstring(read(src))
    index = {}                                       # norm name -> epg id
    for ch in root.iter("channel"):
        cid = ch.get("id")
        names = [cid] + [d.text for d in ch.findall("display-name") if d.text]
        for n in names:
            k = norm(n)
            if k:
                index.setdefault(k, cid)
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m3u", default=M3U_URL)
    ap.add_argument("--epg", default=EPG_URL)
    ap.add_argument("--out", default="bg_epg.m3u")
    a = ap.parse_args()

    index = load_epg(a.epg)
    keys = list(index)
    valid_ids = set(index.values())
    lines = read(a.m3u).decode("utf-8", "replace").splitlines()
    out, matched, missed = [], 0, []

    for line in lines:
        if line.startswith("#EXTM3U"):
            out.append(f'#EXTM3U url-tvg="{a.epg}"')
            continue
        if line.startswith("#EXTINF"):
            m = re.search(r'tvg-id="([^"]*)"', line)
            tid = m.group(1) if m else ""
            title = line.rsplit(",", 1)[-1]
            hit = ALIASES.get(tid) if ALIASES.get(tid) in valid_ids else None
            for cand in (norm(tid), norm(title)):
                if hit:
                    break
                if cand and cand in index:
                    hit = index[cand]
                    break
            if not hit:
                for cand in (norm(tid), norm(title)):
                    close = difflib.get_close_matches(cand, keys, n=1, cutoff=0.9)
                    if close:
                        hit = index[close[0]]
                        break
            if hit:
                matched += 1
                if m:
                    line = line.replace(m.group(0), f'tvg-id="{hit}"')
                else:
                    line = line.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-id="{hit}"', 1)
            else:
                missed.append(title)
        out.append(line)

    open(a.out, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print(f"Съвпаднали: {matched}, без съвпадение: {len(missed)}")
    for t in missed:
        print("  -", t)
    print(f"Записано в {a.out}")


if __name__ == "__main__":
    sys.exit(main())
