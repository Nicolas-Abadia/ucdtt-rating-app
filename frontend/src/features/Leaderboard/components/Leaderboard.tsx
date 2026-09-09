import { useId, useState } from 'react';
import Icon from '../../../components/Icon';
import PlayerRow from './PlayerRow';
import type { PlayerData } from '../types';
import styles from './Leaderboard.module.css';

export default function Leaderboard({ players }: { players: PlayerData[] }) {
  const [searchTerm, setSearchTerm] = useState('');
  const searchId = useId();
  const query = searchTerm.trim().toLowerCase();
  // Preserve backend order and global ranks when filtering the full roster.
  const visiblePlayers = players.filter((player) => !query || player.id.toString() === query || player.name.toLowerCase().includes(query));

  return (
    <section className={styles.leaderboardPanel} aria-label="Player standings">
      <div className={styles.searchBar}>
        <label className={styles.srOnly} htmlFor={searchId}>Search players by name or ID</label>
        <span className={styles.searchIcon}><Icon name="search" size={18} /></span>
        <input id={searchId} type="search" placeholder="Search by name or ID" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} />
      </div>
      {visiblePlayers.length === 0 && <p className={styles.emptyState} role="status">{query ? 'No matching players.' : 'No players available.'}</p>}
      <ul className={styles.playerList}>
        {visiblePlayers.map((player) => <PlayerRow key={player.id} player={player} rank={player.rank} />)}
      </ul>
    </section>
  );
}
