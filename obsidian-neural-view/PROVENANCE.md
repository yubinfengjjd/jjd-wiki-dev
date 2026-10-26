# Visual and implementation provenance

- Visual upstream: https://github.com/luoluo-121/neural-creator-dashboard
- Frozen commit: `769d690fa1c06d985926d8f16772d15514b718e1` (retrieved 2026-10-22).
- `src/vendor/Scene.jsx`: derived from upstream `src/neural/Home.jsx` Scene, spring positioning, particle, video-to-canvas and fan animation. Business summaries replaced with existing-note and explicit-link counts; five module ids mapped to wiki folders; video refs and SVG ids scoped; visibility and unmount handling added. Original upstream clone is untouched.
- `src/vendor/NetworkCanvas.jsx`: upstream Canvas network retained; uses real graph adapter and visibility/local animation time.
- `src/vendor/theme.js`: upstream palette and filters retained, module ids replaced; resource paths provided by Obsidian rather than web-root assets.
- `src/vendor/icons.jsx` and `src/vendor/neural.css`: copied from upstream. Build scopes every CSS selector, animation name and custom animated property to the native view; local size/toolbar/detail adjustments live in `src/ui/overrides.css`.
- `media/{orb.mp4,orb.jpg,jellyfish.mp4,jellyfish.jpg}`: upstream unchanged originals. Upstream README attributes core videos to Dreamina AI-generated assets; retain upstream third-party/platform and AI-material qualifications.
- Upstream `LICENSE`, `NOTICE.md` and `licenses/MIT-legacy.txt` retained verbatim. Current upstream policy is PolyForm Noncommercial 1.0.0, subject to prior MIT and third-party exceptions in NOTICE. This integration does not relabel those materials or assert exclusive rights to generated media. Imported vault notes retain their owner's rights.
- React / React DOM, esbuild, PostCSS and other npm packages keep their own licenses. React's bundled notice is retained by esbuild; dependency license texts remain in installed package directories. `obsidian` is external at runtime.
- Local adapter, Obsidian ItemView wrapper, detail UI, build harness and tests are integration code for this local installation. No blanket license grant over the assembled directory is made here.
- No upstream `src/data`, `graph.js`, localStorage editor, drafts/ideas pages, account statistics, analytics or AI integration is imported.

The native plugin build never contains the preview fixtures. `preview/` is a separately built local test harness that uses the same React render entry and has no access to the real vault.
