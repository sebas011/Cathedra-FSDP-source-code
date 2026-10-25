export function localToday(now: Date = new Date()) {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: "Asia/Manila",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(now);
  const part = (type: string) => parts.find((item) => item.type === type)?.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}

/** SQLite service timestamps without an offset are UTC, not browser-local time. */
export function registrationTimestamp(value: string | null | undefined) {
  if (!value?.trim()) return null;
  let normalized = value.trim().replace(" ", "T");
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(normalized)) return null;
  if (!/(?:Z|[+-]\d{2}:?\d{2})$/i.test(normalized)) normalized += "Z";
  const instant = new Date(normalized);
  return Number.isNaN(instant.getTime()) ? null : instant.toISOString();
}

export function formatRegistrationDate(value: string | null | undefined, locale?: string) {
  const instant = registrationTimestamp(value);
  return instant
    ? new Date(instant).toLocaleDateString(locale, {
        day: "2-digit",
        month: "short",
        year: "numeric",
        timeZone: "Asia/Manila",
      })
    : "Not recorded";
}

export function formatRecordDateTime(value: string | null | undefined, locale?: string) {
  const instant = registrationTimestamp(value);
  return instant
    ? new Intl.DateTimeFormat(locale, {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "Asia/Manila",
      }).format(new Date(instant))
    : "Not recorded";
}

/** Format recognized years only; keep partial and historical custom periods intact. */
export function formatAcademicYear(value: string) {
  const text = value.trim();
  const compact = text.match(/^(\d{4})\s*(?:[-–/]\s*)?(\d{4})$/);
  if (compact) {
    const start = Number(compact[1]),
      end = Number(compact[2]);
    if (start >= 1000 && start <= 9998 && end === start + 1) return `${compact[1]}-${compact[2]}`;
  }
  return value;
}
