#!/usr/bin/env python3
"""Helper for the studio website. Python 3 standard library only (+ `cwebp` or Pillow for images).

The website itself is plain static HTML - this script only saves copy/paste work.
It never writes outside the website folder; app folders are only READ.

  import  Create apps/<slug>/ from an app project that has the usual store/ layout:
            <app>/store/play-icon-512.png              icon
            <app>/store/feature-graphic-1024x500.png   feature graphic (optional)
            <app>/store/screenshots/*.png              screenshots (top level only)
            <app>/store/privacy-policy.html            privacy policy (body copied unchanged)
            <app>/store/listings/en-US.txt             TITLE / SHORT / FULL DESCRIPTION (optional)
            <app>/app/build.gradle(.kts)               applicationId
          python3 _tools/sitetool.py import ../OrbitHop
          python3 _tools/sitetool.py import ../OrbitHop --slug orbit-hop --short "One tap. Infinite space."

  new     Create an empty app page from _template (fill in the TODOs by hand):
          python3 _tools/sitetool.py new --name "My Game" --package com.example.mygame

  fill    Replace placeholders in every published page:
          python3 _tools/sitetool.py fill --studio "Sunny Paw Games" --email hello@example.com
          python3 _tools/sitetool.py fill --app pawzzle-pals --date "1 December 2025"

  sync-policy  Re-copy an app's privacy policy text after you changed it in the app project
          (only the policy text between the POLICY markers is replaced):
          python3 _tools/sitetool.py sync-policy ../PawzzlePals --slug pawzzle-pals

  page    Create a non-app page at /<slug>/ (About, FAQ, Press...) and add it to the menu:
          python3 _tools/sitetool.py page --slug faq --title "Questions and answers" --nav "FAQ"

  nav     Copy the shared header/menu and footer (_template/header.html, footer.html)
          into every page. Run it after editing either file:
          python3 _tools/sitetool.py nav

  check   List anything still unfinished ([EMAIL], TODO, ...) before you publish:
          python3 _tools/sitetool.py check
"""
import argparse
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
TEMPLATE = SITE / "_template"
HOME = SITE / "index.html"
HEADER = TEMPLATE / "header.html"
# Shared blocks copied into every page between <!-- NAME:START --> and <!-- NAME:END -->
PARTIALS = {"HEADER": TEMPLATE / "header.html", "FOOTER": TEMPLATE / "footer.html"}
SHOT_WIDTH = 540            # screenshots are shown at 200 px wide; 540 keeps them sharp on hi-dpi
PLACEHOLDERS = ["[YOUR NAME / STUDIO]", "[EMAIL]", "[DATE]", "TODO"]


# ---------- small helpers ----------

def die(msg):
    sys.exit(f"error: {msg}")


def inside_site(p: Path) -> Path:
    p = p.resolve()
    if SITE not in p.parents and p != SITE:
        die(f"refusing to write outside the website folder: {p}")
    return p


def write(p: Path, text: str):
    p = inside_site(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "app"


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def fill_tokens(text: str, values: dict) -> str:
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def to_webp(src: Path, dst: Path, width=None, height=None, quality=82):
    dst = inside_site(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("cwebp"):
        cmd = ["cwebp", "-quiet", "-q", str(quality)]
        if width:
            cmd += ["-resize", str(width), str(height or 0)]
        subprocess.run(cmd + [str(src), "-o", str(dst)], check=True)
        return
    try:
        from PIL import Image
    except ImportError:
        die("need `cwebp` (brew install webp) or Pillow (pip install pillow) to convert images")
    im = Image.open(src)
    if width:
        h = height or round(im.height * width / im.width)
        im = im.resize((width, h), Image.LANCZOS)
    im.save(dst, "WEBP", quality=quality)


def image_size(p: Path):
    """Return (w, h) of a PNG or WebP without third-party libraries."""
    b = p.read_bytes()[:64]
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        kind = b[12:16]
        if kind == b"VP8 ":
            return int.from_bytes(b[26:28], "little") & 0x3FFF, int.from_bytes(b[28:30], "little") & 0x3FFF
        if kind == b"VP8L":
            bits = int.from_bytes(b[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if kind == b"VP8X":
            return int.from_bytes(b[24:27], "little") + 1, int.from_bytes(b[27:30], "little") + 1
    return None


# ---------- reading an app project (read-only) ----------

def read_listing(store: Path) -> dict:
    f = store / "listings" / "en-US.txt"
    out = {}
    if not f.exists():
        return out
    section = None
    buf = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(TITLE|SHORT DESCRIPTION|FULL DESCRIPTION)\b.*:\s*$", line.strip())
        if m:
            section = m.group(1)
            buf[section] = []
            continue
        if section:
            buf[section].append(line)
    for k, v in buf.items():
        out[k] = "\n".join(v).strip()
    return out


def read_package(app_dir: Path):
    for name in ("app/build.gradle.kts", "app/build.gradle"):
        f = app_dir / name
        if f.exists():
            m = re.search(r'applicationId\s*=?\s*"([^"]+)"', f.read_text(encoding="utf-8"))
            if m:
                return m.group(1)
    return None


def read_policy(store: Path):
    f = store / "privacy-policy.html"
    if not f.exists():
        return None, None
    t = f.read_text(encoding="utf-8")
    body = re.search(r"<body[^>]*>(.*)</body>", t, re.S | re.I)
    title = re.search(r"<title>(.*?)</title>", t, re.S | re.I)
    name = None
    if title:
        name = re.split(r"\s+[–-]\s+Privacy", html.unescape(title.group(1)).strip())[0].strip()
    return (body.group(1).strip("\n") if body else None), name


def description_html(text: str) -> str:
    """Plain store text -> HTML. Blank lines split blocks; a block whose lines all
    start with a symbol/emoji (or • - * ★) becomes a list, anything else a paragraph."""
    parts = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        if len(lines) > 1 and all(not l[0].isalnum() for l in lines):
            items = [re.sub(r"^[•*\-★]\s*", "", l) for l in lines]
            parts.append("    <ul>\n" + "\n".join(f"      <li>{esc(i)}</li>" for i in items) + "\n    </ul>")
        else:
            parts.append(f"    <p>{esc(' '.join(lines))}</p>")
    return "\n".join(parts)


def alt_from_filename(app_name: str, stem: str, n: int) -> str:
    words = re.sub(r"^\d+[-_ ]*", "", stem).replace("-", " ").replace("_", " ").strip()
    return f"{app_name} screenshot {n}" + (f": {words}" if words else "")


# ---------- writing pages ----------

def page_url(p: Path) -> str:
    rel = p.relative_to(SITE).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def sync_headers() -> int:
    """Copy the shared partials (_template/header.html, _template/footer.html) between the
    matching markers of every published page. The menu link of the current page gets
    aria-current="page"."""
    partials = {k: f.read_text(encoding="utf-8").strip("\n") for k, f in PARTIALS.items() if f.exists()}
    changed = 0
    for p in published_html():
        t = n = p.read_text(encoding="utf-8")
        url = page_url(p)
        for name, block in partials.items():
            if f"<!-- {name}:START -->" not in n:
                continue
            if name == "HEADER":
                block = re.sub(r"(<nav[^>]*>.*?</nav>)",
                               lambda m: m.group(1).replace(f'<a href="{url}">', f'<a href="{url}" aria-current="page">'),
                               block, flags=re.S)
            n = re.sub(rf"(<!-- {name}:START -->).*?(<!-- {name}:END -->)",
                       lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), n, flags=re.S)
        if n != t:
            write(p, n)
            changed += 1
    return changed


def update_home_card(values: dict):
    card = fill_tokens((TEMPLATE / "card.html").read_text(encoding="utf-8"), values)
    home = HOME.read_text(encoding="utf-8")
    slug = re.escape(values["SLUG"])
    home = re.sub(rf"[ \t]*<!-- app:{slug} -->.*?<!-- /app:{slug} -->\n", "", home, flags=re.S)
    marker = "    <!-- APPS:END -->"
    if marker not in home:
        die("could not find '<!-- APPS:END -->' in index.html")
    write(HOME, home.replace(marker, card + marker))


def write_app(values: dict, dest: Path, policy_body: str, has_feature: bool):
    page = fill_tokens((TEMPLATE / "app" / "index.html").read_text(encoding="utf-8"), values)
    if not has_feature:
        page = re.sub(r"\s*<!-- FEATURE:START -->.*?<!-- FEATURE:END -->", "", page, flags=re.S)
    write(dest / "index.html", page)
    pol = (TEMPLATE / "app" / "privacy-policy.html").read_text(encoding="utf-8")
    write(dest / "privacy-policy.html", fill_tokens(pol, {"NAME": values["NAME"]}).replace("{{POLICY}}", policy_body))
    update_home_card(values)
    sync_headers()


def default_facts(package: str, has_ads: bool) -> str:
    facts = [("Platform", "Android phones and tablets"), ("Google Play ID", package)]
    if has_ads:
        facts.append(("Ads", "Child-safe, non-personalised ads (Google AdMob)"))
    return "\n".join(f"    <dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in facts)


def cmd_import(a):
    app_dir = Path(a.app_dir).expanduser().resolve()
    store = app_dir / "store"
    if not store.is_dir():
        die(f"{store} not found")
    if SITE == app_dir or SITE in app_dir.parents:
        die("the app folder must be outside the website folder")

    listing = read_listing(store)
    policy_body, policy_name = read_policy(store)
    name = a.name or policy_name or listing.get("TITLE", "").split(":")[0].strip() or app_dir.name
    package = a.package or read_package(app_dir) or die("applicationId not found; pass --package")
    slug = a.slug or slugify(name)
    short = a.short or listing.get("SHORT DESCRIPTION") or "TODO: one-sentence description"
    full = listing.get("FULL DESCRIPTION") or "TODO: describe the game."

    dest = SITE / "apps" / slug
    if dest.exists() and not a.force:
        die(f"apps/{slug} already exists (use --force to overwrite; your hand edits there will be lost)")

    icon = store / "play-icon-512.png"
    if not icon.exists():
        die(f"{icon} not found")
    img = dest / "img"
    inside_site(img).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(icon, inside_site(img / "icon-512.png"))
    to_webp(icon, img / "icon-192.webp", 192, 192)

    feature = store / "feature-graphic-1024x500.png"
    if feature.exists():
        to_webp(feature, img / "feature.webp")

    shots = []
    for i, f in enumerate(sorted((store / "screenshots").glob("*.png")), 1):
        out = img / "screens" / (f.stem + ".webp")
        to_webp(f, out, SHOT_WIDTH)
        w, h = image_size(inside_site(out)) or (SHOT_WIDTH, SHOT_WIDTH * 2)
        alt = alt_from_filename(name, f.stem, i)
        shots.append(f'    <li><img src="img/screens/{out.name}" width="{w}" height="{h}" '
                     f'loading="lazy" alt="{esc(alt)}"></li>')

    if policy_body is None:
        policy_body = "<h1>" + esc(name) + " – Privacy Policy</h1>\n<p>TODO: paste the privacy policy.</p>"
        print("WARNING: no store/privacy-policy.html found - add the policy before publishing.")
    has_ads = "admob" in (policy_body or "").lower()

    values = {
        "NAME": esc(name), "SLUG": slug, "PACKAGE": esc(package), "SHORT": esc(short),
        "DESCRIPTION": description_html(full), "SCREENSHOTS": "\n".join(shots),
        "FACTS": default_facts(package, has_ads),
    }
    write_app(values, dest, policy_body, feature.exists())
    print(f"Created apps/{slug}/ ({len(shots)} screenshots) and added a card to index.html.")
    print("Next: review the page, improve screenshot alt texts, then run `check`.")
    print(f"Privacy policy URL: https://<username>.github.io/apps/{slug}/privacy-policy.html")


def cmd_new(a):
    slug = a.slug or slugify(a.name)
    dest = SITE / "apps" / slug
    if dest.exists():
        die(f"apps/{slug} already exists")
    values = {
        "NAME": esc(a.name), "SLUG": slug, "PACKAGE": esc(a.package),
        "SHORT": esc(a.short or "TODO: one-sentence description"),
        "DESCRIPTION": "    <p>TODO: describe the game.</p>",
        "SCREENSHOTS": '    <!-- TODO: <li><img src="img/screens/01.webp" width="540" height="1200" '
                       'loading="lazy" alt="What the screenshot shows"></li> -->',
        "FACTS": default_facts(a.package, False),
    }
    policy = "<h1>" + esc(a.name) + " – Privacy Policy</h1>\n<p>TODO: paste the privacy policy.</p>"
    write_app(values, dest, policy, has_feature=False)
    inside_site(dest / "img").mkdir(parents=True, exist_ok=True)
    print(f"Created apps/{slug}/. Add img/icon-512.png and img/icon-192.webp, then fill in the TODOs.")


def cmd_page(a):
    slug = slugify(a.slug)
    if slug in ("apps", "assets"):
        die(f"'{slug}' is reserved")
    dest = SITE / slug / "index.html"
    if dest.exists():
        die(f"{slug}/index.html already exists")
    t = (TEMPLATE / "page.html").read_text(encoding="utf-8")
    write(dest, fill_tokens(t, {"TITLE": esc(a.title), "DESCRIPTION": esc(a.description or a.title)}))
    if a.nav:
        h = HEADER.read_text(encoding="utf-8")
        link = f'      <a href="/{slug}/">{esc(a.nav)}</a>\n'
        if f'href="/{slug}/"' not in h:
            write(HEADER, h.replace("    </nav>", link + "    </nav>"))
    sync_headers()
    print(f"Created {slug}/index.html" + (" and added it to the menu." if a.nav else "."))
    print(f"URL: https://<username>.github.io/{slug}/")


def cmd_sync_policy(a):
    body, name = read_policy(Path(a.app_dir).expanduser().resolve() / "store")
    if body is None:
        die("store/privacy-policy.html not found")
    slug = a.slug or slugify(name or Path(a.app_dir).name)
    p = SITE / "apps" / slug / "privacy-policy.html"
    if not p.exists():
        die(f"apps/{slug}/privacy-policy.html not found (pass --slug)")
    t = p.read_text(encoding="utf-8")
    n = re.sub(r"(<!-- POLICY:START.*?-->\n).*(\n<!-- POLICY:END -->)",
               lambda m: m.group(1) + body + m.group(2), t, flags=re.S)
    if n == t:
        print("Already up to date.")
    else:
        write(p, n)
        print(f"Updated apps/{slug}/privacy-policy.html (placeholders come back - run `fill` again).")


def cmd_nav(_a):
    print(f"Updated the header in {sync_headers()} page(s).")


def template_html():
    yield from TEMPLATE.rglob("*.html")


def published_html():
    for p in SITE.rglob("*.html"):
        rel = p.relative_to(SITE)
        if not any(part.startswith(("_", ".")) for part in rel.parts):
            yield p


def cmd_fill(a):
    reps = {}
    if a.studio:
        reps["[YOUR NAME / STUDIO]"] = esc(a.studio)
    if a.email:
        e = esc(a.email)
        reps["[EMAIL]"] = f'<a href="mailto:{e}">{e}</a>'
    if a.date and not a.app:
        die("--date needs --app <slug> (each policy has its own effective date)")
    if not reps and not a.date:
        die("nothing to fill")
    changed = 0
    for p in list(published_html()) + list(template_html()):
        t = p.read_text(encoding="utf-8")
        n = t
        for k, v in reps.items():
            # inside <title>/<meta> use plain text, not a link
            n = re.sub(r"(<title>.*?</title>|<meta[^>]*>)",
                       lambda m: m.group(0).replace(k, re.sub(r"<[^>]+>", "", v)), n, flags=re.S)
            n = n.replace(k, v)
        if a.date and p == SITE / "apps" / a.app / "privacy-policy.html":
            n = n.replace("[DATE]", esc(a.date))
        if n != t:
            write(p, n)
            changed += 1
    sync_headers()
    print(f"Updated {changed} file(s).")


def cmd_check(_a):
    problems = 0
    for p in sorted(published_html()):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for ph in PLACEHOLDERS:
                if ph in line:
                    print(f"{p.relative_to(SITE)}:{i}: {ph}")
                    problems += 1
        t = p.read_text(encoding="utf-8")
        for name in PARTIALS:
            if re.search(rf"<!-- {name}:START -->\s*<!-- {name}:END -->", t):
                print(f"{p.relative_to(SITE)}: {name.lower()} is empty - run `nav`")
                problems += 1
    ads = (SITE / "app-ads.txt").read_text(encoding="utf-8")
    if "pub-" not in ads:
        print("app-ads.txt: no publisher line")
        problems += 1
    print("All good." if not problems else f"{problems} item(s) left to fill in.")
    return 1 if problems else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("import", help="import an app project with a store/ folder (read-only)")
    i.add_argument("app_dir")
    i.add_argument("--slug"); i.add_argument("--name"); i.add_argument("--package"); i.add_argument("--short")
    i.add_argument("--force", action="store_true", help="overwrite an existing apps/<slug>/")
    n = sub.add_parser("new", help="blank app page from the template")
    n.add_argument("--name", required=True); n.add_argument("--package", required=True)
    n.add_argument("--slug"); n.add_argument("--short")
    f = sub.add_parser("fill", help="replace [YOUR NAME / STUDIO], [EMAIL], [DATE]")
    f.add_argument("--studio"); f.add_argument("--email"); f.add_argument("--date"); f.add_argument("--app")
    pg = sub.add_parser("page", help="new non-app page at /<slug>/")
    pg.add_argument("--slug", required=True); pg.add_argument("--title", required=True)
    pg.add_argument("--description"); pg.add_argument("--nav", help="menu label (omit to keep it out of the menu)")
    sp = sub.add_parser("sync-policy", help="re-copy an app's privacy policy text")
    sp.add_argument("app_dir"); sp.add_argument("--slug")
    sub.add_parser("nav", help="copy the shared header and footer into every page")
    sub.add_parser("check", help="list unfinished placeholders")
    a = ap.parse_args()
    sys.exit({"import": cmd_import, "new": cmd_new, "page": cmd_page, "nav": cmd_nav, "sync-policy": cmd_sync_policy,
              "fill": cmd_fill, "check": cmd_check}[a.cmd](a) or 0)


if __name__ == "__main__":
    main()
