#!/usr/bin/env python3
"""
ZEBRA BETA · 취향의 발견 / 모두의 큐레이션 개별 항목 페이지 생성기 (SEO)

하는 일:
  · taste/taste.json, everyone/everyone.json 을 읽어
  · published 항목마다 정적 페이지를 생성:
        taste/<slug>/index.html
        everyone/<slug>/index.html
  · 각 페이지에 고유명사를 앞세운 <title>·<h1>, 본문 실제 HTML,
    og 태그(자켓/사진 이미지), JSON-LD(MusicRecording/Article) 삽입
  · sitemap.xml 을 영구 지면 전체로 재생성

사용법:  python3 _build_taste_everyone/build.py
플레이어/리더 화면(코너 index.html)은 건드리지 않는다.
"""
import json, re, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://zebrabeta.kr"
GA = "G-B0TNF05GFQ"

def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)

def absurl(path_rel, base_dir):
    """taste.json 의 상대경로를 사이트 절대 URL 로."""
    p = str(path_rel or "").strip()
    if not p:
        return ""
    if p.startswith("http"):
        return p
    # base_dir 기준 상대 경로 정규화 (../ 처리)
    from posixpath import normpath
    joined = normpath(f"/{base_dir}/{p}")
    return SITE + joined

def paras(body):
    out = []
    for p in re.split(r"\n\s*\n", str(body or "").strip()):
        p = p.strip()
        if not p:
            continue
        out.append("<p>" + esc(p).replace("\n", "<br>") + "</p>")
    return "".join(out)

HEAD = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<script async src="https://www.googletagmanager.com/gtag/js?id={ga}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{ga}');
</script>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{og_image}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&family=Noto+Serif+KR:wght@200;300;400;500&display=swap" rel="stylesheet">
<script type="application/ld+json">
{jsonld}
</script>
<script>
if (/KAKAOTALK/i.test(navigator.userAgent)) {{
  location.href = "kakaotalk://web/openExternal?url=" + encodeURIComponent(location.href);
  setTimeout(function(){{ location.href = "kakaotalk://inappbrowser/close"; }}, 0);
}}
</script>
<style>
:root{{--paper:#F5F3ED;--card:#FBFAF6;--ink:#26221C;--ink-soft:#332F28;--grey:#5A554C;--faint:#A9A297;--line:#e3ded3;--gold:#b0975a;--serif:'Noto Serif KR',serif;--latin:'Cormorant Garamond',serif;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
html{{-webkit-text-size-adjust:100%;}}
body{{background:var(--paper);color:var(--ink);font-family:var(--serif);font-weight:300;line-height:1.9;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}}
.inner{{max-width:640px;margin:0 auto;padding:76px 32px 100px;}}
.crumb{{text-align:center;font-family:var(--latin);font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:var(--gold);margin-bottom:18px;}}
.crumb a{{color:var(--gold);text-decoration:none;}}
h1.ttl{{font-family:var(--serif);font-weight:400;font-size:21px;text-align:center;color:var(--ink);line-height:1.5;margin-bottom:10px;}}
.by{{font-family:var(--latin);font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:var(--gold);text-align:center;margin-bottom:44px;}}
{extra_css}
.foot{{text-align:center;margin-top:70px;}}
.foot a{{font-family:var(--latin);font-size:12px;letter-spacing:0.16em;color:var(--faint);text-decoration:none;}}
.foot a:hover{{color:var(--gold);}}
.colophon{{text-align:center;margin-top:22px;font-family:var(--latin);font-style:italic;font-weight:300;font-size:12px;letter-spacing:0.18em;color:var(--faint);}}
</style>
</head>
<body>
<main class="inner">
"""

FOOT = """
<div class="foot"><a href="https://zebrabeta.kr">HOME</a></div>
<div class="colophon">zebra beta · movement 2.</div>
</main>
</body>
</html>
"""

TASTE_CSS = """
.r-body{font-size:14.5px;line-height:2.2;color:var(--ink-soft);}
.r-body .r-photo{float:left;width:44%;margin:6px 26px 14px 0;}
.r-body .r-photo img{width:100%;display:block;border-radius:2px;}
.r-body .r-photo-2{float:none;clear:both;width:65%;margin:22px auto 8px;}
.r-body .r-photo figcaption{font-family:var(--latin);font-size:10px;letter-spacing:0.14em;text-transform:uppercase;color:var(--faint);text-align:center;margin-top:7px;}
.r-body p{margin-bottom:1.5em;}
.r-body p:first-of-type{margin-top:0;}
.r-body .clear{clear:both;}
.r-embed{margin:0 auto 10px;max-width:400px;}
.r-embed iframe{display:block;width:100%;height:520px;border:0;background:#fff;border-radius:2px;}
.r-cap{font-family:var(--latin);font-size:10.5px;letter-spacing:0.12em;color:var(--faint);text-align:center;margin:0 0 34px;}
.r-links{text-align:center;margin-top:40px;font-size:13px;}
.r-links a{font-family:var(--serif);font-weight:300;color:var(--grey);text-decoration:none;border-bottom:1px solid var(--line);padding-bottom:1px;}
.r-links a:hover{color:var(--gold);border-color:var(--gold);}
.r-links .sep{color:var(--faint);margin:0 10px;}
@media(max-width:480px){.inner{padding:64px 24px 80px;}h1.ttl{font-size:19px;}.r-body{font-size:14px;line-height:2.1;}.r-body .r-photo{width:42%;margin:4px 16px 0 0;}.r-body .r-photo-2{width:88%;margin:18px auto 6px;}.r-embed iframe{height:480px;}}
"""

EVERYONE_CSS = """
.player{position:relative;width:100%;max-width:400px;margin:0 auto;aspect-ratio:1;background:#d8d2c6 center/cover no-repeat;cursor:pointer;overflow:hidden;border-radius:2px;box-shadow:0 1px 2px rgba(70,64,54,0.04),0 6px 16px rgba(70,64,54,0.05);}
.player .play{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}
.player .play::before{content:"";width:50px;height:50px;border-radius:50%;background:rgba(20,18,15,0.42);position:absolute;}
.player:hover .play::before{background:rgba(20,18,15,0.58);}
.player .play::after{content:"";position:relative;margin-left:4px;border-style:solid;border-width:8px 0 8px 14px;border-color:transparent transparent transparent #f6f3ec;}
.player iframe{position:absolute;inset:0;width:100%;height:100%;border:0;display:block;}
.song{font-family:var(--latin);font-weight:400;font-size:24px;text-align:center;margin-top:40px;color:var(--ink);line-height:1.3;}
.artist{font-family:var(--latin);font-style:italic;font-weight:300;font-size:15px;text-align:center;color:var(--grey);margin-top:6px;}
.note-label{font-family:var(--serif);font-weight:300;font-size:11px;letter-spacing:0.02em;text-align:center;color:var(--faint);margin-top:48px;}
.quote{font-family:var(--serif);font-weight:300;font-size:13.5px;line-height:2.3;color:var(--ink-soft);text-align:center;margin-top:15px;}
.pby{font-family:var(--latin);font-size:10.5px;letter-spacing:0.2em;text-transform:uppercase;text-align:center;color:var(--gold);margin-top:46px;}
@media(max-width:480px){.inner{padding:64px 24px 80px;}.song{font-size:21px;}}
"""

def taste_slug(item, folder):
    if item.get("slug"):
        return item["slug"]
    return folder  # fallback

def build_taste(items):
    urls = []
    for item in items:
        if item.get("published") is False:
            continue
        # slug 결정
        cov = item.get("cover") or ""
        folder = cov.split("/")[0] if "/" in cov and not cov.startswith("..") else ""
        slug = item.get("slug") or folder or re.sub(r"[^a-z0-9]+", "", item.get("title","").lower())[:16]
        title = item.get("title","")
        by = item.get("by","")
        preview = item.get("preview") or ""
        desc = re.sub(r"\s+", " ", preview).strip()[:150]
        canon = f"{SITE}/taste/{slug}/"
        img_rel = item.get("cover_full") or item.get("cover") or ""
        og_image = absurl(img_rel, "taste") or f"{SITE}/taste/taste_og.jpg"

        # 본문
        is_quote = item.get("kind") in ("quote","문장")
        embed_html = ""
        if item.get("embed"):
            m = re.search(r"instagram\.com/(p|reel)/([A-Za-z0-9_-]+)", item["embed"])
            if m:
                embed_html = (f'<div class="r-embed"><iframe src="https://www.instagram.com/{m.group(1)}/{m.group(2)}/embed/" '
                              f'loading="lazy" scrolling="no" allowtransparency="true" title="{esc(title)}"></iframe></div>'
                              + (f'<div class="r-cap">{esc(item.get("caption",""))}</div>' if item.get("caption") else ""))
        photo = ""
        if not embed_html and (item.get("cover_full") or item.get("cover")):
            pimg = absurl(item.get("cover_full") or item.get("cover"), "taste")
            cap = f'<figcaption>사진 · {esc(item["photo_by"])}</figcaption>' if item.get("photo_by") else ""
            photo = f'<figure class="r-photo"><img src="{pimg}" alt="{esc(title)}">{cap}</figure>'
        photo2 = ""
        if item.get("cover_2"):
            p2 = absurl(item["cover_2"], "taste")
            cap = f'<figcaption>사진 · {esc(item["photo_by"])}</figcaption>' if item.get("photo_by") else ""
            photo2 = f'<figure class="r-photo r-photo-2"><img src="{p2}" alt="{esc(item.get("cover_2_alt",""))}">{cap}</figure>'
        links = ""
        if isinstance(item.get("links"), list) and item["links"]:
            links = '<div class="r-links">' + '<span class="sep">·</span>'.join(
                f'<a href="{esc(l["url"])}" target="_blank" rel="noopener">{esc(l["label"])}</a>' for l in item["links"]) + '</div>'
        if is_quote:
            body_html = f'<div class="r-quote">{esc(item.get("body") or title)}</div>'
        else:
            body_html = '<div class="r-body">' + embed_html + photo + paras(item.get("body")) + photo2 + '<div class="clear"></div></div>'

        jsonld = {
            "@context": "https://schema.org", "@type": "Article",
            "headline": title, "description": desc, "image": og_image,
            "mainEntityOfPage": canon, "inLanguage": "ko",
            "publisher": {"@type": "Organization", "name": "지브라 베타",
                          "logo": {"@type": "ImageObject", "url": f"{SITE}/zebra-logo.png"}},
        }
        if by:
            jsonld["author"] = {"@type": "Person", "name": by}

        head = HEAD.format(ga=GA, title=esc(f"{title} — 취향의 발견 | 지브라 베타"),
                           desc=esc(desc), canon=canon, og_title=esc(title),
                           og_type="article", og_image=esc(og_image),
                           jsonld=json.dumps(jsonld, ensure_ascii=False, indent=2),
                           extra_css=TASTE_CSS)
        html_doc = (head
                    + f'<div class="crumb"><a href="/taste/">취향의 발견</a></div>\n'
                    + f'<h1 class="ttl">{esc(title)}</h1>\n'
                    + (f'<div class="by">{esc(by)}</div>\n' if by else '')
                    + body_html + links
                    + FOOT.format(corner="/taste/", corner_name="취향의 발견"))
        out = ROOT / "taste" / slug / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html_doc, encoding="utf-8")
        urls.append((canon, "monthly", "0.7"))
        print(f"  taste/{slug}/  ← {title}")
    return urls

def build_everyone(items):
    urls = []
    for item in items:
        if item.get("published") is False:
            continue
        slug = item["slug"]; title = item.get("title",""); artist = item.get("artist","")
        note = item.get("note",""); by = item.get("by","")
        canon = f"{SITE}/everyone/{slug}/"
        og_image = absurl(item.get("cover"), "everyone")
        desc = re.sub(r"\s+"," ", f"{artist} '{title}' — {note}").strip()[:150]
        yt = item.get("youtube","")

        jsonld = {
            "@context": "https://schema.org", "@type": "MusicRecording",
            "name": title, "byArtist": {"@type": "MusicGroup", "name": artist},
            "image": og_image, "url": canon,
        }
        if note:
            jsonld["description"] = re.sub(r"\s+"," ", note).strip()

        head = HEAD.format(ga=GA, title=esc(f"{title} — {artist} | 모두의 큐레이션 · 지브라 베타"),
                           desc=esc(desc), canon=canon, og_title=esc(f"{title} — {artist}"),
                           og_type="music.song", og_image=esc(og_image),
                           jsonld=json.dumps(jsonld, ensure_ascii=False, indent=2),
                           extra_css=EVERYONE_CSS)
        note_html = ""
        if note:
            note_html = f'<div class="note-label">한줄 소개</div><div class="quote">&ldquo;{esc(note).replace(chr(10),"<br>")}&rdquo;</div>'
        player = (f'<div class="player" data-embed="https://www.youtube-nocookie.com/embed/{esc(yt)}?autoplay=1" '
                  f'style="background-image:url(\'{og_image}\');" role="button" aria-label="{esc(title)} 재생">'
                  f'<div class="play" aria-hidden="true"></div></div>')
        html_doc = (head
                    + f'<div class="crumb"><a href="/everyone/">모두의 큐레이션</a></div>\n'
                    + player
                    + f'<h1 class="song">{esc(title)}</h1>\n<div class="artist">{esc(artist)}</div>\n'
                    + note_html
                    + (f'<div class="pby">Curated by {esc(by)}</div>' if by else '')
                    + '<script>(function(){var p=document.querySelector(".player");if(!p)return;p.addEventListener("click",function(){if(p.dataset.played)return;p.dataset.played="1";var f=document.createElement("iframe");f.src=p.getAttribute("data-embed");f.setAttribute("allow","accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture");f.setAttribute("allowfullscreen","");p.innerHTML="";p.appendChild(f);p.style.cursor="default";});})();</script>'
                    + FOOT.format(corner="/everyone/", corner_name="모두의 큐레이션"))
        out = ROOT / "everyone" / slug / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html_doc, encoding="utf-8")
        urls.append((canon, "monthly", "0.7"))
        print(f"  everyone/{slug}/  ← {title} — {artist}")
    return urls

def build_sitemap(item_urls):
    fixed = [
        (f"{SITE}/", "weekly", "1.0"),
        (f"{SITE}/everyone/", "weekly", "0.8"),
        (f"{SITE}/taste/", "weekly", "0.8"),
        (f"{SITE}/bside/", "monthly", "0.6"),
        (f"{SITE}/curator/ilpostino/", "monthly", "0.7"),
        (f"{SITE}/curator/minorppong/", "monthly", "0.7"),
        (f"{SITE}/curator/professionnel/", "monthly", "0.7"),
    ]
    rows = fixed + item_urls
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, cf, pr in rows:
        lines.append(f"  <url>\n    <loc>{loc}</loc>\n    <changefreq>{cf}</changefreq>\n    <priority>{pr}</priority>\n  </url>")
    lines.append("</urlset>\n")
    (ROOT / "sitemap.xml").write_text("\n".join(lines), encoding="utf-8")
    print(f"  sitemap.xml  ← {len(rows)} URLs")

if __name__ == "__main__":
    taste = json.loads((ROOT/"taste"/"taste.json").read_text(encoding="utf-8"))
    every = json.loads((ROOT/"everyone"/"everyone.json").read_text(encoding="utf-8"))
    print("생성:")
    u1 = build_taste(taste)
    u2 = build_everyone(every)
    build_sitemap(u1 + u2)
    print("완료.")
