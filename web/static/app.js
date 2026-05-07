/* app.js — Manifest-driven benchmark frontend */
"use strict";

document.addEventListener("DOMContentLoaded", async () => {
  await loadManifests();
});

async function loadManifests() {
  const sel = document.getElementById("manifest-select");
  sel.innerHTML = "";
  try {
    const res = await fetch("/api/manifests");
    const data = await res.json();
    const manifests = data.manifests || [];
    if (!manifests.length) {
      const opt = document.createElement("option");
      opt.value = "benchmark/manifests/pilot_hybrid.jsonl";
      opt.textContent = "benchmark/manifests/pilot_hybrid.jsonl";
      sel.appendChild(opt);
      return;
    }
    for (const path of manifests) {
      const opt = document.createElement("option");
      opt.value = path;
      opt.textContent = path;
      sel.appendChild(opt);
    }
  } catch (e) {
    writeOutput(`Failed to load manifests: ${e.message}`);
  }
}

async function runManifest() {
  setStatus("Running", "blue");
  const form = new FormData();
  form.append("manifest", document.getElementById("manifest-select").value);
  form.append("models", document.getElementById("models-input").value || "gemma4");
  form.append("max_steps", document.getElementById("max-steps-input").value || "15");
  form.append("timeout_s", document.getElementById("timeout-input").value || "180");
  form.append("repetitions", "1");
  form.append("output", "logs/benchmark_results.jsonl");
  form.append("report_output", "logs/benchmark_report.json");
  try {
    const res = await fetch("/api/run-manifest", { method: "POST", body: form });
    const data = await res.json();
    writeOutput(JSON.stringify(data, null, 2));
    setStatus(data.ok ? "Resolved" : "Failed", data.ok ? "green" : "red");
  } catch (e) {
    writeOutput(`Run failed: ${e.message}`);
    setStatus("Failed", "red");
  }
}

async function analyzeLatest() {
  setStatus("Running", "blue");
  const form = new FormData();
  form.append("input_path", "latest");
  form.append("output", "logs/benchmark_report.json");
  try {
    const res = await fetch("/api/analyze", { method: "POST", body: form });
    const data = await res.json();
    writeOutput(JSON.stringify(data, null, 2));
    setStatus(data.ok ? "Ready" : "Failed", data.ok ? "green" : "red");
  } catch (e) {
    writeOutput(`Analyze failed: ${e.message}`);
    setStatus("Failed", "red");
  }
}

async function buildManifest() {
  setStatus("Running", "blue");
  const form = new FormData();
  form.append("historical_source", document.getElementById("historical-source").value);
  form.append("synthetic_source", document.getElementById("synthetic-source").value);
  form.append("output", document.getElementById("manifest-output").value);
  form.append("target_count", "30");
  form.append("historical_ratio", "0.7");
  form.append("synthetic_ratio", "0.3");
  form.append("seed", "13");
  try {
    const res = await fetch("/api/build-manifest", { method: "POST", body: form });
    const data = await res.json();
    writeOutput(JSON.stringify(data, null, 2));
    setStatus(data.ok ? "Ready" : "Failed", data.ok ? "green" : "red");
    await loadManifests();
  } catch (e) {
    writeOutput(`Build failed: ${e.message}`);
    setStatus("Failed", "red");
  }
}

function writeOutput(text) {
  document.getElementById("output-stream").textContent = text;
}

function setStatus(text, color) {
  const badge = document.getElementById("status-badge");
  badge.textContent = text;
  badge.className = `badge badge-${color}`;
}
