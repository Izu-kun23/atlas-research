const $ = (id) => document.getElementById(id);
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
async function api(path, options = {}) {
  const r = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!r.ok) {
    let e;
    try {
      e = await r.json();
    } catch {
      e = { detail: r.statusText };
    }
    throw Error(
      typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail),
    );
  }
  return r.json();
}
function message(text, error = false) {
  $("status").textContent = text;
  $("status").className = "status" + (error ? " error" : "");
}
async function busy(button, fn) {
  if (button) button.disabled = true;
  try {
    await fn();
  } catch (e) {
    message(e.message, true);
  } finally {
    if (button) button.disabled = false;
  }
}
function stats(items) {
  $("stats").innerHTML = items
    .map(
      ([label, value, hint]) =>
        `<div class="stat"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div><div class="hint">${esc(hint)}</div></div>`,
    )
    .join("");
}
