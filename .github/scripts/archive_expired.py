"""만료된 issue 지면 처리 (archive-expired 워크플로가 매일 실행)

1) issue/{slug}/ 를 archive/{series}/{번호}/ 로 복사 (사본이 없을 때만)
2) 사본이 확인되면 issue/{slug}/index.html 을 '이관 안내' 페이지로 바꾼다.
   - 원본 HTML에 노트·크레딧이 남지 않게 (검색 수집·?archive=1 열람 차단)
   - <head>(제목·og·스타일·noindex)는 그대로 두고 본문만 안내문으로 교체
   - 이미지 파일은 그대로 둔다 (_data/issue.json 의 cover 가 참조)
안전장치: 이관 안내 페이지는 절대 archive 로 복사하지 않는다 (STUB 표식으로 구분).
"""
import json, os, re, shutil
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
STUB = "<!-- ZEBRA_EXPIRED_STUB -->"
ROBOTS = '<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">'
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

def make_stub(html):
    head = html[: html.index("<body")]
    if ROBOTS not in head:
        head = head.replace("</head>", ROBOTS + "\n</head>", 1)
    m = re.search(r'getElementById\("sheet"\)\.innerHTML\s*=\s*`(.*?)`;', html, re.S)
    moved = m.group(1) if m else DEFAULT_MOVED
    cls = re.search(r'<main class="([^"]*)" id="sheet">', html)
    cls = cls.group(1) if cls else "sheet"
    return head + "<body>\n" + STUB + '\n  <main class="' + cls + '" id="sheet">' + moved + "\n  </main>\n</body>\n</html>\n"

def main():
    now = datetime.now(KST)
    items = json.load(open("_data/issue.json", encoding="utf-8"))
    log = []
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
            continue                                   # 아직 공개 중
        slug = e["slug"]
        sid = e.get("series_id") or re.match(r"[a-z]+", slug).group(0)
        num = re.sub(r"^[a-z]+", "", slug) or slug
        src, dst = f"issue/{slug}", f"archive/{sid}/{num}"
        page = os.path.join(src, "index.html")
        if not os.path.isfile(page):
            continue
        html = open(page, encoding="utf-8").read()
        if "<body" not in html:
            print(f"::warning::{slug}: 원본 HTML 이상 — 건너뜀")
            continue
        stubbed = STUB in html
        apage = os.path.join(dst, "index.html")
        if not os.path.isfile(apage):
            if stubbed:
                print(f"::warning::{slug}: 원본이 이미 안내문인데 아카이브 사본이 없음 — 건너뜀")
                continue
            os.makedirs(dst, exist_ok=True)
            for f in os.listdir(src):
                shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
            log.append(f"{slug} -> {dst}")
        if not stubbed:
            a = open(apage, encoding="utf-8").read()
            if STUB in a or len(a) < 2000:
                print(f"::warning::{slug}: 아카이브 사본이 온전하지 않음 — 원본 유지")
                continue
            stub = make_stub(html)                     # 먼저 만들고 나서 쓴다 (실패 시 원본 보존)
            with open(page, "w", encoding="utf-8") as fh:
                fh.write(stub)
            log.append(f"{slug} stub")
    print("done:", log if log else "nothing new")
    open("/tmp/copied.txt", "w").write("\n".join(log))

if __name__ == "__main__":
    main()
