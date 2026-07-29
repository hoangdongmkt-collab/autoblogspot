import json

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

merged = {}
for part in ['_trans_fr_b_part1.json', '_trans_fr_b_part2.json', '_trans_fr_b_part3.json']:
    with open(f"D:/autoblogspot/{part}", "r", encoding="utf-8") as f:
        data = json.load(f)
    merged.update(data)

print(f"Total slugs after merge: {len(merged)}")
missing = [s for s in TARGET_SLUGS if s not in merged]
extra   = [s for s in merged if s not in TARGET_SLUGS]
print(f"Missing: {missing}")
print(f"Extra:   {extra}")

# Write final file
with open("D:/autoblogspot/_trans_fr_b.json", "w", encoding="utf-8") as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)
print("Written _trans_fr_b.json")

# Validate re-read
with open("D:/autoblogspot/_trans_fr_b.json", "r", encoding="utf-8") as f:
    check = json.load(f)
print(f"Validation: {len(check)} slugs present")
for s in TARGET_SLUGS:
    assert s in check, f"MISSING: {s}"
print("All 23 target slugs confirmed present ✓")
