/* app.js — Bug Squashing Agent frontend logic */
"use strict";

let currentEventSource = null;
let currentMode = "case";
let uploadedContent = null;
let totalInputTokens = 0;
let totalOutputTokens = 0;
let startTime = null;
let caseFiles = {};  // case_id -> code

// ── Boot ─────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  await loadCases();
  setupUploadZone();
});

async function loadCases() {
  try {
    const res = await fetch("/api/cases");
    const data = await res.json();
    const sel = document.getElementById("case-select");
    sel.innerHTML = "";
    for (const c of data.cases) {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      sel.appendChild(opt);
    }
    // Load first case preview
    if (data.cases.length > 0) await loadCasePreview(data.cases[0]);
    sel.addEventListener("change", e => loadCasePreview(e.target.value));
  } catch (e) {
    console.error("Failed to load cases:", e);
  }
}

async function loadCasePreview(caseId) {
  if (!caseId) return;
  try {
    const res = await fetch(`/api/case-code?case_id=${encodeURIComponent(caseId)}`);
    if (!res.ok) return;
    const data = await res.json();
    caseFiles[caseId] = data.code;
    const pre = document.getElementById("case-code");
    pre.textContent = data.code;
    document.getElementById("case-preview").classList.remove("hidden");
  } catch {
    // Endpoint may not exist; hide preview gracefully
    document.getElementById("case-preview").classList.add("hidden");
  }
}

// ── Tabs ──────────────────────────────────────────────────────────────────
function switchMode(mode) {
  currentMode = mode;
  document.getElementById("tab-case").classList.toggle("tab-active", mode === "case");
  document.getElementById("tab-upload").classList.toggle("tab-active", mode === "upload");
  document.getElementById("mode-case").classList.toggle("hidden", mode !== "case");
  document.getElementById("mode-upload").classList.toggle("hidden", mode !== "upload");
}

// ── Upload ────────────────────────────────────────────────────────────────
function setupUploadZone() {
  const zone = document.getElementById("upload-zone");
  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", e => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file) readFile(file);
  });
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) readFile(file);
}

function readFile(file) {
  const reader = new FileReader();
  reader.onload = e => {
    uploadedContent = e.target.result;
    document.getElementById("upload-hint").textContent = file.name;
    document.getElementById("upload-code").textContent = uploadedContent;
    document.getElementById("upload-preview").classList.remove("hidden");
  };
  reader.readAsText(file);
}

// ── Run ───────────────────────────────────────────────────────────────────
async function startRun() {
  if (currentEventSource) { currentEventSource.close(); currentEventSource = null; }

  const model = document.getElementById("model-select").value;
  clearOutput();
  resetStats();
  startTime = Date.now();

  setBadge("Running", "blue");
  setRunBtn(false);
  showTyping(true);

  if (currentMode === "case") {
    const caseId = document.getElementById("case-select").value;
    if (!caseId) return alert("Please select a case.");
    streamFrom("/api/run", { case_id: caseId, model });
  } else {
    if (!uploadedContent) return alert("Please upload a .py file.");
    const form = new FormData();
    form.append("model", model);
    form.append("file", new Blob([uploadedContent], { type: "text/x-python" }), "buggy.py");
    streamFromUpload("/api/upload", form);
  }
}

function streamFrom(url, params) {
  // POST with form body, get SSE back via EventSource-compatible fetch
  const form = new FormData();
  for (const [k, v] of Object.entries(params)) form.append(k, v);
  fetchSSE(url, form);
}

function streamFromUpload(url, form) {
  fetchSSE(url, form);
}

function fetchSSE(url, form) {
  fetch(url, { method: "POST", body: form })
    .then(res => {
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      function pump() {
        reader.read().then(({ done, value }) => {
          if (done) { onStreamDone(); return; }
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop();
          for (const part of parts) {
            const eventMatch = part.match(/^event: (.+)/m);
            const dataMatch = part.match(/^data: (.+)/m);
            if (eventMatch && dataMatch) {
              try { handleSSEEvent(eventMatch[1], JSON.parse(dataMatch[1])); }
              catch { /* ignore parse errors */ }
            }
          }
          pump();
        });
      }
      pump();
    })
    .catch(e => {
      appendEvent("error", `Fetch error: ${e.message}`);
      onStreamDone();
    });
}

function handleSSEEvent(type, data) {
  switch (type) {
    case "started":
      appendEvent("info", `🚀 Agent started — Model: <strong>${escHtml(data.model)}</strong> | Case: ${escHtml(data.case_id)}`);
      break;
    case "step_start":
      appendStepStart(data.step, data.max_steps);
      break;
    case "agent_text":
      totalInputTokens += data.input_tokens || 0;
      totalOutputTokens += data.output_tokens || 0;
      updateStats();
      appendAgentText(data.step, data.text, data.input_tokens, data.output_tokens, data.latency_ms);
      break;
    case "tool_call":
      appendToolCall(data.step, data.name, data.args);
      break;
    case "tool_result":
      appendToolResult(data.step, data.name, data.result);
      break;
    case "dream":
      showDream(data.text);
      break;
    case "done":
      onDone(data.resolved, data.steps);
      break;
    case "error":
      appendEvent("error", `⚠️ ${escHtml(data.message)}`);
      break;
  }
}

// ── DOM helpers ───────────────────────────────────────────────────────────
function appendStepStart(step, max) {
  const el = div("event event-step_start");
  el.textContent = `Step ${step} / ${max}`;
  stream().appendChild(el);
  scrollStream();
}

function appendAgentText(step, text, inputTok, outputTok, latency) {
  const el = div("event event-agent_text");
  el.innerHTML = `
    <div class="event-label">🤖 Agent — Step ${step}
      <span style="font-weight:400;color:var(--text-muted);margin-left:10px;">
        ↑${inputTok} ↓${outputTok} tok · ${(latency/1000).toFixed(1)}s
      </span>
    </div>
    <div class="event-body">${escHtml(text)}</div>`;
  stream().appendChild(el);
  scrollStream();
}

function appendToolCall(step, name, args) {
  const el = div("event event-tool_call");
  el.innerHTML = `
    <div class="event-label">🔧 Tool Call — Step ${step}</div>
    <div class="tool-name">${escHtml(name)}()</div>
    <div class="tool-args">${escHtml(JSON.stringify(args, null, 2))}</div>`;
  stream().appendChild(el);
  scrollStream();
}

function appendToolResult(step, name, result) {
  const el = div("event event-tool_result");
  el.innerHTML = `
    <div class="event-label">📤 ${escHtml(name)} output — Step ${step}</div>
    <div class="event-body">${escHtml(result)}</div>`;
  stream().appendChild(el);
  scrollStream();
}

function appendEvent(type, html) {
  const el = div(`event event-${type}`);
  el.innerHTML = html;
  stream().appendChild(el);
  scrollStream();
}

function onDone(resolved, steps) {
  const elapsed = startTime ? ((Date.now() - startTime) / 1000).toFixed(1) : "?";
  document.getElementById("stat-steps").textContent = steps;
  document.getElementById("stat-latency").textContent = `${elapsed}s`;

  if (resolved) {
    const el = div("event event-done-resolved");
    el.innerHTML = `<div class="event-done-title" style="color:var(--success)">✅ Bug Resolved!</div>
      <div style="color:var(--text-dim);font-size:13px">Agent fixed the bug in ${steps} steps · ${elapsed}s</div>`;
    stream().appendChild(el);
    setBadge("Resolved", "green");
    document.getElementById("stat-status").textContent = "✅";
    document.getElementById("stat-status").style.color = "var(--success)";
  } else {
    const el = div("event event-done-failed");
    el.innerHTML = `<div class="event-done-title" style="color:var(--danger)">❌ Max Steps Reached</div>
      <div style="color:var(--text-dim);font-size:13px">Agent could not resolve within ${steps} steps</div>`;
    stream().appendChild(el);
    setBadge("Failed", "red");
    document.getElementById("stat-status").textContent = "❌";
    document.getElementById("stat-status").style.color = "var(--danger)";
  }

  scrollStream();
  onStreamDone();
}

function showDream(text) {
  document.getElementById("dream-content").textContent = text;
  document.getElementById("dream-panel").classList.remove("hidden");
}

function onStreamDone() {
  showTyping(false);
  setRunBtn(true);
  if (!document.getElementById("stat-status").textContent.includes("✅") &&
      !document.getElementById("stat-status").textContent.includes("❌")) {
    setBadge("Ready", "green");
  }
}

// ── Stats ─────────────────────────────────────────────────────────────────
function updateStats() {
  document.getElementById("stat-tokens").textContent =
    `${(totalInputTokens + totalOutputTokens).toLocaleString()}`;
  if (startTime) {
    document.getElementById("stat-latency").textContent =
      `${((Date.now() - startTime)/1000).toFixed(1)}s`;
  }
}

function resetStats() {
  totalInputTokens = 0;
  totalOutputTokens = 0;
  ["stat-steps","stat-tokens","stat-latency","stat-status"].forEach(id => {
    document.getElementById(id).textContent = "—";
    document.getElementById(id).style.color = "";
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────
function stream() { return document.getElementById("output-stream"); }
function scrollStream() { const s = stream(); s.scrollTop = s.scrollHeight; }
function div(cls) { const el = document.createElement("div"); el.className = cls; return el; }
function escHtml(s) {
  return String(s || "")
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function clearOutput() {
  stream().innerHTML = `<div class="empty-state">
    <div class="empty-icon">🤖</div>
    <div class="empty-title">Agent Idle</div>
    <div class="empty-sub">Select a case and model, then click <strong>Run Agent</strong>.</div>
  </div>`;
  document.getElementById("dream-panel").classList.add("hidden");
  document.getElementById("dream-content").textContent = "";
  setBadge("Ready", "green");
  resetStats();
}

function setRunBtn(enabled) {
  const btn = document.getElementById("run-btn");
  btn.disabled = !enabled;
  btn.innerHTML = enabled ? '<span class="btn-icon">▶</span> Run Agent'
                          : '<span class="btn-icon">⏳</span> Running…';
}

function showTyping(show) {
  document.getElementById("typing-indicator").classList.toggle("hidden", !show);
}

function setBadge(text, color) {
  const b = document.getElementById("status-badge");
  b.textContent = text;
  b.className = `badge badge-${color}`;
}
