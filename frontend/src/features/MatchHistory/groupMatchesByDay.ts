import type { MatchSummary } from '../../types/match';

interface MatchDayGroup {
  dayKey: string;
  label: string;
  matches: MatchSummary[];
}

const dayLabel = new Intl.DateTimeFormat(undefined, {
  year: 'numeric', month: 'long', day: 'numeric',
});

export function groupMatchesByDay(matches: MatchSummary[]): MatchDayGroup[] {
  const groups = new Map<string, MatchDayGroup>();
  for (const match of matches) {
    const date = new Date(match.date);
    // Local calendar parts, not ISO slicing (which would group by UTC day).
    const dayKey = [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'),
      String(date.getDate()).padStart(2, '0')].join('-');
    let group = groups.get(dayKey);
    if (!group) {
      group = { dayKey, label: dayLabel.format(date), matches: [] };
      groups.set(dayKey, group);
    }
    group.matches.push(match);
  }
  // Keep backend order, including the primary-key tie-break for equal times.
  return Array.from(groups.values());
}
