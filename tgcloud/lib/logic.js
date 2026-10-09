export function russianNumber(value, one, few, many) {
  const word = value % 10 === 1 && value % 100 !== 11 ? one
    : [2, 3, 4].includes(value % 10) && ![12, 13, 14].includes(value % 100) ? few : many;

  return `${value} ${word}`;
}

export function formatElapsed(lastPostAt, now) {
  const seconds = Math.max(0, now - lastPostAt);
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor(seconds % 86400 / 3600);
  
  const parts = [];
  
  if (days) parts.push(russianNumber(days, 'день', 'дня', 'дней'));
  if (hours) parts.push(russianNumber(hours, 'час', 'часа', 'часов'));
  
  return parts.length ? `${parts.join(' и ')} назад` : 'меньше часа назад';
}

export function localCalendar(timestamp, timezone) {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(timestamp * 1000));
  
  const fields = Object.fromEntries(parts.map(p => [p.type, p.value]));
  
  return {
    day: Math.floor(Date.UTC(+fields.year, +fields.month - 1, +fields.day) / 86400000),
    hour: +fields.hour,
  };
}

export function dueReminder(lastPostAt, now, settings) {
  if (lastPostAt == null) return null;
  
  const current = localCalendar(now, settings.timezone);
  const age = current.day - localCalendar(lastPostAt, settings.timezone).day;
  
  if (age >= settings.streakDays + 1) return 'lost';
  if (current.hour >= 22 && age === settings.streakDays) return 'final';
  if (current.hour >= 22 && age === settings.streakDays - 1) return 'close';
  
  return null;
}

