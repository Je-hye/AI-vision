const statusBadge = document.getElementById("statusBadge");
const health = document.getElementById("health");
const latestFrame = document.getElementById("latestFrame");
const overlay = document.getElementById("overlay");
const emptyFrame = document.getElementById("emptyFrame");
const metrics = document.getElementById("metrics");
const detectionsList = document.getElementById("detections");
const eventsBody = document.getElementById("eventsBody");

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  return response.json();
}

async function loadHealth() {
  const result = await api("/health");
  health.textContent = result.roboflow_configured
    ? `Roboflow configured: ${result.model_id}`
    : `Roboflow API key missing. Set ROBOFLOW_API_KEY in .env`;
}

async function start() {
  const targetClasses = document
    .getElementById("targetClasses")
    .value.split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  await api("/streams/start", {
    method: "POST",
    body: JSON.stringify({
      stream_url: document.getElementById("streamUrl").value,
      confidence_threshold: Number(document.getElementById("confidence").value),
      frame_sample_fps: Number(document.getElementById("fps").value),
      consecutive_frames: Number(document.getElementById("consecutive").value),
      cooldown_seconds: Number(document.getElementById("cooldown").value),
      target_classes: targetClasses,
    }),
  });
  await refresh();
}

async function stop() {
  await api("/streams/stop", { method: "POST" });
  await refresh();
}

async function refresh() {
  const [status, events] = await Promise.all([api("/streams/status"), api("/events")]);
  renderStatus(status);
  renderEvents(events);
}

function renderStatus(status) {
  statusBadge.textContent = status.status;
  statusBadge.style.background = status.status === "error" ? "#ffd8d3" : "#dfe7eb";
  metrics.innerHTML = `
    <div>Frames: ${status.frame_count}</div>
    <div>Analyzed: ${status.analyzed_count}</div>
    <div>Last error: ${status.last_error || "none"}</div>
  `;
  detectionsList.innerHTML = "";
  status.last_detections.forEach((detection) => {
    const item = document.createElement("li");
    item.textContent = `${detection.class_name} (${Math.round(detection.confidence * 100)}%)`;
    detectionsList.appendChild(item);
  });
  if (status.latest_frame_url) {
    emptyFrame.style.display = "none";
    latestFrame.src = status.latest_frame_url;
    latestFrame.onload = () => drawOverlay(status.last_detections);
  } else {
    emptyFrame.style.display = "grid";
    drawOverlay([]);
  }
}

function drawOverlay(detections) {
  const rect = overlay.getBoundingClientRect();
  overlay.width = rect.width;
  overlay.height = rect.height;
  const ctx = overlay.getContext("2d");
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  ctx.strokeStyle = "#f4c430";
  ctx.fillStyle = "#f4c430";
  ctx.lineWidth = 2;
  ctx.font = "14px system-ui";
  const imageWidth = latestFrame.naturalWidth;
  const imageHeight = latestFrame.naturalHeight;
  if (!imageWidth || !imageHeight) {
    return;
  }
  const scale = Math.min(overlay.width / imageWidth, overlay.height / imageHeight);
  const renderedWidth = imageWidth * scale;
  const renderedHeight = imageHeight * scale;
  const offsetX = (overlay.width - renderedWidth) / 2;
  const offsetY = (overlay.height - renderedHeight) / 2;
  detections.forEach((detection) => {
    const box = detection.bbox;
    const x = offsetX + (box.x - box.width / 2) * scale;
    const y = offsetY + (box.y - box.height / 2) * scale;
    const width = box.width * scale;
    const height = box.height * scale;
    ctx.strokeRect(x, y, width, height);
    ctx.fillText(detection.class_name, x + 4, Math.max(16, y - 6));
  });
}

function renderEvents(events) {
  eventsBody.innerHTML = "";
  events.forEach((event) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${new Date(event.timestamp).toLocaleString()}</td>
      <td>${event.gesture}</td>
      <td>${Math.round(event.confidence * 100)}%</td>
      <td>${event.source}</td>
    `;
    eventsBody.appendChild(row);
  });
}

document.getElementById("startBtn").addEventListener("click", () => start().catch(alert));
document.getElementById("stopBtn").addEventListener("click", () => stop().catch(alert));

loadHealth().catch((error) => {
  health.textContent = error.message;
});
refresh().catch(() => {});
setInterval(() => refresh().catch(() => {}), 500);
