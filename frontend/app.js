"use strict";

const RISK_LEVELS = { LOW: "#2eae62", MODERATE: "#e2bf3f", HIGH: "#e07a20", VERY_HIGH: "#c94343" };
const map = L.map("map", { zoomControl: false }).setView([20, 0], 2);
L.control.zoom({ position: "bottomleft" }).addTo(map);
const baseLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(map);
const display = (value, suffix = "") => value === null || value === undefined || Number.isNaN(Number(value)) ? "unknown" : `${value}${suffix}`;
const percent = value => value === null || value === undefined ? "unknown" : `${Math.round(Number(value) * 100)}%`;
const riskLayer = L.geoJSON(null, {
  style: feature => ({ color: RISK_LEVELS[feature.properties.risk_level] || "#64748b", weight: 1, fillColor: RISK_LEVELS[feature.properties.risk_level] || "#64748b", fillOpacity: .52 }),
  onEachFeature: (feature, layer) => {
    const p = feature.properties;
    layer.bindPopup(`<strong>Flood risk: ${p.risk_level} — ${display(p.risk_score, "/100")}</strong><br>Rainfall: location forecast<br>Elevation: ${display(p.elevation_m, " m")}<br>Slope: ${display(p.slope_deg, "°")}<br>Built-up: ${percent(p.built_up_fraction)}<br>Water: ${percent(p.water_fraction)}<br>Land cover: ${display(p.land_cover_class)}<br>Water distance: ${display(p.water_distance_m, " m")}<br>Buildings: ${display(p.building_count)}`);
  }
}).addTo(map);
let marker;
let selected = { lat: 20, lon: 0 };

function setSelected(lat, lon) {
  selected = { lat, lon };
  document.querySelector("#selected-coordinates").textContent = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
  if (marker) marker.setLatLng([lat, lon]); else marker = L.marker([lat, lon]).addTo(map);
}
function setMessage(text, isError = false) {
  const message = document.querySelector("#analysis-message");
  message.textContent = text;
  message.classList.toggle("error", isError);
  document.querySelector("#map-message").textContent = text;
  document.querySelector("#map-message").classList.toggle("error", isError);
}
function setRiskColor(level) {
  document.querySelector("#risk-level").style.background = RISK_LEVELS[level] || "#64748b";
}
function setLoading(isLoading) {
  const button = document.querySelector("#analyze-location");
  button.disabled = isLoading;
  button.classList.toggle("is-loading", isLoading);
  button.setAttribute("aria-busy", String(isLoading));
}
function formatSources(sources) {
  return Object.values(sources || {}).filter(Boolean).join(" · ");
}

async function analyzeLocation() {
  setLoading(true);
  setMessage("Fetching weather, terrain, land cover, and map context…");
  try {
    const response = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(selected) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Data is not available for this location.");
    if (!data.grid || !Array.isArray(data.grid.features) || !data.grid.features.length || !data.risk) throw new Error("The analysis returned an incomplete result.");
    riskLayer.clearLayers();
    riskLayer.addData(data.grid);
    map.fitBounds(riskLayer.getBounds(), { padding: [24, 24] });
    document.querySelector("#risk-score").textContent = data.risk.score;
    document.querySelector("#risk-level").textContent = data.risk.level;
    setRiskColor(data.risk.level);
    document.querySelector("#rainfall").textContent = `${Number(data.weather?.rainfall?.next_6h_mm || 0).toFixed(1)} mm / 6h`;
    const props = data.grid.features.find(f => f.properties.cell_id === data.risk.cell_id)?.properties || data.grid.features[0].properties;
    document.querySelector("#elevation").textContent = display(props.elevation_m, " m");
    document.querySelector("#slope").textContent = display(props.slope_deg, "°");
    document.querySelector("#built-up").textContent = percent(props.built_up_fraction);
    document.querySelector("#water-distance").textContent = display(props.water_distance_m, " m");
    document.querySelector("#land-cover").textContent = display(props.land_cover_class);
    document.querySelector("#contributors").textContent = (data.risk.top_contributors || []).join(", ").replaceAll("_", " ") || "Not enough data to rank contributors";
    const list = document.querySelector("#explanation");
    list.replaceChildren(...(data.risk.explanation || []).map(text => { const li = document.createElement("li"); li.textContent = text; return li; }));
    document.querySelector("#result-panel").hidden = false;
    setMessage(`Analysis complete · ${formatSources(data.sources)}`);
    document.querySelector("#result-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    setMessage(error.message || "Data is not available for this location.", true);
  } finally {
    setLoading(false);
  }
}

map.on("click", event => { setSelected(event.latlng.lat, event.latlng.lng); setMessage("Location selected · ready to analyze."); });
document.querySelector("#analyze-location").addEventListener("click", analyzeLocation);
document.querySelector("#my-location").addEventListener("click", () => {
  if (!navigator.geolocation) return setMessage("Geolocation is not available. Select a place on the map.", true);
  setMessage("Requesting your location permission…");
  navigator.geolocation.getCurrentPosition(position => { setSelected(position.coords.latitude, position.coords.longitude); map.setView([selected.lat, selected.lon], 10); setMessage("Your location is selected · ready to analyze."); }, () => setMessage("Location permission was not granted.", true));
});
L.control.layers({ "OpenStreetMap": baseLayer }, { "Risk grid": riskLayer }, { collapsed: true }).addTo(map);
setSelected(selected.lat, selected.lon);
