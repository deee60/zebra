"""만료된 issue 지면 처리 (archive-expired 워크플로가 매일 03:00 KST 실행)

전문 보관은 비공개 금고(deee60/zebra-vault)가 한다 (2026-11-24부터). 이 저장소는 공개라 사본을 두지 않는다.
금고 작업(keep-site-originals)이 3시간마다 이 저장소를 읽어 전문을 복사하고, 보관한 지면의 지문을 사이트에 알린다.

1) issue/{slug}/index.html 이 아직 전문이고, 금고에 같은 지문의 사본이 있으면
2) '맛보기' 페이지로 바꾼다
   - 자켓 · 압인 · 곡명 · 연주자 · 노트 첫 문단(흐리게) · "아카이브로 이관되었습니다" · 최근 발행물 보기
   - 크레딧 중간부터 스트리밍까지 이어서 흐리게, 스트리밍 버튼은 보이되 주소를 지워 눌리지 않게
   - 영상 · 노트 나머지 · 덧붙임은 넣지 않는다 (금고에만)
   - 검색 허용(index), 제목 · 설명 · canonical 을 검색용으로
   노트가 없는 지면(예: halloween26)은 '이관 안내'만 두고 검색 금지
3) 맛보기 페이지 목록으로 sitemap-issue.xml 을 다시 쓴다

안전장치
- 발행 중(만료 전) 지면은 절대 건드리지 않는다
- 금고에 같은 판의 사본이 없으면(목록을 못 읽은 경우 포함) 맛보기로 바꾸지 않고 전문을 하루 더 둔다
- 이미 맛보기·안내인 페이지는 다시 만들지 않는다. 맛보기 모양을 바꾸려면 금고 사본으로 손으로 다시 만든다
- 새 내용을 다 만든 뒤에 파일을 쓴다 (도중 실패해도 원본이 비지 않게)
"""
import hashlib, html as H, json, os, re, shutil, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from issue_head import fix_head, add_jsonld
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
SITE = "https://zebrabeta.kr"
VAULT_HELD = SITE + "/_z/vault-held"
STUB = "<!-- ZEBRA_EXPIRED_STUB -->"
TEASER_TAG = "ZEBRA_EXPIRED_TEASER"
TEASER = "<!-- ZEBRA_EXPIRED_TEASER v6 -->"   # 맛보기 표식. 모양을 바꾸면 v 숫자를 올리고 금고 사본으로 다시 만든다
NOINDEX = '<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">'
INDEX = '<meta name="robots" content="index, follow">'
DEFAULT_MOVED = """
    <div class="spacer"></div>
    <div class="moved">
      <hr class="rule">
      <p class="line">이 큐레이션은<br>아카이브로 이관되었습니다</p>
      <p class="sub">지브라의 큐레이션은<br>발행 후 72시간 동안 열립니다.<br>이후 아카이브로 옮겨집니다.</p>
      <p class="home"><a href="/latest/">최근 발행물 보기</a></p>
    </div>
    <div class="spacer"></div>
    <p class="colophon">zebra beta · movement 2.</p>"""

TEASER_CSS = """<style>
  /* 만료 맛보기 */
  .note p.teaser{ -webkit-mask-image:linear-gradient(#000 35%, transparent 100%); mask-image:linear-gradient(#000 35%, transparent 100%); }
  .gate{ text-align:center; margin:clamp(18px,3vh,26px) 0 clamp(40px,6vh,56px); }
  .gate .g-rule{ width:40px; margin:0 auto 22px; border:0; border-top:1px solid var(--rule, #cfc9bb); }
  .gate .g-line{ font-family:"Noto Serif KR",serif; font-size:15px; color:var(--ink,#2a2722); margin:0 0 22px; letter-spacing:.02em; }
  .gate .g-home a{ display:inline-block; color:#8b877c; font-family:"Noto Serif KR",serif; font-weight:400; font-size:15px; letter-spacing:.02em;
    text-decoration:underline; text-decoration-thickness:1px; text-underline-offset:6px; text-decoration-color:#c9c3b7; }
  .listen a, .note .credit a{ pointer-events:none; cursor:default; }
</style>"""

TEASER_GATE = """<div class="gate">
  <hr class="g-rule">
  <p class="g-line">이 큐레이션은 아카이브로 이관되었습니다</p>
  <p class="g-home"><a href="/latest/">최근 발행물 보기</a></p>
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

TEASER_SHARE = 0.35   # 맛보기로 보여줄 노트 분량 상한(전체 글자 수 대비)

def teaser_text(paras):
    """첫 문단에서 문장 단위로, 노트 전체의 35%를 넘지 않게 잘라낸다.
    첫 문장이 이미 절반을 넘으면 35% 지점의 띄어쓰기에서 끊고 '…'."""
    first = re.sub(r"^<p>|</p>$", "", paras[0].strip())
    total = sum(len(plain(x)) for x in paras) or 1
    limit = max(total * TEASER_SHARE, min(60, total * 0.5))   # 아주 짧은 노트도 한 줄은 보이게
    sents = re.split(r"(?<=[.!?])\s+", first)
    out = sents[0]
    for x in sents[1:]:
        if len(plain("<p>" + out + " " + x + "</p>")) > limit:
            break
        out += " " + x
    if len(plain("<p>" + out + "</p>")) > total * 0.5:
        cut = out[: int(limit)]
        sp = cut.rfind(" ")
        cut = cut[:sp] if sp > 0 else cut
        for o, c in (("(", ")"), ("《", "》"), ("〈", "〉"), ("'", "'")):
            if cut.count(o) > cut.count(c) if o != c else cut.count(o) % 2:
                cut = cut[: cut.rfind(o)]              # 괄호·따옴표 안에서 끊기지 않게
        out = cut.rstrip(" ,·") + "…"
    return out

def make_teaser(src_html, e):
    """아카이브 사본(원본 전체)에서 맛보기 페이지를 만든다. 노트가 없으면 None."""
    inner = note_inner(src_html)
    if inner is None or "<p>" not in inner:
        return None
    paras = re.findall(r"<p>.*?</p>", inner, re.S)
    credit = re.search(r'<div class="credit">.*?</div>(?=\s*$)', inner, re.S) or re.search(r'<div class="credit">.*', inner, re.S)
    teaser_txt = teaser_text(paras)
    teaser_p = '<p class="teaser">' + teaser_txt + "</p>"
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
    desc = plain("<p>" + teaser_txt + "</p>")
    desc = desc if len(desc) <= 150 else desc[:148].rstrip() + "…"
    url = f"{SITE}/issue/{e['slug']}/"
    head = head.replace(NOINDEX, "").replace(INDEX, "")
    head = re.sub(r"<title>.*?</title>", "<title>" + H.escape(title, quote=False) + "</title>", head, count=1, flags=re.S)
    head = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="' + H.escape(desc) + '">', head, count=1)
    head = re.sub(r'\s*<link rel="canonical"[^>]*>', "", head)
    head = head.replace("</head>", INDEX + '\n<link rel="canonical" href="' + url + '">\n' + TEASER_CSS + "\n</head>", 1)
    # 아카이브 사본이 옛 틀이어도 맛보기에는 지금 기준 태그를 채운다 (2026-11-24): GA · 방문 기록 · 카톡 꼬리표 · 새 공유 그림
    head = head.replace("/zebra-og.png", "/zebra-og-v2.png")
    head = fix_head(head, url)[0]
    return head + body

def main():
    now = datetime.now(KST)
    items = json.load(open("_data/issue.json", encoding="utf-8"))
    log, teasers = [], []
    # 금고(비공개 zebra-vault)가 보관한 전문의 지문 목록. 금고 작업이 3시간마다 사이트 어드민에 알린다.
    try:
        held = json.load(urllib.request.urlopen(urllib.request.Request(VAULT_HELD, headers={"user-agent": "zebra-bot"}), timeout=20)).get("held") or {}
    except Exception as x:
        print(f"::warning::금고 목록을 못 읽음({x}) — 오늘은 맛보기로 바꾸지 않음"); held = {}
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

        # 이미 맛보기·안내면 그대로 둔다 (전문은 금고에만 있으므로 여기서 다시 만들지 않는다)
        if not is_original:
            if TEASER_TAG in cur:
                teasers.append(e)
            continue

        # 1) 금고에 이 판의 전문이 들어갔는지 확인 — 같은 지문일 때만 맛보기로 바꾼다
        want = hashlib.sha1(open(page, "rb").read()).hexdigest()
        if held.get(slug) != want:
            print(f"::warning::{slug}: 금고에 이 판의 사본이 아직 없음 — 오늘은 전문 유지(다음 날 다시)"); continue

        # 2) 맛보기 (노트 없으면 안내)
        out = make_teaser(cur, e)
        if out is None:
            out = make_stub(cur); kind = "stub"
        else:
            kind = "teaser"; teasers.append(e)
            out = add_jsonld(out, SITE + "/issue/" + slug + "/", e)[0]   # 원본에서 이미 넘어왔으면 그대로
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
