# WoW 「슬라이드」는 본인 발표 PDF · 「기술문서」라는 말 쓰지 않기 (수강생 본인 규칙)

`/portfolio-update`가 렌더러를 템플릿으로 덮어써도 잊지 않도록 여기에 둡니다.
근거: 강사님 Asana 피드백(11-21) "기술문서 라는 워딩 수정하렴 / 그리고 슬라이드는 니꺼 원본 써". 렌더러 수정은 건우 님이 허락했습니다(11-25).

- **WoW(`5-wow-hardcore-analysis`)의 「슬라이드」는 만든 덱이 아니라 건우 님 발표 PDF**로 갑니다:
  `src/5-wow-hardcore-analysis/Present File/WoW_클래식_하드코어_전투시스템_분석_개선_v2.pdf`
  (개선판 pptx에서 외부 자료와 다른 사실 일곱 곳만 고친 판 — `…_개선_v2.pptx`. 원본 `…분석.pptx.pdf` · `…_개선.pptx(.pdf)`는 고치지 않습니다.)
- **문서 이름은 「분석 문서」**입니다. WoW 화면(포트폴리오 페이지 · 상세 문서 · custom)에 「기술문서」 · 「상세 기술문서」가 보이지 않게 합니다. 다른 프로젝트 이름은 그대로입니다.
  파일 이름 `기술문서.md`는 빌드가 읽는 이름이라 그대로 둡니다.

## 어디에 있나 (렌더러 4곳 + custom)

| 파일 | 무엇 |
|---|---|
| `assets/common.js` | `ORIGINAL_DECK`(폴더 → PDF 경로) · `DOC_NAME`(폴더 → 「분석 문서」) 표, `originalDeck(id)` · `docName(id, short)`, `projectUrl`이 PDF가 있으면 PDF 주소를 돌려줌. `return {…}`에 `originalDeck, docName` |
| `assets/project-deck.js` | 맨 앞(옛 주소 처리 전)에 `if (id && PF.originalDeck(id)) { … location.replace(PF.originalDeck(id)); return; }` — `project.html?p=5-wow…`를 열어도 PDF로(PDF를 내려받는 브라우저를 위해 `#deck`에 링크 한 줄도 둠). 맺음 장면 카드 `label: PF.docName(p.id)` |
| `assets/doc.js` | 탭 제목 · 빵부스러기 · 머리 라벨의 `T('name.doc')` → `PF.docName(id)` (3곳). 슬라이드 버튼은 `PF.projectUrl`을 쓰므로 그대로 PDF |
| `assets/portfolio.js` | 문서 버튼 · 보이는 주소 · 한눈에 보기 링크의 `T('name.doc')` · `t('name.doc')` · `T('name.doc-short')` → `PF.docName(p.id[, true])` (4곳) |
| `custom/index.html` | `ORIGINAL_DECK`(같은 PDF) · `docLabel`(분석 프로젝트 → 「분석 문서」) |

## 빌드할 때

- `/portfolio-build`는 데이터에 `deck`을 만들지만, WoW는 **`deck`을 쓰지 않습니다**(렌더러가 PDF로 보내므로 덱이 보일 곳이 없음).
  `data/projects/5-wow-hardcore-analysis.json`에 `deck`을 넣지 않고, `src/5-wow-hardcore-analysis/deck-edits.json`도 만들지 않습니다(11-26 지움).
  빌드 점검 중 「`highlights[].section`이 `deck.slides`에 있다」 항목은 WoW에는 해당하지 않습니다.
- 발표 PDF를 다시 고치면 `…_v2.pptx`를 고친 뒤 PowerPoint에서 PDF로 저장하고(같은 이름), 문서 1-3 「자료」 링크와 이 규칙의 경로가 같은지 봅니다.

## `/portfolio-update` 뒤

1. 위 표의 다섯 곳에 `ORIGINAL_DECK` · `docName`이 남아 있는지 봅니다(`grep -n "originalDeck\|docName\|ORIGINAL_DECK" assets/*.js custom/index.html`).
2. 없어졌으면 다시 넣고, `project.html?p=5-wow-hardcore-analysis`가 PDF로 넘어가는지 · 상세 문서 `doc.html?p=5-wow-hardcore-analysis`에 「기술문서」가 없는지 열어 봅니다. 수강생에게 알립니다.
3. 다른 프로젝트도 원본 발표 자료로 바꾸려면 `ORIGINAL_DECK` · `DOC_NAME` 두 표에 한 줄씩 더하면 됩니다.
