// Light/dark theme toggle, persisted to localStorage.

const savedTheme = localStorage.getItem("ecu-theme") || "dark";
document.documentElement.setAttribute("data-theme", savedTheme);
