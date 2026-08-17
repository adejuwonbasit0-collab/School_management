
// ── navbar scroll ──
const navbar = document.getElementById("navbar");
if (navbar) {
  const tick = () => navbar.classList.toggle("scrolled", window.scrollY > 30);
  window.addEventListener("scroll", tick, { passive: true });
  tick();
}

// ── mobile menu ──
const mobileBtn = document.getElementById("mobile-menu-btn");
const mobileMenu = document.getElementById("mobile-menu");
if (mobileBtn && mobileMenu) {
  mobileBtn.addEventListener("click", () => mobileMenu.classList.toggle("hidden"));
  document.addEventListener("click", e => {
    if (!mobileBtn.contains(e.target) && !mobileMenu.contains(e.target))
      mobileMenu.classList.add("hidden");
  });
}

// ── flash auto-dismiss ──
setTimeout(() => document.querySelectorAll(".flash-msg").forEach(el => {
  el.style.transition = "opacity 0.5s, transform 0.5s";
  el.style.opacity = "0"; el.style.transform = "translateX(16px)";
  setTimeout(() => el.remove(), 500);
}), 4500);

// ── toast utility ──
function showToast(msg, type = "info") {
  const colors = {
    success: "border-green-500/30 text-green-400 bg-green-500/8",
    error:   "border-red-500/30 text-red-400 bg-red-500/8",
    warning: "border-yellow-500/30 text-yellow-400 bg-yellow-500/8",
    info:    "border-cyan-500/30 text-cyan-400 bg-cyan-500/8",
  };
  const icons = { success:"✓", error:"✕", warning:"⚠", info:"ℹ" };
  const toast = document.createElement("div");
  toast.className = `flash-msg glass border rounded-xl px-4 py-3 text-sm font-medium flex items-center gap-2 ${colors[type]||colors.info}`;
  toast.style.cssText = "animation:slide-in 0.3s ease;max-width:22rem;pointer-events:auto;";
  toast.innerHTML = `<span class="flex-shrink-0">${icons[type]||"ℹ"}</span><span class="flex-1">${msg}</span><button onclick="this.parentElement.remove()" style="opacity:0.5;margin-left:auto" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.5">✕</button>`;
  let container = document.getElementById("flash-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "flash-container";
    container.style.cssText = "position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;display:flex;flex-direction:column;gap:0.5rem;";
    document.body.appendChild(container);
  }
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = "opacity 0.4s, transform 0.4s";
    toast.style.opacity = "0"; toast.style.transform = "translateX(16px)";
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}

// ── modal helpers ──
function toggleModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle("hidden");
}
document.addEventListener("click", e => {
  if (e.target.classList.contains("modal-overlay")) e.target.classList.add("hidden");
});

// ── scroll reveal ──
(function () {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      e.target.style.opacity = "1";
      e.target.style.transform = "translateY(0)";
      obs.unobserve(e.target);
    });
  }, { threshold: 0.08 });
  document.querySelectorAll(".reveal").forEach(el => {
    el.style.opacity = "0";
    el.style.transform = "translateY(28px)";
    el.style.transition = "opacity 0.65s ease, transform 0.65s ease";
    obs.observe(el);
  });
})();

// ── active nav link ──
const currentPath = window.location.pathname;
document.querySelectorAll(".nav-link").forEach(a => {
  if (a.getAttribute("href") === currentPath) a.classList.add("active");
});

// ── scroll-aware glass navbar ──
(function() {
  const nav = document.getElementById("navbar");
  if (!nav) return;
  function onScroll() {
    if (window.scrollY > 12) nav.classList.add("nav-scrolled");
    else nav.classList.remove("nav-scrolled");
  }
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });
})();

// ── magnetic button hover (subtle pull toward cursor) ──
(function() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  if (window.matchMedia("(hover: none)").matches) return; // skip on touch devices
  document.querySelectorAll(".btn-neon, .btn-ghost-neon").forEach(btn => {
    btn.classList.add("btn-magnetic");
    btn.addEventListener("mousemove", (e) => {
      const r = btn.getBoundingClientRect();
      const x = (e.clientX - r.left - r.width / 2) * 0.18;
      const y = (e.clientY - r.top - r.height / 2) * 0.18;
      btn.style.transform = `translate(${x}px, ${y}px)`;
    });
    btn.addEventListener("mouseleave", () => { btn.style.transform = ""; });
  });
})();
