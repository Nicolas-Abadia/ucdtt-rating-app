import styles from './PageLayout.module.css';
import controls from './Button.module.css';

interface RequestStateProps {
  title: string;
  message?: string;
  loading?: boolean;
  onRetry?: () => void;
}

export default function RequestState({ title, message, loading = false, onRetry }: RequestStateProps) {
  return (
    <div className={loading ? styles.loadingContainer : styles.errorContainer} role={loading ? 'status' : 'alert'}>
      {loading && <div className={styles.spinner} aria-hidden="true" />}
      <h2>{title}</h2>
      {message && <p>{message}</p>}
      {onRetry && <button type="button" className={controls.button} onClick={onRetry}>Try again</button>}
    </div>
  );
}
