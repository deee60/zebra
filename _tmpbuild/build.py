#!/usr/bin/env python3
"""
ZEBRA BETA 지면 생성기

사용법:
    python3 build.py issues/vol34.json

하는 일:
  · 계절 + 자켓 채도로 배경색 계산 (자켓이 라우드하면 지면을 죽인다)
  · 상단 배치 A/B/C 선택 — 최근 회차와 겹치지 않게
  · EXPIRES = 발행시각 + 72시간, 이관 예고 문구 자동 생성
  · 자켓을 base64로 심어 단일 HTML 출력
  · history.json 에 이력 기록 (다음 회차 연속 회피용)
"""

import base64, colorsys, json, random, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent
KST = timezone(timedelta(hours=9))
WINDOW_HOURS = 72

# ── 계절 팔레트 (색상환 각도). 잔잔한 범위만 사용 ────────────────
SEASON_HUES = {
    "spring": [95, 78, 45],    # 연둣빛 · 새잎 · 햇빛 모래
    "summer": [205, 190, 172], # 하늘 · 물빛 · 청록
    "autumn": [35, 22, 48],    # 모래 · 흙빛 · 마른 풀
    "winter": [215, 232, 200], # 회청 · 남빛 · 서늘한 청
}
SEASON_KO = {"spring": "봄", "summer": "여름", "autumn": "가을", "winter": "겨울"}
LAYOUTS = ["lay-a", "lay-b", "lay-c"]


def season_of(dt):
    m = dt.month
    if m in (3, 4, 5):   return "spring"
    if m in (6, 7, 8):   return "summer"
    if m in (9, 10, 11): return "autumn"
    return "winter"


def jacket_stats(path):
    """자켓의 평균 채도·명도 (0~1). 작게 줄여서 빠르게 계산."""
    im = Image.open(path).convert("RGB")
    im.thumbnail((80, 80))
    raw = im.tobytes()
    sat = light = 0.0
    n = len(raw) // 3
    for i in range(0, len(raw), 3):
        h, l, s = colorsys.rgb_to_hls(raw[i] / 255, raw[i+1] / 255, raw[i+2] / 255)
        sat += s
        light += l
    return sat / n, light / n


def pick_bg(season, sat, light, recent_hues):
    """자켓이 화려하면 배경 채도를 낮추고, 어두우면 배경을 밝힌다."""
    hues = SEASON_HUES[season]
    # 최근 3회와 색상환에서 40도 이상 떨어진 색만 후보로
    def far(h):
        return all(min(abs(h - r), 360 - abs(h - r)) >= 40 for r in recent_hues)
    cands = [h for h in hues if far(h)] or hues
    hue = random.choice(cands)

    if sat > 0.45:    s = 0.07   # 라우드한 자켓 → 거의 무채색
    elif sat > 0.22:  s = 0.14
    else:             s = 0.22   # 조용한 자켓 → 배경이 색을 조금 가짐

    if light < 0.40:  l = 0.84   # 어두운 자켓 → 배경 밝게
    elif light > 0.70: l = 0.74  # 밝은 자켓 → 톤 내림
    else:             l = 0.80

    r, g, b = colorsys.hls_to_rgb(hue / 360, l, s)
    return hue, "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def pick_layout(recent_layouts, forced=None):
    if forced:
        return forced
    avoid = set(recent_layouts[-2:])
    cands = [x for x in LAYOUTS if x not in avoid] or LAYOUTS
    return random.choice(cands)


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def build_upper(cfg, layout):
    # jacket_mode: "embed"(기본, base64 삽입) 또는 "external"(같은 폴더의 파일 참조)
    if cfg.get("jacket_mode", "external") == "external":
        src = cfg.get("jacket_src") or f'{cfg["slug"]}.jpg'
    else:
        src = "data:image/jpeg;base64,{{JACKET}}"
    plate = ('    <figure class="plate">\n'
             f'      <img src="{src}" alt="앨범 커버">\n'
             '    </figure>')
    romaji = cfg.get("romaji", "").strip()
    # stamp:true 면 series 를 letterpress 인장으로 (여름밤 series 자리 그대로, 크기만 눌림 질감).
    # false 면 일반 텍스트 series (번외).
    if cfg.get("stamp"):
        stamp_label = cfg.get("stamp_text") or cfg["series"]
        series_html = (
            '      <div class="stamp"><span class="sp-t">'
            f'{esc(stamp_label)}</span><span class="sp-line"></span></div>\n'
        )
    else:
        series_html = f'      <p class="series">{esc(cfg["series"])}</p>\n'
    # 곡명 부제 축소: song 안의 (...) 괄호 부분을 작은 span 으로
    song_html = esc(cfg["song"])
    m = re.match(r"^(.*?)\s*(\([^)]*\))\s*$", cfg["song"])
    if m:
        song_html = f'{esc(m.group(1))} <span class="sub">{esc(m.group(2))}</span>'
    titles = (
        '    <div class="titles">\n'
        f'{series_html}'
        f'      <h1>{song_html}</h1>\n'
        f'      <p class="romaji">{esc(romaji)}</p>\n'
        f'      <p class="artist">{esc(cfg["artist"])}</p>\n'
        '    </div>'
    )
    # B는 제목이 먼저, A·C는 자켓이 먼저 (여름밤 04 그대로)
    return f"{titles}\n\n{plate}" if layout == "lay-b" else f"{plate}\n\n{titles}"


def build_note(text, credit=""):
    text = (text or "").strip()
    credit = (credit or "").strip()
    out = ""
    if text:
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        for p in paras:
            if p.startswith("[안내]"):
                out += f'<div class="aside">{esc(p[4:].strip())}</div>'
            else:
                out += f"<p>{esc(p)}</p>"
    if credit:
        lines = "<br>".join(esc(l.strip()) for l in credit.split("\n") if l.strip())
        out += f'<div class="credit">{lines}</div>'
    return out


OFF_MSG = "스트리밍 권리가 없습니다"

SERVICES = [
    ("Apple Music", True), ("Spotify", True), ("YouTube Music", True), ("Tidal", True),
    ("멜론", False), ("지니", False), ("벅스", False),
]


def build_listen(links, icons):
    """7개 칩을 항상 낸다. 링크가 없거나 권리가 없으면 톤다운 + 호버 안내, 클릭 불가."""
    rows = []
    for latin_row, label in ((True, "해외 스트리밍"), (False, "국내 스트리밍")):
        items = []
        for name, is_latin in SERVICES:
            if is_latin != latin_row:
                continue
            cls = " latin" if is_latin else ""
            v = links.get(name)
            url = off = None
            if isinstance(v, str) and v.strip():
                url = v.strip()
            elif isinstance(v, dict):
                off = v.get("off") or OFF_MSG
            else:
                off = OFF_MSG

            if url:
                attr = f' class="{cls.strip()}"' if cls else ""
                items.append(f'        <a{attr} href="{esc(url)}" target="_blank" '
                             f'rel="noopener">{icons[name]}{name}</a>')
            else:
                items.append(f'        <span class="off{cls}" data-off="{esc(off)}" '
                             f'aria-disabled="true">{icons[name]}{name}</span>')
        rows.append(f'      <nav class="listen-row" aria-label="{label}">\n'
                    + "\n".join(items) + "\n      </nav>")
    return "\n".join(rows)


def build_film(yt_id, caption):
    if not yt_id:
        return ""
    return (
        '    <figure class="film">\n'
        '      <div class="mat">\n'
        '        <div class="frame">\n'
        f'          <iframe src="https://www.youtube-nocookie.com/embed/{esc(yt_id)}" '
        f'title="{esc(caption)}" loading="lazy" '
        'allow="accelerometer; clipboard-write; encrypted-media; picture-in-picture; web-share" '
        'allowfullscreen></iframe>\n'
        '        </div>\n'
        '      </div>\n'
        f'      <figcaption>{esc(caption)}</figcaption>\n'
        '    </figure>'
    )


def notice_text(expires_dt):
    """'이 지면은 8월 3일 자정에 아카이브로 이관됩니다' — EXPIRES에서 자동 생성"""
    return f"이 지면은 {expires_dt.month}월 {expires_dt.day}일 자정에 아카이브로 이관됩니다"


URL_PATTERNS = {
    "Apple Music":   r"^https://music\.apple\.com/\w+/song/.+/\d+",
    "Spotify":       r"^https://open\.spotify\.com/track/[\w]+",
    "YouTube Music": r"^https://music\.youtube\.com/watch\?v=[\w-]{11}$",
    "Tidal":         r"^https://(listen\.)?tidal\.com/track/\d+",
    "멜론":          r"^https://www\.melon\.com/song/detail\.htm\?songId=\d+$",
    "지니":          r"^https://www\.genie\.co\.kr/detail/songInfo\?xgnm=\d+$",
    "벅스":          r"^https://music\.bugs\.co\.kr/track/\d+$",
}


def validate(cfg):
    """빠뜨림과 형식 오류를 구조적으로 막는다. 7개 서비스를 모두 '명시'해야 통과."""
    errs = []
    missing = [k for k in ("slug", "series", "song", "artist", "published",
                           "jacket", "youtube", "caption") if not str(cfg.get(k, "")).strip()]
    if missing:
        errs.append("필수 필드 누락    : " + ", ".join(missing))

    slug = str(cfg.get("slug", "")).strip()
    if slug.endswith(".html") or "/" in slug:
        errs.append(f"slug 형식        : '{slug}' — 확장자·슬래시 없이 'summernight04' 형태여야 합니다")

    yt = str(cfg.get("youtube", "")).strip()
    if yt and not re.fullmatch(r"[\w-]{11}", yt):
        errs.append(f"유튜브 ID 형식    : '{yt}' — 11자리여야 합니다")

    links = cfg.get("links") or {}
    undeclared = [n for n, _ in SERVICES if n not in links]
    if undeclared:
        errs.append("링크 미선언       : " + ", ".join(undeclared)
                    + '\n                    URL 또는 null 로 명시해야 합니다')

    for name, _ in SERVICES:
        v = links.get(name)
        if isinstance(v, str) and v.strip():
            if not re.match(URL_PATTERNS[name], v.strip()):
                errs.append(f"{name} 주소 형식 오류\n"
                            f"                    받은 값 : {v.strip()}\n"
                            f"                    기대 형식: {URL_PATTERNS[name]}")

    # 유튜브 뮤직 링크와 임베드 ID가 어긋나면 잡는다
    ym = links.get("YouTube Music")
    if yt and isinstance(ym, str) and yt not in ym:
        errs.append(f"유튜브 불일치     : 임베드 {yt} / 링크 {ym}")

    if errs:
        print("생성 중단 — 확인이 필요합니다\n")
        for e in errs:
            print("  " + e)
        sys.exit(1)


def main(cfg_path):
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    validate(cfg)
    icons = json.loads((ROOT / "icons.json").read_text(encoding="utf-8"))
    tpl = (ROOT / "_template.html").read_text(encoding="utf-8")
    css = (ROOT / "base.css").read_text(encoding="utf-8")

    hist_path = ROOT / "history.json"
    hist = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else []

    published = datetime.fromisoformat(cfg["published"]).replace(tzinfo=KST)
    expires = (published + timedelta(hours=WINDOW_HOURS)).replace(
        hour=23, minute=59, second=59, microsecond=0)

    jacket = ROOT / cfg["jacket"]
    sat, light = jacket_stats(jacket)
    season = cfg.get("season") or season_of(published)

    recent_hues = [h["hue"] for h in hist[-3:]]
    recent_layouts = [h["layout"] for h in hist]
    hue, bg = pick_bg(season, sat, light, recent_hues)
    layout = pick_layout(recent_layouts, cfg.get("layout"))

    b64 = base64.b64encode(jacket.read_bytes()).decode()

    html = (tpl
        .replace("{{CSS}}", css.replace("{{BG}}", bg))
        .replace("{{LAYOUT}}", layout)
        .replace("{{PAGE_TITLE}}", esc(f'{cfg["series"]} | Zebra Beta'))
        .replace("{{OG_TITLE}}", esc(f'{cfg["song"]} — {cfg["artist"]}'))
        .replace("{{OG_DESC}}", esc(cfg.get("og_desc", "zebra beta movement 2.")))
        .replace("{{NOTICE}}", notice_text(expires))
        .replace("{{UPPER}}", build_upper(cfg, layout))
        .replace("{{NOTE}}", build_note(cfg.get("note"), cfg.get("credit")))
        .replace("{{LISTEN}}", build_listen(cfg.get("links", {}), icons))
        .replace("{{FILM}}", build_film(cfg.get("youtube"), cfg.get("caption", "")))
        .replace("{{EXPIRES}}", expires.isoformat())
        .replace("{{JACKET}}", b64))

    out = ROOT / "out" / "issue" / cfg["slug"] / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    hist = [h for h in hist if h.get("slug") != cfg["slug"]]
    hist.append({
        "slug": cfg["slug"], "kind": cfg.get("kind", "music"),
        "series": cfg["series"], "title": cfg["song"],
        "romaji": cfg.get("romaji", ""), "artist": cfg["artist"],
        "path": f'issue/{cfg["slug"]}/',
        "cover": f'issue/{cfg["slug"]}/{cfg.get("jacket_src") or cfg["slug"]+".jpg"}',
        "published": cfg["published"][:10],
        "expires": expires.isoformat(),
        "layout": layout, "hue": hue, "bg": bg, "season": season,
    })
    hist.sort(key=lambda h: h["published"])
    hist_path.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")

    # 발행 목록 — 공개 저장소의 _data/issue.json 으로 커밋한다
    FIELDS = ("slug","kind","series","title","romaji","artist",
              "path","cover","published","expires","layout","bg")
    listing = [{k: h[k] for k in FIELDS if k in h} for h in hist]
    idx = ROOT / "out" / "_data" / "issue.json"
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text(json.dumps(listing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"생성  {out}")
    print(f"  배치      {layout}  (곡명 {{'lay-a':26,'lay-b':28,'lay-c':24}}[layout]px)"
          .replace("{'lay-a':26,'lay-b':28,'lay-c':24}[layout]",
                   str({'lay-a':26,'lay-b':28,'lay-c':24}[layout])))
    print(f"  배경      {bg}   (계절 {SEASON_KO[season]} · 색상 {hue}°)")
    print(f"  자켓      채도 {sat:.2f} · 명도 {light:.2f} → 배경 채도 {'낮음' if sat>0.45 else '보통' if sat>0.22 else '높음'}")
    print(f"  노출      ~ {expires:%Y-%m-%d %H:%M} (72시간)")
    print(f"  노트      {'있음' if cfg.get('note') else '없음 (여백 유지)'}")
    print(f"  용량      {len(html)/1024:.0f}KB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "issues/latest.json")
