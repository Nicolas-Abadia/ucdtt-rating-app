import type { RatingPoint } from '../../types/profile';
import styles from './PlayerProfilePage.module.css';

const formatDate = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' });

// Small inline SVG line chart. No chart dependency is installed; the table
// beneath the SVG carries the same values for screen readers and precision.
export default function RatingChart({ points }: { points: RatingPoint[] }) {
  if (points.length === 0) {
    return <p className={styles.chartEmpty}>No rating changes in the last 90 days.</p>;
  }
  if (points.length === 1) {
    const [point] = points;
    return (
      <p className={styles.chartEmpty}>
        Only one rating point in the last 90 days: {point.rating} on {formatDate.format(new Date(point.date))}.
      </p>
    );
  }

  const width = 320;
  const height = 120;
  const times = points.map((point) => new Date(point.date).getTime());
  const ratings = points.map((point) => point.rating);
  const minTime = Math.min(...times);
  const maxTime = Math.max(...times);
  const minRating = Math.min(...ratings);
  const maxRating = Math.max(...ratings);
  const spanTime = maxTime - minTime || 1;
  const spanRating = maxRating - minRating || 1;
  const coords = points.map((point, index) => ({
    x: ((times[index] - minTime) / spanTime) * (width - 16) + 8,
    y: height - 8 - ((point.rating - minRating) / spanRating) * (height - 16),
  }));
  const path = coords.map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(' ');
  const described = points.map((point) => `${formatDate.format(new Date(point.date))}: ${point.rating}`).join(', ');

  return (
    <figure className={styles.chart}>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Rating over time: ${described}`}>
        <path d={path} fill="none" stroke="var(--night-sky-blue)" strokeWidth={2} />
        {coords.map((point, index) => (
          <circle key={points[index].match} cx={point.x} cy={point.y} r={3} fill="var(--aggie-yellow)" />
        ))}
      </svg>
      <table className={styles.chartTable}>
        <caption>Rating history values</caption>
        <thead><tr><th scope="col">Date</th><th scope="col">Rating</th></tr></thead>
        <tbody>
          {points.map((point) => (
            <tr key={point.match}>
              <td>{formatDate.format(new Date(point.date))}</td>
              <td>{point.rating}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
