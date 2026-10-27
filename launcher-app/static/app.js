"use strict";

const LANGUAGES = { en: "English", fr: "Français", it: "Italiano", de: "Deutsch", es: "Español" };
const ALL = "\u0000all";
const $ = (id) => document.getElementById(id);

let messages = {};
let config = {};
let data = { categories: [], apps: [] };
let selected = ALL;

function t(key, vars = {}) {
  let text = messages[key] || key;
  for (const [name, value] of Object.entries(vars)) {
    text = text.replace(`{${name}}`, value);
  }
  return text;
}

function storedLanguage() {
  try { return localStorage.getItem("launcher-lang"); } catch (e) { return null; }
}

function pickLanguage() {
  const stored = storedLanguage();
  if (stored && LANGUAGES[stored]) return stored;
  for (const tag of navigator.languages || [navigator.language || "en"]) {
    const code = tag.slice(0, 2).toLowerCase();
    if (LANGUAGES[code]) return code;
  }
  return "en";
}

async function loadLanguage(code) {
  const response = await fetch(`/i18n/${code}.json`);
  messages = await response.json();
  document.documentElement.lang = code;
  for (const node of document.querySelectorAll("[data-i18n]")) {
    node.textContent = t(node.dataset.i18n);
  }
  $("search").placeholder = t("search_placeholder");
  updatePasswordToggle();
}

function updatePasswordToggle() {
  const shown = $("password").type === "text";
  const button = $("toggle-password");
  button.setAttribute("aria-pressed", String(shown));
  button.setAttribute("aria-label", t(shown ? "hide_password" : "show_password"));
  button.title = button.getAttribute("aria-label");
}

function togglePassword() {
  const input = $("password");
  input.type = input.type === "password" ? "text" : "password";
  updatePasswordToggle();
  input.focus();
}

async function api(path, options = {}) {
  const response = await fetch(path, { credentials: "same-origin", ...options });
  let body = null;
  if (response.status !== 204) {
    try { body = await response.json(); } catch (e) { body = null; }
  }
  return { status: response.status, body };
}

function element(tag, attributes = {}, children = []) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (name === "text") node.textContent = value;
    else node.setAttribute(name, value);
  }
  for (const child of children) node.append(child);
  return node;
}

function initials(name) {
  const words = name.split(/\s+/).filter(Boolean);
  return (words.length > 1 ? words[0][0] + words[1][0] : name.slice(0, 2)).toUpperCase();
}

function renderHeader() {
  $("hostname").textContent = location.hostname;
  // A custom sentence is shown as typed; only the default one is translated
  $("welcome").textContent = config.welcome || t("welcome_default");
  const user = config.user;
  $("user").hidden = !user;
  $("logout").hidden = !user;
  if (user) $("user").textContent = user.display_name || user.name;

  const support = config.support || {};
  const links = $("support-links");
  links.replaceChildren();
  if (support.email) links.append(element("a", { href: `mailto:${support.email}`, text: support.email }));
  if (support.phone) links.append(element("a", { href: `tel:${support.phone.replace(/\s+/g, "")}`, text: support.phone }));
  if (support.url && /^https?:\/\//.test(support.url)) {
    links.append(element("a", { href: support.url, class: "btn primary", target: "_blank", rel: "noopener noreferrer", text: t("support_ticket") }));
  }
  $("support").hidden = links.childElementCount === 0;
}

function categoryOf(app) {
  if (app.category && data.categories.includes(app.category)) return app.category;
  return app.external ? t("links") : t("applications");
}

function renderApps() {
  const query = $("search").value.trim().toLowerCase();
  const groups = new Map();
  for (const name of [...data.categories, t("applications"), t("links")]) groups.set(name, []);
  for (const app of data.apps) groups.get(categoryOf(app)).push(app);

  const chips = $("chips");
  chips.replaceChildren();
  const used = [...groups].filter(([, apps]) => apps.length > 0).map(([name]) => name);
  if (!used.includes(selected)) selected = ALL;
  for (const name of used.length > 1 ? [ALL, ...used] : []) {
    const chip = element("button", { type: "button", class: "chip", "aria-pressed": String(name === selected),
      text: name === ALL ? t("all") : name });
    chip.addEventListener("click", () => { selected = name; renderApps(); });
    chips.append(chip);
  }

  const container = $("groups");
  container.replaceChildren();
  let shown = 0;
  for (const [name, apps] of groups) {
    if (selected !== ALL && name !== selected) continue;
    const matching = apps
      .filter((app) => !query || app.name.toLowerCase().includes(query) || app.host.toLowerCase().includes(query))
      .sort((a, b) => a.name.localeCompare(b.name));
    if (matching.length === 0) continue;
    shown += matching.length;
    const grid = element("div", { class: "grid" });
    for (const app of matching) {
      const logo = element("span", { class: "logo", "aria-hidden": "true" });
      if (app.logo) logo.append(element("img", { src: app.logo, alt: "" }));
      else logo.textContent = initials(app.name);
      const body = element("span", { class: "card-body" }, [
        element("span", { class: "card-name", text: app.name }),
        element("span", { class: "card-host", text: app.host }),
      ]);
      const card = element("a", { class: "card", href: app.url, target: "_blank", rel: "noopener noreferrer" }, [logo, body]);
      if (app.external) card.append(element("span", { class: "badge", text: t("external") }));
      grid.append(card);
    }
    container.append(element("div", { class: "group" }, [element("h2", { text: name }), grid]));
  }

  const count = data.apps.filter((app) => !app.external).length;
  $("lead").textContent = t("lead", { count });
  $("empty").hidden = shown > 0;
  $("empty").textContent = data.apps.length === 0 ? t("no_apps") : t("no_match");
}

async function showApps() {
  const result = await api("/api/apps");
  if (result.status === 401) return showLogin();
  data = result.body || { categories: [], apps: [] };
  $("login-view").hidden = true;
  $("apps-view").hidden = false;
  renderApps();
}

function showLogin() {
  $("apps-view").hidden = true;
  $("login-view").hidden = false;
  $("lead").textContent = t("login_lead");
  $("username").focus();
}

async function login(event) {
  event.preventDefault();
  const button = event.submitter || $("login-form").querySelector("button");
  const error = $("login-error");
  error.hidden = true;
  button.disabled = true;
  const result = await api("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: $("username").value, password: $("password").value }),
  });
  button.disabled = false;
  $("password").value = "";
  // Never leave a revealed password field behind after a login attempt
  $("password").type = "password";
  updatePasswordToggle();
  if (result.status === 200) {
    config.user = result.body;
    renderHeader();
    return showApps();
  }
  error.textContent = t({ 401: "login_invalid", 429: "login_blocked" }[result.status] || "login_error");
  error.hidden = false;
}

async function logout() {
  await api("/api/logout", { method: "POST" });
  config.user = null;
  data = { categories: [], apps: [] };
  renderHeader();
  showLogin();
}

async function main() {
  const lang = pickLanguage();
  const select = $("lang");
  for (const [code, label] of Object.entries(LANGUAGES)) {
    select.append(element("option", { value: code, text: label }));
  }
  select.value = lang;
  select.addEventListener("change", async () => {
    try { localStorage.setItem("launcher-lang", select.value); } catch (e) { /* private mode */ }
    await loadLanguage(select.value);
    renderHeader();
    if (!$("apps-view").hidden) renderApps();
    else $("lead").textContent = t("login_lead");
  });
  $("search").addEventListener("input", renderApps);
  $("login-form").addEventListener("submit", login);
  $("logout").addEventListener("click", logout);
  $("toggle-password").addEventListener("click", togglePassword);

  await loadLanguage(lang);
  config = (await api("/api/config")).body || {};
  renderHeader();
  if (config.auth_mode === "ldap" && !config.user) showLogin();
  else showApps();
}

main();
