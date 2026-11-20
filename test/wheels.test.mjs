import test from 'node:test';
import assert from 'node:assert/strict';
import { PRIZE_WHEEL, CARD_WHEEL, validateWheel, pickIndex, sectorCenter, targetRotation, indexAtPointer } from '../src/wheels.mjs';

test('both canonical configurations total 100%, with exact lengths', () => {
  assert.equal(validateWheel(PRIZE_WHEEL), true);
  assert.equal(validateWheel(CARD_WHEEL), true);
  assert.equal(PRIZE_WHEEL.length, 8);
  assert.equal(CARD_WHEEL.length, 6);
  assert.deepEqual(PRIZE_WHEEL.map(x => x.weight), [20,20,15,15,10,10,5,5]);
  assert.deepEqual(CARD_WHEEL.map(x => x.weight), [25,22,19,16,11,7]);
});

test('currency is only вельветы, without tokens or real roubles', () => {
  for (const reward of PRIZE_WHEEL) assert.doesNotMatch(reward.title, /₽|\bVL\b|\bAVL\b/i);
  assert.equal(PRIZE_WHEEL[0].title, '10 вельветов');
  assert.equal(PRIZE_WHEEL[1].title, '20 вельветов');
  assert.equal(PRIZE_WHEEL[3].title, '50 вельветов');
});

test('boundary values select the correct adjacent prize sector', () => {
  assert.equal(pickIndex(PRIZE_WHEEL, 0), 0);
  assert.equal(pickIndex(PRIZE_WHEEL, 0.199999), 0);
  assert.equal(pickIndex(PRIZE_WHEEL, 0.2), 1);
  assert.equal(pickIndex(PRIZE_WHEEL, 0.4), 2);
  assert.equal(pickIndex(PRIZE_WHEEL, 0.55), 3);
  assert.equal(pickIndex(PRIZE_WHEEL, 0.7), 4);
  assert.equal(pickIndex(PRIZE_WHEEL, 0.8), 5);
  assert.equal(pickIndex(PRIZE_WHEEL, 0.9), 6);
  assert.equal(pickIndex(PRIZE_WHEEL, 0.95), 7);
  assert.equal(pickIndex(PRIZE_WHEEL, 0.999999), 7);
});

test('card boundaries follow six configured rarities', () => {
  assert.deepEqual(CARD_WHEEL.map(s => s.id), ['classic','elite','royal','epic','mythic','eternal']);
  assert.equal(pickIndex(CARD_WHEEL, 0.24999999), 0);
  assert.equal(pickIndex(CARD_WHEEL, 0.25), 1);
  assert.equal(pickIndex(CARD_WHEEL, 0.47), 2);
  assert.equal(pickIndex(CARD_WHEEL, 0.66), 3);
  assert.equal(pickIndex(CARD_WHEEL, 0.82), 4);
  assert.equal(pickIndex(CARD_WHEEL, 0.93), 5);
});

test('every pointer landing resolves to exactly the drawn segment', () => {
  for (const wheel of [PRIZE_WHEEL, CARD_WHEEL]) {
    for (const previousAngle of [0, 15, 257, 1597, 10800]) {
      wheel.forEach((_segment, index) => {
        const rotation = targetRotation(wheel, index, previousAngle, 5);
        assert.ok(rotation >= previousAngle + 1800);
        assert.equal(indexAtPointer(wheel, rotation), index);
        assert.ok(sectorCenter(wheel, index) >= 0);
      });
    }
  }
});

test('bad inputs and tampered weights fail closed', () => {
  assert.throws(() => validateWheel([{id:'x',weight:101,title:'x'}]));
  assert.throws(() => validateWheel([{id:'x',weight:50,title:'x'}, {id:'x',weight:50,title:'x'}]));
  assert.throws(() => pickIndex(PRIZE_WHEEL, 1), RangeError);
  assert.throws(() => pickIndex(PRIZE_WHEEL, -0.1), RangeError);
  assert.throws(() => targetRotation(PRIZE_WHEEL, -1), RangeError);
});

test('deterministic simulated distribution mirrors configured probabilities', () => {
  // 10,000 samples at cell centers across [0,1): every 1% is exactly 100 samples.
  for (const wheel of [PRIZE_WHEEL, CARD_WHEEL]) {
    const counts = wheel.map(() => 0);
    for (let i = 0; i < 10000; i++) counts[pickIndex(wheel, (i + 0.5)/10000)]++;
    assert.deepEqual(counts, wheel.map(s => s.weight * 100));
  }
});
