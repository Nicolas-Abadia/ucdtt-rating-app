import { useState } from 'react';
import SearchField from '../../../components/SearchField';
import PlayerRow from './PlayerRow';
import type { PlayerData } from '../types';
import styles from './Leaderboard.module.css';

export default function Leaderboard({ players }: { players: PlayerData[] }) {
  const [searchTerm, setSearchTerm] = useState('');
  const query = searchTerm.trim().toLowerCase();
  // Preserve backend order and global ranks when filtering the full roster.
  const visiblePlayers = players.filter((player) => !query || player.id.toString() === query || player.name.toLowerCase().includes(query));

  return (
    <section className={styles.leaderboardPanel} aria-label="Player standings">
      <SearchField value={searchTerm} onChange={setSearchTerm}
        label="Search players by name or ID" placeholder="Search by name or ID" />
      {visiblePlayers.length === 0 && <p className={styles.emptyState} role="status">{query ? 'No matching players.' : 'No players available.'}</p>}
      <ul className={styles.playerList}>
        {visiblePlayers.map((player) => <PlayerRow key={player.id} player={player} rank={player.rank} />)}
      </ul>
    </section>
  );
}
