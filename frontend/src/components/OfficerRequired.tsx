import styles from './OfficerRequired.module.css';

// Shared gate for officer-only write pages: one panel, one login link.
export default function OfficerRequired({ message }: { message: string }) {
  return (
    <section className={styles.panel}>
      <h2>Officer login required</h2>
      <p>{message}</p>
      <a href="#login" className={styles.link}>Open officer login</a>
    </section>
  );
}
