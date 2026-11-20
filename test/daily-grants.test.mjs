import test from 'node:test';
import assert from 'node:assert/strict';
import { eligibleDailyGrants, unclaimedDailyGrants } from '../src/daily-grants.mjs';

// A test fixture ONLY: user has not approved production quota, times, or timezone.
const example = {
  campaign: 'drop-1',
  timeZone: 'Europe/Berlin',
  windows: [
    { id: 'morning', at: '08:00', spins: 6 },
    { id: 'evening', at: '19:00', spins: 6 }
  ]
};
const moment = value => new Date(value);

test('daily grants are unavailable before the configured local window', () => {
  assert.deepEqual(eligibleDailyGrants(example, moment('2026-11-20T06:30:00Z')), []);
  assert.deepEqual(eligibleDailyGrants(example, moment('2026-11-20T07:00:00Z')).map(g => g.window), ['morning']);
  assert.deepEqual(eligibleDailyGrants(example, moment('2026-11-20T18:00:00Z')).map(g => g.window), ['morning', 'evening']);
});

test('grant keys are stable and scoped to each calendar day, campaign and window', () => {
  const a = eligibleDailyGrants(example, moment('2026-11-20T18:00:00Z'));
  const b = eligibleDailyGrants(example, moment('2026-11-21T18:00:00Z'));
  assert.deepEqual(a.map(g => g.key), ['drop-1:2026-11-20:morning','drop-1:2026-11-20:evening']);
  assert.notEqual(a[0].key, b[0].key);
});

test('previously credited grants are not proposed again', () => {
  const claimed = ['drop-1:2026-11-20:morning'];
  const available = unclaimedDailyGrants(example, moment('2026-11-20T18:10:00Z'), claimed);
  assert.equal(available.length, 1);
  assert.equal(available[0].window, 'evening');
  assert.equal(unclaimedDailyGrants(example, moment('2026-11-20T18:10:00Z'), [...claimed, available[0].key]).length, 0);
});

test('time zone DST is evaluated at the instant, not using a fixed UTC offset', () => {
  const morningUTC = moment('2026-03-29T05:00:00Z'); // Berlin 07:00 CEST
  const morningOpen = moment('2026-03-29T06:00:00Z'); // Berlin 08:00 CEST
  assert.equal(eligibleDailyGrants(example, morningUTC).length, 0);
  assert.equal(eligibleDailyGrants(example, morningOpen).length, 1);
});

test('bad schedules and clocks are rejected', () => {
  assert.throws(() => eligibleDailyGrants({...example, timeZone: 'Not/AZone'}, moment('2026-11-20T12:00:00Z')));
  assert.throws(() => eligibleDailyGrants({...example, windows: [...example.windows, example.windows[0]]}, moment('2026-11-20T12:00:00Z')));
  assert.throws(() => eligibleDailyGrants({...example, windows: [{id:'x',at:'25:44',spins:6}]}, moment('2026-11-20T12:00:00Z')));
  assert.throws(() => eligibleDailyGrants(example, new Date('nonsense')));
});
