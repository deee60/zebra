_build_taste_everyone/ — 취향의 발견 · 모두의 큐레이션 개별 페이지 생성기

이 폴더는 taste·everyone 항목별로 정적 HTML 페이지를 자동 생성한다.
(SEO/검색 유입용. 사람 눈에 보이는 화면은 기존 SPA 그대로 유지.)

실행:
  python3 _build_taste_everyone/build_taste_everyone.py

읽는 데이터:
  taste/taste.json       (항목마다 slug 있으면 페이지 생성)
  everyone/everyone.json (곡마다 slug 있으면 페이지 생성)

만드는 파일:
  taste/<slug>/index.html
  everyone/<slug>/index.html
  sitemap.xml (전체 재작성)

혼동 주의:
  · 건조주의보 등 issue(72시간 발행물) 생성기는 _build/build.py 다른 파일이다.
  · 이 스크립트는 SPA 목록 화면(taste/index.html, everyone/index.html)은 절대 건드리지 않는다.
