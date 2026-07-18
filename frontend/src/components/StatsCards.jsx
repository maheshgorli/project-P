import styles from "./StatsCards.module.css";

const CARDS = [
  { key: "wildfires", icon: "🔥", label: "Wildfires",     color: "fire"    },
  { key: "storms",    icon: "🌪",  label: "Storms",        color: "storm"   },
  { key: "total",     icon: "🌍",  label: "Total Events",  color: "accent"  },
  { key: "images",    icon: "🛰",  label: "Images Saved",  color: "success" },
];

/**
 * Stats bar at the top of the dashboard.
 * Props:
 *   wildfires  — number
 *   storms     — number
 *   images     — number
 */
export default function StatsCards({ wildfires = 0, storms = 0, images = 0 }) {
  const values = {
    wildfires,
    storms,
    total: wildfires + storms,
    images,
  };

  return (
    <div className={styles.grid} role="region" aria-label="Event statistics">
      {CARDS.map(({ key, icon, label, color }) => (
        <div key={key} className={`${styles.card} ${styles[color]}`}>
          <span className={styles.icon} aria-hidden="true">{icon}</span>
          <div>
            <div className={styles.value}>{values[key]}</div>
            <div className={styles.label}>{label}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
