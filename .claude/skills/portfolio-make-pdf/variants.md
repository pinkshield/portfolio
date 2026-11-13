# PDF 배치 다듬기 후보 (theme/pdf.css에 넣는 조각)

**패턴은 어느 페이지에나, 조각의 선택자는 예시입니다.** 아래 B~H의 선택자(`.stk`, `.sec.proj`, `.fe-list`, `#contact .cols3` …)는
이 스킬을 처음 만든 페이지(템플릿을 `/portfolio-custom`으로 바꾼 한 수강생의 레이아웃)의 것입니다. 다른 페이지에서는 그 페이지의 `index.html`을 읽고
같은 역할의 요소(기술 스택 격자, 프로젝트 소개의 [정보 | 대표 그림], 기능 목록, 연락처 단 …)를 찾아 선택자만 바꿔 씁니다.

조각은 모두 `@media print { … }` 안에 넣습니다(`@page` 규칙만 밖). 도구가 이 CSS를 페이지 인쇄 규칙 **뒤에** 넣으므로 같은 선택자면 이깁니다
(원래 규칙에 `!important`가 있으면 조각에도). 한 번에 하나씩 시험하고, 좋아진 것끼리 묶어 다시 시험합니다.
배치 폭·글씨 규칙은 맨 위 설정 줄(`/* layout-px: N */` 등)로 정합니다(도구가 읽음).

배치 폭(1040)에서 쪽 하나의 본문 높이 ≈ 1560px(쪽 위·아래 여백 12mm 기준), 폭 1040px. 배치 폭을 줄이면 둘 다 같은 비율로 줄어 **글씨는 커지고 한 쪽에 들어가는 양은 줄어듭니다**
(폭 960 → 높이 ≈ 1440 · 900 → ≈ 1350 · 780 → ≈ 1170). 쪽 위 여백을 늘리면(예: 20mm) 그만큼 더 줄어듭니다.

## P. 처음 준비 패턴 — 기본 인쇄 규칙이 PDF 규칙과 어긋날 때

템플릿 페이지의 인쇄 규칙은 대개 "A4 폭(약 688px) 휴대폰 배치 + 버튼 숨김 + 주소 목록"을 전제로 합니다. 도구가 넓은 배치를 줄여 찍으므로 아래처럼 맞춥니다.
선택자는 그 페이지의 것을 찾아 바꿉니다.

| 패턴 | 조각(예) | 언제 |
|---|---|---|
| P-1 흰 종이 | `:root { --bg: #fff !important; --ink: #20233A !important; … } body { background: #fff !important; }` | 인쇄에서 어두운 테마가 남을 때(대개 페이지에 이미 있음) |
| P-2 쪽 여백 | `@page { margin-top: 20mm; }` (밖에) | 쪽 위가 너무 붙어 보일 때. 도구가 이 값으로 쪽 높이를 계산 |
| P-3 큰 절은 새 쪽에서 | `#stack, .sec.proj, #glance { break-before: page; padding-top: 0 !important; }` | 절 머리가 쪽 중간에서 시작하거나 위가 비어 보일 때 |
| P-4 링크 버튼 보이기 | `.btn-links, .cap { display: flex !important; }` · 버튼 묶음이 `.no-print`면 그 묶음만 `display: flex !important` | 화면의 링크 버튼이 PDF에서 사라질 때(규칙 3) |
| P-5 주소 목록 숨기기 | `.purls, .print-urls { display: none !important; }` (맨 아래 연락처의 주소는 그대로) | 버튼 대신 주소를 글로 풀어 쓴 목록이 있을 때(규칙 3) |
| P-6 링크 밑줄·화살표 | `a.tlink { text-decoration-line: underline !important; } .nt-icon { display: inline-block !important; }` | 인쇄 규칙이 밑줄·↗를 지울 때 |
| P-7 캡션 뺀 그림 기준 정렬 | `figure.item-fig { display: contents !important; } figure.item-fig > .img { grid-column: 2; grid-row: 1 / span 2; } figure.item-fig > figcaption { grid-column: 2; grid-row: 3; }` + 글 칸 `grid-row: 1 / 2` | 그림 옆 글이 캡션까지 포함한 높이의 가운데로 갈 때(규칙 4) |
| P-8 줄 고르게 | `h1, h2, h3, .tagline { text-wrap: balance; } p, dd, li { text-wrap: pretty; }` | 큰 글 끝 낱말 하나만 떨어질 때(규칙 11) |
| P-9 고정·움직임 풀기 | `.sticky-thing { position: static !important; height: auto !important; } .reveal { opacity: 1 !important; transform: none !important; }` | 화면용 고정(sticky)·스크롤 효과가 인쇄에서 겹치거나 사라질 때 |

## A. 글씨 키우기

| 후보 | 조각 | 효과 · 주의 |
|---|---|---|
| A-1 배치 폭 960 | `/* layout-px: 960 */` | 72% → 본문 약 7.5pt. 기타 프로젝트 카드 3열 → 2열(1024 미만) |
| A-2 배치 폭 900 | `/* layout-px: 900 */` | 76% → 본문 약 8pt. 기능 소개 4줄이 한 쪽에 안 들어갈 수 있음 → G-1/G-2 |
| A-3 배치 폭 820·780 | `/* layout-px: 820 */` · `/* layout-px: 780 */` | 84%·88% → 본문 약 8.8·9.3pt. 768 이상이라 단 나눔은 유지되지만 칸이 좁아짐 → C-2(정보 표 비율)·F-4(연락처)·G-3(소개 큰 문장)을 함께 봄. **768 아래로는 내리지 않음**(휴대폰 배치에 가까워짐) |
| A-4 작은 글만 키우기 | `.eyebrow { font-size: 13px !important; } .chip { font-size: 13px !important; }` | 배치는 그대로, 5~6pt인 영문 머리말·칩만 키움. **캡션은 넣지 않음**(도구가 줄바꿈을 보고 정함) |
| A-6 글씨 사이 비율 한도 | `/* ratio-limit: 1.25 */` (숫자만 바꿈, `off`면 끔) | 원본에서 가장 큰 글 대비 비율이 이 배수까지만 달라짐 — 기본 켜짐(1.25). 작은 글을 더 키우고 싶으면 올리고(1.3~1.4), 원본 비율에 더 가깝게 하려면 내림(1.1~1.2). 올리면 본문이 커지지만 제목·이름과의 차이가 줄어듦 |
| A-5 이미 잘 보이는 글 기준 | `/* keep-readable: 10pt */` (숫자만 바꿈, `off`면 끔) | 배치 폭을 줄여도 화면 비율로 이미 이 크기 이상인 글은 키우지 않음 — 기본 켜짐(10pt). 큰 글이 너무 작아 보이면 숫자를 올리고, 본문과 큰 글 차이가 너무 작으면 내림 |

## B. 3열 격자 (예: 기술 스택 `#stack`)

| 후보 | 조각 | 효과 |
|---|---|---|
| B-1 3×2 → 2×3 | `.stk { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; column-gap: 64px !important; }` | 세로로 길어져 빈 곳이 줄고 근거 글 줄이 길어짐 |
| B-2 머리 쪽에 붙이기 | `#stack { break-before: auto !important; padding-top: 96px !important; }` | 머리(이름·소개) 쪽 아래 빈 곳에 이어 붙임 — 둘을 합쳐 한 쪽에 들어갈 때만 |

## C. [정보 | 대표 그림] 2단 (예: 프로젝트 소개 `.sec.proj`, 30 : 70)

| 후보 | 조각 | 효과 |
|---|---|---|
| C-1 가로 → 세로 | `.sec.proj .split { grid-template-columns: 1fr !important; gap: 32px !important; } .sec.proj .split .media { order: 0 !important; max-width: 760px; }` | 대표 그림 위 · 정보 표 아래. 쪽 아래 빈 곳이 줄어듦 |
| C-2 비율 35:65 · 40:60 · 45:55 | `.sec.proj .split { grid-template-columns: 40fr 60fr !important; }` (숫자만 바꿈) | 정보 표가 넓어져 '환경'·'구현 범위' 칸과 칩의 줄바꿈이 줄어듦. 고르는 법은 아래 "정보 표 비율 고르기" |

## D. [글 | 그림] 줄 목록 (예: 기능 소개 `.sec.core`, 기능마다 [글 | 그림 380px] 4줄)

| 후보 | 조각 | 효과 |
|---|---|---|
| D-1 줄 → 2×2 격자 | `.fe-list { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap: 36px 40px !important; } .fe-list > .fe-item { display: block !important; } .fe-inline > figcaption { margin: 8px 0 14px !important; text-align: left !important; }` | 그림이 커지고(폭 절반) 글은 그림 아래. (그림 묶음 `.fe-inline`은 칸을 만들지 않음 — 그림 `.fe-img`과 캡션이 각각 칸) |
| D-2 그림 칸 크기 | `.fe-list > .fe-item { grid-template-columns: minmax(0, 1fr) 340px !important; }` (숫자만 바꿈) | 배치 폭을 줄였을 때 4줄이 한 쪽에 들어가게. 들어가는 최대 폭 ≈ (배치 폭 × 1.5 − 314) ÷ 3 → 900: 340 · 860: 320 · 820: 300 · 780: 280. 여유 있게 20px 덜 잡음(900: 320 · 820: 280 · 780: 260). **종이 위 55mm 미만이 되면 안 됨**(`images_mm.feature_min`) |
| D-3 그림 왼쪽 | `.fe-inline > .fe-img, .fe-inline > figcaption { grid-column: 1 !important; } .fe-head, .fe-detail { grid-column: 2 !important; } .fe-list > .fe-item { grid-template-columns: 380px minmax(0, 1fr) !important; } .fe-inline > figcaption { text-align: left !important; }` | 화면과 반대지만 글이 읽는 방향 끝에 옴 — 화면 배치를 따르는 것이 기본이므로 다른 후보로 안 될 때만 |

## E. 카드 격자 (예: 기타 프로젝트 `#others`, 3열 — 배치 폭 1024 미만이면 2열)

| 후보 | 조각 | 효과 |
|---|---|---|
| E-1 3열 → 2열 | `#others .grid { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }` | 카드가 넓어지고 세로로 길어짐 |
| E-3 2+1 → 세로 1열 | `#others .grid { grid-template-columns: 1fr !important; gap: 20px !important; }` (카드 안은 화면처럼 제목·정보 아래 설명) | 카드 3장이 한 줄에 안 들어가 2+1로 쪼개질 때(규칙 5) |
| E-2 요약과 한 쪽에 | `#glance { break-before: auto !important; padding-top: 96px !important; }` | 기타 프로젝트 쪽 아래에 프로젝트 요약을 이어 붙임 — 합쳐도 쪽 수가 늘지 않을 때만 |

## F. 줄 목록 · 여러 단 (예: 프로젝트 요약 `#glance` · 연락처 `#contact`)

| 후보 | 조각 | 효과 |
|---|---|---|
| F-1 연락처 새 쪽 | `#contact { break-before: page !important; padding-top: 0 !important; }` | 요약 쪽과 연락처 쪽을 깔끔히 나눔(이미 따로 쪽이면 필요 없음) |
| F-2 연락처 2단 | `#contact .cols3 { grid-template-columns: 2fr 5fr !important; } #contact .cols3 > :nth-child(2) { display: none !important; } #contact .cols3 > :nth-child(3) ul { columns: 2; column-gap: 32px; }` | 링크 목록이 짧아져 요약 쪽 아래에 들어갈 수 있음 |
| F-3 요약 줄 간격 | `.gl-row { padding: 24px 0 !important; }` | 요약이 짧아짐 |
| F-5 요약 칸 비율 | `.gl-row { grid-template-columns: 200px 150px minmax(0, 1fr) !important; }` | [그림 | 이름 | 본문]에서 이름 칸을 줄이고 본문 칸을 넓힘 — 본문 줄 수가 줄어듦 |
| F-4 PROJECT를 CONTACT 아래로, LINK를 오른쪽 넓은 칸에 (추천) | `#contact .cols3 { grid-template-columns: 35fr 65fr !important; column-gap: 48px !important; row-gap: 40px !important; } #contact .cols3 > :nth-child(1) { grid-column: 1; grid-row: 1; } #contact .cols3 > :nth-child(2) { grid-column: 1; grid-row: 2; } #contact .cols3 > :nth-child(3) { grid-column: 2; grid-row: 1 / span 2; } #contact .cols3 > :nth-child(3) li .print-only { display: inline !important; } #contact .cols3 > :nth-child(3) li > span { flex-direction: column; }` | 링크 이름과 주소가 한 줄(`GitHub github.com/…`)이 되어 LINK 목록 길이가 절반 가까이로 줄고, 주소가 단어 중간에서 끊기지 않음(`wrap.url_broken` 0). LINK를 2열로 나누면 오히려 주소가 끊기므로 1열 |

## G. 공통

| 후보 | 조각 | 효과 |
|---|---|---|
| G-1 절 머리 간격 | `.sec-head { margin-bottom: 28px !important; } .sec.core .sec-head { margin-bottom: 28px !important; }` | 쪽마다 위쪽 여유를 조금 줄임 |
| (G-2·G-3 없앰) | — | 큰 제목·자기소개 문장을 따로 줄이던 조각은 A-5(이미 잘 보이는 글은 키우지 않기)가 대신함. 큰 글의 끝 낱말 하나 떨어짐은 기본 인쇄 규칙의 `text-wrap: balance`가 막음 |

## H. 장 표지 (예: 프로젝트 소개 — 원본에 흐린 대표 이미지 배경이 있는 절)

| 후보 | 조각 | 효과 · 주의 |
|---|---|---|
| H-1 꽉 찬 흐린 배경 · 어두운 글씨 | `@page proj-cover { margin: 0; }` + `@media print { .sec.proj { page: proj-cover; break-before: page; color-scheme: dark; --bg: #000 !important; --ink: #F5F5F7 !important; …(어두운 테마 색 전부 !important) box-sizing: border-box; padding: calc(<위 여백>mm / var(--pdf-scale, 1)) calc(14mm / var(--pdf-scale, 1)) calc(12mm / var(--pdf-scale, 1)) !important; } html, body { background: transparent !important; } .proj-backdrop { display: block !important; } }` + 설정 줄 `/* backdrop: .proj-backdrop */` (예시 페이지의 `theme/pdf.css` 묶음 — 어두운 테마 색은 그 페이지 테마 값으로) | 원본처럼 대표 이미지가 쪽 전체에 번지는 장 표지. 여백 없는 쪽(이름 붙은 쪽)이라 안쪽 여백을 `--pdf-scale`(도구가 넣음)로 나눠 종이 위 여백을 다른 쪽과 같게 지킴. 흐린 배경은 도구가 그림으로 굳혀 **그 쪽 자체의 배경(@page)**으로 칠하고 대비를 맞춤(`backdrop-contrast`). **절에 배경색·최소 높이를 주지 않음**(절 배경은 Chrome이 바로 앞 쪽 맨 아래 경계에도 그려 가는 선이 생김), **html·body 바탕은 투명**(흰 바탕이 쪽 배경을 덮음). 글자 그림자(.text-lift)·대표 그림 그림자도 넣지 않음(PDF에서 사각형 얼룩) |
| H-2 배경 대비 | `/* backdrop-contrast: 3 */` (숫자만 바꿈) | 밝은 배경을 얼마나 검게 덮을지. 3 = 원본 색에 가깝게(지금), 3.5 = 조금 어둡게, 4.5 = 작은 글까지 확실히 |

## 정보 표 비율 고르기 (프로젝트 소개)

대표 그림을 크게 두려다 정보 표가 너무 좁아지면(종이 위 `images_mm.table_mm` 55mm 미만, `wrap.table.max` 5줄 이상, 칩이 3줄 이상) C-2를 30 → 35 → 40 → 45 순서로 시험합니다.
- 정보 표의 가장 긴 칸이 **4줄 이하**이고 칸 줄 수 합(`wrap.table.total`)이 지금보다 늘지 않는 비율 중 **대표 그림이 가장 큰 것**을 고릅니다.
- 대표 그림은 종이 위 **90mm 이상**(`images_mm.cover_min`)을 지킵니다. 45:55로도 표가 4줄을 넘으면 C-1(세로)을 시험합니다.

새 후보를 만들 때는 화면의 배치를 먼저 따르고(단 나눔·순서·그림 쪽), 바꾸는 범위는 문제가 있는 절 하나로 좁힙니다.
선택자는 그 페이지 `index.html`의 인쇄 규칙(`@media print`)과 화면 규칙을 읽고 고릅니다.
