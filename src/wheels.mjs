// Prototype-only weights. No accounting or grants are performed here.
export const PRIZE_WHEEL = Object.freeze([
  { id: 'velvets10', title: '10 вельветов', short: '10', weight: 20, color: '#785061' },
  { id: 'velvets20', title: '20 вельветов', short: '20', weight: 20, color: '#a66f5d' },
  { id: 'classic', title: 'Карта Classic', short: 'Classic', weight: 15, color: '#6e6d91' },
  { id: 'velvets50', title: '50 вельветов', short: '50', weight: 15, color: '#a87b49' },
  { id: 'elite', title: 'Карта Elite', short: 'Elite', weight: 10, color: '#be655f' },
  { id: 'spin1', title: '1 крутка', short: '+1', weight: 10, color: '#477c7c' },
  { id: 'spin2', title: '2 крутки', short: '+2', weight: 5, color: '#7163a2' },
  { id: 'royal', title: 'Карта Royal', short: 'Royal', weight: 5, color: '#bd8c43' }
]);

export const CARD_WHEEL = Object.freeze([
  { id: 'classic', title: 'Classic', short: 'Classic', weight: 25, color: '#827e9c' },
  { id: 'elite', title: 'Elite', short: 'Elite', weight: 22, color: '#bd6364' },
  { id: 'royal', title: 'Royal', short: 'Royal', weight: 19, color: '#d39d42' },
  { id: 'epic', title: 'Epic', short: 'Epic', weight: 16, color: '#c74a32' },
  { id: 'mythic', title: 'Mythic', short: 'Mythic', weight: 11, color: '#9a4eb4' },
  { id: 'eternal', title: 'Eternal', short: 'Eternal', weight: 7, color: '#348eae' }
]);

export function validateWheel(segments) {
  if (!Array.isArray(segments) || segments.length === 0) throw new Error('Missing segments');
  const ids = new Set();
  let sum = 0;
  for (const s of segments) {
    if (!s || typeof s.id !== 'string' || !s.id || ids.has(s.id)) throw new Error('Duplicate or missing ID');
    if (!Number.isSafeInteger(s.weight) || s.weight <= 0) throw new Error('Invalid weight');
    if (typeof s.title !== 'string' || !s.title) throw new Error('Invalid title');
    ids.add(s.id);
    sum += s.weight;
  }
  if (sum !== 100) throw new Error('Probabilities must total 100%');
  return true;
}

// unit is in [0,1). On the server, draw it from a cryptographic RNG.
export function pickIndex(segments, unit) {
  validateWheel(segments);
  if (!Number.isFinite(unit) || unit < 0 || unit >= 1) throw new RangeError('Expected random unit in [0,1)');
  const target = unit * 100;
  let cumulative = 0;
  for (let i = 0; i < segments.length; i++) {
    cumulative += segments[i].weight;
    if (target < cumulative) return i;
  }
  throw new Error('Unreachable random target');
}

export function sectorCenter(segments, index) {
  validateWheel(segments);
  if (!Number.isInteger(index) || index < 0 || index >= segments.length) throw new RangeError('Invalid index');
  let before = 0;
  for (let i = 0; i < index; i++) before += segments[i].weight;
  return (before + segments[index].weight / 2) * 3.6;
}

// Unrotated sector starts at 12 o'clock and increases clockwise.
// Clockwise CSS rotation means the sector center reaches 12 o'clock at -center.
export function targetRotation(segments, index, currentAngle = 0, revolutions = 5) {
  const center = sectorCenter(segments, index);
  if (!Number.isFinite(currentAngle) || !Number.isSafeInteger(revolutions) || revolutions < 0) throw new RangeError('Invalid rotation');
  const normalized = ((currentAngle + center) % 360 + 360) % 360;
  const correction = (360 - normalized) % 360;
  return currentAngle + revolutions * 360 + correction;
}

export function indexAtPointer(segments, angle) {
  validateWheel(segments);
  if (!Number.isFinite(angle)) throw new RangeError('Invalid angle');
  const normalized = ((angle % 360) + 360) % 360;
  const unrotated = (360 - normalized) % 360;
  const value = unrotated / 3.6;
  let cumulative = 0;
  for (let i = 0; i < segments.length; i++) {
    cumulative += segments[i].weight;
    if (value < cumulative) return i;
  }
  return segments.length - 1;
}

export function browserRandomUnit() {
  if (!globalThis.crypto || !globalThis.crypto.getRandomValues) {
    throw new Error('Secure browser RNG unavailable');
  }
  const sample = new Uint32Array(1);
  globalThis.crypto.getRandomValues(sample);
  return sample[0] / 4294967296;
}
