# gps_denied_navigation_sim — Project Page

Static project page for the [`gps_denied_navigation_sim`](https://github.com/riotu-lab/gps_denied_navigation_sim) ROS 2 package. Deployable as-is via GitHub Pages.

## Contents

- `index.html` — the single-page site (Bulma + FontAwesome + Mermaid via CDN, no build step)
- `static/css/`, `static/js/` — vendored Bulma / FontAwesome / carousel / slider bundles
- `static/images/uav/` — renders of the three UAV models (copied from [`../media/uav_models`](../media/uav_models))
- `static/images/worlds/` — renders of the six simulation worlds (copied from [`../media/world_models`](../media/world_models))
- `generate_figures.py` — legacy script for generating analysis figures from a CSV dataset (kept for reference; not required to build the site)

## Local preview

No build step is required — just serve the folder:

```bash
cd website
python3 -m http.server 8000
# → open http://localhost:8000
```

## Deploy to GitHub Pages

1. Commit the `website/` folder to the repository default branch (typically `main`).
2. In **Settings → Pages**, set the source to **Deploy from a branch**, branch `main`, folder `/website`.
3. Alternatively, publish the folder as its own `gh-pages` branch:

   ```bash
   # from the repo root
   git subtree push --prefix website origin gh-pages
   ```

GitHub serves the page at `https://<org>.github.io/<repo>/` (or the CNAME you configure).

## Refreshing the UAV / world images

If new renders are added to `../media/uav_models` or `../media/world_models`, copy them to the mirrored folders:

```bash
cp ../media/uav_models/*.png   static/images/uav/
cp ../media/world_models/*.png static/images/worlds/
```

Then edit the relevant `<img src="./static/images/uav/…">` tags in `index.html`.

## License

Website template adapted from [Nerfies](https://github.com/nerfies/nerfies.github.io), licensed under CC BY-SA 4.0. Simulator content MIT-licensed, see the package `LICENSE` / `package.xml`.
