"""
Content Intelligence Engine — scans local models to discover content ideas,
applies brand voice settings, generates video scripts, and creates AI images.
"""
import os
import json
import time
from datetime import datetime, timedelta
import requests
from flask import current_app
from app.extensions import db
from app.ai_tools.routes import _call_ai
from app.utils.settings import get_setting

def scan_website_intelligence() -> dict:
    """Scans all site tables for projects, services, products, blog posts,
    testimonials, and trends to build a comprehensive context structure."""
    context = {}
    try:
        from app.models.content import Project, Service, BlogPost, Testimonial
        from app.models.commerce import Product
        from app.models.platform import TrendItem
        
        # 1. Projects
        projects = Project.query.order_by(Project.created_at.desc()).limit(5).all()
        context["projects"] = [{
            "title": p.title,
            "description": p.description[:200] if p.description else "",
            "category": p.category,
            "image": p.image_url,
            "gallery": p.gallery,
            "live_url": p.live_url,
            "github_url": p.github_url,
            "tags": p.tags,
            "tech_stack": p.tech_stack,
            "link": f"/projects/{p.slug}" if p.slug else ""
        } for p in projects]

        # 2. Services
        services = Service.query.limit(5).all()
        context["services"] = [{
            "title": s.title,
            "description": s.description[:200] if s.description else "",
            "price": s.price,
            "features": s.features,
            "icon": s.icon,
            "link": f"/services" # global service catalog link
        } for s in services]

        # 3. Products
        products = Product.query.limit(5).all()
        context["products"] = [{
            "title": pr.title,
            "description": pr.description[:200] if pr.description else "",
            "price": str(pr.price) if pr.price else "0",
            "sale_price": str(pr.sale_price) if pr.sale_price else "",
            "currency": pr.currency,
            "images": pr.images,
            "tags": pr.tags,
            "tech_stack": pr.tech_stack,
            "demo_url": pr.demo_url,
            "preview_url": pr.preview_url,
            "license": pr.license,
            "link": f"/products/{pr.slug}" if pr.slug else ""
        } for pr in products]

        # 4. Blogs
        blogs = BlogPost.query.order_by(BlogPost.created_at.desc()).limit(5).all()
        context["blogs"] = [{
            "title": b.title,
            "excerpt": b.excerpt[:200] if b.excerpt else "",
            "cover_image": b.cover_image,
            "tags": b.tags,
            "link": f"/blog/{b.slug}" if b.slug else ""
        } for b in blogs]

        # 5. Testimonials
        testimonials = Testimonial.query.limit(5).all()
        context["testimonials"] = [{
            "name": t.name,
            "company": t.company,
            "role": t.role,
            "avatar": t.avatar,
            "content": t.content[:200] if t.content else ""
        } for t in testimonials]

        # 6. Trends & Media Video scan
        trends = TrendItem.query.limit(5).all()
        context["trends"] = [{
            "title": tr.title,
            "query": tr.query
        } for tr in trends]

        # Scan uploaded videos in media library
        from app.models.content import MediaFile
        videos = MediaFile.query.filter(MediaFile.mime_type.like("video/%")).limit(5).all()
        context["uploaded_videos"] = [{
            "filename": v.filename,
            "mime_type": v.mime_type,
            "url": f"/static/uploads/{v.filename}"
        } for v in videos]

    except Exception as e:
        current_app.logger.warning("Failed to query models for website intelligence: %s", e)

    return context


def get_brand_voice_prompt() -> str:
    """Loads and formats the custom brand voice rules from settings."""
    tone = get_setting("brand_voice_tone") or "Professional, authoritative, engaging"
    audience = get_setting("brand_voice_audience") or "Business founders and tech leaders"
    exclude_words = get_setting("brand_voice_exclude") or "synergy, transform, revolutionize"
    guidelines = get_setting("brand_voice_guidelines") or "Keep it clear, concise, and punchy."

    return (
        f"Apply the following Brand Voice settings strictly:\n"
        f"- Tone: {tone}\n"
        f"- Target Audience: {audience}\n"
        f"- Words/Phrases to EXCLUDE: {exclude_words}\n"
        f"- Custom Writing Guidelines: {guidelines}\n"
        "Your generated copy must sound natural, match these constraints, and avoid any filler."
    )


def generate_content_ideas() -> list:
    """Uses LLM to discover content ideas based on the scanned website context."""
    site_context = scan_website_intelligence()
    brand_voice = get_brand_voice_prompt()
    
    prompt = (
        "Here is the scanned content context of our website:\n"
        f"{json.dumps(site_context, indent=2)}\n\n"
        "Generate exactly 5 highly engaging, specific content ideas (topics and formats) "
        "that we can write or publish to increase traffic. "
        "For each idea, provide:\n"
        "1. A catchy Title\n"
        "2. A summary Description/Hook\n"
        "3. Recommended Format (e.g., Blog Post, LinkedIn Update, Twitter Thread, Video Script)\n"
        "4. Why this idea fits (Targeting criteria)\n\n"
        "Return the output as a valid JSON list of objects, each containing: "
        "'title', 'description', 'format', 'reason'. Return ONLY the JSON array without backticks."
    )
    
    text, err = _call_ai(system_prompt=brand_voice, messages=[{"role": "user", "content": prompt}], max_tokens=1500)
    if err:
        return []
    
    try:
        # Strip potential markdown formatting
        cleaned_text = text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        return json.loads(cleaned_text.strip())
    except Exception:
        # Fallback list
        return [
            {
                "title": "Unlocking Value in Our Services",
                "description": "A breakdown of how custom services accelerate client growth.",
                "format": "Blog Post",
                "reason": "Scanned services list indicates strong unique selling propositions."
            }
        ]


def generate_video_script(topic: str) -> dict:
    """Generates a video script breakdown with hooks, outlines, and B-Roll cues."""
    brand_voice = get_brand_voice_prompt()
    
    prompt = (
        f"Create a complete video script for the following topic: '{topic}'\n\n"
        "Structure the response to include:\n"
        "1. Hook (First 5 seconds)\n"
        "2. Intro & Setup\n"
        "3. Body points (with visual B-Roll prompts for each point)\n"
        "4. Call to Action (Outro)\n\n"
        "Format the output as a valid JSON object containing: "
        "'hook', 'intro', 'body' (a list of objects with 'point' and 'b_roll'), 'outro'. "
        "Return ONLY the raw JSON object without backticks."
    )
    
    text, err = _call_ai(system_prompt=brand_voice, messages=[{"role": "user", "content": prompt}], max_tokens=1500)
    if err:
        return {"error": err}
        
    try:
        cleaned_text = text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        return json.loads(cleaned_text.strip())
    except Exception:
        return {"raw_text": text}


def generate_ai_image(prompt: str) -> str:
    """Generates an image via OpenAI DALL-E and saves it to static/uploads/."""
    api_key = get_setting("openai_api_key") or current_app.config.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key is not configured. Please add it to Settings first.")
        
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "response_format": "url"
    }
    
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"DALL-E generation failed: {resp.text}")
        
    data = resp.json()
    image_url = data.get("data", [{}])[0].get("url")
    if not image_url:
        raise RuntimeError("No image URL returned from DALL-E response.")
        
    # Download image locally
    img_resp = requests.get(image_url, timeout=20)
    if img_resp.status_code != 200:
        raise RuntimeError("Failed to download generated image.")
        
    # Save to uploads directory
    uploads_dir = os.path.join(current_app.root_path, "static", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    filename = f"ai_gen_{int(time.time())}.png"
    filepath = os.path.join(uploads_dir, filename)
    
    with open(filepath, "wb") as f:
        f.write(img_resp.content)
        
    return f"/static/uploads/{filename}"
