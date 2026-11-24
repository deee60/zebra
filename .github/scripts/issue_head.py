"""지면 <head> 누락 태그 채우기 · 자켓 줄이기 (2026-11-24)

publish-queue 가 발행 직후 부른다. 손으로도 돌릴 수 있다.
  python3 .github/scripts/issue_head.py head  issue/gayo04/index.html [--live]
  python3 .github/scripts/issue_head.py cover issue/gayo04

head  : GA · 방문 기록(/_z/t.js) · 카톡 꼬리표 · canonical 이 없으면 넣는다.
        --live 면 발행 중 지면이라 검색 차단 표시도 없으면 넣는다(템플릿과 같은 값).
        이미 있는 건 건드리지 않는다.
        같은 때 검색엔진용 곡 정보(JSON-LD)도 없으면 넣는다(add_jsonld).
share : 모든 지면 아티스트 아래에 공유 아이콘이 없으면 넣는다. python3 .github/scripts/issue_head.py share all
ld    : 모든 지면에 곡 정보(JSON-LD)가 없으면 넣는다.  python3 .github/scripts/issue_head.py ld all
cover : 지면 폴더의 jpg 중 긴 변 1000px 또는 200KB 를 넘는 것을 줄인다.
        줄이기 전에 원본을 _covers_original/{slug}/ 에 둔다(Pages 공개 제외 폴더).
        archive_expired.py 는 원본이 있으면 그걸 아카이브 사본으로 쓴다.
"""
import html as H, json, os, re, shutil, sys

GA = """<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-B0TNF05GFQ"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-B0TNF05GFQ');
</script>"""
TJS = '<script src="/_z/t.js" defer></script>'
NOINDEX = '<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">'
KAKAO_OLD = 'location.href = "kakaotalk://web/openExternal?url=" + encodeURIComponent(location.href);'
KAKAO_NEW = ('var _u = location.href; try { var _x = new URL(_u); if (!_x.searchParams.has("utm_source")) '
             '{ _x.searchParams.set("utm_source", "kakaotalk"); _u = _x.href; } } catch (e) {}\n'
             '  location.href = "kakaotalk://web/openExternal?url=" + encodeURIComponent(_u);')
KAKAO_BLOCK = """<script>
/* 카카오톡 인앱 브라우저 탈출 */
if (/KAKAOTALK/i.test(navigator.userAgent)) {
  """ + KAKAO_NEW + """
  setTimeout(function(){ location.href = "kakaotalk://inappbrowser/close"; }, 0);
}
</script>"""


def fix_head(html, url, live=False):
    head_end = html.index("</head>")
    head = html[:head_end]
    added = []
    if "googletagmanager.com/gtag" not in head:
        head = head.replace('<meta charset="UTF-8">', '<meta charset="UTF-8">\n' + GA, 1); added.append("GA")
    if "/_z/t.js" not in head:
        if "gtag('config'" in head:
            head = re.sub(r"(gtag\('config', 'G-B0TNF05GFQ'\);\s*</script>)", r"\1\n" + TJS, head, count=1)
        else:
            head = head.replace('<meta charset="UTF-8">', '<meta charset="UTF-8">\n' + TJS, 1)
        added.append("방문기록")
    if live and 'name="robots"' not in head:
        head = re.sub(r'(<meta name="viewport"[^>]*>)', r"\1\n" + NOINDEX, head, count=1); added.append("검색차단")
    if 'rel="canonical"' not in head and url:
        head = head + '<link rel="canonical" href="' + url + '">\n'; added.append("canonical")
    if "utm_source" not in head:
        if KAKAO_OLD in head:
            head = head.replace(KAKAO_OLD, KAKAO_NEW, 1)
        elif "KAKAOTALK" not in head:
            head = head + KAKAO_BLOCK + "\n"
        added.append("카톡꼬리표")
    return head + html[head_end:], added


SITE = "https://zebrabeta.kr/"


def _txt(fragment):
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def add_jsonld(html, url, entry=None):
    """검색엔진에 주는 곡 정보(보이지 않음). 이미 있으면 그대로 둔다.
    지면의 제목·아티스트·크레딧 '앨범' 줄·노트 첫 문단과 issue.json 의 발행일·서가·자켓을 쓴다."""
    if "application/ld+json" in html or "</head>" not in html:
        return html, False
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    a = re.search(r'<p class="artist"[^>]*>(.*?)</p>', html, re.S)
    if not m or not a:
        return html, False
    name, artist = _txt(m.group(1)), _txt(a.group(1))
    rec = {"@type": "MusicRecording", "name": name, "byArtist": {"@type": "MusicGroup", "name": artist}}
    al = re.search(r'<span class="cr-label">앨범</span><span class="cr-names">(.*?)</span></span></span>', html, re.S)
    if al:
        parts = [_txt(x) for x in re.findall(r'<span class="cr-name">(.*?)</span>', al.group(1) + "</span>", re.S)]
        if parts:
            alb = {"@type": "MusicAlbum", "name": parts[0]}
            if re.fullmatch(r"\d{4}", parts[-1]):
                alb["datePublished"] = parts[-1]
            rec["inAlbum"] = alb
    zebra = {"@type": "Organization", "name": "지브라 베타", "url": SITE}
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": f"{name} — {artist}",
          "inLanguage": "ko", "url": url, "author": zebra, "publisher": zebra, "about": rec}
    n = re.search(r'<div class="note"[^>]*>\s*<p[^>]*>(.*?)</p>', html, re.S)
    if n:
        d = _txt(n.group(1))
        ld["description"] = d if len(d) <= 160 else d[:159].rstrip() + "…"
    if entry:
        if entry.get("published"):
            ld["datePublished"] = entry["published"] + "T00:00:00+09:00"
        if entry.get("series"):
            ld["articleSection"] = entry["series"]
        if entry.get("cover"):
            ld["image"] = SITE + entry["cover"]
    tag = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
    i = html.index("</head>")
    return html[:i] + tag + html[i:], True


SHARE_ICON = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 15V3"/>'
              '<path d="M7.5 7.5 12 3l4.5 4.5"/><path d="M5 11v8.5h14V11"/></svg>')
SHARE_HTML = ('\n      <p class="zshare-wrap"><a class="zshare" href="#" aria-label="이 지면 공유하기">' + SHARE_ICON +
              '<span class="zshare-done" aria-live="polite"></span></a></p>')
SHARE_HEAD = """<style id="zshare-css">
  .zshare-wrap{margin:16px 0 0;text-align:center;line-height:0}
  .zshare{position:relative;display:inline-flex;padding:12px;margin:-12px;color:var(--faint,#a9a297);-webkit-tap-highlight-color:transparent}
  .zshare-done{position:absolute;left:50%;top:100%;transform:translateX(-50%);font-size:11px;letter-spacing:.12em;line-height:1;white-space:nowrap;color:var(--faint,#a9a297)}
</style>
<script>
  /* 지면 공유: 폰은 공유 창, PC는 주소 복사 */
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest && ev.target.closest('.zshare'); if (!a) return;
    ev.preventDefault();
    var c = document.querySelector('link[rel="canonical"]');
    var url = c ? c.href : location.origin + location.pathname;
    var done = a.querySelector('.zshare-done');
    if (navigator.share) { navigator.share({ title: document.title, url: url }).catch(function () {}); return; }
    var say = function (t) { done.textContent = t; setTimeout(function () { done.textContent = ''; }, 1600); };
    if (navigator.clipboard) navigator.clipboard.writeText(url).then(function () { say('복사됨'); }, function () { say(url); });
    else say(url);
  });
</script>
"""


def add_share(html):
    """아티스트 이름 아래 공유 아이콘(18px). 폰은 공유 창, PC는 주소 복사. 이미 있으면 그대로.
    위치·크기를 바꿀 때: 여기(SHARE_HTML·SHARE_HEAD)를 고친 뒤, 이미 붙은 지면은 zshare-wrap·zshare-css 를
    지우고 `issue_head.py share all` 로 다시 붙인다. _build/build.py 의 타이틀 구조와 연동."""
    added = False
    if 'class="zshare-wrap"' not in html:
        m = re.search(r'<p class="artist"[^>]*>.*?</p>', html, re.S)
        if not m:
            return html, False
        html = html[:m.end()] + SHARE_HTML + html[m.end():]
        added = True
    if 'id="zshare-css"' not in html and "</head>" in html:
        i = html.index("</head>")
        html = html[:i] + SHARE_HEAD + html[i:]
        added = True
    return html, added


def entry_for(slug):
    try:
        for e in json.load(open("_data/issue.json", encoding="utf-8")):
            if e.get("slug") == slug:
                return e
    except Exception:
        pass
    return None


def shrink_covers(folder, long_side=1000, max_bytes=200_000):
    from PIL import Image
    slug = os.path.basename(folder.rstrip("/"))
    done = []
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith((".jpg", ".jpeg")):
            continue
        p = os.path.join(folder, f)
        im = Image.open(p)
        if max(im.size) <= long_side and os.path.getsize(p) <= max_bytes:
            continue
        import glob
        if not glob.glob(os.path.join("archive", "*", "*", f)):   # 아카이브 사본에 원본이 이미 있으면 따로 안 둔다
            keep = os.path.join("_covers_original", slug)
            os.makedirs(keep, exist_ok=True)
            if not os.path.exists(os.path.join(keep, f)):
                shutil.copy2(p, os.path.join(keep, f))
        im = im.convert("RGB")
        if max(im.size) > long_side:
            r = long_side / max(im.size)
            im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
        before = os.path.getsize(p)
        for q in (86, 82, 78, 74):
            im.save(p, "JPEG", quality=q, optimize=True, progressive=True)
            if os.path.getsize(p) <= max_bytes:
                break
        done.append(f"{f} {before//1024}KB→{os.path.getsize(p)//1024}KB")
    return done


if __name__ == "__main__":
    cmd, target = sys.argv[1], sys.argv[2]
    if cmd == "head":
        live = "--live" in sys.argv
        m = re.search(r"(issue/[^/]+/)", target)
        url = "https://zebrabeta.kr/" + m.group(1) if m else ""
        html = open(target, encoding="utf-8").read()
        html, added = fix_head(html, url, live)
        html, ok = add_jsonld(html, url, entry_for(url.rstrip("/").split("/")[-1]) if url else None)
        if ok: added.append("곡정보")
        html, ok = add_share(html)
        if ok: added.append("공유")
        # 지면 구조가 바뀌어 붙일 자리를 못 찾으면 발행 기록에 경고를 남긴다(안내 페이지는 제외)
        if "ZEBRA_EXPIRED_STUB" not in html:
            if 'class="zshare-wrap"' not in html:
                print("::warning::공유 아이콘을 붙일 자리(<p class=\"artist\">)를 못 찾음 — 지면 구조가 바뀌었으면 add_share 를 고칠 것")
            if "application/ld+json" not in html:
                print("::warning::곡 정보(JSON-LD)를 못 만듦 — h1·artist 구조가 바뀌었으면 add_jsonld 를 고칠 것")
        open(target, "w", encoding="utf-8").write(html)
        print(target, "추가:", ", ".join(added) or "없음")
    elif cmd == "ld":
        import glob
        pages = sorted(glob.glob("issue/*/index.html")) if target == "all" else [target]
        for pg in pages:
            slug = pg.split("/")[1]
            html = open(pg, encoding="utf-8").read()
            html, ok = add_jsonld(html, SITE + "issue/" + slug + "/", entry_for(slug))
            if ok:
                open(pg, "w", encoding="utf-8").write(html)
            print(pg, "곡정보", "넣음" if ok else "그대로")
    elif cmd == "share":
        import glob
        pages = sorted(glob.glob("issue/*/index.html")) if target == "all" else [target]
        for pg in pages:
            html = open(pg, encoding="utf-8").read()
            html, ok = add_share(html)
            if ok:
                open(pg, "w", encoding="utf-8").write(html)
            print(pg, "공유", "넣음" if ok else "그대로")
    elif cmd == "cover":
        print(target, "자켓:", "; ".join(shrink_covers(target)) or "줄일 것 없음")
