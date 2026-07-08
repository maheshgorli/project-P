import { useEffect, useState } from "react";
import api from "./services/api";

function App() {
  const [wildfires, setWildfires] = useState([]);
  const [storms, setStorms] = useState([]);

  useEffect(() => {
    api.get("/wildfires")
      .then((res) => {
        setWildfires(res.data);
      })
      .catch((err) => {
        console.error("Wildfire Error:", err);
      });

    api.get("/storms")
      .then((res) => {
        setStorms(res.data);
      })
      .catch((err) => {
        console.error("Storm Error:", err);
      });
  }, []);

  return (
    <div
      style={{
        padding: "20px",
        fontFamily: "Arial, sans-serif",
        backgroundColor: "#f5f5f5",
        minHeight: "100vh",
      }}
    >
      <h1
        style={{
          textAlign: "center",
          marginBottom: "30px",
        }}
      >
        🌍 Geo Satellite Tracking Platform
      </h1>

      {/* Stats Section */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          gap: "20px",
          marginBottom: "30px",
        }}
      >
        <div
          style={{
            background: "#fff",
            padding: "15px 30px",
            borderRadius: "10px",
            boxShadow: "0 2px 5px rgba(0,0,0,0.1)",
          }}
        >
          🔥 Wildfires: {wildfires.length}
        </div>

        <div
          style={{
            background: "#fff",
            padding: "15px 30px",
            borderRadius: "10px",
            boxShadow: "0 2px 5px rgba(0,0,0,0.1)",
          }}
        >
          🌪 Storms: {storms.length}
        </div>

        <div
          style={{
            background: "#fff",
            padding: "15px 30px",
            borderRadius: "10px",
            boxShadow: "0 2px 5px rgba(0,0,0,0.1)",
          }}
        >
          🌍 Total Events: {wildfires.length + storms.length}
        </div>
      </div>

      {/* Two Column Layout */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "25px",
        }}
      >
        {/* Wildfires */}
        <div>
          <h2
            style={{
              textAlign: "center",
              color: "orange",
              marginBottom: "20px",
            }}
          >
            🔥 Active Wildfires
          </h2>

          {wildfires.map((fire) => (
            <div
              key={fire.event_id}
              style={{
                backgroundColor: "#fff",
                borderRadius: "12px",
                padding: "15px",
                marginBottom: "15px",
                boxShadow: "0 2px 5px rgba(0,0,0,0.1)",
              }}
            >
              <h3>{fire.title}</h3>

              <p>
                <strong>Event ID:</strong> {fire.event_id}
              </p>

              <p>
                <strong>Category:</strong> {fire.category}
              </p>

              <p>
                <strong>Coordinates:</strong>{" "}
                {fire.coordinates?.join(", ")}
              </p>
            </div>
          ))}
        </div>

        {/* Storms */}
        <div>
          <h2
            style={{
              textAlign: "center",
              color: "#0077ff",
              marginBottom: "20px",
            }}
          >
            🌪 Active Storms
          </h2>

          {storms.map((storm) => (
            <div
              key={storm.event_id}
              style={{
                backgroundColor: "#fff",
                borderRadius: "12px",
                padding: "15px",
                marginBottom: "15px",
                boxShadow: "0 2px 5px rgba(0,0,0,0.1)",
              }}
            >
              <h3>{storm.title}</h3>

              <p>
                <strong>Event ID:</strong> {storm.event_id}
              </p>

              <p>
                <strong>Category:</strong> {storm.category}
              </p>

              <p>
                <strong>Coordinates:</strong>{" "}
                {storm.coordinates?.join(", ")}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;