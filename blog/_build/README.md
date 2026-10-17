# Guide builder

The 28 guides under `blog/` are generated, not hand-edited. Editing a
published `blog/<slug>/index.html` directly will be overwritten on the
next build.

To change a guide, edit `content.py` and rebuild:

    python3 blog/_build/build.py

That rewrites every post, the blog index and `sitemap.xml` from a single
source, so the SEO scaffolding (titles, canonicals, schema, breadcrumbs,
interlinks) stays consistent across all of them.

`content.py` also holds the publish dates. They are presentational: search
engines take freshness from first crawl and sitemap `lastmod`, not from
the byline.
