/* Optional host callbacks. The standalone viewer has no analytics dependency. */
"use strict";
(function(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.CitylinerIntegration = api;
})(typeof window === "object" ? window : null, function() {
  function createHooks(adapter) {
    function invoke(name, args) {
      try { return adapter?.[name]?.(...args); } catch (_) { /* Host failures cannot break the map. */ }
    }
    const hooks = {};
    for (const name of ["ready", "loading", "action", "time", "playing", "context", "event"])
      hooks[name] = (...args) => invoke(name, args);
    hooks.shareUrl = href => {
      const value = invoke("shareUrl", [href]);
      try {
        const candidate = new URL(value);
        if (candidate.origin === new URL(href).origin) return candidate.href;
      } catch (_) { /* Keep the original view link if the adapter returns no valid URL. */ }
      return href;
    };
    return hooks;
  }
  return {createHooks};
});
