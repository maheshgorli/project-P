import { useEffect, useState, useCallback } from "react";
import api from "../services/api";
import ImageCard from "../components/ImageCard";
import LoadingSpinner from "../components/LoadingSpinner";
import Toast from "../components/Toast";
import styles from "./Gallery.module.css";

export default function Gallery() {
  const [images, setImages]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast]     = useState({ message: "", type: "info" });

  const fetchGallery = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/gallery");
      setImages(res.data);
    } catch (err) {
      console.error("Gallery fetch error:", err);
      setToast({ message: "Failed to load gallery from backend.", type: "error" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGallery();
  }, [fetchGallery]);

  return (
    <main className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>🛰 Satellite Image Gallery</h1>
          <p className={styles.subtitle}>Previously downloaded satellite images</p>
        </div>
        <button
          className={styles.refreshBtn}
          onClick={fetchGallery}
          disabled={loading}
          aria-label="Refresh gallery"
        >
          {loading ? <LoadingSpinner size="14px" color="currentColor" /> : "↺"}&nbsp;
          Refresh
        </button>
      </div>

      {/* Body */}
      {loading ? (
        <div className={styles.loadingRow}>
          <LoadingSpinner size="36px" color="var(--accent)" />
          <span>Loading images…</span>
        </div>
      ) : images.length === 0 ? (
        <div className={styles.empty}>
          <span className={styles.emptyIcon} aria-hidden="true">🛰</span>
          <h2>No images yet</h2>
          <p>
            Go to the Dashboard and click&nbsp;
            <strong>Start Monitoring</strong> to download satellite images.
          </p>
        </div>
      ) : (
        <>
          <p className={styles.count}>
            {images.length} image{images.length !== 1 ? "s" : ""} stored
          </p>
          <div className={styles.grid} role="list">
            {images.map((img) => (
              <div key={img.filename} role="listitem">
                <ImageCard image={img} />
              </div>
            ))}
          </div>
        </>
      )}

      <Toast
        message={toast.message}
        type={toast.type}
        onClose={() => setToast({ message: "", type: "info" })}
      />
    </main>
  );
}
