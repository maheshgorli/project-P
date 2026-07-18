import styles from "./ImageCard.module.css";

/**
 * Gallery image card.
 * Props: image — gallery item object from GET /gallery
 */
export default function ImageCard({ image }) {
  const confidence = image.confidence
    ? `${(image.confidence * 100).toFixed(0)}%`
    : "N/A";

  const confidenceClass =
    image.confidence >= 0.8
      ? styles.high
      : image.confidence >= 0.5
      ? styles.mid
      : styles.low;

  function handleDownload() {
    const link = document.createElement("a");
    link.href = image.image_url;
    link.download = image.filename;
    link.click();
  }

  return (
    <article className={styles.card}>
      {/* Image */}
      <div className={styles.imgWrap}>
        <img
          src={image.image_url}
          alt={`Satellite image: ${image.disaster_type} at ${image.location}`}
          className={styles.img}
          loading="lazy"
          onError={(e) => {
            e.currentTarget.src = "";
            e.currentTarget.closest(`.${styles.imgWrap}`).setAttribute(
              "data-empty",
              "true"
            );
          }}
        />
        <span className={styles.type}>{image.disaster_type}</span>
      </div>

      {/* Metadata */}
      <div className={styles.body}>
        <dl className={styles.meta}>
          <div className={styles.row}>
            <dt>📅 Date</dt>
            <dd>{image.date}</dd>
          </div>
          <div className={styles.row}>
            <dt>📍 Location</dt>
            <dd>{image.location}</dd>
          </div>
          <div className={styles.row}>
            <dt>🤖 AI Prediction</dt>
            <dd>{image.prediction || "Pending"}</dd>
          </div>
          <div className={styles.row}>
            <dt>📊 Confidence</dt>
            <dd className={confidenceClass}>{confidence}</dd>
          </div>
        </dl>

        <button
          className={styles.downloadBtn}
          onClick={handleDownload}
          aria-label={`Download ${image.filename}`}
        >
          ⬇ Download
        </button>
      </div>
    </article>
  );
}
