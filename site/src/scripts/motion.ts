// Motion layer for the site. Small functions, one lifecycle.
// Rules (hard): reduced motion = no motion at all (final state, no Lenis, no tilt, no scroll story);
// content is visible if JS fails; animate transform / opacity only (plus stroke-dashoffset and a
// clip wipe for chart line draw-in); never animate a number; every draw-in ends in exactly the final chart.
// Timings and easing come from the tokens in global.css (:root), read at run time.
import Lenis from 'lenis';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const REDUCE_OK = '(prefers-reduced-motion: no-preference)';
const DESKTOP = `${REDUCE_OK} and (min-width: 64rem)`;
const FINE = `${REDUCE_OK} and (pointer: fine) and (hover: hover)`;

let mm: gsap.MatchMedia | null = null;
let offPage: AbortController | null = null;

// ---------- helpers ----------
type Tok = { ease: string; pop: string; step: number; short: number; base: number; long: number; rise: number };
function tokens(): Tok {
  const cs = getComputedStyle(document.documentElement);
  const v = (n: string) => cs.getPropertyValue(n).trim();
  const ms = (n: string, d: number) => parseFloat(v(n)) || d;
  return {
    ease: v('--ease-out') || 'ease-out',
    pop: v('--ease-pop') || 'ease-out',
    step: ms('--dur-step', 300), short: ms('--dur-short', 400), base: ms('--dur-base', 550), long: ms('--dur-long', 700),
    rise: ms('--rise', 14),
  };
}

/** A set of WAAPI animations and hidden-state classes that a cleanup can undo. */
function makeScope() {
  const anims = new Set<Animation>();
  const pre = new Set<Element>();
  const undo: Array<() => void> = [];
  return {
    play(el: Element, kf: Keyframe[], o: KeyframeAnimationOptions) {
      const a = el.animate(kf, { fill: 'backwards', ...o });
      anims.add(a);
      a.finished.then(() => anims.delete(a), () => anims.delete(a));
      return a;
    },
    hide(el: Element) { el.classList.add('m-pre'); pre.add(el); },
    show(el: Element) { el.classList.remove('m-pre'); pre.delete(el); },
    onUndo(fn: () => void) { undo.push(fn); },
    clear() {
      anims.forEach((a) => a.cancel());
      anims.clear();
      pre.forEach((el) => el.classList.remove('m-pre'));
      pre.clear();
      undo.splice(0).reverse().forEach((fn) => fn());
    },
  };
}
type Scope = ReturnType<typeof makeScope>;

const belowFold = (el: Element) => {
  if (el.closest('details:not([open])')) return false; // closed details: not laid out, leave alone
  return el.getBoundingClientRect().top > window.innerHeight;
};

// ---------- always on (also with reduced motion) ----------
function syncNav() {
  // The header persists across page swaps, so aria-current is updated here.
  const here = location.pathname.replace(/\/$/, '');
  document.querySelectorAll<HTMLAnchorElement>('.site-header nav a').forEach((a) => {
    const p = new URL(a.href).pathname.replace(/\/$/, '');
    if (p === here) a.setAttribute('aria-current', 'page');
    else a.removeAttribute('aria-current');
  });
}

function headerRule(signal: AbortSignal) {
  const h = document.querySelector('.site-header');
  if (!h) return;
  const set = () => h.classList.toggle('is-scrolled', window.scrollY > 8);
  set();
  window.addEventListener('scroll', set, { passive: true, signal });
}

// ---------- motion parts ----------
function smoothScroll(s: Scope) {
  const lenis = new Lenis({ anchors: false });
  lenis.on('scroll', ScrollTrigger.update);
  const tick = (t: number) => lenis.raf(t * 1000);
  gsap.ticker.add(tick);
  gsap.ticker.lagSmoothing(0);
  s.onUndo(() => { gsap.ticker.remove(tick); lenis.destroy(); });
}

function progressRule() {
  const header = document.querySelector('.site-header') ?? document.body;
  let bar = header.querySelector<HTMLElement>('.nav-progress');
  if (!bar) {
    bar = document.createElement('div');
    bar.className = 'nav-progress';
    bar.setAttribute('aria-hidden', 'true');
    header.appendChild(bar);
  }
  gsap.fromTo(bar, { scaleX: 0 }, {
    scaleX: 1, ease: 'none',
    scrollTrigger: { trigger: document.documentElement, start: 'top top', end: 'bottom bottom', scrub: true },
  });
}

/** Hero: text in one beat, feeder draws trunk first (one soft pulse), branches by depth, then load dots. ~2.7 s, once. */
function heroEntrance(s: Scope, t: Tok) {
  const hero = document.querySelector('#hero');
  const art = document.querySelector('.feeder-hero .feeder-art');
  const gated = document.documentElement.classList.contains('js-motion');
  document.documentElement.classList.add('motion-ready');
  if (!hero || !gated) return; // gate timed out (slow JS): the hero is already shown, do not replay it

  const kicker = hero.querySelector('.hero-text .kicker');
  const h1 = hero.querySelector('.hero-text h1');
  const list = hero.querySelector('.hero-text ol');
  if (kicker) s.play(kicker, [{ opacity: 0 }, { opacity: 1 }], { duration: t.short, easing: t.ease });
  if (h1) s.play(h1, [
    { clipPath: 'inset(0 0 100% 0)', transform: `translateY(${t.rise}px)` },
    { clipPath: 'inset(0 0 0% 0)', transform: 'none' },
  ], { duration: t.long, easing: t.ease, delay: 60 });
  if (list) s.play(list, [{ opacity: 0, transform: `translateY(${t.rise}px)` }, { opacity: 1, transform: 'none' }],
    { duration: t.base, easing: t.ease, delay: 180 });

  if (!art) return;
  const tx = art.querySelector('.tx');
  const trunk = art.querySelector<SVGPathElement>('path.trunk');
  const loads = art.querySelector('.loads');
  const dash = (o: number) => ({ strokeDasharray: '1', strokeDashoffset: String(o) });
  if (tx) s.play(tx, [{ opacity: 0 }, { opacity: 1 }], { duration: 300, easing: t.ease });
  if (trunk) {
    s.play(trunk, [dash(1), dash(0)], { duration: 900, easing: t.ease, delay: 100 });
    pulse(s, trunk, 950);
  }
  art.querySelectorAll<SVGPathElement>('.net path').forEach((p) => {
    const d = parseFloat(p.style.getPropertyValue('--d')) || 0;
    s.play(p, [dash(1), dash(0)], { duration: t.long, easing: t.ease, delay: 600 + d * 1100 });
  });
  if (loads) s.play(loads, [{ opacity: 0 }, { opacity: 1 }], { duration: t.short, easing: t.ease, delay: 2250 });
}

/** One soft pulse running out along the trunk from the transformer (a temporary copy, removed when done). */
function pulse(s: Scope, trunk: SVGPathElement, delay = 0) {
  const p = trunk.cloneNode() as SVGPathElement;
  p.setAttribute('class', 'trunk-pulse'); // inline styles below override the trunk look
  Object.assign(p.style, { stroke: 'var(--limit)', strokeWidth: '7px', strokeLinecap: 'round', opacity: '0', pointerEvents: 'none' });
  trunk.after(p);
  const a = s.play(p, [
    { strokeDasharray: '0.12 1.2', strokeDashoffset: '0.12', opacity: 0 },
    { opacity: 0.45, offset: 0.15 },
    { opacity: 0.45, offset: 0.8 },
    { strokeDasharray: '0.12 1.2', strokeDashoffset: '-1', opacity: 0 },
  ], { duration: 1000, easing: 'linear', delay, fill: 'both' });
  const drop = () => p.remove();
  a.finished.then(drop, drop);
}

/** 3D tilt that follows the pointer (fine pointer desktops only). Max about 5 degrees. */
function heroTilt(s: Scope) {
  const fig = document.querySelector('.feeder-hero');
  const stage = fig?.querySelector<HTMLElement>('.feeder-stage');
  const area = document.querySelector<HTMLElement>('#hero');
  if (!fig || !stage || !area) return;
  fig.classList.add('tilt-on');
  const rx = gsap.quickTo(stage, 'rotationX', { duration: 0.7, ease: 'power3.out' });
  const ry = gsap.quickTo(stage, 'rotationY', { duration: 0.7, ease: 'power3.out' });
  const ac = new AbortController();
  area.addEventListener('pointermove', (e) => {
    const r = stage.getBoundingClientRect();
    const nx = Math.max(-1, Math.min(1, (e.clientX - (r.left + r.width / 2)) / (r.width / 2)));
    const ny = Math.max(-1, Math.min(1, (e.clientY - (r.top + r.height / 2)) / (r.height / 2)));
    ry(nx * 5);
    rx(-ny * 4);
  }, { signal: ac.signal });
  area.addEventListener('pointerleave', () => { rx(0); ry(0); }, { signal: ac.signal });
  s.onUndo(() => { ac.abort(); fig.classList.remove('tilt-on'); gsap.set(stage, { clearProps: 'transform' }); });
}

/** Section headline group: kicker fades, h2 mask-reveals, the next two text blocks rise. Once, below the fold only. */
function sectionReveals(s: Scope, t: Tok) {
  document.querySelectorAll<HTMLElement>('main section:not(#hero)').forEach((sec) => {
    const kicker = sec.querySelector<HTMLElement>(':scope > .kicker');
    const h2 = sec.querySelector<HTMLElement>(':scope > h2');
    if (!h2 || !belowFold(h2)) return;
    const text: HTMLElement[] = [];
    for (let el = h2.nextElementSibling as HTMLElement | null; el && text.length < 2; el = el.nextElementSibling as HTMLElement | null) {
      if (!el.matches('p, ol, ul:not(.cards)')) break;
      text.push(el);
    }
    const group = [kicker, h2, ...text].filter(Boolean) as HTMLElement[];
    group.forEach((el) => s.hide(el));
    ScrollTrigger.create({
      trigger: h2, start: 'top 85%', once: true,
      onEnter: () => {
        group.forEach((el) => s.show(el));
        if (kicker) s.play(kicker, [{ opacity: 0 }, { opacity: 1 }], { duration: t.short, easing: t.ease });
        s.play(h2, [
          { clipPath: 'inset(0 0 100% 0)', transform: `translateY(${t.rise}px)` },
          { clipPath: 'inset(0 0 0% 0)', transform: 'none' },
        ], { duration: t.long, easing: t.ease, delay: 40 });
        const gaps = [160, 260]; // shrinking gaps, not a metronome
        const rise = [t.rise, t.rise - 2];
        text.forEach((el, i) => s.play(el, [{ opacity: 0, transform: `translateY(${rise[i]}px)` }, { opacity: 1, transform: 'none' }],
          { duration: t.base - i * 50, easing: t.ease, delay: gaps[i] }));
      },
    });
  });
}

/** Figure frames (image sheets): fade in once. */
function figureFades(s: Scope, t: Tok) {
  document.querySelectorAll<HTMLElement>('main figure.sheet').forEach((fig) => {
    if (!belowFold(fig)) return;
    s.hide(fig);
    ScrollTrigger.create({
      trigger: fig, start: 'top 88%', once: true,
      onEnter: () => { s.show(fig); s.play(fig, [{ opacity: 0 }, { opacity: 1 }], { duration: t.base, easing: t.ease }); },
    });
  });
}

/** Line chart: frame fades, lines draw left to right, band fades, markers pop. Ends in exactly the static chart. */
function lineChartDraw(s: Scope, t: Tok, fig: HTMLElement) {
  const svg = fig.querySelector<SVGSVGElement>('svg.chart-svg');
  if (!svg) return;
  s.play(fig, [{ opacity: 0 }, { opacity: 1 }], { duration: 300, easing: t.ease });
  const lines = [...svg.querySelectorAll<SVGPolylineElement>(':scope > polyline.ln')];
  const order = ['p1', 'p2', 'p3'];
  lines.sort((a, b) => order.findIndex((c) => a.classList.contains(c)) - order.findIndex((c) => b.classList.contains(c)));
  lines.forEach((ln, i) => {
    const delay = 150 + i * 90;
    if (ln.classList.contains('p1')) {
      const len = ln.getTotalLength();
      s.play(ln, [{ strokeDasharray: `${len}`, strokeDashoffset: `${len}` }, { strokeDasharray: `${len}`, strokeDashoffset: '0' }],
        { duration: 800, easing: t.ease, delay });
    } else {
      wipe(s, svg, ln, 800, delay, t.ease); // dashed lines keep their dash pattern while drawing
    }
  });
  const band = svg.querySelector(':scope > polygon.band');
  if (band) s.play(band, [{ opacity: 0 }, { opacity: 1 }], { duration: t.short, easing: t.ease, delay: 500 });
  const pts = [...svg.querySelectorAll<SVGGElement>('g.pt')];
  pts.sort((a, b) => a.getBBox().x - b.getBBox().x);
  pts.forEach((g, i) => {
    const delay = 850 + i * 35;
    const mk = g.querySelector<SVGElement>('.mk');
    if (mk) {
      mk.style.transformBox = 'fill-box';
      mk.style.transformOrigin = '50% 50%';
      s.play(mk, [{ transform: 'scale(0.6)', opacity: 0 }, { transform: 'scale(1)', opacity: 1 }], { duration: 380, easing: t.pop, delay });
    }
    g.querySelectorAll('.ptlabel').forEach((l) => s.play(l, [{ opacity: 0 }, { opacity: 1 }], { duration: 300, easing: t.ease, delay: delay + 120 }));
  });
}

/** Left-to-right reveal with a temporary SVG clipPath whose rect scales in X (transform only). */
function wipe(s: Scope, svg: SVGSVGElement, el: SVGElement, duration: number, delay: number, easing: string) {
  const NS = 'http://www.w3.org/2000/svg';
  const vb = svg.viewBox.baseVal;
  const id = `m-wipe-${Math.random().toString(36).slice(2, 8)}`;
  const cp = document.createElementNS(NS, 'clipPath');
  cp.setAttribute('id', id);
  const r = document.createElementNS(NS, 'rect');
  r.setAttribute('x', '0'); r.setAttribute('y', '0');
  r.setAttribute('width', String(vb.width)); r.setAttribute('height', String(vb.height));
  cp.appendChild(r);
  svg.appendChild(cp);
  el.setAttribute('clip-path', `url(#${id})`);
  const a = s.play(r, [{ transform: 'scaleX(0)' }, { transform: 'scaleX(1)' }], { duration, delay, easing });
  const done = () => { el.removeAttribute('clip-path'); cp.remove(); };
  a.finished.then(done, done);
}

/** Bar chart: each panel's bars grow from the axis when that panel enters, then the value labels fade in. */
function barChartDraw(s: Scope, t: Tok, fig: HTMLElement) {
  const svg = fig.querySelector<SVGSVGElement>('svg.chart-svg');
  if (!svg) return;
  s.play(fig, [{ opacity: 0 }, { opacity: 1 }], { duration: 300, easing: t.ease });
  [...svg.querySelectorAll<SVGGElement>(':scope > g')].forEach((panel, pi) => {
    const bars = [...panel.querySelectorAll<SVGRectElement>('rect.bar')];
    if (!bars.length) return;
    const run = (base: number) => {
      s.show(panel);
      bars.forEach((b, i) => {
        b.style.transformBox = 'fill-box';
        b.style.transformOrigin = '50% 100%';
        s.play(b, [{ transform: 'scaleY(0)' }, { transform: 'scaleY(1)' }], { duration: 600, easing: t.ease, delay: base + i * 60 });
      });
      panel.querySelectorAll('.val, .inbar').forEach((l) => s.play(l, [{ opacity: 0 }, { opacity: 1 }],
        { duration: 300, easing: t.ease, delay: base + 450 + bars.length * 60 }));
    };
    if (pi === 0 || !belowFold(panel)) { run(150 + pi * 120); return; }
    s.hide(panel);
    const st = ScrollTrigger.create({ trigger: panel, start: 'top 85%', once: true, onEnter: () => run(0) });
    s.onUndo(() => st.kill()); // made inside a callback, so not tracked by gsap.matchMedia
  });
}

function charts(s: Scope, t: Tok) {
  document.querySelectorAll<HTMLElement>('main figure.chart').forEach((fig) => {
    if (!belowFold(fig)) return;
    s.hide(fig);
    const isBars = !!fig.querySelector('rect.bar');
    ScrollTrigger.create({
      trigger: fig, start: 'top 80%', once: true,
      onEnter: () => { s.show(fig); (isBars ? barChartDraw : lineChartDraw)(s, t, fig); },
    });
  });
}

/** Scroll story "How the limit binds" (desktop only). The feeder stays fixed beside the EXISTING flagship
 *  cards; three steps (30 / 60 / 100% of houses with solar) highlight the matching cards. No numbers move. */
function limitStory(s: Scope, t: Tok) {
  const sec = document.querySelector<HTMLElement>('#flagship');
  const cards = sec?.querySelector<HTMLElement>(':scope > ul.cards');
  const art = document.querySelector<HTMLElement>('.feeder-hero .feeder-art');
  if (!sec || !cards || !art) return;
  const all = [...cards.querySelectorAll<HTMLElement>('li.card')];
  const find = (re: RegExp) => all.filter((c) => re.test(c.querySelector('.card-label')?.textContent ?? ''));
  // Labels below are the site's own wording: step names from the flagship text, limit names from the
  // chart's "cable" label and the 60% card's caveat. No new numbers.
  const steps = [
    { name: '30% of houses with solar', on: find(/^Hosting capacity, 30%/), also: [] as HTMLElement[], limit: 'Binding limit: cable (assumed rating)' },
    { name: '60% of houses with solar', on: find(/^Hosting capacity, 60%/), also: find(/^Voltage-only limit at 60%/), limit: 'Binding limit: assumed trunk cable rating' },
    { name: '100% of houses with solar', on: find(/^Hosting capacity, 100%/), also: [] as HTMLElement[], limit: 'Binding limit: cable (assumed rating)' },
  ];
  if (steps.some((st) => !st.on.length)) return; // page changed: do nothing rather than guess

  const story = document.createElement('div');
  story.className = 'story';
  const aside = document.createElement('div');
  aside.className = 'story-aside';
  aside.setAttribute('aria-hidden', 'true'); // visual duplicate of content already on the page
  const pic = art.cloneNode(true) as HTMLElement;
  pic.removeAttribute('role');
  pic.removeAttribute('aria-label');
  pic.querySelector<HTMLElement>('.feeder-stage')?.removeAttribute('style');
  pic.querySelectorAll('.trunk-pulse').forEach((n) => n.remove());
  const title = document.createElement('p');
  title.className = 'story-title';
  title.textContent = 'How the limit binds (simulated)';
  const list = document.createElement('ol');
  list.className = 'story-steps';
  steps.forEach((st) => { const li = document.createElement('li'); li.textContent = st.name; list.appendChild(li); });
  const lim = document.createElement('p');
  lim.className = 'story-limit';
  aside.append(title, pic, list, lim);
  cards.before(story);
  story.append(aside, cards);
  const trunk = pic.querySelector<SVGPathElement>('path.trunk');

  let cur = -1;
  const setStep = (i: number) => {
    if (i === cur) return;
    cur = i;
    story.classList.toggle('is-live', i >= 0);
    all.forEach((c) => c.classList.remove('is-on', 'is-also'));
    [...list.children].forEach((li, k) => li.classList.toggle('is-on', k === i));
    if (i < 0) { lim.textContent = ''; return; }
    steps[i].on.forEach((c) => c.classList.add('is-on'));
    steps[i].also.forEach((c) => c.classList.add('is-also'));
    lim.textContent = steps[i].limit;
    s.play(lim, [{ opacity: 0, transform: 'translateY(6px)' }, { opacity: 1, transform: 'none' }], { duration: t.step, easing: t.ease });
    if (i === 1 && trunk) pulse(s, trunk);
  };
  ScrollTrigger.create({
    trigger: story, start: 'top 75%', end: 'bottom 75%',
    onUpdate: (st) => setStep(Math.min(2, Math.floor(st.progress * 3))),
    onEnter: (st) => setStep(Math.min(2, Math.floor(st.progress * 3))),
    onEnterBack: (st) => setStep(Math.min(2, Math.floor(st.progress * 3))),
    onLeave: () => setStep(-1),
    onLeaveBack: () => setStep(-1),
  });

  s.onUndo(() => {
    all.forEach((c) => c.classList.remove('is-on', 'is-also'));
    story.before(cards);
    story.remove();
  });
}

function refreshOnImages(signal: AbortSignal) {
  const refresh = () => ScrollTrigger.refresh();
  document.querySelectorAll<HTMLImageElement>('main img').forEach((img) => {
    if (!img.complete) img.addEventListener('load', refresh, { once: true, signal });
  });
  if (document.readyState !== 'complete') window.addEventListener('load', refresh, { once: true, signal });
}

// ---------- lifecycle ----------
function init() {
  // Runs once per page: at first script run (no waiting for window load) and on astro:page-load after a swap.
  const main = document.querySelector<HTMLElement>('main');
  if (!main || main.dataset.motionInit) return;
  main.dataset.motionInit = '1';
  offPage?.abort();
  offPage = new AbortController();
  syncNav();
  headerRule(offPage.signal);

  mm = gsap.matchMedia();
  mm.add(REDUCE_OK, () => {
    const s = makeScope();
    const t = tokens();
    smoothScroll(s);
    progressRule();
    heroEntrance(s, t);
    sectionReveals(s, t);
    figureFades(s, t);
    charts(s, t);
    return () => s.clear();
  });
  mm.add(DESKTOP, () => {
    const s = makeScope();
    limitStory(s, tokens());
    ScrollTrigger.refresh();
    return () => s.clear();
  });
  mm.add(FINE, () => {
    const s = makeScope();
    heroTilt(s);
    return () => s.clear();
  });
  if (offPage) refreshOnImages(offPage.signal);
  // Reduced motion: nothing above runs; make sure the hero gate never hides anything.
  document.documentElement.classList.add('motion-ready');
}

function cleanup() {
  offPage?.abort();
  offPage = null;
  mm?.revert(); // kills every tween and ScrollTrigger made above and runs each scope's clear()
  mm = null;
  ScrollTrigger.getAll().forEach((st) => st.kill()); // belt and braces: no instance survives a page swap
}

init();
document.addEventListener('astro:page-load', init);
document.addEventListener('astro:before-swap', cleanup);
document.addEventListener('astro:after-swap', () => {
  syncNav(); // persisted header: update aria-current before the new page is shown
  // New <html> attributes come from the next page: re-arm the hero gate before it is shown.
  if (!window.matchMedia(REDUCE_OK).matches) return;
  const d = document.documentElement;
  d.classList.add('js-motion');
  setTimeout(() => { if (!d.classList.contains('motion-ready')) d.classList.remove('js-motion'); }, 2500);
});
