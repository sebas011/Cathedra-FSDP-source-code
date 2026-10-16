export function localToday() {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
}

/** Format recognized years only; keep partial and historical custom periods intact. */
export function formatAcademicYear(value: string, completeSingleYear = false) {
  const text = value.trim();
  const compact = text.match(/^(\d{4})\s*(?:[-–/]\s*)?(\d{4})$/);
  if (compact) {
    const start = Number(compact[1]),
      end = Number(compact[2]);
    if (start >= 1000 && start <= 9998 && end === start + 1) return `${compact[1]}-${compact[2]}`;
  }
  if (completeSingleYear && /^\d{4}$/.test(text)) {
    const start = Number(text);
    if (start >= 1000 && start <= 9998) return `${text}-${start + 1}`;
  }
  return value;
}
