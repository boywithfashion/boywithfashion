// Main timeline for the Viplav "outgrown" reel: caption pops and rings, camera (jump-cut
// framing, punch-ins, shake, flashes), the crown on "leader" and the name card.
// Every time it uses comes from window.REEL_EDL, the edit decision list that
// tools/build_index.py writes into index.html; the script inlines this file there too.
(function () {
  const EDL = window.REEL_EDL;
  const tl = gsap.timeline({ paused: true });

  // ---- Captions: each group shows at its first word; every word pops on its own cue.
  EDL.caps.forEach(function (g) {
    tl.set("#" + g.id, { opacity: 1 }, g.start);
    tl.set("#" + g.id, { opacity: 0 }, g.end);
    g.words.forEach(function (w) {
      const power = Boolean(w.c);
      tl.fromTo(
        "#" + w.id,
        { scale: power ? 0 : 0.35, y: power ? 0 : 36, rotation: power ? -7 : 0, opacity: 0 },
        {
          scale: 1,
          y: 0,
          rotation: 0,
          opacity: 1,
          duration: power ? 0.26 : 0.17,
          ease: power ? "back.out(2.4)" : "back.out(2.6)",
        },
        Math.max(0, w.t - 0.03),
      );
      if (w.ring) {
        const path = document.querySelector("#" + w.id + " .ring path");
        const len = path.getTotalLength();
        gsap.set(path, { strokeDasharray: len, strokeDashoffset: len, opacity: 0 });
        tl.fromTo(path, { opacity: 0 }, { opacity: 1, duration: 0.01, immediateRender: false }, w.t + 0.12);
        tl.fromTo(
          path,
          { strokeDashoffset: len },
          { strokeDashoffset: 0, duration: 0.32, ease: "power2.inOut", immediateRender: false },
          w.t + 0.12,
        );
      }
    });
  });

  // ---- Camera, shake and flash are pure functions of time (seek-safe in any order):
  // each jump cut sets a base framing (optionally drifting), each punch eases from the
  // value it interrupts to its target and holds until the next cut.
  const PUNCH_IN = 0.12;
  const SHAKE = [
    [0.04, -18, 10, -0.6],
    [0.08, 16, -8, 0.5],
    [0.12, -10, 6, -0.3],
    [0.16, 6, -3, 0.2],
    [0.21, 0, 0, 0],
  ];
  // No flash on the paper rip: the tear is the transition.
  const flashes = EDL.brollIn
    .map(function (t) {
      return { t: t, a: 0.45 };
    })
    .concat(
      EDL.punches
        .filter(function (p) {
          return p.shake;
        })
        .map(function (p) {
          return { t: p.t, a: 0.35 };
        }),
    );
  function easeOut3(x) {
    return 1 - Math.pow(1 - x, 3);
  }
  function sineInOut(x) {
    return -(Math.cos(Math.PI * x) - 1) / 2;
  }
  const HALF_FRAME = 0.5 / 30;
  // Camera state [scale, lift px] at time t.
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
        const k = easeOut3(Math.min(1, (x - p.t) / PUNCH_IN));
        return [from[0] + (p.s - from[0]) * k, from[1] + (p.dy - from[1]) * k];
      };
    }
    return fn(t);
  }
  // Crown on "leader": drops in with a bounce and follows the head track.
  function easeOutBack(x) {
    const c1 = 2.2;
    const c3 = c1 + 1;
    return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2);
  }
  function crownAt(t) {
    const c = EDL.crown;
    if (t < c.in - HALF_FRAME || t >= c.out) return null;
    const tr = c.track;
    let x = tr[0][1];
    let y = tr[0][2];
    for (let i = 0; i < tr.length - 1; i++) {
      if (t >= tr[i][0] && t <= tr[i + 1][0]) {
        const k = (t - tr[i][0]) / (tr[i + 1][0] - tr[i][0]);
        x = tr[i][1] + (tr[i + 1][1] - tr[i][1]) * k;
        y = tr[i][2] + (tr[i + 1][2] - tr[i][2]) * k;
      } else if (t > tr[tr.length - 1][0]) {
        x = tr[tr.length - 1][1];
        y = tr[tr.length - 1][2];
      }
    }
    const k = Math.min(1, Math.max(0, (t - c.in) / 0.3));
    const drop = (1 - easeOutBack(k)) * -320;
    return { x: x, y: y + drop, o: Math.min(1, k * 4) };
  }
  function shakeAt(t) {
    for (const p of EDL.punches) {
      if (!p.shake) continue;
      const d = t - p.t;
      if (d < 0 || d >= SHAKE[SHAKE.length - 1][0]) continue;
      let prev = [0, 0, 0, 0];
      for (const k of SHAKE) {
        if (d <= k[0]) {
          const u = (d - prev[0]) / (k[0] - prev[0]);
          return [1, 2, 3].map(function (i) {
            return prev[i] + (k[i] - prev[i]) * u;
          });
        }
        prev = k;
      }
    }
    return [0, 0, 0];
  }
  function flashAt(t) {
    let a = 0;
    for (const f of flashes) {
      const d = t - f.t;
      if (d < 0 || d > 0.19) continue;
      a = Math.max(a, d < 0.03 ? (f.a * d) / 0.03 : f.a * (1 - (d - 0.03) / 0.16));
    }
    return a;
  }
  const cam = document.getElementById("cam");
  const crown = document.getElementById("crown");
  const camShake = document.getElementById("cam-shake");
  const flash = document.getElementById("flash");
  const clock = { t: 0 };
  function paintCamera() {
    const t = clock.t;
    const c = camAt(t);
    gsap.set(cam, { scale: c[0], y: c[1] });
    const cr = crownAt(t);
    if (cr) gsap.set(crown, { x: cr.x - 140, y: cr.y - 170, opacity: cr.o });
    else gsap.set(crown, { opacity: 0 });
    const sh = shakeAt(t);
    gsap.set(camShake, { x: sh[0], y: sh[1], rotation: sh[2] });
    gsap.set(flash, { opacity: flashAt(t) });
  }
  paintCamera();
  tl.fromTo(
    clock,
    { t: 0 },
    { t: EDL.duration, duration: EDL.duration, ease: "none", onUpdate: paintCamera },
    0,
  );

  // ---- Name card: slides up on "Viplav", each word lands on its cue.
  tl.fromTo(
    "#namecard",
    { yPercent: 140, rotation: 6, opacity: 0 },
    { yPercent: 0, rotation: -2, opacity: 1, duration: 0.3, ease: "back.out(2)" },
    EDL.namecard.in,
  );
  EDL.namecard.words.forEach(function (w) {
    tl.fromTo(
      "#" + w.id,
      { scale: 0, opacity: 0 },
      { scale: 1, opacity: 1, duration: 0.2, ease: "back.out(3.5)" },
      Math.max(EDL.namecard.in, w.t - 0.03),
    );
  });

  window.__timelines["main"] = tl;
})();
