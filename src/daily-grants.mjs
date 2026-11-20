// Pure scheduling utility; does not credit user accounts or persist state.
// This module intentionally has no fixed production schedule or wallet.
function assertSchedule(schedule) {
  if (!schedule || typeof schedule !== 'object') throw new TypeError('Missing schedule');
  if (typeof schedule.campaign !== 'string' || !/^[a-z0-9_-]{1,40}$/i.test(schedule.campaign))
    throw new TypeError('Invalid campaign');
  if (typeof schedule.timeZone !== 'string') throw new TypeError('Missing time zone');
  try { new Intl.DateTimeFormat('en-GB', { timeZone: schedule.timeZone }).format(new Date()); }
  catch { throw new TypeError('Invalid time zone'); }
  if (!Array.isArray(schedule.windows) || schedule.windows.length < 1 || schedule.windows.length > 6)
    throw new TypeError('Invalid windows');
  const ids = new Set();
  for (const w of schedule.windows) {
    if (!w || typeof w.id !== 'string' || !/^[a-z0-9_-]{1,24}$/i.test(w.id) || ids.has(w.id))
      throw new TypeError('Duplicate or invalid window id');
    if (typeof w.at !== 'string' || !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(w.at))
      throw new TypeError('Invalid window time');
    if (!Number.isSafeInteger(w.spins) || w.spins < 1 || w.spins > 100)
      throw new TypeError('Invalid spin grant');
    ids.add(w.id);
  }
}

function localDateTime(date, timeZone) {
  if (!(date instanceof Date) || !Number.isFinite(date.getTime())) throw new TypeError('Invalid date');
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
  }).formatToParts(date);
  const part = key => parts.find(p => p.type === key)?.value;
  return {
    date: part('year') + '-' + part('month') + '-' + part('day'),
    clock: part('hour') + ':' + part('minute')
  };
}

// Eligible means the grant window opened today. A SQL unique key, not this
// function, must guarantee once-only credit when multiple workers race.
export function eligibleDailyGrants(schedule, now) {
  assertSchedule(schedule);
  const { date, clock } = localDateTime(now, schedule.timeZone);
  return schedule.windows
    .filter(window => window.at <= clock)
    .map(window => ({
      key: schedule.campaign + ':' + date + ':' + window.id,
      campaign: schedule.campaign,
      date, window: window.id, spins: window.spins
    }));
}

export function unclaimedDailyGrants(schedule, now, previouslyCredited = []) {
  if (!Array.isArray(previouslyCredited)) throw new TypeError('Expected credited grant keys');
  const credited = new Set(previouslyCredited);
  return eligibleDailyGrants(schedule, now).filter(grant => !credited.has(grant.key));
}
