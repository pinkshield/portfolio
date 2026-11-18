# 발표 덱 장면 배치 (수강생 본인 규칙)

`/portfolio-update`가 렌더러·스킬·`CLAUDE.md`를 템플릿으로 덮어써도 남도록 여기에 둡니다. 설계: `설계-발표덱-배치-보완.md`.

## 어디에 무엇을 쓰나

| 층 | 파일 | 무엇 |
|---|---|---|
| 내용 | `src/<폴더>/deck-edits.json` (`/portfolio-edit`) | 장면에 보일 것 — 틀, 원문 그림·표, 카드 문장, 나누기·합치기 |
| 배치 | `theme/deck-layout.css` | 장면 안에서 놓을 자리 — 다이어그램 크기, 카드 자리, 장 표지 그림 |

- 렌더러(`index.html`·`project.html`·`doc.html`·`assets/`)는 배치를 위해 고치지 않습니다. 업데이트가 덮어씁니다.
- `theme/deck-layout.css`의 규칙에는 반드시 `#deck:has(a[href*="p=<폴더>"])`를 앞에 붙입니다. 장면 id(`ch-intro` 등)는 다섯 덱이 함께 쓰기 때문입니다.
- 장 표지 그림은 CSS 배경이라 발표 덱 [PPTX로 저장]에는 들어가지 않습니다. 화면·PDF에만 보입니다.

## 지킬 것

1. **`/portfolio-theme` 뒤**: 이 스킬은 `theme/theme.css`를 통째로 다시 씁니다. 다 쓴 뒤 파일 **첫 줄**에
   `@import url("deck-layout.css");`가 있는지 보고, 없으면 다시 넣습니다(@import는 다른 규칙보다 앞에 있어야 먹습니다).
2. **`/portfolio-update` 뒤**: 배치를 넣은 덱(`deck-layout.css`에 `p=<폴더>`로 적힌 덱 — 지금은 `4-team-even`·`1-watch-your-back`)을 열어 확인합니다.
   - `await PFScene.whenReady()` 뒤 `PFScene.report().audit`이 0건인지 봅니다.
   - `deck-layout.css`에 적은 장면 id와 클래스(`.dk`·`.vis`·`.cards`·`.ch-mid`·`.vbox[data-kind]`)가 아직 그 장면에 있는지 봅니다.
   - 없어졌으면 그 장면은 원래 자동 배치로 돌아간 것입니다(깨지지 않음). 새 구조에 맞춰 그 규칙만 고치고, 수강생에게 알립니다.
3. **기술 문서 절 제목을 바꾸거나 다시 빌드해서 장면 id가 바뀌면**, `deck-layout.css`의 그 장면 이름도 함께 바꿉니다.
4. 배치를 고친 뒤에는 그 덱의 `audit`(잘림·넘침)이 0건인지 확인합니다. 넘치면 칸 비율·카드 폭을 줄여 맞춥니다.
