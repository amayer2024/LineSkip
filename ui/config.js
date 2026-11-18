// Service base URLs. Local defaults; the CD pipeline overwrites this file at deploy
// time with the Azure Container Apps URLs (A2 §1a: URLs are configuration, not hardcoded).
window.LINESKIP_CONFIG = {
  passesUrl: "http://localhost:8001",
  analyticsUrl: "http://localhost:8002",
};
