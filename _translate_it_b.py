#!/usr/bin/env python
"""Translate articles 23-45 content from Vietnamese HTML to Italian."""

import json
import sys
import os

sys.path.insert(0, r'D:\autoblogspot')
from app.blog_data import ARTICLES
import anthropic

ARTICLES_BY_SLUG = {a['slug']: a for a in ARTICLES}

TARGET_SLUGS = [
    'autoblogspot-vs-viet-bai-thu-cong-chi-phi',
    'free-vs-paid-ai-model-auto-blog',
    'sitemap-xml-auto-blog-toi-uu',
    'huong-dan-su-dung-autoblogspot-dang-bai-tu-dong',
    'wordpress-vs-blogspot-so-sanh-toan-dien-2025',
    'kiem-tien-voi-affiliate-marketing-va-auto-blog',
    'content-marketing-tu-dong-scale-traffic-0-10000',
    'google-helpful-content-update-ai-khong-bi-phat',
    'toi-uu-blogspot-cho-seo-len-top-google-2025',
    'hashnode-vs-wordpress-nen-tang-nao-cho-developer-blog',
    'cong-cu-viet-bai-ai-mien-phi-tot-nhat-2025',
    'internal-linking-chien-luoc-backlink-noi-bo-blog-network',
    'tumblr-seo-cach-tang-traffic-tu-tumblr-2025',
    'ai-model-tot-nhat-de-viet-content-seo-claude-gpt-gemini',
    'cach-kiem-tien-tu-blog-google-adsense-2025',
    'schema-markup-la-gi-va-cach-them-vao-blog',
    'content-pillar-la-gi-xay-dung-he-thong-pillar-content',
    'e-e-a-t-la-gi-toi-uu-bai-viet-theo-tieu-chi-google',
    'long-tail-keyword-la-gi-nghien-cuu-tu-khoa-duoi-dai',
    'cach-tang-toc-do-index-google-indexnow-search-console',
    'cach-xay-dung-blog-network-tang-authority',
    'groq-openrouter-api-free-de-viet-blog-tu-dong',
    'autoblogspot-vs-rankiq-vs-koala-ai-so-sanh-cong-cu',
]

SYSTEM_PROMPT = """You are a professional translator specializing in Italian (italiano).
Translate the Vietnamese text content in the provided HTML to fluent Italian.
Rules:
1. Keep ALL HTML tags exactly as they are (do not modify, add, or remove any tags or attributes)
2. Only translate the visible text nodes (text between tags)
3. Keep technical terms, brand names (AutoBlogspot, Google, WordPress, etc.), URLs, code snippets, and numbers unchanged
4. The translation must be fluent, natural Italian — not word-for-word
5. Return ONLY the translated HTML, no explanations, no markdown fences
"""

def translate_html(client, slug, html_content):
    print(f"  Translating {slug}...", flush=True)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Translate this Vietnamese HTML to Italian. Return only the translated HTML:\n\n{html_content}"
            }
        ]
    )
    return response.content[0].text

def main():
    # Load .env.production if exists
    env_file = r'D:\autoblogspot\.env.production'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())

    client = anthropic.Anthropic()

    # Load existing translations if any
    output_path = r'D:\autoblogspot\_trans_it_b.json'
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        print(f"Loaded {len(translations)} existing translations")
    else:
        translations = {}

    total = len(TARGET_SLUGS)
    for i, slug in enumerate(TARGET_SLUGS, 1):
        if slug in translations:
            print(f"  [{i}/{total}] {slug} — already done, skipping")
            continue

        article = ARTICLES_BY_SLUG[slug]
        html_content = article['content']

        print(f"[{i}/{total}]", flush=True)
        translated = translate_html(client, slug, html_content)
        translations[slug] = translated

        # Save incrementally after each article
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(translations, f, ensure_ascii=False, indent=2)
        print(f"  -> Saved ({len(translations)}/{total})", flush=True)

    print(f"\nDone! {len(translations)} articles translated to {output_path}")

if __name__ == '__main__':
    main()
