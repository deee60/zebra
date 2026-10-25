#!/usr/bin/env python3
"""B-SIDE 렌더러 — bside/bside.json 을 읽어 bside/index.html 을 그린다.
주차(week) 단위: 최신 주는 펼쳐진 채 맨 위, 지난 주들은 접혀서 아래로(날짜 클릭 시 펼침).
항목은 기존 아코디언(headline 클릭 → 본문) 유지. selected 개념 없음 — bside.json 에 든 것만 그린다.
published:false 항목은 피드·개별 페이지·사이트맵 모두에서 뺀다(보일 항목이 없는 주차는 피드에서 통째로 뺀다).
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).parent          # _build_bside/
SITE = ROOT.parent                    # repo root
DATA = SITE / "bside" / "bside.json"
OUT  = SITE / "bside" / "index.html"

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def has_page(it):
    return bool(str(it.get("slug","")).strip()) and it.get("published") is not False

def visible_items(w):
    # published:false 는 피드에서도 뺀다 (개별 페이지·사이트맵과 같은 규칙)
    return [it for it in w.get("items", []) if it.get("published") is not False]

def render_item(it):
    src = str(it.get("source", "")).strip()
    src_html = f' <span class="trend-source">({esc(src)})</span>' if src else ""
    return (
        '    <li class="trend-item">\n'
        '      <div class="trend-headline" onclick="toggle(this)">\n'
        f'        <span class="trend-category">{esc(it.get("category",""))}</span>\n'
        f'        <span class="trend-title">{esc(it.get("title",""))}</span>\n'
        '        <span class="trend-arrow">\u203a</span>\n'
        '      </div>\n'
        '      <div class="trend-body">\n'
        f'        <p class="trend-summary">{esc(it.get("summary",""))}{src_html}</p>\n'
        '      </div>\n'
        '    </li>'
    )

def render_week(w, newest, head=None, items_src=None, year=None):
    """주 하나 또는 (접힌) 달 하나를 같은 모양의 줄로 그린다.
    head: 줄·로고 아래에 보일 글자 (기본 'updated <label>')."""
    head = head or f'updated {w.get("label","")}'
    items = "\n".join(render_item(it) for it in (items_src if items_src is not None else visible_items(w)))
    cls = "week open" if newest else "week"
    yattr = f' data-year="{esc(year)}"' if year else ""
    return (
        f'  <section class="{cls}" data-label="{esc(head)}"{yattr}>\n'
        '    <div class="week-header" onclick="toggleWeek(this)">\n'
        f'      <span class="week-date">{esc(head)}</span>\n'
        '      <span class="week-arrow">\u203a</span>\n'
        '    </div>\n'
        '    <ul class="trend-list week-items">\n'
        f'{items}\n'
        '    </ul>\n'
        '  </section>'
    )


SITE_URL = "https://zebrabeta.kr"

def attr(s):
    return esc(s).replace('"', "&quot;")

DETAIL = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-B0TNF05GFQ"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-B0TNF05GFQ');
</script>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_tag}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="https://zebrabeta.kr/zebra-og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Cormorant+SC:wght@400;500&family=Noto+Serif+KR:wght@300;400;500&display=swap" rel="stylesheet">
<script type="application/ld+json">
{jsonld}
</script>
<style>
  :root {{ --cream:#EDE9DF; --ink:#2B2A26; --gray:#8b877c; --faint:#b8b3a8; --gold:#b89a5a; --divider:#e1ddd3; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:var(--cream); color:var(--ink); font-family:'Noto Serif KR',serif; -webkit-font-smoothing:antialiased; }}
  .page {{ max-width:520px; margin:0 auto; padding:48px 24px 120px; }}
  .crumb {{ text-align:center; margin-bottom:56px; }}
  .crumb {{ font-family:'Cormorant SC',serif; font-weight:500; font-size:14px; letter-spacing:2.5px; color:var(--gray); }}
  .meta {{ font-family:'Cormorant Garamond',serif; font-size:11px; letter-spacing:.1em; color:var(--faint); margin-bottom:14px; }}
  h1 {{ font-weight:400; font-size:19px; line-height:1.7; word-break:keep-all; margin-bottom:32px; padding-bottom:28px; border-bottom:1px solid var(--divider); }}
  .body p {{ font-weight:300; font-size:14px; line-height:2.1; word-break:keep-all; margin-bottom:1.4em; }}
  .source {{ font-family:'Cormorant Garamond',serif; font-size:12px; letter-spacing:.08em; color:var(--faint); margin-top:8px; }}
  .footer {{ margin-top:120px; text-align:center; }}
  .colophon {{ font-family:'Cormorant Garamond',serif; font-style:italic; font-weight:300; font-size:12px; letter-spacing:.18em; color:rgb(169,162,151); }}
  .home {{ margin-top:16px; }}
  .home a {{ font-family:'Cormorant Garamond',serif; font-size:12px; letter-spacing:.16em; color:rgb(169,162,151); text-decoration:none; transition:color .3s ease; }}
  .home a:hover {{ color:var(--gold); }}
  /* copy guard (same as issue pages): block text selection; right-click/copy via script below */
  html,body{{ -webkit-user-select:none; -moz-user-select:none; -ms-user-select:none; user-select:none; -webkit-touch-callout:none; }}
  a,button,iframe,input,textarea{{ -webkit-user-select:auto; user-select:auto; }}
</style>
</head>
<body>
<div class="page">
  <div class="crumb">B-SIDE</div>
  <div class="meta">{category} &middot; {label}</div>
  <h1>{title}</h1>
  <div class="body">{body}</div>
  {source_html}
  <footer class="footer">
    <p class="colophon">zebra beta &middot; movement 2.</p>
    <div class="home"><a href="https://zebrabeta.kr">HOME</a></div>
  </footer>
</div>
<script>
(function(){{
  var block=function(e){{ e.preventDefault(); return false; }};
  document.addEventListener("contextmenu", block);
  document.addEventListener("copy", block);
  document.addEventListener("cut", block);
  document.addEventListener("dragstart", block);
}})();
</script>
</body>
</html>
"""

def paragraphs(text):
    parts = [p.strip() for p in re.split(r"\n\s*\n", str(text or "").strip()) if p.strip()]
    return "".join("<p>" + esc(p).replace("\n", "<br>") + "</p>" for p in parts)

def build_details(weeks):
    made = []
    for w in weeks:
        for it in w.get("items", []):
            if not has_page(it):
                continue
            slug = str(it["slug"]).strip()
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
                print(f"  건너뜀(slug 형식 오류): {slug}")
                continue
            title = str(it.get("title", ""))
            summary = str(it.get("summary", ""))
            desc = re.sub(r"\s+", " ", summary).strip()
            desc = desc if len(desc) <= 150 else desc[:149] + "\u2026"
            canon = f"{SITE_URL}/bside/{slug}/"
            src = str(it.get("source", "")).strip()
            jsonld = {
                "@context": "https://schema.org", "@type": "Article",
                "headline": title, "description": desc,
                "datePublished": w.get("date", ""), "inLanguage": "ko",
                "mainEntityOfPage": canon, "image": f"{SITE_URL}/zebra-og.png",
                "publisher": {"@type": "Organization", "name": "지브라 베타",
                              "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/zebra-og.png"}},
            }
            doc = DETAIL.format(
                title_tag=attr(f"{title} — B-SIDE | 지브라 베타"),
                desc=attr(desc), canon=canon, og_title=attr(title),
                jsonld=json.dumps(jsonld, ensure_ascii=False, indent=2).replace("</", "<\\/"),
                category=esc(it.get("category", "")), label=esc(w.get("label", "")),
                title=esc(title), body=paragraphs(summary),
                source_html=(f'<p class="source">({esc(src)})</p>' if src else ""),
            )
            out = SITE / "bside" / slug / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(doc, encoding="utf-8")
            made.append(slug)
    return made

TEMPLATE = '<!DOCTYPE html>\n<html lang="ko">\n<head>\n<meta charset="UTF-8">\n<script async src="https://www.googletagmanager.com/gtag/js?id=G-B0TNF05GFQ"></script>\n<script>\n  window.dataLayer = window.dataLayer || [];\n  function gtag(){dataLayer.push(arguments);}\n  gtag(\'js\', new Date());\n  gtag(\'config\', \'G-B0TNF05GFQ\');\n</script>\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>B-SIDE — zebra beta</title>\n<meta name="description" content="지브라 베타가 매주 골라 전하는 음악·책·전시·영화 소식.">\n<link rel="canonical" href="https://zebrabeta.kr/bside/">\n<meta property="og:title" content="B-SIDE · zebra beta">\n<meta property="og:type" content="website">\n<meta property="og:url" content="https://zebrabeta.kr/bside/">\n<meta property="og:image" content="https://zebrabeta.kr/zebra-og.png">\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n<meta name="twitter:card" content="summary_large_image">\n<link rel="preconnect" href="https://fonts.googleapis.com">\n<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400;1,600&family=Cormorant+SC:wght@400;500&family=Noto+Serif+KR:wght@300;400;500&display=swap" rel="stylesheet">\n<style>\n  :root {\n    --cream: #EDE9DF;\n    --ink: #2B2A26;\n    --gray: #8b877c;\n    --faint: #b8b3a8;\n    --gold: #b89a5a;\n    --divider: #e1ddd3;\n  }\n  * { margin: 0; padding: 0; box-sizing: border-box; }\n  body {\n    background: var(--cream);\n    color: var(--ink);\n    font-family: \'Noto Serif KR\', serif;\n    -webkit-font-smoothing: antialiased;\n  }\n  .page {\n    max-width: 520px;\n    margin: 0 auto;\n    padding: 48px 24px 120px;\n  }\n  .header {\n    text-align: center;\n    margin-bottom: 72px;\n  }\n  .header h1 {\n    font-family: \'Cormorant Garamond\', serif;\n    font-weight: 400;\n    font-size: 18px;\n    letter-spacing: 1.68px;\n    color: rgb(139, 135, 124);\n    margin-bottom: 8px;\n  }\n  .header .updated {\n    font-family: \'Cormorant Garamond\', serif;\n    font-style: italic;\n    font-size: 11px;\n    color: rgb(169, 162, 151);\n  }\n  @media (max-width: 480px) {\n    .header { margin-bottom: 48px; }\n  }\n  .trend-list { list-style: none; }\n  .trend-item { border-bottom: 1px solid var(--divider); }\n  .trend-headline {\n    display: flex;\n    align-items: baseline;\n    gap: 10px;\n    padding: 18px 0;\n    cursor: pointer;\n    transition: color 0.2s;\n    -webkit-tap-highlight-color: transparent;\n  }\n  .trend-headline:hover { color: var(--gold); }\n  .trend-category {\n    font-family: \'Cormorant Garamond\', serif;\n    font-size: 11px;\n    letter-spacing: 0.1em;\n    text-transform: uppercase;\n    color: var(--faint);\n    flex-shrink: 0;\n    line-height: 1;\n    min-width: 32px;\n    padding-top: 3px;\n  }\n  .trend-title {\n    font-family: \'Noto Serif KR\', serif;\n    font-weight: 400;\n    font-size: 15px;\n    line-height: 1.65;\n    flex: 1;\n  }\n  .trend-arrow {\n    font-family: \'Cormorant Garamond\', serif;\n    font-size: 14px;\n    color: var(--faint);\n    flex-shrink: 0;\n    transition: transform 0.9s cubic-bezier(0.25, 0.1, 0.25, 1), color 0.6s ease;\n  }\n  .trend-item.open .trend-arrow {\n    transform: rotate(90deg);\n    color: var(--gold);\n  }\n  .trend-body {\n    max-height: 0;\n    overflow: hidden;\n    opacity: 0;\n    transition: max-height 1s cubic-bezier(0.25, 0.1, 0.25, 1), opacity 0.8s ease 0.15s, padding 1s cubic-bezier(0.25, 0.1, 0.25, 1);\n  }\n  .trend-item.open .trend-body {\n    max-height: 1000px;\n    opacity: 1;\n    padding-bottom: 20px;\n  }\n  .trend-summary {\n    font-family: \'Noto Serif KR\', serif;\n    font-weight: 300;\n    font-size: 13.5px;\n    line-height: 2;\n    color: var(--ink);\n    padding: 0 0 0 28px;\n    word-break: keep-all;\n  }\n  .trend-source {\n    font-family: \'Cormorant Garamond\', serif;\n    font-size: 11px;\n    letter-spacing: 0.08em;\n    color: var(--faint);\n    white-space: nowrap;\n  }\n  .footer {\n    margin-top: 150px;\n    text-align: center;\n  }\n  .colophon {\n    font-family: \'Cormorant Garamond\', serif;\n    font-style: italic;\n    font-weight: 300;\n    font-size: 12px;\n    letter-spacing: 0.18em;\n    color: rgb(169, 162, 151);\n  }\n  .home-link-wrap {\n    margin-top: 16px;\n  }\n  .home-link-wrap a {\n    font-family: \'Cormorant Garamond\', serif;\n    font-size: 12px;\n    letter-spacing: 0.16em;\n    color: rgb(169, 162, 151);\n    text-decoration: none;\n    transition: color 0.3s ease;\n  }\n  .home-link-wrap a:hover { color: var(--gold); }\n\n  /* ── 주차 폴딩 (B-SIDE weekly) ── */\n  .weeks { display: flex; flex-direction: column; }\n  .week.open { order: -1; margin-bottom: 36px; }\n  .week.open > .week-header { display: none; }\n  .week:not(.open) > .week-header { border-bottom-color: transparent; opacity: 0.85; }\n  .week > .week-header { transition: opacity 0.5s ease, color 0.2s; }\n  .week.open > .week-header .week-date { color: var(--ink); }\n  .week-header {\n    display: flex; align-items: baseline; gap: 10px;\n    padding: 22px 0; cursor: pointer; border-bottom: 1px solid var(--divider);\n    -webkit-tap-highlight-color: transparent; transition: color 0.2s;\n  }\n  .week-header:hover { color: var(--gold); }\n  .week-date {\n    font-family: \'Cormorant Garamond\', serif; font-style: italic;\n    font-size: 13px; letter-spacing: 0.08em; color: var(--gray);\n  }\n  .week-arrow {\n    font-family: \'Cormorant Garamond\', serif; font-size: 14px; color: var(--faint);\n    margin-left: auto; flex-shrink: 0;\n    transition: transform 0.9s cubic-bezier(0.25,0.1,0.25,1), color 0.6s ease;\n  }\n  .week.open > .week-header .week-arrow { transform: rotate(90deg); color: var(--gold); }\n  .week-items {\n    overflow: hidden; max-height: 0;\n    transition: max-height 1.1s cubic-bezier(0.25,0.1,0.25,1);\n  }\n  .week.open > .week-items { max-height: 12000px; }\n  .week[data-month] > .week-header { padding: 15px 0; }\n  .week[data-month] > .week-header .week-date { font-size: 12.5px; }\n  .year-row { display: flex; align-items: baseline; margin-top: 40px; padding: 18px 0 14px; border-top: 1px solid var(--divider); cursor: pointer; -webkit-tap-highlight-color: transparent; }\n  .year-row .week-date { font-family: \'Cormorant SC\', serif; font-style: normal; font-weight: 500; font-size: 13px; letter-spacing: 0.32em; color: var(--gray); }\n  .year-row:hover .week-date { color: var(--gold); }\n  .year-row ~ .year-row { margin-top: 0; }\n  .year-row.expanded .week-arrow { transform: rotate(90deg); color: var(--gold); }\n  .week[data-year]:not(.open) { display: none; padding-left: 18px; }\n  .week[data-year].shown:not(.open) { display: block; }\n  /* copy guard (same as issue pages): block text selection; right-click/copy via script below */\n  html,body{ -webkit-user-select:none; -moz-user-select:none; -ms-user-select:none; user-select:none; -webkit-touch-callout:none; }\n  a,button,iframe,input,textarea{ -webkit-user-select:auto; user-select:auto; }\n</style>\n</head>\n<body>\n<div class="page">\n  <header class="header">\n    <h1 style="font-family:\'Cormorant SC\',serif; font-weight:500; font-size:16px; letter-spacing:2.5px; color:rgb(139,135,124);">B-SIDE</h1>\n    <p class="updated" id="current-week">updated {{UPDATED}}</p>\n  </header>\n  <div class="weeks">\n{{WEEKS}}\n  </div>\n  <footer class="footer">\n    <p class="colophon">zebra beta &middot; movement 2.</p>\n    <div class="home-link-wrap"><a href="https://zebrabeta.kr">HOME</a></div>\n  </footer>\n</div>\n<script>\nfunction toggleWeek(el) {\n  var wk = el.closest(\'.week\');\n  var wasOpen = wk.classList.contains(\'open\');\n  document.querySelectorAll(\'.week.open\').forEach(function(w) { w.classList.remove(\'open\'); });\n  document.querySelectorAll(\'.trend-item.open\').forEach(function(i) { i.classList.remove(\'open\'); });\n  if (!wasOpen) wk.classList.add(\'open\');\n  var cw = document.getElementById(\'current-week\');\n  if (cw) cw.textContent = (wk.classList.contains(\'open\') ? wk : document.querySelector(\'.week\')).getAttribute(\'data-label\');\n  window.scrollTo({ top: 0, behavior: \'smooth\' });\n}\nfunction toggleYear(el) {\n  var on = !el.classList.contains(\'expanded\');\n  el.classList.toggle(\'expanded\', on);\n  document.querySelectorAll(\'.week[data-year="\' + el.getAttribute(\'data-year\') + \'"]\').forEach(function(w) { w.classList.toggle(\'shown\', on); });\n}\nfunction toggle(el) {\n  var item = el.closest(\'.trend-item\');\n  var wasOpen = item.classList.contains(\'open\');\n  document.querySelectorAll(\'.trend-item.open\').forEach(function(i) {\n    i.classList.remove(\'open\');\n  });\n  if (!wasOpen) item.classList.add(\'open\');\n}\n</script>\n<script>\n(function(){\n  var block=function(e){ e.preventDefault(); return false; };\n  document.addEventListener("contextmenu", block);\n  document.addEventListener("copy", block);\n  document.addEventListener("cut", block);\n  document.addEventListener("dragstart", block);\n})();\n</script>\n</body>\n</html>\n'

FEED_MONTHS = 3   # 피드에 남기는 달 수: 이번 달은 주 줄로, 그 앞 두 달은 달 줄로. 나머지는 연도 줄 안으로.
MONTHS = ["January","February","March","April","May","June","July",
          "August","September","October","November","December"]

def render_feed(shown):
    cur = shown[0]["date"][:7] if shown else ""          # 최신 주가 속한 달 (YYYY-MM)
    recent = [w for w in shown if w["date"][:7] == cur]
    older = [w for w in shown if w["date"][:7] != cur]
    blocks = [render_week(w, i == 0) for i, w in enumerate(recent)]
    groups = []                      # [(year, month, [weeks])] 최신순
    for w in older:
        y, m = w["date"][:4], int(w["date"][5:7])
        if groups and groups[-1][0] == y and groups[-1][1] == m:
            groups[-1][2].append(w)
        else:
            groups.append((y, m, [w]))
    seen_years = set()
    for gi, (y, m, ws) in enumerate(groups):
        past = gi >= FEED_MONTHS - 1
        if past and y not in seen_years:
            seen_years.add(y)
            blocks.append(f'  <div class="year-row" data-year="{esc(y)}" onclick="toggleYear(this)">\n'
                          f'    <span class="week-date">{esc(y)}</span>\n'
                          '    <span class="week-arrow">\u203a</span>\n  </div>')
        items = [it for w in ws for it in visible_items(w)]
        blocks.append(render_week(ws[0], False, head=f"{MONTHS[m-1]} {y}",
                                  items_src=items, year=(y if past else None)).replace('<section class="week"', '<section class="week" data-month="1"', 1))
    return blocks

def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    weeks = sorted(data.get("weeks", []), key=lambda w: w.get("date", ""), reverse=True)
    shown = [w for w in weeks if visible_items(w)]   # 보일 항목이 없는 주차는 피드에서 통째로 뺀다
    updated = shown[0]["label"] if shown else ""
    blocks = render_feed(shown)
    html = TEMPLATE.replace("{{UPDATED}}", esc(updated)).replace("{{WEEKS}}", "\n".join(blocks))
    OUT.write_text(html, encoding="utf-8")
    made = build_details(weeks)
    print(f"개별 페이지 {len(made)}개: " + ", ".join(made))
    print(f"\uc0dd\uc131 {OUT}  (\uc8fc\ucc28 {len(shown)} \u00b7 \ucd5c\uc2e0 {updated})")

if __name__ == "__main__":
    main()
