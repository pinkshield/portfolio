// (직접 고친 기능) 자기소개서 — letter.html
//   레포 맨 위의 자기소개서.md(수강생 파일)를 그대로 그립니다. 글을 만들거나 고치지 않습니다.
//   모양은 상세 기술문서(doc.css)와 같음: 왼쪽 목차(## 제목) · 가운데 본문 · 오른쪽 내 정보 카드. 인쇄는 A4.
//   md 해석은 assets/md-blocks.js(PF.md.parse) — 그림 상대경로만 레포 맨 위 기준으로 되돌림.
//   점검: PFLetter.report() → { ready, headings, strings }
(async () => {
  const FILE = '자기소개서.md';
  const root = document.getElementById('app');
  const html = document.documentElement;
  const info = { headings: 0, error: '' };
  window.PFLetter = { report: () => ({ page: 'letter', ready: html.dataset.docReady === '1', ...info, strings: PF.stringsReport() }) };
  if (PF.guardFileProtocol(root)) return;

  const { esc, inline, link, isUrl, shortUrl } = PF;
  const T = (k, v) => esc(PF.t(k, v));
  const [pf] = await Promise.all([PF.loadJSON('data/portfolio.json').catch(() => ({})), PF.loadStrings()]);
  PF.applyTheme(pf.settings?.accent);
  document.querySelector('.skip-link')?.replaceChildren(PF.t('ui.skip'));
  const prof = pf.profile || {};
  const name = prof.name || '';
  document.title = `${PF.t('name.letter')}${name ? ' · ' + name : ''}`;

  let md;
  try { md = await PF.loadText(FILE); }
  catch (err) {
    info.error = err.message;
    PF.notice(root, `${PF.t('name.letter')}가 아직 없습니다`, `<p>레포 맨 위에 <code>${esc(FILE)}</code>를 만들면 이 페이지에 보입니다.</p>
      <p>${link({ href: 'index.html', label: T('ui.back'), kind: 'page', cls: 'btn' })}</p>`);
    return done();
  }

  const contact = [
    prof.email && `<p>${link({ href: `mailto:${prof.email}`, label: esc(prof.email), kind: 'mail' })}</p>`,
    isUrl(prof.github) && `<p>${link({ href: prof.github, label: esc(shortUrl(prof.github)), kind: 'external' })}</p>`,
  ].filter(Boolean).join('');

  root.innerHTML = `
    <header class="doc-head">
      <div class="doc-head-in">
        <p class="crumb">${link({ href: 'index.html', label: T('ui.back'), kind: 'page' })}<span aria-hidden="true">›</span><b>${T('name.letter')}</b></p>
      </div>
    </header>
    <div class="doc-page">
      <nav class="toc" id="toc" aria-label="자기소개서 목차"><p class="toc-title">${T('name.toc')}</p><div class="toc-links"></div></nav>
      <main class="doc-main" id="main" tabindex="-1">
        <article class="md" id="doc"></article>
      </main>
      <aside class="rail" aria-label="내 정보">
        <section class="rail-card"><p class="rail-title">${esc(name)}</p>
          ${prof.tagline ? `<p class="now-title">${inline(prof.tagline)}</p>` : ''}
          <div class="rail-misc">${contact}</div></section>
        <section class="rail-card rail-misc">
          ${link({ href: 'index.html', label: T('ui.back'), kind: 'page' })}
          <a href="#top" class="to-top">${T('doc.top')} ↑</a>
        </section>
      </aside>
    </div>
    <footer class="doc-foot"><span>© ${esc(name)}</span>${link({ href: 'index.html', label: T('ui.back'), kind: 'page' })}</footer>`;

  const { frag, headings } = PF.md.parse(md, '');
  // 그림 상대경로: md-blocks는 src/<폴더>/ 기준으로 바꾸므로 레포 맨 위 기준으로 되돌림
  frag.querySelectorAll('[data-md-src]').forEach((el) => el.setAttribute('src', PF.encodePath(PF.md.decode(el.dataset.mdSrc))));
  frag.querySelectorAll('a[href]').forEach((a) => {
    const href = a.getAttribute('href');
    if (/^https?:/i.test(href)) { a.target = '_blank'; a.rel = 'noopener'; }
  });
  frag.querySelectorAll('table').forEach((tb) => {
    const w = document.createElement('div');
    w.className = 'table-wrap';
    tb.replaceWith(w); w.appendChild(tb);
  });
  // 맨 앞 # 제목은 상세 문서처럼 머리(.doc-intro)로 — 본문(.md)은 # 제목을 따로 꾸미지 않음
  const h1 = frag.querySelector('h1');
  if (h1) {
    const intro = document.createElement('div');
    intro.className = 'doc-intro';
    intro.innerHTML = `<p class="eyebrow">${T('name.letter')}</p><h1>${esc(h1.textContent.trim())}</h1>`;
    h1.remove();
    document.getElementById('doc').before(intro);
  }
  const doc = document.getElementById('doc');
  doc.replaceChildren(frag);
  const toc = headings.filter((h) => h.level === 2).map((h) => `<a class="h2" href="#${esc(h.id)}">${esc(h.text)}</a>`).join('');
  document.querySelectorAll('.toc-links').forEach((el) => { el.innerHTML = toc; });
  info.headings = headings.length;
  if (location.hash) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();
  done();

  function done() { (document.fonts ? document.fonts.ready : Promise.resolve()).then(() => { html.dataset.docReady = '1'; }); }
})();
