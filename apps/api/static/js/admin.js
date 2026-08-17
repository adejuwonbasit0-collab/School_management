
// sidebar toggle
const sidebarToggle = document.getElementById("sidebar-toggle");
const sidebar = document.getElementById("sidebar");
if (sidebarToggle && sidebar) {
  sidebarToggle.addEventListener("click", () => sidebar.classList.toggle("-translate-x-full"));
}

// modal toggle
function toggleModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle("hidden");
}
document.addEventListener("click", e => {
  if (e.target.classList.contains("modal-overlay")) e.target.classList.add("hidden");
});

// escape closes modals
document.addEventListener("keydown", e => {
  if (e.key === "Escape") document.querySelectorAll(".modal-overlay:not(.hidden)").forEach(m => m.classList.add("hidden"));
});

// flash auto-dismiss
setTimeout(() => document.querySelectorAll(".flash-msg").forEach(el => {
  el.style.transition = "opacity 0.5s";
  el.style.opacity = "0";
  setTimeout(() => el.remove(), 500);
}), 4500);
