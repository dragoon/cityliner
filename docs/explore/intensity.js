/* Pure display transforms; never change the timetable counts. */
"use strict";
((root) => {
  function visual(count, peak, maximum, view, reference = 0) {
    const scale = Math.max(4, peak || 0);
    if (view === "change") {
      const delta = count - reference;
      return {intensity: peak > 0 ? Math.min(1, Math.abs(delta) / scale) : 0, delta};
    }
    if (view === "rhythm") {
      return {intensity: peak > 0 ? Math.pow(Math.min(1, Math.max(0, count / scale)), 1.2) : 0, delta: 0};
    }
    return {intensity: count > 0 && maximum > 0 ? Math.log1p(count) / Math.log1p(maximum) : 0, delta: 0};
  }
  function blend(from, to, fraction, output) {
    const t = Math.max(0, Math.min(1, fraction));
    for (let i = 0; i < output.length; i++) output[i] = from[i] + (to[i] - from[i]) * t;
    return output;
  }
  function color(hex, intensity) {
    const factor = Math.max(0, Math.min(1, intensity));
    return `rgb(${[1, 3, 5].map(i => Math.round(parseInt(hex.slice(i, i + 2), 16) * factor)).join(",")})`;
  }
  const api = {visual, color, blend};
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.CitylinerIntensity = api;
})(typeof window === "object" ? window : {});
