const VN_TIMEZONE = 'Asia/Ho_Chi_Minh';

const vnDateKeyFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: VN_TIMEZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

const vnDisplayDateFormatter = new Intl.DateTimeFormat('vi-VN', {
  timeZone: VN_TIMEZONE,
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
});

const vnShortDateFormatter = new Intl.DateTimeFormat('vi-VN', {
  timeZone: VN_TIMEZONE,
  day: '2-digit',
  month: '2-digit',
});

const vnTimeFormatter = new Intl.DateTimeFormat('vi-VN', {
  timeZone: VN_TIMEZONE,
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

const vnWeekdayFormatter = new Intl.DateTimeFormat('vi-VN', {
  timeZone: VN_TIMEZONE,
  weekday: 'short',
});

const vnMonthLabelFormatter = new Intl.DateTimeFormat('vi-VN', {
  timeZone: VN_TIMEZONE,
  month: 'long',
  year: 'numeric',
});

const vnHeaderDateFormatter = new Intl.DateTimeFormat('vi-VN', {
  timeZone: VN_TIMEZONE,
  weekday: 'long',
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
});

/**
 * Format a Date instance into YYYY-MM-DD in Asia/Ho_Chi_Minh.
 */
export function formatDateKeyVN(date = new Date()) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
  return vnDateKeyFormatter.format(date);
}

/**
 * Parse a check-in item's timestamp reliably, preserving explicit timezone offsets
 * and falling back to date-only strings anchored to Asia/Ho_Chi_Minh.
 */
export function parseCheckinTimestamp(item) {
  if (!item) return null;

  if (item.checkin_time) {
    const raw = String(item.checkin_time).trim();
    const hasOffset = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw);
    const parsed = new Date(hasOffset ? raw : `${raw}+07:00`);
    if (!Number.isNaN(parsed.getTime())) return parsed;
  }

  if (item.date) {
    const rawDate = String(item.date).trim();
    const datePart = rawDate.slice(0, 10);
    if (/^\d{4}-\d{2}-\d{2}$/.test(datePart)) {
      // Anchor date-only mock/DTO fields to noon +07:00 so VN date key never shifts.
      const parsed = new Date(`${datePart}T12:00:00+07:00`);
      if (!Number.isNaN(parsed.getTime())) return parsed;
    }
    const fallback = new Date(rawDate);
    if (!Number.isNaN(fallback.getTime())) return fallback;
  }

  return null;
}

/**
 * Return the YYYY-MM-DD calendar key in Asia/Ho_Chi_Minh for a check-in record.
 */
export function getCheckinDateKeyVN(item) {
  if (!item) return '';
  if (item.checkin_time) {
    const parsed = parseCheckinTimestamp({ checkin_time: item.checkin_time });
    if (parsed) return formatDateKeyVN(parsed);
  }
  if (item.date) {
    const rawDate = String(item.date).trim();
    if (/^\d{4}-\d{2}-\d{2}/.test(rawDate)) return rawDate.slice(0, 10);
    const parsed = parseCheckinTimestamp(item);
    if (parsed) return formatDateKeyVN(parsed);
  }
  return '';
}

/**
 * Return a new array of check-in logs sorted oldest -> newest.
 */
export function getSortedHistoryAsc(history = []) {
  return [...history].sort((a, b) => {
    const ta = parseCheckinTimestamp(a)?.getTime() ?? 0;
    const tb = parseCheckinTimestamp(b)?.getTime() ?? 0;
    if (ta !== tb) return ta - tb;
    return getCheckinDateKeyVN(a).localeCompare(getCheckinDateKeyVN(b));
  });
}

/**
 * Return the chronologically latest saved check-in record, or null when none exist.
 */
export function getLatestCheckin(history = []) {
  if (!Array.isArray(history) || history.length === 0) return null;
  const sorted = getSortedHistoryAsc(history);
  return sorted[sorted.length - 1] || null;
}

/**
 * Determine whether any saved check-in falls on today's date in Asia/Ho_Chi_Minh.
 */
export function hasCheckedInTodayVN(history = [], now = new Date()) {
  if (!Array.isArray(history) || history.length === 0) return false;
  const todayKey = formatDateKeyVN(now);
  return history.some((item) => getCheckinDateKeyVN(item) === todayKey);
}

/**
 * Return the latest saved check-in from today (Asia/Ho_Chi_Minh), or null.
 */
export function getTodayLatestCheckinVN(history = [], now = new Date()) {
  if (!Array.isArray(history) || history.length === 0) return null;
  const todayKey = formatDateKeyVN(now);
  const todayItems = getSortedHistoryAsc(history).filter(
    (item) => getCheckinDateKeyVN(item) === todayKey
  );
  return todayItems.length > 0 ? todayItems[todayItems.length - 1] : null;
}

export function formatCheckinDateVN(item) {
  const dt = parseCheckinTimestamp(item);
  if (!dt) return item?.date || '--';
  return vnDisplayDateFormatter.format(dt);
}

export function formatCheckinShortDateVN(item) {
  const dt = parseCheckinTimestamp(item);
  if (!dt) {
    const key = getCheckinDateKeyVN(item);
    return key ? `${key.slice(8, 10)}/${key.slice(5, 7)}` : '--';
  }
  return vnShortDateFormatter.format(dt);
}

export function formatCheckinDateTimeVN(item) {
  const dt = parseCheckinTimestamp(item);
  if (!dt) return item?.date || '--';
  if (item?.checkin_time) {
    return `${vnDisplayDateFormatter.format(dt)} • ${vnTimeFormatter.format(dt)}`;
  }
  return vnDisplayDateFormatter.format(dt);
}

export function formatHeaderTodayVN(now = new Date()) {
  return vnHeaderDateFormatter.format(now);
}

export function getMonthKeyVN(itemOrDate) {
  if (itemOrDate instanceof Date) {
    return formatDateKeyVN(itemOrDate).slice(0, 7);
  }
  const key = getCheckinDateKeyVN(itemOrDate);
  return key ? key.slice(0, 7) : '';
}

export function formatMonthPillVN(monthKey) {
  if (!/^\d{4}-\d{2}$/.test(monthKey || '')) return monthKey || '';
  const dt = new Date(`${monthKey}-15T12:00:00+07:00`);
  const formatted = vnMonthLabelFormatter.format(dt);
  return formatted.charAt(0).toUpperCase() + formatted.slice(1);
}

/**
 * Build the last `count` calendar days anchored in Asia/Ho_Chi_Minh (oldest -> newest).
 */
export function getRecentDaysVN(count = 14, now = new Date()) {
  const todayKey = formatDateKeyVN(now);
  const [y, m, d] = todayKey.split('-').map(Number);
  const baseUtcNoon = new Date(Date.UTC(y, m - 1, d, 5, 0, 0)); // 12:00 +07:00
  const days = [];

  for (let i = count - 1; i >= 0; i--) {
    const cursor = new Date(baseUtcNoon.getTime() - i * 86400000);
    const dateStr = formatDateKeyVN(cursor);
    const [, mm, dd] = dateStr.split('-');
    const shortWeekday = vnWeekdayFormatter.format(cursor).replace(/^Th(?:ứ)?\s*/i, 'T');
    days.push({
      dateStr,
      dayLabel: `${Number(dd)}/${Number(mm)}`,
      weekday: shortWeekday,
    });
  }

  return days;
}
