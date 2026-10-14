# Host integration

Generate a [local demo](README.md#local-demo), or copy the viewer HTML, JS, CSS and `fonts/` into your host directory, then stage a bundle with `citylines.explorer.publish --gallery-root PATH`. Serve over HTTP.

Set optional `window.citylinerHooks` before `explorer.js` loads. Callback failures are isolated; the viewer has no built-in analytics.

| Hook | Trigger |
| --- | --- |
| `ready(context, startTime)` | Day rendered; Unix timestamp |
| `loading()` | Loading starts or fails |
| `context(context)` | Display style changes |
| `action()` | City/date/mode/view changes or section tap |
| `time(startTime)` | Manual scrubbing |
| `playing(boolean)` | Playback starts or pauses |
| `event(name, details)` | `loadFailed`, `linkCopied`, `artworkReady` |
| `shareUrl(href)` | Same-origin share URL override |

Context includes city, bundle and view. The host owns engagement rules and event storage.
Use the `site:head`, `site:header` and `site:footer` HTML markers for branding. Pin the imported viewer revision and retain its licence and source attribution.
