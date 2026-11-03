# Studio website (GitHub Pages)

Plain static HTML/CSS, no build step. GitHub Pages serves this folder as-is from the
`main` branch, root (`/`). No cookies, analytics, web fonts or third-party scripts
(every page has a Content-Security-Policy that blocks them), so it stays
Families/COPPA friendly.

```
index.html                              home page: one card per app + short "about me"
about/index.html                        profile / bio page
app-ads.txt                             ONE file for all apps (all ad networks)
404.html
assets/css/site.css                     shared styles
assets/img/favicon.svg
apps/<slug>/index.html                  app page
apps/<slug>/privacy-policy.html         per-app privacy policy (URL goes into Play Console)
apps/<slug>/img/                        icon-512.png, icon-192.webp, screens/*.webp
_template/header.html                   shared header + menu for EVERY page (edit here only)
_template/app/, card.html               starting point for new apps (not published)
_template/page.html                     starting point for other pages (FAQ, Press...)
_tools/sitetool.py                       helper script (not published)
```

Folders starting with `_` and this README are not published (see `_config.yml`).

## Golden rule: never change a published URL

Once a URL is in Play Console, keep it forever:
`/app-ads.txt`, `/apps/<slug>/` and `/apps/<slug>/privacy-policy.html`.
Pick the slug once (lowercase, hyphens, e.g. `pawzzle-pals`) and never rename it.
Links inside the site are either relative or start at the site root (`/about/`), so the same files work unchanged on a custom domain.

## How the site is organised (extensibility)

Three kinds of content, each with its own template and command:

| What | Lives at | Create with |
|---|---|---|
| An app | `/apps/<slug>/` (+ `privacy-policy.html`) | `sitetool.py import ../App` or `new` |
| Any other page (About, FAQ, Press, Contact…) | `/<slug>/` | `sitetool.py page --slug faq --title "…" --nav "FAQ"` |
| Site-wide files (`app-ads.txt`, menu, CSS) | root, `_template/header.html`, `assets/` | edit by hand |

The header and menu are the same on every page. Edit `_template/header.html`, then run
`python3 _tools/sitetool.py nav`. The page you're on is highlighted automatically.
Never edit the part between `<!-- HEADER:START -->` and `<!-- HEADER:END -->` on a page,
because `nav` overwrites it.

## Edit your profile

Edit `about/index.html` (plain HTML). To add a photo, save a square ~400 px image as
`assets/img/profile.webp` (`cwebp -resize 400 400 photo.jpg -o assets/img/profile.webp`)
and swap the `RD` initials for the `<img>` line shown in the comment. Keep phone numbers
and home addresses off the site.

## Add a new app

### Option A: import from an app project (recommended)

This works when the app folder uses the usual `store/` layout (`play-icon-512.png`,
`screenshots/*.png`, `privacy-policy.html`, optional `feature-graphic-1024x500.png` and
`listings/en-US.txt`). The script only reads the app folder.

```sh
cd website
python3 _tools/sitetool.py import ../OrbitHop            # slug = orbit-hop
python3 _tools/sitetool.py import ../OrbitHop --slug orbit-hop --short "One tap. Infinite space."
```

This creates `apps/<slug>/` (index page, privacy policy copied unchanged, images
converted to small WebP files) and adds the card to `index.html`.
Images need `cwebp` (`brew install webp`) or Pillow.

### Option B: by hand

1. Copy `_template/app/` to `apps/<slug>/`.
2. In `apps/<slug>/index.html`, replace every `{{NAME}}`, `{{SHORT}}`, `{{PACKAGE}}`
   (applicationId), `{{SCREENSHOTS}}`, `{{DESCRIPTION}}`, `{{FACTS}}`.
   Delete the FEATURE block if you have no feature graphic.
3. In `apps/<slug>/privacy-policy.html`, replace `{{NAME}}` and paste the policy body at `{{POLICY}}`.
4. Put `icon-512.png`, `icon-192.webp` and `screens/*.webp` in `apps/<slug>/img/`.
5. Copy `_template/card.html` into `index.html` just above `<!-- APPS:END -->` and replace
   `{{SLUG}}`, `{{NAME}}`, `{{SHORT}}`, `{{PACKAGE}}`.
   (Or run `python3 _tools/sitetool.py new --name "My Game" --package com.example.mygame`,
   which does steps 1, 3 and 5 for you with TODOs to fill in.)

### Then, in both cases

1. Write meaningful screenshot alt text (say what the picture shows, not "screenshot 3").
2. Fill in the placeholders:
   ```sh
   python3 _tools/sitetool.py fill --studio "Your Studio" --email you@example.com
   python3 _tools/sitetool.py fill --app <slug> --date "1 December 2025"
   ```
3. Run `python3 _tools/sitetool.py check`. It must say "All good."
4. Preview: `python3 -m http.server 8765 --bind 127.0.0.1`, open http://127.0.0.1:8765
5. Commit and push. The site updates in about 1 minute.
6. Play Console for the new app:
   - Store settings > Website: `https://<username>.github.io`
   - App content > Privacy policy: `https://<username>.github.io/apps/<slug>/privacy-policy.html`
7. If you later change the policy in the app project, re-copy it with
   `python3 _tools/sitetool.py sync-policy ../App` (then `fill --app <slug> --date …`).
8. If the new app uses a **different** ad network or AdMob account, add its lines to
   `app-ads.txt`. Apps on the same AdMob account need nothing new.

## app-ads.txt

One line per ad network/seller, all apps share it:

```
google.com, pub-2588052647404572, DIRECT, f08c47fec0942fa0
```

It must stay at the root of the domain that is in each app's Play "Website" field.

## Custom domain later (e.g. mystudio.com)

1. Buy the domain. At the DNS provider add:
   - apex `mystudio.com`: four `A` records 185.199.108.153, 185.199.109.153,
     185.199.110.153, 185.199.111.153 (and optional `AAAA` 2606:50c0:8000::153,
     2606:50c0:8001::153, 2606:50c0:8002::153, 2606:50c0:8003::153)
   - `www`: `CNAME` to `<username>.github.io`
2. GitHub: Settings > Pages > Custom domain: `mystudio.com` > Save (this commits a
   `CNAME` file; keep it). Wait for the DNS check, then tick **Enforce HTTPS**.
   Optional but recommended: verify the domain in your GitHub account settings
   (Settings > Pages > Add a domain) to prevent takeover.
3. `https://<username>.github.io/...` now redirects (301) to `https://mystudio.com/...`
   with the same path, so the old privacy URLs keep working.
4. Play Console, for **every** app: change Website to `https://mystudio.com`, and
   optionally the privacy URL to `https://mystudio.com/apps/<slug>/privacy-policy.html`.
5. AdMob re-crawls app-ads.txt from the new Website domain (`https://mystudio.com/app-ads.txt`).
   Check AdMob > Apps > app-ads.txt after about 24 hours.
   Keep the domain renewed. If it lapses, app-ads.txt and the privacy URLs break.
