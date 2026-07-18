import styles from "./EventCard.module.css";

/**
 * Single wildfire / storm event card.
 * Props:
 *   event  — { title, event_id, category, coordinates }
 *   type   — "wildfire" | "storm"
 */
export default function EventCard({ event, type }) {
  const isWildfire = type === "wildfire";

  return (
    <article className={`${styles.card} ${isWildfire ? styles.wildfire : styles.storm}`}>
      <div className={styles.badge}>
        {isWildfire ? "🔥" : "🌪"} {event.category}
      </div>
      <h3 className={styles.title}>{event.title}</h3>
      <dl className={styles.meta}>
        <div className={styles.row}>
          <dt>Event ID</dt>
          <dd>{event.event_id}</dd>
        </div>
        {event.coordinates && (
          <div className={styles.row}>
            <dt>Coordinates</dt>
            <dd>
              {Number(event.coordinates[1]).toFixed(4)}°,&nbsp;
              {Number(event.coordinates[0]).toFixed(4)}°
            </dd>
          </div>
        )}
      </dl>
    </article>
  );
}
