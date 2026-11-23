# "포트폴리오로" 링크는 custom/ (수강생 본인 규칙)

`/portfolio-update`가 렌더러를 템플릿으로 덮어써도 잊지 않도록 여기에 둡니다.

- 상세 문서·슬라이드의 "포트폴리오로" 링크는 기본 `index.html`이 아니라 직접 생성 페이지 **`custom/`**로 갑니다.
  - `assets/doc.js`: 위 빵부스러기·아래 바닥글·프로젝트를 못 찾았을 때 버튼 (3곳)
  - `assets/project-deck.js`: 표지 링크 목록·마지막 장면 카드(보이는 주소도 `PF.visibleUrl('custom/')`)·프로젝트를 못 찾았을 때 버튼·좁은 화면 안내 (4곳)
- **배포 첫 화면 = custom**: `.github/workflows/pages.yml`이 배포할 때만 사이트의 `index.html`을 `custom/index.html`(`../` → `./`)로 바꾸고,
  원래 렌더러는 `print.html`로 올립니다. 레포의 `index.html`은 렌더러 그대로 둡니다(바꾸지 않음 — PDF·점검·편집 모드가 씀).
  - `custom/index.html`을 다시 만들면 경로는 계속 `../`로 씁니다(배포가 바꿈). `../`가 data·src·theme·assets·doc·project·letter·자기소개서.md 말고 다른 것을 가리키면 배포 결과를 다시 봅니다.
  - Pages 설정 Source가 "GitHub Actions"여야 합니다. 사이트 첫 화면이 기본 페이지로 나오면 이 설정부터 봅니다.
- **`/portfolio-update` 뒤**: 위 두 파일에서 `href: 'index.html'`·`'index.html', 'page'`·`PF.visibleUrl('')`이 다시 생겼는지 보고, 있으면 `custom/`으로 되돌린 뒤 수강생에게 알립니다.
