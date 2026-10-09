# Hosting the reusable viewer

The viewer runs without analytics. Export a GTFS bundle, stage it with
`python -m citylines.explorer.publish --bundle PATH --gallery-root docs/explore`,
and serve `docs` over HTTP. The included demo is synthetic, not a real city.

An optional host script can set `window.citylinerHooks` before `explorer.js`
executes. `integration.js` isolates callback failures from the viewer.

| Callback | Trigger |
| --- | --- |
| `ready(context, startTime)` | The selected day has rendered; time is a Unix timestamp |
| `loading()` | Loading starts or fails |
| `context(context)` | Display style changes |
| `action()` | Deliberate city/date/mode/view changes or a section tap |
| `time(startTime)` | Manual time scrubbing |
| `playing(boolean)` | Playback starts or pauses |
| `event(name, details)` | `loadFailed` with a `stage`, `linkCopied`, or `artworkReady` |
| `shareUrl(href)` | Optional same-origin URL transformation before copying |

Context contains the public `city`, `bundle`, and selected `view`. Action
notifications have no built-in engagement threshold, campaign rules, event
storage, or network requests. Host integrations own any interpretation.

The `site:head`, `site:header`, and `site:footer` HTML markers allow a host
build to add its own scripts and branding while reusing the shared interface.
Keep a pinned upstream revision and preserve its license and source attribution.
