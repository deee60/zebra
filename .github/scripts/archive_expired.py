"""만료된 issue 지면 처리 (archive-expired 워크플로가 매일 03:00 KST 실행)

1) issue/{slug}/ 를 archive/{series}/{번호}/ 로 복사 (사본이 없을 때만, 원본일 때만)
2) issue/{slug}/index.html 을 '맛보기' 페이지로 바꾼다 (아카이브 사본에서 만든다)
   - 자켓 · 압인 · 곡명 · 연주자 · 노트 첫 문단(흐리게) · "아카이브로 이관되었습니다" · 지브라 베타 링크
   - 크레딧 중간부터 스트리밍까지 이어서 흐리게, 스트리밍 버튼은 보이되 주소를 지워 눌리지 않게
   - 영상 · 노트 나머지 · 덧붙임은 넣지 않는다 (아카이브에만)
   - 검색 허용(index), 제목 · 설명 · canonical 을 검색용으로
   노트가 없는 지면(예: halloween26)은 '이관 안내'만 두고 검색 금지
3) 맛보기 페이지 목록으로 sitemap-issue.xml 을 다시 쓴다

안전장치
- 발행 중(만료 전) 지면은 절대 건드리지 않는다
- 원본을 바꾸기 전에 아카이브 사본의 스트리밍 링크 수 · 영상 수 · 노트가 원본과 같은지 대조한다. 다르면 멈춘다
- 맛보기/안내 페이지는 절대 아카이브로 복사하지 않는다 (표식으로 구분)
- 새 내용을 다 만든 뒤에 파일을 쓴다 (도중 실패해도 원본이 비지 않게)
"""
import html as H, json, os, re, shutil
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
SITE = "https://zebrabeta.kr"
STUB = "<!-- ZEBRA_EXPIRED_STUB -->"
TEASER_TAG = "ZEBRA_EXPIRED_TEASER"
TEASER = "<!-- ZEBRA_EXPIRED_TEASER v2 -->"   # 모양을 바꾸면 v 숫자를 올린다 → 다음 실행 때 전부 아카이브 사본에서 다시 만듦
NOINDEX = '<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">'
INDEX = '<meta name="robots" content="index, follow">'
DEFAULT_MOVED = """
    <div class="spacer"></div>
    <div class="moved">
      <hr class="rule">
      <p class="line">이 큐레이션은<br>아카이브로 이관되었습니다</p>
      <p class="sub">지브라의 큐레이션은<br>발행 후 72시간 동안 열립니다.<br>이후 아카이브로 옮겨지며,<br>아카이브는 V1.0부터 회원에게 열립니다.</p>
      <p class="home"><a href="https://zebrabeta.kr">지브라 베타</a></p>
    </div>
    <div class="spacer"></div>
    <p class="colophon">zebra beta · movement 2.</p>"""

TEASER_CSS = """<style>
  /* 만료 맛보기 */
  .note p.teaser{ -webkit-mask-image:linear-gradient(#000 35%, transparent 100%); mask-image:linear-gradient(#000 35%, transparent 100%); }
  .gate{ text-align:center; margin:clamp(18px,3vh,26px) 0 clamp(40px,6vh,56px); }
  .gate .g-rule{ width:40px; margin:0 auto 22px; border:0; border-top:1px solid var(--rule, #cfc9bb); }
  .gate .g-line{ font-family:"Noto Serif KR",serif; font-size:15px; color:var(--ink,#2a2722); margin:0 0 22px; letter-spacing:.02em; }
  .gate .g-home a{ display:inline-block; color:#6E5422; font-family:"Noto Serif KR",serif; font-weight:600; font-size:14px; letter-spacing:.06em;
    text-decoration:underline; text-decoration-thickness:1px; text-underline-offset:6px; text-decoration-color:#C8B07A; }
  .listen a, .note .credit a{ pointer-events:none; cursor:default; }
</style>"""

TEASER_GATE = """<div class="gate">
  <hr class="g-rule">
  <p class="g-line">이 큐레이션은 아카이브로 이관되었습니다</p>
  <p class="g-home"><a href="https://zebrabeta.kr">지브라 베타</a></p>
</div>"""

TEASER_JS = """<div class="tailfade" aria-hidden="true"></div>
<script>
(function(){var f=document.querySelector('.tailfade');
function bg(){var e=document.querySelector('.listen')||document.getElementById('sheet');while(e){var c=getComputedStyle(e).backgroundColor;if(c&&c!=='rgba(0, 0, 0, 0)'&&c!=='transparent')return c;e=e.parentElement;}return 'rgb(255, 255, 255)';}
function a(c,o){return c.replace(/rgba?\\(([^,]+),([^,]+),([^,)]+).*\\)/,'rgba($1,$2,$3,'+o+')');}
function place(){var end=document.querySelector('.listen');if(!end){f.style.display='none';return;}
var cr=document.querySelector('.note .credit'),ls=document.querySelectorAll('.note .credit .cr-line'),y0;
if(ls.length>4){y0=ls[4].getBoundingClientRect().top-14;}else if(cr){var r=cr.getBoundingClientRect();y0=r.top+r.height*.45;}else{y0=end.getBoundingClientRect().top-10;}
y0+=scrollY;var y1=end.getBoundingClientRect().bottom+scrollY+6,c=bg();
f.style.cssText='position:absolute;left:0;right:0;pointer-events:none;top:'+y0+'px;height:'+Math.max(0,y1-y0)+'px;background:linear-gradient(to bottom,'+a(c,0)+' 0%,'+a(c,.55)+' 30%,'+a(c,.93)+' 100%);';}
addEventListener('load',place);addEventListener('resize',place);place();})();
</script>
"""

def slug_paths(e):
    slug = e["slug"]
    sid = e.get("series_id") or re.match(r"[a-z]+", slug).group(0)
    num = re.sub(r"^[a-z]+", "", slug) or slug
    return slug, f"issue/{slug}", f"archive/{sid}/{num}"

def body_of(h):
    return h[h.index("<body"):]

def listen_links(h):
    m = re.search(r'<footer class="listen">.*?</footer>', h, re.S)
    return len(re.findall(r"<a\b[^>]*\bhref=", m.group(0))) if m else 0

def film_count(h):
    return len(re.findall(r"youtube(?:-nocookie)?\.com/embed/", body_of(h)))

def note_inner(h):
    """note 안쪽 HTML (없으면 None). note 는 <p>..</p>, <div class=aside|credit> 만 담는다."""
    i = h.find('<div class="note">')
    if i < 0:
        return None
    j = i + len('<div class="note">')
    depth, k = 1, j
    for m in re.finditer(r"<div\b|</div>", h[j:]):
        depth += 1 if m.group(0) == "<div" else -1
        if depth == 0:
            k = j + m.start()
            break
    return h[j:k]

def plain(s):
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", "", s))).strip()

def make_stub(src_html):
    head = src_html[: src_html.index("<body")]
    head = head.replace(INDEX, "")
    if NOINDEX not in head:
        head = head.replace("</head>", NOINDEX + "\n</head>", 1)
    m = re.search(r'getElementById\("sheet"\)\.innerHTML\s*=\s*`(.*?)`;', src_html, re.S)
    moved = m.group(1) if m else DEFAULT_MOVED
    cls = re.search(r'<main class="([^"]*)" id="sheet">', src_html)
    cls = cls.group(1) if cls else "sheet"
    return head + "<body>\n" + STUB + '\n  <main class="' + cls + '" id="sheet">' + moved + "\n  </main>\n</body>\n</html>\n"

def make_teaser(src_html, e):
    """아카이브 사본(원본 전체)에서 맛보기 페이지를 만든다. 노트가 없으면 None."""
    inner = note_inner(src_html)
    if inner is None or "<p>" not in inner:
        return None
    paras = re.findall(r"<p>.*?</p>", inner, re.S)
    credit = re.search(r'<div class="credit">.*?</div>(?=\s*$)', inner, re.S) or re.search(r'<div class="credit">.*', inner, re.S)
    teaser_p = paras[0].replace("<p>", '<p class="teaser">', 1)
    cred = credit.group(0) if credit else ""
    cred = re.sub(r'(<a\b[^>]*?)\s+href="[^"]*"', r"\1", cred)          # 크레딧 안 링크(뮤직비디오 등)도 눌리지 않게
    cred = re.sub(r'\s+target="_blank"|\s+rel="noopener"', "", cred)
    new_inner = teaser_p + TEASER_GATE + cred

    head = src_html[: src_html.index("<body")]
    body = body_of(src_html)
    # 본문 정리
    body = body.replace(inner, new_inner, 1)
    body = re.sub(r"<script\b.*?</script>", "", body, flags=re.S)
    body = re.sub(r'\s*<p class="notice">.*?</p>', "", body, flags=re.S)
    body = re.sub(r'\s*<div class="pair">.*?</figure></div>', "", body, flags=re.S)
    body = re.sub(r'\s*<figure class="film[^"]*">.*?</figure>', "", body, flags=re.S)
    m = re.search(r'<footer class="listen">.*?</footer>', body, re.S)
    if m:
        f = re.sub(r'(<a\b[^>]*?)\s+href="[^"]*"', r"\1", m.group(0))
        f = re.sub(r'\s+target="_blank"|\s+rel="noopener"', "", f)
        body = body.replace(m.group(0), f, 1)
    body = body.replace("</body>", TEASER_JS + "</body>", 1)
    body = body.replace("<body>", "<body>\n" + TEASER, 1)

    # 머리 (검색용)
    song, artist, series = e.get("title", ""), e.get("artist", ""), (e.get("series", "") or "").rstrip(". ")
    series = re.sub(r"^지브라\s*베타\s*", "", series)                       # 제목 끝 '| 지브라 베타'와 겹치지 않게
    title = " — ".join(x for x in [song, artist] if x) + (" · " + series if series else "") + " | 지브라 베타"
    desc = plain(paras[0])
    desc = desc if len(desc) <= 150 else desc[:148].rstrip() + "…"
    url = f"{SITE}/issue/{e['slug']}/"
    head = head.replace(NOINDEX, "").replace(INDEX, "")
    head = re.sub(r"<title>.*?</title>", "<title>" + H.escape(title, quote=False) + "</title>", head, count=1, flags=re.S)
    head = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="' + H.escape(desc) + '">', head, count=1)
    head = re.sub(r'\s*<link rel="canonical"[^>]*>', "", head)
    head = head.replace("</head>", INDEX + '\n<link rel="canonical" href="' + url + '">\n' + TEASER_CSS + "\n</head>", 1)
    return head + body

def main():
    now = datetime.now(KST)
    items = json.load(open("_data/issue.json", encoding="utf-8"))
    log, teasers = [], []
    for e in items:
        exp = e.get("expires")
        if not exp:
            continue
        try:
            t = datetime.fromisoformat(exp)
        except Exception:
            continue
        if t.tzinfo is None:
            t = t.replace(tzinfo=KST)
        if t > now:
            continue                                   # 아직 공개 중 → 손대지 않음
        slug, src, dst = slug_paths(e)
        page, apage = os.path.join(src, "index.html"), os.path.join(dst, "index.html")
        if not os.path.isfile(page):
            continue
        cur = open(page, encoding="utf-8").read()
        if "<body" not in cur:
            print(f"::warning::{slug}: 원본 HTML 이상 — 건너뜀"); continue
        is_original = STUB not in cur and TEASER_TAG not in cur

        # 1) 아카이브 사본
        if not os.path.isfile(apage):
            if not is_original:
                print(f"::warning::{slug}: 원본이 이미 바뀌었는데 아카이브 사본이 없음 — 건너뜀"); continue
            os.makedirs(dst, exist_ok=True)
            for f in os.listdir(src):
                shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
            log.append(f"{slug} -> {dst}")
        arch = open(apage, encoding="utf-8").read()
        if STUB in arch or TEASER_TAG in arch or "<body" not in arch:
            print(f"::warning::{slug}: 아카이브 사본이 온전하지 않음 — 원본 유지"); continue
        if is_original:
            checks = [(listen_links(cur), listen_links(arch), "스트리밍 링크"),
                      (film_count(cur), film_count(arch), "영상"),
                      (plain(note_inner(cur) or ""), plain(note_inner(arch) or ""), "노트")]
            bad = [n for a, b, n in checks if a != b]
            if bad:
                print(f"::warning::{slug}: 아카이브 사본과 원본이 다름({', '.join(bad)}) — 원본 유지"); continue

        # 2) 맛보기 (노트 없으면 안내)
        if TEASER in cur:
            teasers.append(e); continue
        out = make_teaser(arch, e)
        if out is None:
            if STUB in cur:
                continue
            out = make_stub(arch); kind = "stub"
        else:
            kind = "teaser"; teasers.append(e)
        with open(page, "w", encoding="utf-8") as fh:
            fh.write(out)
        log.append(f"{slug} {kind}")

    # 3) 맛보기 사이트맵
    rows = []
    for e in teasers:
        d = (e.get("expires") or "")[:10]
        rows.append(f"  <url><loc>{SITE}/issue/{e['slug']}/</loc>" + (f"<lastmod>{d}</lastmod>" if d else "") + "</url>")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n"
    old = open("sitemap-issue.xml", encoding="utf-8").read() if os.path.exists("sitemap-issue.xml") else ""
    if xml != old:
        open("sitemap-issue.xml", "w", encoding="utf-8").write(xml)
        log.append(f"sitemap-issue.xml ({len(rows)})")
    print("done:", log if log else "nothing new")
    open("/tmp/copied.txt", "w").write("\n".join(log))

if __name__ == "__main__":
    main()
