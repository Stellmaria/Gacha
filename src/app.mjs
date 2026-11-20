import { PRIZE_WHEEL, CARD_WHEEL, pickIndex, targetRotation, browserRandomUnit, validateWheel } from './wheels.mjs';

const SVG_NS = 'http://www.w3.org/2000/svg';
const wheel = document.querySelector('#wheel');
const spin = document.querySelector('#spin');
const status = document.querySelector('#result');
const oddsList = document.querySelector('#odds-list');
const modeButtons = [...document.querySelectorAll('.mode')];
let currentMode = 'cards';
let angle = 0;
let busy = false;

function element(tag, props = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(props)) node.setAttribute(key, String(value));
  return node;
}

function polar(degrees, radius) {
  const a = degrees * Math.PI / 180;
  return { x: 180 + radius * Math.sin(a), y: 180 - radius * Math.cos(a) };
}

function wedge(start, end) {
  const a = polar(start, 155);
  const b = polar(end, 155);
  return 'M180 180 L' + a.x + ' ' + a.y + ' A155 155 0 ' + (end - start > 180 ? 1 : 0) +
    ' 1 ' + b.x + ' ' + b.y + ' Z';
}

function svgText(parent, x, y, text, cls, fontSize) {
  const node = element('text', { x, y, class: cls, 'font-size': fontSize });
  node.textContent = text;
  parent.append(node);
}

function segmentsForMode() { return currentMode === 'prizes' ? PRIZE_WHEEL : CARD_WHEEL; }

function renderWheel() {
  const segments = segmentsForMode();
  validateWheel(segments);
  wheel.replaceChildren();
  const outerRing = element('circle', { cx: 180, cy: 180, r: 168, fill: '#170d1b', stroke: '#dcad83', 'stroke-width': 6 });
  wheel.append(outerRing);
  let start = 0;
  for (const s of segments) {
    const end = start + s.weight * 3.6;
    const group = element('g');
    group.append(element('path', { d: wedge(start, end), fill: s.color, stroke: '#edc49b', 'stroke-width': 1.6 }));
    const center = polar((start + end) / 2, 108);
    svgText(group, center.x, center.y - 1, s.short, 'wheel-label', s.weight <= 7 ? 10 : 12);
    svgText(group, center.x, center.y + 14, s.weight + '%', 'wheel-weight', 10);
    wheel.append(group);
    start = end;
  }
  wheel.append(element('circle', { cx: 180, cy: 180, r: 156, fill: 'none', stroke: '#f4d5b1', 'stroke-width': 2 }));
  wheel.setAttribute('aria-label', currentMode === 'prizes' ? 'Призовое колесо из восьми секторов' : 'Карточное колесо с шестью редкостями');
  wheel.style.transition = 'none';
  wheel.style.transform = 'rotate(0deg)';
  angle = 0;
  // Force the zero-angle reset to render before enabling the transition.
  void wheel.getBoundingClientRect();
  wheel.style.transition = '';

  oddsList.replaceChildren();
  for (const s of segments) {
    const item = document.createElement('div');
    item.className = 'odds-item';
    const left = document.createElement('span');
    left.className = 'odds-name';
    const swatch = document.createElement('span');
    swatch.className = 'swatch';
    swatch.style.background = s.color;
    swatch.style.color = s.color;
    swatch.setAttribute('aria-hidden', 'true');
    const title = document.createElement('span');
    title.textContent = s.title;
    left.append(swatch, title);
    const pct = document.createElement('span');
    pct.className = 'odds-pct';
    pct.textContent = s.weight + '%';
    item.append(left, pct);
    oddsList.append(item);
  }
}

function setMode(next) {
  if (busy || !['prizes', 'cards'].includes(next) || currentMode === next) return;
  currentMode = next;
  for (const button of modeButtons) {
    const selected = button.dataset.mode === next;
    button.classList.toggle('active', selected);
    button.setAttribute('aria-pressed', String(selected));
  }
  status.textContent = 'Готово к демонстрационному вращению.';
  renderWheel();
}

function runSpin() {
  if (busy) return;
  const segments = segmentsForMode();
  let index;
  try {
    index = pickIndex(segments, browserRandomUnit());
  } catch (error) {
    status.textContent = 'Не удалось запустить демо: ' + error.message;
    return;
  }
  const target = targetRotation(segments, index, angle, 6);
  busy = true;
  spin.disabled = true;
  for (const button of modeButtons) button.disabled = true;
  spin.textContent = 'КОЛЕСО ВРАЩАЕТСЯ…';
  status.textContent = 'Колесо вращается…';
  let finished = false;
  let fallback;

  function finish() {
    if (finished) return;
    finished = true;
    clearTimeout(fallback);
    wheel.removeEventListener('transitionend', onTransitionEnd);
    angle = target;
    busy = false;
    spin.disabled = false;
    for (const button of modeButtons) button.disabled = false;
    spin.textContent = 'КРУТИТЬ ЕЩЁ';
    const reward = segments[index].title;
    status.textContent = (currentMode === 'cards' ? 'Выпала редкость: ' : 'Результат: ') + reward + ' · демо, без начисления';
  }

  function onTransitionEnd(event) {
    if (event.target === wheel && event.propertyName === 'transform') finish();
  }

  wheel.addEventListener('transitionend', onTransitionEnd);
  fallback = setTimeout(finish, 6100);
  requestAnimationFrame(() => {
    wheel.style.transform = 'rotate(' + target + 'deg)';
  });
}

for (const button of modeButtons) button.addEventListener('click', () => setMode(button.dataset.mode));
spin.addEventListener('click', runSpin);
renderWheel();
