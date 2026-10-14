// Main timeline for the Viplav "outgrown" reel: phrase captions with word-by-word highlight,
// red circles, the camera (jump-cut framing, slow drift, gentle punch-ins) and the name card.
// Every time it uses comes from window.REEL_EDL, the edit decision list that
// tools/build_index.py writes into index.html; the script inlines this file there too.
(function () {
  const EDL = window.REEL_EDL;
  const tl = gsap.timeline({ paused: true });

  const WHITE = "#ffffff";
  const YELLOW = "#ffe11a";
  const RED = "#ff2b2b";

  // ---- Captions: a phrase eases in, each word lights up as it is spoken, then settles to
  // white (or keeps its power colour), and the phrase eases out.
  EDL.caps.forEach(function (g) {
    const cap = "#" + g.id;
    tl.fromTo(cap, { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }, g.start - 0.06);
    tl.fromTo(
      cap,
      { opacity: 1 },
      { opacity: 0, duration: 0.2, ease: "power1.in", immediateRender: false },
      g.end - 0.2,
    );
    g.words.forEach(function (w) {
      const el = "#" + w.id;
      const lit = w.c === "r" ? RED : YELLOW;
      const rest = w.c === "r" ? RED : w.c === "y" ? YELLOW : WHITE;
      tl.fromTo(
        el,
        { color: WHITE, scale: 1 },
        { color: lit, scale: 1.06, duration: 0.18, ease: "power2.out" },
        Math.max(0, w.on - 0.04),
      );
      tl.fromTo(
        el,
        { color: lit, scale: 1.06 },
        { color: rest, scale: 1, duration: 0.15, ease: "power1.out", immediateRender: false },
        w.off - 0.04,
      );
      if (w.ring) {
        const path = document.querySelector(el + " .ring path");
        const len = path.getTotalLength();
        // Hidden until it draws: a fully offset dash still paints its round cap as a dot.
        gsap.set(path, { strokeDasharray: len, strokeDashoffset: len, opacity: 0 });
        tl.fromTo(path, { opacity: 0 }, { opacity: 1, duration: 0.01, immediateRender: false }, w.on + 0.15);
        tl.fromTo(
          path,
          { strokeDashoffset: len },
          { strokeDashoffset: 0, duration: 0.6, ease: "power2.inOut", immediateRender: false },
          w.on + 0.15,
        );
      }
    });
  });

  // ---- Camera: a pure function of time (seek-safe in any order). Each jump cut sets a base
  // framing that drifts slowly; each punch eases from the value it interrupts to its target
  // and holds until the next cut.
  const HALF_FRAME = 0.5 / 30;
  function easeInOut2(x) {
    return x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
  }
  function sineInOut(x) {
    return -(Math.cos(Math.PI * x) - 1) / 2;
  }
  function camAt(t) {
    let seg = EDL.cam[0];
    for (const c of EDL.cam) if (c.t <= t + HALF_FRAME) seg = c;
    const segEnd = seg.t + seg.dur;
    let fn = function (x) {
      if (!seg.drift) return [seg.s, 0];
      const k = Math.min(1, Math.max(0, (x - seg.t) / seg.dur));
      return [seg.s + (seg.drift - seg.s) * sineInOut(k), 0];
    };
    for (const p of EDL.punches) {
      if (p.t < seg.t - HALF_FRAME || p.t >= segEnd - HALF_FRAME || p.t > t) continue;
      const prev = fn;
      const from = prev(p.t);
      fn = function (x) {
        if (x < p.t) return prev(x);
        const k = easeInOut2(Math.min(1, (x - p.t) / p.d));
        return [from[0] + (p.s - from[0]) * k, from[1] + (p.dy - from[1]) * k];
      };
    }
    return fn(t);
  }
  const cam = document.getElementById("cam");
  const clock = { t: 0 };
  function paintCamera() {
    const c = camAt(clock.t);
    gsap.set(cam, { scale: c[0], y: c[1] });
  }
  paintCamera();
  tl.fromTo(clock, { t: 0 }, { t: EDL.duration, duration: EDL.duration, ease: "none", onUpdate: paintCamera }, 0);

  // ---- Name card: eases up once the paper rip has revealed the speaker, and stays.
  tl.fromTo(
    "#namecard",
    { yPercent: 60, rotation: 0, opacity: 0 },
    { yPercent: 0, rotation: -2, opacity: 1, duration: 0.6, ease: "power2.out" },
    EDL.namecard.in,
  );

  window.__timelines["main"] = tl;
})();
