#!/usr/bin/env python3
"""
Static builder for the Park City Ski Villa guides.

Renders every post in content.py to blog/<slug>/index.html, plus the blog
index, and rewrites the image sitemap entries for the whole site. The SEO
scaffolding (title, meta, canonical, Open Graph, BlogPosting + FAQPage +
BreadcrumbList schema, breadcrumbs, H1, related links) is generated once
here so it cannot drift between posts.

    python3 blog/_build/build.py
"""

import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from content import POSTS, SITE  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
BLOG = os.path.join(ROOT, "blog")
BASE = SITE["base"]


# ── helpers ──────────────────────────────────────────────────────────────

def e(s):
    return html.escape(s, quote=True)


def by_slug():
    return {p["slug"]: p for p in POSTS}


def img_variants(name):
    """Return (srcset, width, height, full_src) for an image stem in images/."""
    meta = SITE["images"][name]
    stem, ext, w, h, sizes = meta["stem"], meta["ext"], meta["w"], meta["h"], meta["variants"]
    parts = [f"../../images/{stem}-{s}.webp {s}w" for s in sizes]
    parts.append(f"../../images/{stem}.{ext} {w}w")
    return ", ".join(parts), w, h, f"../../images/{stem}.{ext}"


# ── body block rendering ─────────────────────────────────────────────────

def render_blocks(blocks, posts_by_slug, self_slug):
    out = []
    for b in blocks:
        kind = b[0]

        if kind == "p":
            out.append(f"    <p>{b[1]}</p>")

        elif kind == "h2":
            out.append(f'    <h2 id="{e(b[2])}">{e(b[1])}</h2>')

        elif kind == "h3":
            out.append(f"    <h3>{e(b[1])}</h3>")

        elif kind == "ul":
            items = "\n".join(f"      <li>{i}</li>" for i in b[1])
            out.append(f"    <ul>\n{items}\n    </ul>")

        elif kind == "ol":
            items = "\n".join(f"      <li>{i}</li>" for i in b[1])
            out.append(f"    <ol>\n{items}\n    </ol>")

        elif kind == "note":
            paras = "\n".join(f"      <p>{p}</p>" for p in b[2])
            out.append(
                f'    <div class="note">\n'
                f'      <div class="note-t">{e(b[1])}</div>\n{paras}\n    </div>'
            )

        elif kind == "fig":
            srcset, w, h, src = img_variants(b[1])
            out.append(
                f"    <figure>\n"
                f'      <img src="{src}" srcset="{srcset}"\n'
                f'           sizes="(max-width: 46rem) calc(100vw - 40px), 46rem"\n'
                f'           width="{w}" height="{h}" loading="{b[4]}" decoding="async"\n'
                f'           alt="{e(b[2])}">\n'
                f"      <figcaption>{e(b[3])}</figcaption>\n"
                f"    </figure>"
            )

        elif kind == "table":
            cap, head, rows = b[1], b[2], b[3]
            th = "".join(f'<th scope="col">{e(c)}</th>' for c in head)
            trs = []
            for r in rows:
                cells = f'<th scope="row">{e(r[0])}</th>' + "".join(f"<td>{e(c)}</td>" for c in r[1:])
                trs.append(f"          <tr>{cells}</tr>")
            body = "\n".join(trs)
            out.append(
                f'    <div class="tw">\n      <table>\n'
                f"        <caption>{e(cap)}</caption>\n"
                f"        <thead>\n          <tr>{th}</tr>\n        </thead>\n"
                f"        <tbody>\n{body}\n        </tbody>\n"
                f"      </table>\n    </div>"
            )

        elif kind == "related":
            # contextual in-body links to sibling guides
            lis = []
            for slug in b[1]:
                if slug == self_slug or slug not in posts_by_slug:
                    continue
                t = posts_by_slug[slug]["title"]
                lis.append(f'      <li><a href="../{slug}/">{e(t)}</a></li>')
            if lis:
                out.append(
                    f'    <div class="toc">\n      <div class="toc-t">{e(b[2])}</div>\n'
                    f"      <ul style=\"margin:0;padding-left:1.1em;\">\n"
                    + "\n".join(lis)
                    + "\n      </ul>\n    </div>"
                )

    return "\n\n".join(out)


def render_toc(blocks):
    heads = [(b[1], b[2]) for b in blocks if b[0] == "h2"]
    if len(heads) < 3:
        return ""
    lis = "\n".join(f'        <li><a href="#{e(a)}">{e(t)}</a></li>' for t, a in heads)
    return (
        '    <nav class="toc" aria-label="On this page">\n'
        '      <div class="toc-t">On this page</div>\n'
        f"      <ol>\n{lis}\n      </ol>\n    </nav>"
    )


def render_faq(faq):
    if not faq:
        return ""
    items = []
    for q, a in faq:
        items.append(
            f"    <details>\n      <summary>{e(q)}</summary>\n"
            f"      <p>{a}</p>\n    </details>"
        )
    return (
        '    <h2 id="faq">Common questions</h2>\n\n' + "\n\n".join(items)
    )


# ── schema ───────────────────────────────────────────────────────────────

def render_schema(p, url):
    graph = [
        {
            "@type": "BlogPosting",
            "@id": url + "#post",
            "headline": p["title"],
            "description": p["desc"],
            "datePublished": p["date"],
            "dateModified": p["date"],
            "inLanguage": "en-US",
            "url": url,
            "mainEntityOfPage": {"@type": "WebPage", "@id": url},
            "image": [f"{BASE}images/{SITE['images'][p['hero']]['stem']}.{SITE['images'][p['hero']]['ext']}"],
            "author": {"@type": "Organization", "name": SITE["name"], "url": BASE},
            "publisher": {"@type": "Organization", "name": SITE["name"], "url": BASE},
            "isPartOf": {"@type": "Blog", "@id": BASE + "blog/#blog", "name": SITE["blog_name"]},
            "about": [
                {"@type": "Place", "name": "Canyons Village, Park City, Utah"},
                {"@type": "SkiResort", "name": "Park City Mountain Resort"},
            ],
            "keywords": ", ".join(p["keywords"]),
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": SITE["name"], "item": BASE},
                {"@type": "ListItem", "position": 2, "name": "Guides", "item": BASE + "blog/"},
                {"@type": "ListItem", "position": 3, "name": p["title"], "item": url},
            ],
        },
    ]
    if p.get("faq"):
        graph.append({
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)},
                }
                for q, a in p["faq"]
            ],
        })
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=2, ensure_ascii=False)


# ── page templates ───────────────────────────────────────────────────────

POST_TMPL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">

<title>{title_tag}</title>
<meta name="description" content="{desc}">
<meta name="author" content="{site_name}">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<link rel="canonical" href="{url}">
<link rel="icon" type="image/svg+xml" href="../../favicon.svg">

<meta property="og:type" content="article">
<meta property="og:site_name" content="{site_name}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{hero_abs}">
<meta property="og:image:alt" content="{hero_alt}">
<meta property="article:published_time" content="{date}">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{hero_abs}">

<meta name="geo.region" content="US-UT">
<meta name="geo.placename" content="Canyons Village, Park City, Utah">
<meta name="geo.position" content="40.6844315;-111.5547043">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,400&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../blog.css">
{prev_next_links}
<script type="application/ld+json">
{schema}
</script>
</head>
<body>

<nav class="nav" aria-label="Main navigation">
  <a href="../../" class="nav-logo">Park City <span>Ski Villa</span></a>
  <div class="nav-right">
    <a href="../" class="nav-link opt">Guides</a>
    <a href="../../#gallery" class="nav-link opt">The Villa</a>
    <a href="../../#contact" class="btn btn-gold">Check Availability</a>
  </div>
</nav>

<nav class="crumbs" aria-label="Breadcrumb">
  <a href="../../">Home</a><span>/</span><a href="../">Guides</a><span>/</span>{crumb}
</nav>

<main class="wrap">

  <header class="post-head">
    <span class="eyebrow">{eyebrow}</span>
    <h1>{h1}</h1>
    <div class="post-meta">
      <span>Published {date_human}</span>
      <span>{place}</span>
      <span>{read} min read</span>
    </div>
  </header>

  <article>

    <p class="lede">{lede}</p>

{hero_fig}

{toc}

{body}

{faq}

    <section class="cta">
      <h2>The villa this guide comes from</h2>
      <p>We own a Premier Two-Bedroom Villa inside Westgate Park City Resort, in Canyons Village. It is 1,100 square feet, two king bedrooms and two queen sleeper sofas, so it sleeps eight in one unit. Full kitchen with a centre island, two bathrooms, in-unit laundry, and a short walk to the Red Pine Gondola.</p>
      <p>It is available for <strong>Presidents' Week 2027, 13 to 20 February</strong>, and we rent it ourselves rather than through an agency.</p>
      <div class="cta-row">
        <a href="../../#contact" class="btn btn-gold">Check availability</a>
        <a href="../../#gallery" class="btn btn-ghost">See the villa</a>
      </div>
    </section>

{pager}

  </article>
</main>

<footer role="contentinfo">
  <div class="f-inner">
    <p><strong style="color:rgba(253,246,236,0.86);">Park City Ski Villa</strong></p>
    <p>Premier Two-Bedroom Villa at Westgate Park City Resort &amp; Spa<br>
       3000 Canyons Resort Drive, Park City, UT 84098</p>
    <p><a href="../../">The villa</a> &nbsp;&middot;&nbsp; <a href="../">All guides</a> &nbsp;&middot;&nbsp; <a href="../../#contact">Check availability</a></p>
    <p class="f-legal">Rented directly by the owners. We are not Westgate Resorts and we are not a letting agency. Lift, fee and transfer details change between seasons, so confirm current figures with the resort before you travel.</p>
  </div>
</footer>

</body>
</html>
"""


def human_date(iso):
    import datetime as dt
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


def build_post(p, posts_by_slug, prev_p, next_p):
    url = f"{BASE}blog/{p['slug']}/"
    hero = SITE["images"][p["hero"]]
    hero_abs = f"{BASE}images/{hero['stem']}.{hero['ext']}"

    srcset, w, h, src = img_variants(p["hero"])
    hero_fig = (
        f"    <figure>\n"
        f'      <img src="{src}" srcset="{srcset}"\n'
        f'           sizes="(max-width: 46rem) calc(100vw - 40px), 46rem"\n'
        f'           width="{w}" height="{h}" loading="eager" fetchpriority="high" decoding="async"\n'
        f'           alt="{e(p["hero_alt"])}">\n'
        f"      <figcaption>{e(p['hero_cap'])}</figcaption>\n"
        f"    </figure>"
    )

    pager_bits = []
    links = []
    if prev_p:
        pager_bits.append(f'<a href="../{prev_p["slug"]}/" rel="prev">&#8592; {e(prev_p["title"])}</a>')
        links.append(f'<link rel="prev" href="{BASE}blog/{prev_p["slug"]}/">')
    if next_p:
        pager_bits.append(f'<a href="../{next_p["slug"]}/" rel="next">{e(next_p["title"])} &#8594;</a>')
        links.append(f'<link rel="next" href="{BASE}blog/{next_p["slug"]}/">')
    pager = ""
    if pager_bits:
        pager = (
            '    <nav class="toc" aria-label="More guides">\n'
            '      <div class="toc-t">Keep reading</div>\n'
            "      <ul style=\"margin:0;padding-left:1.1em;\">\n"
            + "\n".join(f"        <li>{b}</li>" for b in pager_bits)
            + "\n      </ul>\n    </nav>"
        )

    return POST_TMPL.format(
        title_tag=e(p["title_tag"]),
        desc=e(p["desc"]),
        site_name=e(SITE["name"]),
        url=url,
        og_title=e(p["title"]),
        hero_abs=hero_abs,
        hero_alt=e(p["hero_alt"]),
        date=p["date"],
        date_human=human_date(p["date"]),
        prev_next_links=("\n" + "\n".join(links) if links else ""),
        schema=render_schema(p, url),
        crumb=e(p["crumb"]),
        eyebrow=e(p["eyebrow"]),
        h1=e(p["title"]),
        place=e(p.get("place", "Park City, Utah")),
        read=p["read"],
        lede=p["lede"],
        hero_fig=hero_fig,
        toc=render_toc(p["body"]),
        body=render_blocks(p["body"], posts_by_slug, p["slug"]),
        faq=render_faq(p.get("faq")),
        pager=pager,
    )


INDEX_TMPL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>Park City Ski Guides | Canyons Village and Presidents' Week</title>
<meta name="description" content="Practical guides to skiing Park City from Canyons Village: lifts, transfers, lift tickets, costs, family logistics and booking a ski-in villa for Presidents' Week 2027.">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<link rel="canonical" href="{base}blog/">
<link rel="icon" type="image/svg+xml" href="../favicon.svg">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Park City Ski Villa">
<meta property="og:title" content="Park City Ski Guides">
<meta property="og:description" content="Practical guides to skiing Park City from Canyons Village, and booking a ski-in villa for Presidents' Week 2027.">
<meta property="og:url" content="{base}blog/">
<meta property="og:image" content="{base}images/og-preview.jpg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,400&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="blog.css">
<script type="application/ld+json">
{schema}
</script>
</head>
<body>

<nav class="nav" aria-label="Main navigation">
  <a href="../" class="nav-logo">Park City <span>Ski Villa</span></a>
  <div class="nav-right">
    <a href="../#gallery" class="nav-link opt">The Villa</a>
    <a href="../#contact" class="btn btn-gold">Check Availability</a>
  </div>
</nav>

<nav class="crumbs wide" aria-label="Breadcrumb">
  <a href="../">Home</a><span>/</span>Guides
</nav>

<main class="wrap wide">
  <header class="post-head">
    <span class="eyebrow">Park City Planning</span>
    <h1>Park City ski guides</h1>
  </header>

  <p class="lede">Everything we have learned owning and skiing out of a villa in Canyons Village. Lifts, transfers, lift tickets, what a week really costs, and how to book the February weeks that sell out first.</p>

{groups}

  <section class="cta">
    <h2>The villa behind these guides</h2>
    <p>A Premier Two-Bedroom Villa inside Westgate Park City Resort in Canyons Village. 1,100 square feet, sleeps eight, full kitchen, two bathrooms, a short walk to the Red Pine Gondola. Available for Presidents' Week 2027, 13 to 20 February.</p>
    <div class="cta-row">
      <a href="../#contact" class="btn btn-gold">Check availability</a>
      <a href="../#gallery" class="btn btn-ghost">See the villa</a>
    </div>
  </section>
</main>

<footer role="contentinfo">
  <div class="f-inner">
    <p><strong style="color:rgba(253,246,236,0.86);">Park City Ski Villa</strong></p>
    <p>Premier Two-Bedroom Villa at Westgate Park City Resort &amp; Spa<br>
       3000 Canyons Resort Drive, Park City, UT 84098</p>
    <p><a href="../">The villa</a> &nbsp;&middot;&nbsp; <a href="../#contact">Check availability</a></p>
    <p class="f-legal">Rented directly by the owners. We are not Westgate Resorts and we are not a letting agency.</p>
  </div>
</footer>

</body>
</html>
"""


def build_index(posts):
    ordered = sorted(posts, key=lambda p: (p["date"], p["slug"]), reverse=True)

    groups_html = []
    for gname in SITE["group_order"]:
        members = [p for p in ordered if p["group"] == gname]
        if not members:
            continue
        cards = []
        for p in members:
            im = SITE["images"][p["hero"]]
            # thumbnails are small on screen, so only the narrow variants are offered
            srcset = ", ".join(f"../images/{im['stem']}-{v}.webp {v}w" for v in im["variants"] if v <= 960)
            cards.append(
                f'    <a class="pcard" href="{p["slug"]}/">\n'
                f'      <div class="pcard-media">\n'
                f'        <img src="../images/{im["stem"]}-960.webp" srcset="{srcset}"\n'
                f'             sizes="(max-width: 640px) calc(100vw - 40px), (max-width: 1000px) 44vw, 30vw"\n'
                f'             width="{im["w"]}" height="{im["h"]}" loading="lazy" decoding="async"\n'
                f'             alt="{e(p["hero_alt"])}">\n'
                f'      </div>\n'
                f'      <div class="pcard-body">\n'
                f'        <h3>{e(p["title"])}</h3>\n'
                f'        <p>{e(p["desc"])}</p>\n'
                f'        <div class="pm">{human_date(p["date"])} &middot; {p["read"]} min read</div>\n'
                f'      </div>\n'
                f'    </a>'
            )
        n = len(members)
        groups_html.append(
            f'  <div class="pgroup">\n'
            f'    <h2>{e(gname)}</h2>\n'
            f'    <span class="rule"></span>\n'
            f'    <span class="pcount">{n} guide{"s" if n != 1 else ""}</span>\n'
            f'  </div>\n'
            f'  <div class="plist">\n' + "\n".join(cards) + "\n  </div>"
        )

    schema = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Blog",
                "@id": BASE + "blog/#blog",
                "name": SITE["blog_name"],
                "url": BASE + "blog/",
                "description": "Practical guides to skiing Park City from Canyons Village.",
                "publisher": {"@type": "Organization", "name": SITE["name"], "url": BASE},
                "blogPost": [
                    {
                        "@type": "BlogPosting",
                        "headline": p["title"],
                        "url": f"{BASE}blog/{p['slug']}/",
                        "datePublished": p["date"],
                        "description": p["desc"],
                        "image": f"{BASE}images/{SITE['images'][p['hero']]['stem']}.{SITE['images'][p['hero']]['ext']}",
                    }
                    for p in ordered
                ],
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": SITE["name"], "item": BASE},
                    {"@type": "ListItem", "position": 2, "name": "Guides", "item": BASE + "blog/"},
                ],
            },
        ],
    }, indent=2, ensure_ascii=False)

    return INDEX_TMPL.format(base=BASE, schema=schema, groups="\n\n".join(groups_html))


# ── sitemap ──────────────────────────────────────────────────────────────

SITEMAP_HEAD = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
"""


def build_sitemap(posts):
    newest = max(p["date"] for p in posts)
    rows = [SITEMAP_HEAD]

    imgs = "\n".join(
        f"    <image:image>\n"
        f"      <image:loc>{BASE}images/{stem}</image:loc>\n"
        f"      <image:title>{e(title)}</image:title>\n"
        f"    </image:image>"
        for stem, title in SITE["home_images"]
    )
    rows.append(
        f"  <url>\n    <loc>{BASE}</loc>\n    <lastmod>{newest}</lastmod>\n"
        f"    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n{imgs}\n  </url>"
    )
    rows.append(
        f"  <url>\n    <loc>{BASE}blog/</loc>\n    <lastmod>{newest}</lastmod>\n"
        f"    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>"
    )

    for p in sorted(posts, key=lambda x: x["date"], reverse=True):
        hero = SITE["images"][p["hero"]]
        rows.append(
            f"  <url>\n    <loc>{BASE}blog/{p['slug']}/</loc>\n"
            f"    <lastmod>{p['date']}</lastmod>\n"
            f"    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n"
            f"    <image:image>\n"
            f"      <image:loc>{BASE}images/{hero['stem']}.{hero['ext']}</image:loc>\n"
            f"      <image:title>{e(p['hero_alt'])}</image:title>\n"
            f"    </image:image>\n  </url>"
        )

    rows.append("</urlset>\n")
    return "\n".join(rows)


# ── main ─────────────────────────────────────────────────────────────────

def main():
    posts_by_slug = by_slug()
    assert len(posts_by_slug) == len(POSTS), "duplicate slug"

    chrono = sorted(POSTS, key=lambda p: (p["date"], p["slug"]))
    written = 0
    for i, p in enumerate(chrono):
        prev_p = chrono[i - 1] if i > 0 else None
        next_p = chrono[i + 1] if i < len(chrono) - 1 else None
        d = os.path.join(BLOG, p["slug"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(build_post(p, posts_by_slug, prev_p, next_p))
        written += 1

    with open(os.path.join(BLOG, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_index(POSTS))

    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(build_sitemap(POSTS))

    print(f"built {written} posts + blog index + sitemap.xml")


if __name__ == "__main__":
    main()
