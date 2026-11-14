# 지브라베타 방문 기록 관리자 — 이어서 할 일 (1115)

[새 대화창에서 이 문서를 그대로 붙여 넣고 시작하세요. 저장소: deee60/zebra, 브랜치: claude/zebra-stats]

## 목표 (로드)
zebrabeta.kr 방문자를 덕통 관리자처럼 자세히 본다: 어느 나라·도시에서, 어디서 들어와서, 얼마나 머물고, 어떤 페이지를 어떤 순서로 보고,
어떤 기기·브라우저로 왔는지, 무엇을 눌렀는지. AI 관련 칸은 필요 없음. 로드는 비개발자 — 설명은 쉬운 한국어로, 한 단계씩.

## 사이트 구조 (확인됨)
- GitHub Pages 정적 사이트(CNAME zebrabeta.kr), HTML 약 128개. 서버·DB 없음.
- 페이지 생성기: `_build/build.py` + `_build/_template.html`(issue), `_build_bside/build_bside.py`, `_build_taste_everyone/build_taste_everyone.py`.
  GitHub Actions: build_bside.yml, build_taste_everyone.yml, publish-queue.yml, archive-expired.yml.
- 모든 페이지에 구글 애널리틱스(G-B0TNF05GFQ) 있음 — 그대로 둔다.
- 도메인은 로드의 Cloudflare 계정에 연결돼 있음(로드 확인). 덕통과 같은 Cloudflare · GitHub 계정.

## 이미 만든 것 (브랜치 claude/zebra-stats, 폴더 `_stats/`, 아직 배포 안 함)
- `worker.js` — Cloudflare Worker. 주소 zebrabeta.kr/_z/* 에서만 동작(사이트 본체는 GitHub Pages 그대로).
  - `GET /_z/t.js` 추적 스크립트 · `POST /_z/hit` 페이지 열림 · `POST /_z/beat` 머문 시간·스크롤·누른 링크(15초마다 + 떠날 때)
  - `GET /_z/admin` 관리자 화면 · `GET /_z/api/{summary,pages,sources,places,tech,clicks,visitors,visitor,export}` (Bearer ADMIN_TOKEN)
  - 표는 첫 요청 때 자동 생성(ensure). 매일 1회(cron) 180일 지난 기록 삭제. 봇 UA 제외.
  - 저장: 경로·제목·들어온 곳(바깥=도메인, 안=경로)·utm·나라/지역/도시/시간대/통신사(Cloudflare cf)·기기/OS/브라우저(인앱: 카톡·네이버·인스타 구분)·언어·화면크기·처음 방문 여부·머문 시간·스크롤%·누른 링크(최대 20).
  - 저장 안 함: IP, 이름, 이메일. 방문자 구분은 브라우저 localStorage 무작위 id(zv), 방문(세션)은 30분 무활동이면 새로.
- `t.js.txt` — 추적 스크립트(쿠키 없음, sendBeacon).
- `admin.html` — 관리자 화면(한국어, 한국 시간). 토큰 입력 → 기간(1시간~180일, 날짜 하루) · 요약 타일(지금 보는 사람, 방문자, 처음 온 사람, 방문 수, 페이지뷰, 방문당 머문 시간, 방문당 페이지, 한 페이지만 보고 나감) · 시간대별 막대 · 탭(많이 본 페이지: 평균 시간/스크롤/끝까지 읽음, 들어온 곳, 지역, 기기·브라우저·언어·통신사·화면, 누른 링크, 방문자 목록 → 한 사람의 전체 방문 흐름) · CSV 내려받기 · 60초 자동 새로고침.
- `schema.sql`, `wrangler.jsonc`(route zebrabeta.kr/_z/*, D1 바인딩 DB, cron), `package.json`(wrangler 4), `.gitignore`(.dev.vars 등).
- `_config.yml` exclude 에 `_stats` 추가(공개 사이트에 안 올라감).
- 로컬 테스트(wrangler dev --local) 통과: 수집·봇 차단·토큰 없는 요청 401·모든 API·관리자 화면·한 사람 흐름 화면.

## 남은 일 (순서대로)
1. **버그: 시간대별 막대가 안 보임.** `.chart div`에 높이가 없어 막대(%)가 0으로 그려짐 → `.chart div{height:100%}` 등으로 고치고 캡처로 확인.
2. **추적 태그를 모든 페이지에 넣기.** 각 HTML의 GA 스니펫 바로 뒤(`gtag('config', 'G-B0TNF05GFQ');\n</script>` 다음)에
   `<script src="/_z/t.js" defer></script>` 한 줄. 이미 만들어진 HTML 전부 + 생성기 3곳(템플릿/py 안의 GA 스니펫 문자열)에도 넣어서 앞으로 생성되는 페이지에도 들어가게. archive/ 도 포함할지 로드에게 확인.
3. **개인정보 안내.** 사이트에 방침 페이지가 있는지 확인 → 없으면 짧은 안내 문구(방문 기록 수집 항목 · 180일 후 삭제 · IP 미저장)를 어디에 둘지 로드와 정한다.
4. **로드가 Cloudflare에서 할 일 안내(쉬운 말, 한 단계씩, 화면 보며):**
   a. Workers & Pages → D1 → 데이터베이스 만들기, 이름 `zebra-stats` → 만들어진 Database ID를 Claude에게 알려 줌 → Claude가 wrangler.jsonc의 `REPLACE_WITH_D1_ID`에 넣고 커밋(ID는 비밀값 아님).
   b. Workers & Pages → 만들기 → GitHub 저장소 deee60/zebra 연결(Workers Builds), 루트 디렉터리 `_stats`, 배포 명령 `npx wrangler deploy`, 브랜치는 PR 합친 뒤 main.
   c. 그 Worker 설정 → 변수와 비밀 → 비밀 `ADMIN_TOKEN`(긴 무작위 문자열, 로드가 직접 입력·보관. Claude는 값을 보거나 만들지 않는다 — 만드는 방법만 안내).
   d. 배포 후 확인: zebrabeta.kr/_z/t.js 가 열리는지, 사이트를 몇 번 열고 zebrabeta.kr/_z/admin 에서 토큰으로 들어가 숫자가 오르는지.
5. PR 열기(제목 예: "Visit stats Worker + admin") → 로드가 "합쳐" 하면 합치고 배포 확인.

## 지켜야 할 것
- 비밀값(ADMIN_TOKEN)은 코드·커밋·대화에 쓰지 않는다. 저장소가 **공개(public)** 라서 더 조심.
- 기록 스크립트 오류가 사이트 화면을 깨뜨리면 안 된다(전부 try/catch, 실패해도 조용히).
- GA는 그대로 둔다. 기존 생성기·워크플로 동작을 바꾸지 않는다(태그 한 줄 추가만).
- 바꾼 뒤엔 실제 화면을 띄워 캡처로 확인하고 보고한다.
