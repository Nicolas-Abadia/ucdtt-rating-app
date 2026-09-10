import type { CSSProperties } from 'react';
import Icon from '../../../components/Icon';
import { AVATAR_COLORS } from '../../../styles/tokens';
import type { PlayerData } from '../types';
import styles from './PlayerRow.module.css';

interface PlayerRowProps { player: PlayerData; rank: number }

export default function PlayerRow({ player, rank }: PlayerRowProps) {
  const colorIndex = player.id % AVATAR_COLORS.length;
  const avatarStyle = {
    '--avatar-bg': AVATAR_COLORS[colorIndex],
    '--avatar-ink': colorIndex >= 3 ? 'var(--tone-black)' : 'var(--white)',
  } as CSSProperties;

  return (
    <li>
      <a href={`#players/${player.id}`} className={styles.playerCard}>
        <div className={styles.playerAvatar} style={avatarStyle} aria-hidden="true">
          {player.name.trim().charAt(0).toUpperCase()}
        </div>
        <div className={styles.playerBody}>
          <div className={styles.playerInfo}>
            <span className={styles.playerRank} aria-label={`Rank: ${rank}`}>{rank}</span>
            <span className={styles.playerIdentity}>
              <span className={styles.playerName} title={player.name}>{player.name}</span>
              <span className={styles.playerId} title={`Player ID: ${player.id}`}>#{player.id}</span>
            </span>
          </div>
          <div className={styles.stats}>
            <span className={styles.stat} aria-label={`Rating: ${player.display_rating}`}><Icon name="rating" size={16} />{player.display_rating}</span>
            <span className={styles.stat} aria-label={`Wins: ${player.wins}`}><Icon name="win" size={16} />{player.wins} won</span>
            <span className={styles.stat} aria-label={`Losses: ${player.losses}`}><Icon name="loss" size={16} />{player.losses} lost</span>
          </div>
        </div>
      </a>
    </li>
  );
}
