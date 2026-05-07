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

function streamFrom(url, params) {
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
    case "reasoning":
      appendReasoningChain(data.step, data.thinking);
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
  if(stream()) { stream().appendChild(el); scrollStream(); }
}

function appendReasoningChain(step, thinking) {
  const id = `reasoning-body-${step}-${Date.now()}`;
  // Split into logical paragraphs / nodes
  const paragraphs = thinking
    .split(/\n(?:---\n|\n+)/)
    .map(p => p.trim())
    .filter(p => p.length > 0);

  const nodesHtml = paragraphs.map((p, i) => `
    <div class="reasoning-node">
      <div class="reasoning-node-dot"></div>
      ${i < paragraphs.length - 1 ? '<div class="reasoning-node-line"></div>' : ''}
      <div class="reasoning-node-text">${escHtml(p)}</div>
    </div>`).join("");

  const el = div("event event-reasoning");
  el.innerHTML = `
    <button class="reasoning-toggle" onclick="toggleReasoning('${id}', this)" aria-expanded="false">
      <span class="reasoning-icon">🧠</span>
      <span class="reasoning-label">Thinking <span class="reasoning-step-badge">Step ${step}</span></span>
      <span class="reasoning-chevron">▸</span>
    </button>
    <div class="reasoning-body" id="${id}" aria-hidden="true">
      <div class="reasoning-chain">${nodesHtml}</div>
    </div>`;
  if(stream()) { stream().appendChild(el); scrollStream(); }
}

function toggleReasoning(id, btn) {
  const body = document.getElementById(id);
  if(!body) return;
  const expanded = btn.getAttribute("aria-expanded") === "true";
  btn.setAttribute("aria-expanded", String(!expanded));
  body.setAttribute("aria-hidden", String(expanded));
  body.classList.toggle("reasoning-open", !expanded);
  btn.querySelector(".reasoning-chevron").textContent = expanded ? "▸" : "▾";
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
  if(stream()) { stream().appendChild(el); scrollStream(); }
}

function appendToolCall(step, name, args) {
  const el = div("event event-tool_call");
  el.innerHTML = `
    <div class="event-label">🔧 Tool Call — Step ${step}</div>
    <div class="tool-name">${escHtml(name)}()</div>
    <div class="tool-args">${escHtml(JSON.stringify(args, null, 2))}</div>`;
  if(stream()) { stream().appendChild(el); scrollStream(); }
}

function appendToolResult(step, name, result) {
  const el = div("event event-tool_result");
  el.innerHTML = `
    <div class="event-label">📤 ${escHtml(name)} output — Step ${step}</div>
    <div class="event-body">${escHtml(result)}</div>`;
  if(stream()) { stream().appendChild(el); scrollStream(); }
}

function appendEvent(type, html) {
  const el = div(`event event-${type}`);
  el.innerHTML = html;
  if(stream()) { stream().appendChild(el); scrollStream(); }
}

function onDone(resolved, steps) {
  const elapsed = typeof startTime !== 'undefined' && startTime ? ((Date.now() - startTime) / 1000).toFixed(1) : "?";
  if(document.getElementById("stat-steps")) document.getElementById("stat-steps").textContent = steps;
  if(document.getElementById("stat-latency")) document.getElementById("stat-latency").textContent = `${elapsed}s`;

  if (resolved) {
    const el = div("event event-done-resolved");
    el.innerHTML = `<div class="event-done-title" style="color:var(--success)">✅ Bug Resolved!</div>
      <div style="color:var(--text-dim);font-size:13px">Agent fixed the bug in ${steps} steps · ${elapsed}s</div>`;
    if(stream()) stream().appendChild(el);
    setBadge("Resolved", "green");
    if(document.getElementById("stat-status")) {
        document.getElementById("stat-status").textContent = "✅";
        document.getElementById("stat-status").style.color = "var(--success)";
    }
  } else {
    const el = div("event event-done-failed");
    el.innerHTML = `<div class="event-done-title" style="color:var(--danger)">❌ Max Steps Reached</div>
      <div style="color:var(--text-dim);font-size:13px">Agent could not resolve within ${steps} steps</div>`;
    if(stream()) stream().appendChild(el);
    setBadge("Failed", "red");
    if(document.getElementById("stat-status")) {
        document.getElementById("stat-status").textContent = "❌";
        document.getElementById("stat-status").style.color = "var(--danger)";
    }
  }

  if(stream()) scrollStream();
  onStreamDone();
}

function showDream(text) {
  if(document.getElementById("dream-content")) {
    document.getElementById("dream-content").textContent = text;
    document.getElementById("dream-panel").classList.remove("hidden");
  }
}

function onStreamDone() {
  if(typeof showTyping === 'function') showTyping(false);
  if(typeof setRunBtn === 'function') setRunBtn(true);
  if (document.getElementById("stat-status") && !document.getElementById("stat-status").textContent.includes("✅") &&
      !document.getElementById("stat-status").textContent.includes("❌")) {
    setBadge("Ready", "green");

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

// ── Shared utilities ──────────────────────────────────────────────────────
function stream() { return document.getElementById("output-stream"); }
function scrollStream() { const s = stream(); if (s) s.scrollTop = s.scrollHeight; }
function div(cls) { const el = document.createElement("div"); el.className = cls; return el; }
function escHtml(s) {
  return String(s || "")
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function setBadge(text, color) {
  const b = document.getElementById("status-badge");
  if (b) { b.textContent = text; b.className = `badge badge-${color}`; }
}
