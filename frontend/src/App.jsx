import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import Gallery from "./pages/Gallery";
import Monitoring from "./pages/Monitoring";
import styles from "./App.module.css";

export default function App() {
  return (
    <BrowserRouter>
      <div className={styles.layout}>
        <Navbar />
        <div className={styles.content}>
          <Routes>
            <Route path="/"          element={<Dashboard />} />
            <Route path="/gallery"   element={<Gallery />} />
            <Route path="/monitoring" element={<Monitoring />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}
