"""
Run this script once to seed the UI Components library with 10+ sample components.
Usage: python seed_components.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import UIComponent

# ── Component data ──────────────────────────────────────────────────────────

COMPONENTS = [
    {
        "name": "Hero – Animated Grid",
        "category": "Hero",
        "description": "Full-screen hero with animated background grid, glowing orbs, and scroll indicator.",
        "html_code": """<section class="relative min-h-screen flex items-center justify-center overflow-hidden bg-[#0a0a0f] w-full">
  <div class="absolute inset-0 bg-[linear-gradient(to_right,#ffffff08_1px,transparent_1px),linear-gradient(to_bottom,#ffffff08_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_50%,black,transparent)]"></div>
  <div class="relative z-10 max-w-5xl mx-auto text-center px-4">
    <div class="mb-6 inline-block">
      <div class="mx-auto h-28 w-28 rounded-full border-4 border-white/10 bg-gradient-to-br from-cyan-400 to-purple-500 shadow-2xl shadow-cyan-500/30 flex items-center justify-center text-5xl">👨‍💻</div>
    </div>
    <h1 class="text-5xl md:text-7xl font-bold text-white mb-6">Build Digital Experiences That Matter</h1>
    <p class="text-xl md:text-2xl text-gray-400 max-w-3xl mx-auto mb-8">Full-stack developer crafting pixel-perfect products with modern tech.</p>
    <div class="flex flex-wrap justify-center gap-4">
      <a href="#" class="btn-neon">Get Started</a>
      <a href="#" class="btn-ghost-neon">Learn More</a>
    </div>
  </div>
  <div class="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-gray-500 animate-bounce">
    <span class="text-xs uppercase tracking-widest">Scroll</span>
    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/></svg>
  </div>
</section>""",
        "tags": ["hero", "animated"],
        "featured": True,
        "order": 1,
    },
    {
        "name": "Navbar – Glass",
        "category": "Navbar",
        "description": "Sticky glass navbar with logo, links, and CTA button.",
        "html_code": """<nav class="sticky top-0 z-50 w-full backdrop-blur-xl bg-[#0a0a0f]/80 border-b border-white/5">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between items-center h-16">
      <a href="#" class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-purple-500 flex items-center justify-center text-black font-bold">B</div>
        <span class="text-white font-bold text-lg font-display">Brand</span>
      </a>
      <div class="hidden md:flex items-center gap-6 text-sm">
        <a href="#" class="text-gray-300 hover:text-white transition-colors">Home</a>
        <a href="#" class="text-gray-300 hover:text-white transition-colors">About</a>
        <a href="#" class="text-gray-300 hover:text-white transition-colors">Services</a>
        <a href="#" class="btn-neon text-sm py-1.5 px-4">Contact</a>
      </div>
      <button class="md:hidden text-gray-300 hover:text-white">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
      </button>
    </div>
  </div>
</nav>""",
        "tags": ["navbar", "glass"],
        "featured": False,
        "order": 2,
    },
    {
        "name": "Footer – Dark",
        "category": "Footer",
        "description": "Dark footer with logo, quick links, resources, and social icons.",
        "html_code": """<footer class="border-t border-white/5 py-12 px-4 bg-[#0a0a0f]">
  <div class="max-w-7xl mx-auto">
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
      <div>
        <div class="flex items-center gap-2 mb-4">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-purple-500 flex items-center justify-center text-black font-bold">B</div>
          <span class="text-white font-bold text-lg font-display">Brand</span>
        </div>
        <p class="text-sm text-gray-500">Build. Ship. Scale.</p>
      </div>
      <div>
        <h4 class="text-white font-semibold mb-4">Quick Links</h4>
        <ul class="space-y-2 text-sm text-gray-400">
          <li><a href="#" class="hover:text-white transition-colors">Home</a></li>
          <li><a href="#" class="hover:text-white transition-colors">About</a></li>
          <li><a href="#" class="hover:text-white transition-colors">Services</a></li>
        </ul>
      </div>
      <div>
        <h4 class="text-white font-semibold mb-4">Resources</h4>
        <ul class="space-y-2 text-sm text-gray-400">
          <li><a href="#" class="hover:text-white transition-colors">Docs</a></li>
          <li><a href="#" class="hover:text-white transition-colors">Blog</a></li>
          <li><a href="#" class="hover:text-white transition-colors">Support</a></li>
        </ul>
      </div>
      <div>
        <h4 class="text-white font-semibold mb-4">Connect</h4>
        <div class="flex gap-3">
          <a href="#" class="text-gray-400 hover:text-white transition-colors"><i data-lucide="twitter" class="w-5 h-5"></i></a>
          <a href="#" class="text-gray-400 hover:text-white transition-colors"><i data-lucide="github" class="w-5 h-5"></i></a>
          <a href="#" class="text-gray-400 hover:text-white transition-colors"><i data-lucide="linkedin" class="w-5 h-5"></i></a>
        </div>
      </div>
    </div>
    <div class="mt-10 pt-6 border-t border-white/5 text-center text-xs text-gray-600">
      © 2025 Brand. All rights reserved.
    </div>
  </div>
</footer>""",
        "tags": ["footer", "dark"],
        "featured": False,
        "order": 3,
    },
    {
        "name": "Card – Glass",
        "category": "Card",
        "description": "Glass card with icon, title, description, and a call-to-action button.",
        "html_code": """<div class="glass-card rounded-2xl p-6 max-w-sm border border-white/10 hover:border-cyan-500/30 transition-all group">
  <div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-purple-500/20 flex items-center justify-center text-3xl mb-5 group-hover:scale-110 transition-transform">🚀</div>
  <h3 class="text-lg font-bold text-white mb-2 group-hover:text-cyan-300 transition-colors">Web Development</h3>
  <p class="text-sm text-gray-400 leading-relaxed mb-5">Full-stack web apps with Flask, Django, or Next.js. Custom APIs, database design, auth systems, deployment.</p>
  <a href="#" class="text-sm text-cyan-400 hover:text-cyan-300 font-semibold">Learn More →</a>
</div>""",
        "tags": ["card", "glass"],
        "featured": False,
        "order": 4,
    },
    {
        "name": "CTA – Gradient",
        "category": "CTA",
        "description": "Bold call-to-action section with gradient border and two buttons.",
        "html_code": """<section class="py-20 px-4">
  <div class="max-w-4xl mx-auto">
    <div class="gradient-border p-1 rounded-3xl">
      <div class="glass-dark rounded-3xl p-16 text-center relative overflow-hidden">
        <div class="orb orb-cyan w-64 h-64 top-0 left-0 opacity-50"></div>
        <div class="orb orb-purple w-64 h-64 bottom-0 right-0 opacity-50"></div>
        <div class="relative z-10">
          <h2 class="text-4xl sm:text-5xl font-bold font-display gradient-text mb-4">Ready to Build Something Great?</h2>
          <p class="text-gray-400 text-lg mb-10 max-w-xl mx-auto">Let's discuss your project and bring your vision to life.</p>
          <div class="flex flex-wrap gap-4 justify-center">
            <a href="#" class="btn-neon text-base py-4 px-10">Start a Project</a>
            <a href="#" class="btn-ghost-neon text-base py-4 px-10">Learn More</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>""",
        "tags": ["cta", "gradient"],
        "featured": True,
        "order": 5,
    },
    {
        "name": "Login Form",
        "category": "Auth",
        "description": "Glass login card with email, password, remember me, and sign-in button.",
        "html_code": """<div class="w-full max-w-md glass border border-white/10 rounded-2xl p-8">
  <h2 class="text-2xl font-bold font-display gradient-text mb-6 text-center">Welcome Back</h2>
  <form class="space-y-5">
    <div>
      <label class="block text-sm font-medium text-gray-300 mb-1.5">Email</label>
      <input type="email" class="input-field w-full" placeholder="you@example.com">
    </div>
    <div>
      <label class="block text-sm font-medium text-gray-300 mb-1.5">Password</label>
      <input type="password" class="input-field w-full" placeholder="••••••••">
    </div>
    <div class="flex items-center justify-between text-sm">
      <label class="flex items-center gap-2 text-gray-400 cursor-pointer">
        <input type="checkbox" class="rounded accent-cyan-500"> Remember me
      </label>
      <a href="#" class="text-cyan-400 hover:text-cyan-300">Forgot password?</a>
    </div>
    <button type="submit" class="w-full btn-neon justify-center py-3">Sign In</button>
  </form>
  <p class="mt-6 text-center text-sm text-gray-400">No account? <a href="#" class="text-cyan-400 hover:text-cyan-300 font-medium">Create one free</a></p>
</div>""",
        "tags": ["auth", "login"],
        "featured": False,
        "order": 6,
    },
    {
        "name": "Register Form",
        "category": "Auth",
        "description": "Glass registration card with name, email, password, and role selector.",
        "html_code": """<div class="w-full max-w-md glass border border-white/10 rounded-2xl p-8">
  <h2 class="text-2xl font-bold font-display gradient-text mb-6 text-center">Create Account</h2>
  <form class="space-y-4">
    <div>
      <label class="block text-sm font-medium text-gray-300 mb-1.5">Full Name</label>
      <input type="text" class="input-field w-full" placeholder="Your name">
    </div>
    <div>
      <label class="block text-sm font-medium text-gray-300 mb-1.5">Email</label>
      <input type="email" class="input-field w-full" placeholder="you@example.com">
    </div>
    <div>
      <label class="block text-sm font-medium text-gray-300 mb-1.5">Password</label>
      <input type="password" class="input-field w-full" placeholder="Min 6 characters">
    </div>
    <div>
      <label class="block text-sm font-medium text-gray-300 mb-1.5">Account Type</label>
      <select class="input-field w-full">
        <option>User</option>
        <option>Freelancer</option>
        <option>Client</option>
      </select>
    </div>
    <button type="submit" class="w-full btn-neon justify-center py-3">Create Account</button>
  </form>
  <p class="mt-6 text-center text-sm text-gray-400">Already have an account? <a href="#" class="text-cyan-400 hover:text-cyan-300 font-medium">Sign in</a></p>
</div>""",
        "tags": ["auth", "register"],
        "featured": False,
        "order": 7,
    },
    {
        "name": "Button – Neon",
        "category": "Button",
        "description": "Multiple button variants: primary neon, ghost, and purple.",
        "html_code": """<div class="flex flex-wrap gap-4 p-4">
  <button class="btn-neon">Primary Neon</button>
  <button class="btn-ghost-neon">Ghost Neon</button>
  <button class="btn-neon btn-purple">Purple</button>
  <button class="btn-neon" disabled>Disabled</button>
</div>""",
        "tags": ["button", "neon"],
        "featured": False,
        "order": 8,
    },
    {
        "name": "Stats Row",
        "category": "Stats",
        "description": "Four stat cards showing numbers with labels and subtle hover effect.",
        "html_code": """<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-2xl mx-auto">
  <div class="glass gradient-border p-5 rounded-2xl hover:scale-105 transition-transform text-center">
    <div class="text-3xl font-bold font-display gradient-text">50+</div>
    <div class="text-[10px] text-gray-500 mt-1 uppercase tracking-widest">Projects Delivered</div>
  </div>
  <div class="glass gradient-border p-5 rounded-2xl hover:scale-105 transition-transform text-center">
    <div class="text-3xl font-bold font-display gradient-text">30+</div>
    <div class="text-[10px] text-gray-500 mt-1 uppercase tracking-widest">Happy Clients</div>
  </div>
  <div class="glass gradient-border p-5 rounded-2xl hover:scale-105 transition-transform text-center">
    <div class="text-3xl font-bold font-display gradient-text">5+</div>
    <div class="text-[10px] text-gray-500 mt-1 uppercase tracking-widest">Years Experience</div>
  </div>
  <div class="glass gradient-border p-5 rounded-2xl hover:scale-105 transition-transform text-center">
    <div class="text-3xl font-bold font-display gradient-text">15+</div>
    <div class="text-[10px] text-gray-500 mt-1 uppercase tracking-widest">Technologies</div>
  </div>
</div>""",
        "tags": ["stats", "counters"],
        "featured": False,
        "order": 9,
    },
    {
        "name": "Feature Grid",
        "category": "Features",
        "description": "2x2 grid of feature cards with icons, titles, and descriptions.",
        "html_code": """<div class="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-4xl mx-auto">
  <div class="glass-card rounded-2xl p-6 border border-white/10 hover:border-cyan-500/30 transition-all group">
    <div class="text-3xl mb-3 group-hover:scale-110 transition-transform">⚡</div>
    <h3 class="text-lg font-bold text-white mb-2 group-hover:text-cyan-300 transition-colors">Lightning Fast</h3>
    <p class="text-sm text-gray-400">Blazing fast performance with modern tools and optimised code.</p>
  </div>
  <div class="glass-card rounded-2xl p-6 border border-white/10 hover:border-cyan-500/30 transition-all group">
    <div class="text-3xl mb-3 group-hover:scale-110 transition-transform">🛡️</div>
    <h3 class="text-lg font-bold text-white mb-2 group-hover:text-cyan-300 transition-colors">Secure by Default</h3>
    <p class="text-sm text-gray-400">Built with security best practices to protect your data.</p>
  </div>
</div>""",
        "tags": ["features", "grid"],
        "featured": False,
        "order": 10,
    },
]

# ── The important part: update existing components ──

def add_or_update_component(data):
    """Add a component if it doesn't exist, or update it to ensure active=True."""
    existing = UIComponent.query.filter_by(name=data['name']).first()
    if existing:
        # Update existing component to ensure it's active and featured
        existing.active = True
        existing.featured = data.get('featured', False)
        existing.order = data.get('order', 0)
        # Optionally update other fields if needed
        print(f"🔄 Updated '{data['name']}' – active=True, featured={existing.featured}")
        return
    # Insert new
    comp = UIComponent(
        name=data['name'],
        category=data['category'],
        description=data['description'],
        html_code=data['html_code'],
        css_code="",
        js_code="",
        tags=data.get('tags', []),
        featured=data.get('featured', False),
        active=True,
        order=data.get('order', 0)
    )
    db.session.add(comp)
    print(f"➕ Added component: {data['name']}")

def main():
    app = create_app()
    with app.app_context():
        # Create table if it doesn't exist
        db.create_all()

        for comp_data in COMPONENTS:
            add_or_update_component(comp_data)

        db.session.commit()
        print("\n✅ All components are now active and visible!")
        print("Visit /tools/components to see them.")

if __name__ == "__main__":
    main()