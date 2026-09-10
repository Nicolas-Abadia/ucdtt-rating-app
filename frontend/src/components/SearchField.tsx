import { useId } from 'react';
import Icon from './Icon';
import styles from './SearchField.module.css';

interface SearchFieldProps {
  value: string;
  onChange: (value: string) => void;
  label: string;
  placeholder: string;
  describedBy?: string;
}

export default function SearchField({ value, onChange, label, placeholder, describedBy }: SearchFieldProps) {
  const id = useId();
  return (
    <div className={styles.searchBar}>
      <label className={styles.srOnly} htmlFor={id}>{label}</label>
      <span className={styles.searchIcon}><Icon name="search" size={18} /></span>
      <input id={id} type="search" placeholder={placeholder} value={value}
        onChange={(event) => onChange(event.target.value)} aria-describedby={describedBy} />
    </div>
  );
}
