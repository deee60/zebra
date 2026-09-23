#!/usr/bin/env python3
"""B-SIDE 렌더러 — bside/bside.json 을 읽어 bside/index.html 을 그린다.
주차(week) 단위: 최신 주는 펼쳐진 채 맨 위, 지난 주들은 접혀서 아래로(날짜 클릭 시 펼침).
항목은 기존 아코디언(headline 클릭 → 본문) 유지. selected 개념 없음 — bside.json 에 든 것만 그린다.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).parent          # _build_bside/
SITE = ROOT.parent                    # repo root
DATA = SITE / "bside" / "bside.json"
OUT  = SITE / "bside" / "index.html"

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

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

def render_week(w, newest):
    items = "\n".join(render_item(it) for it in w.get("items", []))
    cls = "week open" if newest else "week"
    return (
        f'  <section class="{cls}" data-label="{esc(w.get("label",""))}">\n'
        '    <div class="week-header" onclick="toggleWeek(this)">\n'
        f'      <span class="week-date">updated {esc(w.get("label",""))}</span>\n'
        '      <span class="week-arrow">\u203a</span>\n'
        '    </div>\n'
        '    <ul class="trend-list week-items">\n'
        f'{items}\n'
        '    </ul>\n'
        '  </section>'
    )

TEMPLATE = '<!DOCTYPE html>\n<html lang="ko">\n<head>\n<meta charset="UTF-8">\n<script async src="https://www.googletagmanager.com/gtag/js?id=G-B0TNF05GFQ"></script>\n<script>\n  window.dataLayer = window.dataLayer || [];\n  function gtag(){dataLayer.push(arguments);}\n  gtag(\'js\', new Date());\n  gtag(\'config\', \'G-B0TNF05GFQ\');\n</script>\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>B-SIDE — zebra beta</title>\n<meta property="og:title" content="B-SIDE · zebra beta">\n<meta property="og:type" content="website">\n<meta property="og:url" content="https://zebrabeta.kr/bside/">\n<meta property="og:image" content="https://zebrabeta.kr/zebra-og.png">\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n<meta name="twitter:card" content="summary_large_image">\n<link rel="preconnect" href="https://fonts.googleapis.com">\n<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400;1,600&family=Cormorant+SC:wght@400;500&family=Noto+Serif+KR:wght@300;400;500&display=swap" rel="stylesheet">\n<style>\n  :root {\n    --cream: #EDE9DF;\n    --ink: #2B2A26;\n    --gray: #8b877c;\n    --faint: #b8b3a8;\n    --gold: #b89a5a;\n    --divider: #e1ddd3;\n  }\n  * { margin: 0; padding: 0; box-sizing: border-box; }\n  body {\n    background: var(--cream);\n    color: var(--ink);\n    font-family: \'Noto Serif KR\', serif;\n    -webkit-font-smoothing: antialiased;\n  }\n  .page {\n    max-width: 520px;\n    margin: 0 auto;\n    padding: 48px 24px 120px;\n  }\n  .header {\n    text-align: center;\n    margin-bottom: 72px;\n  }\n  .header h1 {\n    font-family: \'Cormorant Garamond\', serif;\n    font-weight: 400;\n    font-size: 18px;\n    letter-spacing: 1.68px;\n    color: rgb(139, 135, 124);\n    margin-bottom: 8px;\n  }\n  .header .updated {\n    font-family: \'Cormorant Garamond\', serif;\n    font-style: italic;\n    font-size: 11px;\n    color: rgb(169, 162, 151);\n  }\n  @media (max-width: 480px) {\n    .header { margin-bottom: 48px; }\n  }\n  .trend-list { list-style: none; }\n  .trend-item { border-bottom: 1px solid var(--divider); }\n  .trend-headline {\n    display: flex;\n    align-items: baseline;\n    gap: 10px;\n    padding: 18px 0;\n    cursor: pointer;\n    transition: color 0.2s;\n    -webkit-tap-highlight-color: transparent;\n  }\n  .trend-headline:hover { color: var(--gold); }\n  .trend-category {\n    font-family: \'Cormorant Garamond\', serif;\n    font-size: 11px;\n    letter-spacing: 0.1em;\n    text-transform: uppercase;\n    color: var(--faint);\n    flex-shrink: 0;\n    line-height: 1;\n    min-width: 32px;\n    padding-top: 3px;\n  }\n  .trend-title {\n    font-family: \'Noto Serif KR\', serif;\n    font-weight: 400;\n    font-size: 15px;\n    line-height: 1.65;\n    flex: 1;\n  }\n  .trend-arrow {\n    font-family: \'Cormorant Garamond\', serif;\n    font-size: 14px;\n    color: var(--faint);\n    flex-shrink: 0;\n    transition: transform 0.9s cubic-bezier(0.25, 0.1, 0.25, 1), color 0.6s ease;\n  }\n  .trend-item.open .trend-arrow {\n    transform: rotate(90deg);\n    color: var(--gold);\n  }\n  .trend-body {\n    max-height: 0;\n    overflow: hidden;\n    opacity: 0;\n    transition: max-height 1s cubic-bezier(0.25, 0.1, 0.25, 1), opacity 0.8s ease 0.15s, padding 1s cubic-bezier(0.25, 0.1, 0.25, 1);\n  }\n  .trend-item.open .trend-body {\n    max-height: 600px;\n    opacity: 1;\n    padding-bottom: 20px;\n  }\n  .trend-summary {\n    font-family: \'Noto Serif KR\', serif;\n    font-weight: 300;\n    font-size: 13.5px;\n    line-height: 2;\n    color: var(--ink);\n    padding: 0 0 0 28px;\n    word-break: keep-all;\n  }\n  .trend-source {\n    font-family: \'Cormorant Garamond\', serif;\n    font-size: 11px;\n    letter-spacing: 0.08em;\n    color: var(--faint);\n    white-space: nowrap;\n  }\n  .footer {\n    margin-top: 150px;\n    text-align: center;\n  }\n  .colophon {\n    font-family: \'Cormorant Garamond\', serif;\n    font-style: italic;\n    font-weight: 300;\n    font-size: 12px;\n    letter-spacing: 0.18em;\n    color: rgb(169, 162, 151);\n  }\n  .home-link-wrap {\n    margin-top: 16px;\n  }\n  .home-link-wrap a {\n    font-family: \'Cormorant Garamond\', serif;\n    font-size: 12px;\n    letter-spacing: 0.16em;\n    color: rgb(169, 162, 151);\n    text-decoration: none;\n    transition: color 0.3s ease;\n  }\n  .home-link-wrap a:hover { color: var(--gold); }\n\n  /* ── 주차 폴딩 (B-SIDE weekly) ── */\n  .weeks { display: flex; flex-direction: column; }\n  .week.open { order: -1; margin-bottom: 36px; }\n  .week.open > .week-header { display: none; }\n  .week:not(.open) > .week-header { border-bottom-color: transparent; opacity: 0.4; }\n  .week > .week-header { transition: opacity 0.5s ease, color 0.2s; }\n  .week.open > .week-header .week-date { color: var(--ink); }\n  .week-header {\n    display: flex; align-items: baseline; gap: 10px;\n    padding: 22px 0; cursor: pointer; border-bottom: 1px solid var(--divider);\n    -webkit-tap-highlight-color: transparent; transition: color 0.2s;\n  }\n  .week-header:hover { color: var(--gold); }\n  .week-date {\n    font-family: \'Cormorant Garamond\', serif; font-style: italic;\n    font-size: 13px; letter-spacing: 0.08em; color: var(--gray);\n  }\n  .week-arrow {\n    font-family: \'Cormorant Garamond\', serif; font-size: 14px; color: var(--faint);\n    margin-left: auto; flex-shrink: 0;\n    transition: transform 0.9s cubic-bezier(0.25,0.1,0.25,1), color 0.6s ease;\n  }\n  .week.open > .week-header .week-arrow { transform: rotate(90deg); color: var(--gold); }\n  .week-items {\n    overflow: hidden; max-height: 0;\n    transition: max-height 1.1s cubic-bezier(0.25,0.1,0.25,1);\n  }\n  .week.open > .week-items { max-height: 6000px; }\n</style>\n</head>\n<body>\n<div class="page">\n  <header class="header">\n    <h1 style="font-family:\'Cormorant SC\',serif; font-weight:500; font-size:16px; letter-spacing:2.5px; color:rgb(139,135,124);">B-SIDE</h1>\n    <p class="updated" id="current-week">updated {{UPDATED}}</p>\n  </header>\n  <div class="weeks">\n{{WEEKS}}\n  </div>\n  <footer class="footer">\n    <p class="colophon">zebra beta &middot; movement 2.</p>\n    <div class="home-link-wrap"><a href="https://zebrabeta.kr">HOME</a></div>\n  </footer>\n</div>\n<script>\nfunction toggleWeek(el) {\n  var wk = el.closest(\'.week\');\n  var wasOpen = wk.classList.contains(\'open\');\n  document.querySelectorAll(\'.week.open\').forEach(function(w) { w.classList.remove(\'open\'); });\n  document.querySelectorAll(\'.trend-item.open\').forEach(function(i) { i.classList.remove(\'open\'); });\n  if (!wasOpen) wk.classList.add(\'open\');\n  var cw = document.getElementById(\'current-week\');\n  if (cw) cw.textContent = \'updated \' + wk.getAttribute(\'data-label\');\n  window.scrollTo({ top: 0, behavior: \'smooth\' });\n}\nfunction toggle(el) {\n  var item = el.closest(\'.trend-item\');\n  var wasOpen = item.classList.contains(\'open\');\n  document.querySelectorAll(\'.trend-item.open\').forEach(function(i) {\n    i.classList.remove(\'open\');\n  });\n  if (!wasOpen) item.classList.add(\'open\');\n}\n</script>\n</body>\n</html>\n'

def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    weeks = sorted(data.get("weeks", []), key=lambda w: w.get("date", ""), reverse=True)
    updated = weeks[0]["label"] if weeks else ""
    blocks = [render_week(w, i == 0) for i, w in enumerate(weeks)]
    html = TEMPLATE.replace("{{UPDATED}}", esc(updated)).replace("{{WEEKS}}", "\n".join(blocks))
    OUT.write_text(html, encoding="utf-8")
    print(f"\uc0dd\uc131 {OUT}  (\uc8fc\ucc28 {len(weeks)} \u00b7 \ucd5c\uc2e0 {updated})")

if __name__ == "__main__":
    main()
