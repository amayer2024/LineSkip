// Shared client helpers. Base URLs come from config.js (loaded before this file).
const CONFIG = window.LINESKIP_CONFIG || {
  passesUrl: "http://localhost:8001",
  analyticsUrl: "http://localhost:8002",
};
const PASSES = CONFIG.passesUrl;
const ANALYTICS = CONFIG.analyticsUrl;

// The browser stores the Bearer token from /auth/login (same token API any client uses).
const Auth = {
  get: () => localStorage.getItem("ls_token"),
  set: (t) => localStorage.setItem("ls_token", t),
  clear: () => localStorage.removeItem("ls_token"),
};

// authFetch attaches the Bearer token and JSON content type.
function authFetch(url, options = {}) {
  const headers = Object.assign({ "Content-Type": "application/json" }, options.headers);
  const token = Auth.get();
  if (token) headers["Authorization"] = "Bearer " + token;
  return fetch(url, Object.assign({}, options, { headers }));
}

function euros(cents) { return "€" + (cents / 100).toFixed(2); }

// Show/hide nav links depending on whether a token is stored.
function refreshNav() {
  const loggedIn = !!Auth.get();
  document.querySelectorAll("[data-auth-only]").forEach((el) => (el.style.display = loggedIn ? "" : "none"));
  document.querySelectorAll("[data-guest-only]").forEach((el) => (el.style.display = loggedIn ? "none" : ""));
}

document.addEventListener("DOMContentLoaded", () => {
  const logout = document.getElementById("logout-link");
  if (logout) logout.addEventListener("click", (e) => {
    e.preventDefault();
    Auth.clear();
    window.location.href = "index.html";
  });
  refreshNav();
});
