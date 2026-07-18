import { NavLink } from "react-router-dom";
import styles from "./Navbar.module.css";

export default function Navbar() {
  return (
    <header className={styles.header} role="banner">
      <div className={styles.brand}>
        <span className={styles.logo} aria-hidden="true">🛰</span>
        <span className={styles.name}>GeoSat Platform</span>
      </div>
      <nav className={styles.nav} aria-label="Main navigation">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `${styles.link} ${isActive ? styles.active : ""}`
          }
        >
          Dashboard
        </NavLink>
        <NavLink
          to="/gallery"
          className={({ isActive }) =>
            `${styles.link} ${isActive ? styles.active : ""}`
          }
        >
          Image Gallery
        </NavLink>
      </nav>
    </header>
  );
}
