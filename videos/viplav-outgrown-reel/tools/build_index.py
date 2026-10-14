#!/usr/bin/env python3
"""Generate index.html for the Viplav "outgrown" reel from one edit decision list.

Everything time-based lives in the tables below: the kept source ranges of the raw
take (jump cuts that drop the dead air), the word timings from the transcript, the
caption groups, punch-ins and B-roll slots. Output times are derived, never typed
twice, so changing a cut keeps every caption and punch in sync.

Re-running this script overwrites index.html; edits made in Studio to index.html
are lost unless they are carried back into these tables.

    python3 tools/build_index.py
"""

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
W, H = 1080, 1920

# Kept source ranges of assets/footage.mp4 (seconds). Pauses between them are cut.
SEGMENTS = [
    (0.90, 3.60),  # Your business has outgrown you.
    (3.98, 7.22),  # The skills that build a 5 crore business
    (7.53, 9.62),  # won't build a 50 crore business.
    (9.78, 13.24),  # Different scales of business, different challenges,
    (13.58, 15.38),  # different leader qualities.
    (15.95, 17.92),  # The business is ready.
    (18.76, 21.75),  # The question is: are you?  (keeps a beat after "you?" for the circle)
    (22.86, 27.36),  # Businesses grow only when the founders grow.
    (30.32, 31.92),  # Viplav the Coach
    (32.22, 35.42),  # jo badal de aapki soch
]

# Output start of each segment, on the 30 fps frame grid so every cut lands on a frame.
SEG_FRAMES = [round((b - a) * FPS) for a, b in SEGMENTS]
SEG_OUT = []
_f = 0
for n in SEG_FRAMES:
    SEG_OUT.append(round(_f / FPS, 4))
    _f += n
DURATION = round(_f / FPS, 4)


def out(src):
    """Map a source time to output time through the segment that contains it."""
    for (a, b), o in zip(SEGMENTS, SEG_OUT):
        if a - 0.05 <= src <= b + 0.05:
            return round(o + (src - a), 3)
    raise ValueError(f"source time {src} falls in a cut")


# Caption groups: at most two words on screen. Each word is (text, source start, style)
# where style is "" (white), "y" (yellow power word) or "r" (red power word).
# A group stays up until the next group starts (or until its "until" source time).
GROUPS = [
    [("YOUR", 0.96, ""), ("BUSINESS", 1.28, "")],
    [("HAS", 2.08, ""), ("OUTGROWN", 2.32, "y")],
    [("YOU.", 3.20, "r")],
    [("THE", 4.08, ""), ("SKILLS", 4.24, "")],
    [("THAT", 4.96, ""), ("BUILD", 5.20, "")],
    [("A", 5.60, ""), ("₹5 CRORE", 5.76, "y")],
    [("BUSINESS", 6.56, "")],
    [("WON'T", 7.56, "r"), ("BUILD", 7.92, "")],
    [("A", 8.16, ""), ("₹50 CRORE", 8.24, "r")],
    [("BUSINESS.", 9.12, "")],
    [("DIFFERENT", 10.00, ""), ("SCALES", 10.40, "y")],
    [("OF", 10.88, ""), ("BUSINESS", 11.04, "")],
    [("DIFFERENT", 11.84, ""), ("CHALLENGES", 12.16, "r")],
    [("DIFFERENT", 13.68, "")],
    [("LEADER", 14.00, "y"), ("QUALITIES", 14.64, "y")],
    [("THE", 16.00, ""), ("BUSINESS", 16.24, "")],
    [("IS", 17.04, ""), ("READY", 17.36, "y")],
    [("THE", 18.80, ""), ("QUESTION", 19.12, "")],
    [("IS", 19.60, "")],
    [("ARE", 20.16, ""), ("YOU?", 20.64, "r!")],
    [("BUSINESSES", 22.88, ""), ("GROW", 23.92, "y")],
    [("ONLY", 24.80, ""), ("WHEN", 25.36, "")],
    [("THE", 25.68, ""), ("FOUNDERS", 25.92, "y")],
    [("GROW.", 26.88, "y")],
    # 30.40 / 30.92 / 31.10: "Viplav the Coach" is carried by the name card, not captions.
    [("JO", 32.34, ""), ("BADAL", 32.60, "")],
    [("DE", 32.96, ""), ("AAPKI", 33.34, "")],
    [("SOCH", 33.94, "y!")],
]
# Groups that end before the next one starts (source time).
GROUP_UNTIL = {23: 27.36}

# Name card words (source start times).
NAMECARD = [("VIPLAV", 30.40, ""), ("THE", 30.92, ""), ("COACH", 31.10, "r")]

# B-roll sub-compositions: (id, output start, output end).
BROLL = [
    ("broll-crore", out(5.60) - 0.02, out(9.12) + 0.02),
    ("broll-scales", out(10.00), out(13.24)),
    ("broll-ready", out(15.95), out(17.76)),
    ("broll-founders", out(24.80), out(27.36)),
]
# The paper rip tears the READY snapshot away to reveal the speaker.
RIP_START = BROLL[2][2]
RIP_DUR = 1.25

# Camera: per segment a base framing (scale) applied at the cut, an optional slow drift,
# and punch-ins cued to words. Scale is around the face (transform-origin 50% 26%).
CAM_BASE = [1.0, 1.12, 1.0, 1.15, 1.0, 1.06, 1.05, 1.0, 1.08, 1.16]
CAM_DRIFT = {6: 1.16, 8: 1.12, 9: 1.2}  # segment index -> scale reached by segment end
PUNCHES = [  # (source time, scale, shake)
    (2.32, 1.22, False),  # OUTGROWN
    (3.20, 1.38, True),  # YOU.
    (9.12, 1.3, False),  # BUSINESS. (visible as the crore B-roll swipes out)
    (14.00, 1.24, False),  # LEADER
    (14.64, 1.32, False),  # QUALITIES
    (20.64, 1.45, True),  # YOU?
    (23.92, 1.22, False),  # GROW
    (33.94, 1.32, False),  # SOCH
]


# Montserrat Black advance widths (em), measured from the font file, for exact caption fitting.
ADV = {'A': 0.806, 'B': 0.773, 'C': 0.737, 'D': 0.826, 'E': 0.673, 'F': 0.644, 'G': 0.769, 'H': 0.804,
       'I': 0.35, 'J': 0.574, 'K': 0.765, 'L': 0.617, 'M': 0.954, 'N': 0.804, 'O': 0.848, 'P': 0.743,
       'Q': 0.848, 'R': 0.745, 'S': 0.657, 'T': 0.654, 'U': 0.784, 'V': 0.786, 'W': 1.206, 'X': 0.762,
       'Y': 0.71, 'Z': 0.687, '0': 0.692, '1': 0.418, '2': 0.608, '3': 0.614, '4': 0.712, '5': 0.619,
       '6': 0.661, '7': 0.645, '8': 0.678, '9': 0.661, ' ': 0.3, '.': 0.304, ',': 0.304, '?': 0.606,
       '!': 0.314, ':': 0.304, "'": 0.254, '-': 0.39, '₹': 0.728}
TRACKING = -0.02  # letter-spacing, em
STROKE = 0.1  # text stroke, em (half of it shows outside the glyph on each side)
WORD_GAP = 0.24  # column-gap, em
POWER = 1.12  # power words are this much larger
MAX_LINE = 860  # px; leaves room for the pop overshoot inside the 1080 canvas
BOX_H = 300  # caption box height, px


def word_em(text):
    return sum(ADV[c] for c in text) + TRACKING * (len(text) - 1) + STROKE


# Sound effects (assets/sfx: Pixabay-licensed library bundled with HyperFrames, plus the
# synthesized paper-rip.wav). Each cue is placed so the sound's own transient ("hit", seconds
# into the file) lands on the visual event. Volumes keep the effects under the voice.
B = {cid: (s, e) for cid, s, e in BROLL}
HIT = {"whoosh": 0.16, "pop": 0.11, "impact-bass-1": 0.06, "sparkle": 0.02, "paper-rip": 0.0}
SFX = []  # (file, start, duration or None, media start, volume)


def cue(name, event, vol, media_start=0.0, dur=None, hit=None):
    ext = "wav" if name == "paper-rip" else "mp3"
    h = HIT.get(name, 0.0) if hit is None else hit
    SFX.append((f"assets/sfx/{name}.{ext}", round(max(0.0, event - h), 3), dur, media_start, vol))


# Whoosh as every B-roll scene punches in, and as each one swipes out.
for cid, (s, e) in B.items():
    cue("whoosh", s, 0.55)
cue("whoosh", B["broll-crore"][0] + 3.12 + 0.06, 0.45)
cue("whoosh", B["broll-scales"][0] + 3.11 + 0.06, 0.45)
cue("whoosh", B["broll-founders"][0] + 2.44 + 0.06, 0.45)
# Paper tear under the rip.
cue("paper-rip", RIP_START + 0.04, 0.8)
# Bass hits on the slams.
cue("impact-bass-1", out(3.20), 0.32)  # YOU.
cue("impact-bass-1", B["broll-crore"][0] + 2.45, 0.3)  # 50 Cr bar lands
cue("impact-bass-1", B["broll-ready"][0] + 1.41, 0.3)  # READY stamp
cue("impact-bass-1", out(20.64), 0.4)  # YOU?
cue("impact-bass-1", out(33.94), 0.26)  # SOCH
# Riser building under "the question is, are..." and peaking on "you?" (the file peaks ~3.0s in).
cue("riser", out(20.64), 0.16, media_start=1.5, dur=2.0, hit=1.5)
# Pops on power words and on graphics landing.
for t in [
    out(2.32),  # OUTGROWN
    B["broll-crore"][0] + 0.24,  # 5 Cr bar label
    B["broll-crore"][0] + 1.67,  # SAME SKILLS chip
    B["broll-scales"][0] + 0.06,  # shop
    B["broll-scales"][0] + 0.40,  # office
    B["broll-scales"][0] + 0.88,  # tower
    out(14.00),  # LEADER
    out(14.64),  # QUALITIES
    out(23.92),  # GROW
    out(25.92),  # FOUNDERS
    B["broll-founders"][0] + 2.08,  # building follows the founder
    out(30.40),  # name card: VIPLAV
    out(31.10),  # name card: COACH
]:
    cue("pop", t, 0.5)
# "Won't build": a wrong-buzz on the red cross over SAME SKILLS.
cue("error", B["broll-crore"][0] + 2.03, 1.0, media_start=0.55, dur=1.0, hit=0.05)
# "Challenges": a short glitch as the warnings slam on.
cue("glitch-1", B["broll-scales"][0] + 2.16, 0.22, media_start=0.12, dur=0.9, hit=0.05)
# READY tick sparkle.
cue("sparkle", B["broll-ready"][0] + 1.45, 0.25)
# Soft swish as the red circles draw, as the founder grows and as the name card slides up.
cue("whoosh", out(20.64) + 0.12, 0.3)
cue("whoosh", out(33.94) + 0.12, 0.3)
cue("whoosh", B["broll-founders"][0] + 1.12, 0.35)
cue("whoosh", out(30.32) + 0.04, 0.4)

def font_size(group):
    """Largest size that keeps the group on one line, else on two lines, inside the box."""
    widths = [
        word_em(t) * (POWER if style.rstrip("!") else 1) + (0.32 if style.endswith("!") else 0)
        for t, _, style in group
    ]
    one_line = MAX_LINE / (sum(widths) + WORD_GAP * (len(widths) - 1))
    if one_line >= 118 or len(widths) == 1:
        return int(min(190, one_line, BOX_H / POWER))
    two_lines = MAX_LINE / max(widths)
    return int(min(BOX_H / (2 * POWER), two_lines))


def build():
    seg_html = []
    for i, ((a, b), o) in enumerate(zip(SEGMENTS, SEG_OUT)):
        # 1 ms short of the next cut so adjacent clips never overlap on the audio track.
        dur = round(SEG_FRAMES[i] / FPS - 0.001, 4)
        fade = 0.03
        lane = {
            "version": 1,
            "lanes": [
                {
                    "target": "volume",
                    "points": [
                        {"t": 0, "v": 0},
                        {"t": fade, "v": 1},
                        {"t": round(dur - fade, 3), "v": 1},
                        {"t": dur, "v": 0},
                    ],
                }
            ],
        }
        seg_html.append(
            f'          <video id="seg-{i + 1}" class="clip seg" src="assets/footage.mp4" '
            f'data-start="{o}" data-duration="{dur}" data-media-start="{a}" data-track-index="0" '
            f"data-automation='{json.dumps(lane, separators=(',', ':'))}' playsinline data-has-audio=\"true\"></video>"
        )

    broll_html = []
    for k, (cid, s, e) in enumerate(BROLL):
        broll_html.append(
            f'      <div id="{cid}-host" class="broll" data-composition-id="{cid}" '
            f'data-composition-src="compositions/{cid}.html" data-start="{round(s, 3)}" '
            f'data-duration="{round(e - s, 3)}" data-track-index="{2 + k}" data-width="{W}" data-height="{H}"></div>'
        )

    cap_html = []
    cap_events = []  # (group id, start, end, [(word id, start, style)])
    for gi, group in enumerate(GROUPS):
        start = out(group[0][1])
        if gi in GROUP_UNTIL:
            end = out(GROUP_UNTIL[gi])
        elif gi + 1 < len(GROUPS):
            end = out(GROUPS[gi + 1][0][1])
        else:
            end = DURATION
        words = []
        spans = []
        for wi, (text, src, style) in enumerate(group):
            wid = f"w{gi}-{wi}"
            cls = "w"
            circled = style.endswith("!")
            color = style.rstrip("!")
            if color:
                cls += f" {color}"
            if circled:
                cls += " ringed"
            ring = ""
            if circled:
                ring = (
                    '<svg class="ring" viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">'
                    '<path d="M 22 7 C 58 1, 95 8, 97 20 C 99 31, 74 38, 44 37 C 16 36, 2 29, 3 19 C 4 10, 22 4, 52 4.5" /></svg>'
                )
            spans.append(f'<span id="{wid}" class="{cls}">{html.escape(text)}{ring}</span>')
            words.append((wid, out(src), color, circled))
        cap_html.append(
            f'        <div id="cap-{gi}" class="cap" style="font-size: {font_size(group)}px">{"".join(spans)}</div>'
        )
        cap_events.append((f"cap-{gi}", start, end, words))

    sfx_html = []
    for i, (src, start, dur, mstart, vol) in enumerate(sorted(SFX, key=lambda c: c[1])):
        attrs = f'id="sfx-{i + 1}" class="clip" src="{src}" data-start="{start}" data-track-index="{100 + i}"'
        if mstart:
            attrs += f' data-media-start="{mstart}"'
        if dur:
            # Trimmed cue: fade the cut edge out through the volume lane (which carries the level).
            lane = {
                "version": 1,
                "lanes": [
                    {
                        "target": "volume",
                        "points": [
                            {"t": 0, "v": vol},
                            {"t": round(dur - 0.25, 3), "v": vol},
                            {"t": dur, "v": 0},
                        ],
                    }
                ],
            }
            attrs += f' data-duration="{dur}" data-automation=\'{json.dumps(lane, separators=(",", ":"))}\''
        else:
            attrs += f' data-volume="{vol}"'
        sfx_html.append(f"      <audio {attrs}></audio>")

    nc_words = [(f"nc-{i}", out(src), style) for i, (_, src, style) in enumerate(NAMECARD)]
    nc_spans = "".join(
        f'<span id="{wid}" class="nc-w{(" " + style) if style else ""}">{html.escape(NAMECARD[i][0])}</span>'
        for i, (wid, _, style) in enumerate(nc_words)
    )

    # Camera events in output time.
    cam_sets = []
    for i, o in enumerate(SEG_OUT):
        end = SEG_OUT[i + 1] if i + 1 < len(SEG_OUT) else DURATION
        cam_sets.append((o, CAM_BASE[i], CAM_DRIFT.get(i), round(end - o, 3)))
    punches = [(out(src), s, shake) for src, s, shake in PUNCHES]

    data = {
        "duration": DURATION,
        "caps": [
            {"id": g, "start": s, "end": e, "words": [{"id": w, "t": t, "c": c, "ring": r} for w, t, c, r in ws]}
            for g, s, e, ws in cap_events
        ],
        "cam": [{"t": t, "s": s, "drift": d, "dur": dur} for t, s, d, dur in cam_sets],
        "punches": [{"t": t, "s": s, "shake": sh} for t, s, sh in punches],
        "brollIn": [round(s, 3) for _, s, _ in BROLL],
        "namecard": {"in": round(out(30.32) + 0.04, 3), "words": [{"id": w, "t": t} for w, t, _ in nc_words]},
        "rip": RIP_START,
    }

    page = TEMPLATE
    page = page.replace("__DURATION__", str(DURATION))
    page = page.replace("__SEGMENTS__", "\n".join(seg_html))
    page = page.replace("__BROLL__", "\n".join(broll_html))
    page = page.replace("__RIP_START__", str(round(RIP_START, 3)))
    page = page.replace("__RIP_DUR__", str(RIP_DUR))
    page = page.replace("__CAPTIONS__", "\n".join(cap_html))
    page = page.replace("__SFX__", "\n".join(sfx_html))
    page = page.replace("__NAMECARD__", nc_spans)
    page = page.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    (ROOT / "index.html").write_text(page, encoding="utf-8")
    print(f"index.html written: {DURATION}s, {len(SEGMENTS)} cuts, {len(GROUPS)} caption groups")
    for cid, s, e in BROLL:
        print(f"  {cid}: {s:.2f} -> {e:.2f}")
    print(f"  paper rip: {RIP_START:.2f} -> {RIP_START + RIP_DUR:.2f}")
    print(f"  {len(SFX)} sound effects")


TEMPLATE = r"""<!doctype html>
<!--
  Viplav the Coach: "Your business has outgrown you" reel.
  Generated by tools/build_index.py from the edit decision list there; re-running it
  overwrites this file.
-->
<html lang="en" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      /* Montserrat Black ships with HyperFrames; this face only adds the rupee sign. */
      @font-face {
        font-family: "Montserrat Rupee";
        src: url("assets/fonts/montserrat-latin-ext-900-normal.woff2") format("woff2");
        font-weight: 900;
        unicode-range: U+20B9;
      }
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      html,
      body {
        margin: 0;
        width: 1080px;
        height: 1920px;
        overflow: hidden;
        background: #0c0c0f;
      }
      #root {
        position: relative;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: #0c0c0f;
        font-family: "Montserrat Rupee", "Montserrat", sans-serif;
      }
      #cam-shake {
        position: absolute;
        inset: 0;
        z-index: 1;
      }
      #cam {
        position: absolute;
        inset: 0;
        transform-origin: 50% 26%;
      }
      .seg {
        position: absolute;
        left: 0;
        top: 0;
        width: 1080px;
        height: 1920px;
        object-fit: cover;
      }
      .broll {
        position: absolute;
        inset: 0;
        z-index: 5;
      }
      #rip-host {
        position: absolute;
        inset: 0;
        z-index: 8;
      }
      #flash {
        position: absolute;
        inset: 0;
        z-index: 10;
        background: #ffffff;
        opacity: 0;
      }
      #vignette {
        position: absolute;
        inset: 0;
        z-index: 2;
        background: linear-gradient(180deg, rgba(0, 0, 0, 0) 45%, rgba(0, 0, 0, 0.45) 100%);
      }
      #caps {
        position: absolute;
        inset: 0;
        z-index: 20;
      }
      .cap {
        position: absolute;
        left: 50px;
        right: 50px;
        top: 1090px;
        height: 300px;
        display: flex;
        flex-wrap: wrap;
        align-content: center;
        align-items: center;
        justify-content: center;
        column-gap: 0.24em;
        row-gap: 0.02em;
        font-weight: 900;
        line-height: 1;
        letter-spacing: -0.02em;
        text-align: center;
        opacity: 0;
      }
      .w {
        position: relative;
        display: inline-block;
        color: #ffffff;
        -webkit-text-stroke: 0.1em #000000;
        paint-order: stroke fill;
        text-shadow: 0 0.07em 0 rgba(0, 0, 0, 0.85);
        white-space: nowrap;
      }
      .w.y {
        color: #ffe11a;
        font-size: 1.12em;
      }
      .w.r {
        color: #ff2b2b;
        font-size: 1.12em;
      }
      .w.ringed {
        margin: 0 0.12em 0 0.2em;
      }
      .ring {
        position: absolute;
        left: -16%;
        top: -34%;
        width: 132%;
        height: 168%;
        overflow: visible;
      }
      .ring path {
        fill: none;
        stroke: #ff2b2b;
        stroke-width: 3.2;
        stroke-linecap: round;
        stroke-linejoin: round;
      }
      #namecard-wrap {
        position: absolute;
        left: 0;
        right: 0;
        top: 1420px;
        height: 170px;
        z-index: 15;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      #namecard {
        display: flex;
        align-items: center;
        gap: 0.28em;
        padding: 26px 54px 30px;
        background: #f6f1e7;
        color: #0c0c0f;
        font-weight: 900;
        font-size: 84px;
        line-height: 1;
        letter-spacing: -0.02em;
        clip-path: polygon(0% 6%, 7% 0%, 18% 4%, 31% 1%, 44% 5%, 57% 0%, 70% 4%, 83% 1%, 94% 5%, 100% 1%, 99% 52%, 100% 96%, 90% 100%, 76% 95%, 63% 100%, 50% 96%, 36% 100%, 22% 95%, 10% 100%, 0% 95%, 1% 50%);
        box-shadow: 0 12px 0 rgba(0, 0, 0, 0.35);
      }
      .nc-w {
        display: inline-block;
      }
      .nc-w.r {
        color: #ff2b2b;
      }
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="__DURATION__"
      data-width="1080"
      data-height="1920"
      data-fps="30"
    >
      <div id="cam-shake">
        <div id="cam">
__SEGMENTS__
        </div>
      </div>
      <div id="vignette"></div>

__BROLL__

      <div
        id="rip-host"
        data-composition-id="torn-paper-rip"
        data-composition-src="compositions/components/torn-paper-rip.html"
        data-start="__RIP_START__"
        data-duration="__RIP_DUR__"
        data-track-index="7"
        data-variable-values='{"direction":"left-to-right","tone":"white","roughness":62}'
      ></div>

      <div id="flash"></div>

      <div id="namecard-wrap">
        <div id="namecard">__NAMECARD__</div>
      </div>

      <div id="caps">
__CAPTIONS__
      </div>

      <!-- Sound effects -->
__SFX__
    </div>

    <!-- Paper-rip slots: tear a still of the READY B-roll away, revealing the speaker underneath. -->
    <template data-slot="torn-paper-rip-from"><img src="assets/ready-endframe.png" alt="" /></template>
    <template data-slot="torn-paper-rip-to"><div></div></template>

    <script>
      (function () {
        const EDL = __DATA__;
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
              gsap.set(path, { strokeDasharray: len, strokeDashoffset: len });
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
        const flashes = EDL.brollIn
          .concat([EDL.rip])
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
        function camScale(t) {
          let seg = EDL.cam[0];
          for (const c of EDL.cam) if (c.t <= t + 1e-6) seg = c;
          const segEnd = seg.t + seg.dur;
          let fn = function (x) {
            if (!seg.drift) return seg.s;
            const k = Math.min(1, Math.max(0, (x - seg.t) / seg.dur));
            return seg.s + (seg.drift - seg.s) * sineInOut(k);
          };
          for (const p of EDL.punches) {
            if (p.t < seg.t - 1e-6 || p.t >= segEnd - 1e-6 || p.t > t) continue;
            const prev = fn;
            const from = prev(p.t);
            fn = function (x) {
              if (x < p.t) return prev(x);
              return from + (p.s - from) * easeOut3(Math.min(1, (x - p.t) / PUNCH_IN));
            };
          }
          return fn(t);
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
        const camShake = document.getElementById("cam-shake");
        const flash = document.getElementById("flash");
        const clock = { t: 0 };
        function paintCamera() {
          const t = clock.t;
          gsap.set(cam, { scale: camScale(t) });
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
    </script>
  </body>
</html>
"""

if __name__ == "__main__":
    build()
