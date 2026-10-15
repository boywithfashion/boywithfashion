#!/usr/bin/env python3
"""Generate index.html for the Viplav "outgrown" reel from one edit decision list.

Everything time-based lives in the tables below: the kept source ranges of the raw
take (jump cuts that drop the dead air), the word timings from the transcript, the
caption phrases, punch-ins, graphic slots, sound effects and the music bed. Output
times are derived, never typed twice, so changing a cut keeps everything in sync.

Re-running this script overwrites index.html; edits made in Studio to index.html
are lost unless they are carried back into these tables.

    python3 tools/build_index.py
"""

import html
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
W, H = 1080, 1920

# Kept source ranges of assets/footage.mp4 (seconds). Pauses between them are cut, with
# a little extra air left after each sentence so the pacing breathes.
SEGMENTS = [
    (0.90, 3.72),  # Your business has outgrown you.
    (3.98, 7.22),  # The skills that build a 5 crore business
    (7.53, 13.24),  # won't build a 50 crore business. Different scales of business, different challenges,
    (13.58, 15.60),  # different leader qualities.
    (15.95, 18.05),  # The business is ready.
    (18.76, 21.35),  # The question is: are you?
    (22.86, 28.95),  # Businesses grow only when the founders grow.  (+ a held beat for the chart)
    (30.32, 31.92),  # Viplav the Coach
    (32.22, 35.15),  # jo badal de aapki soch  (ends before the next breath)
]

# Output start of each segment, on the 30 fps frame grid so every cut lands on a frame.
# Times are floored to 4 decimals so a clip never starts after the frame it must cover
# (rounding up left one black frame at a cut).
SEG_FRAMES = [round((b - a) * FPS) for a, b in SEGMENTS]


def frame_time(f):
    return math.floor(f / FPS * 10000) / 10000


SEG_OUT = []
_f = 0
for n in SEG_FRAMES:
    SEG_OUT.append(frame_time(_f))
    _f += n
DURATION = frame_time(_f)


def out(src):
    """Map a source time to output time through the segment that contains it."""
    for (a, b), o in zip(SEGMENTS, SEG_OUT):
        if a - 0.05 <= src <= b + 0.05:
            return round(o + (src - a), 3)
    raise ValueError(f"source time {src} falls in a cut")


# Caption phrases: 3-5 words on screen, each word highlighted as it is spoken.
# Each word is (text, source start, style): "" stays white after it is spoken, "y" stays
# yellow and "r" stays red (power words); a trailing "!" draws a red circle around it.
# Word starts were checked against the audio (ASR timestamps were off on a few words).
PHRASES = [
    [("YOUR", 0.96, ""), ("BUSINESS", 1.28, ""), ("HAS", 1.98, ""), ("OUTGROWN", 2.32, "y"), ("YOU.", 3.03, "r")],
    [("THE", 4.08, ""), ("SKILLS", 4.24, "y"), ("THAT", 4.96, ""), ("BUILD", 5.36, "")],
    [("A", 5.55, ""), ("₹5 CRORE", 5.76, "y"), ("BUSINESS", 6.56, "")],
    [("WON'T", 7.56, "r"), ("BUILD", 7.92, ""), ("A", 8.16, ""), ("₹50 CRORE", 8.24, "r"), ("BUSINESS.", 9.00, "")],
    [("DIFFERENT", 10.00, ""), ("SCALES", 10.40, "y"), ("OF", 10.88, ""), ("BUSINESS,", 11.04, "")],
    [("DIFFERENT", 11.84, ""), ("CHALLENGES,", 12.16, "r")],
    [("DIFFERENT", 13.68, ""), ("LEADER", 14.00, "y"), ("QUALITIES.", 14.64, "y")],
    [("THE", 16.00, ""), ("BUSINESS", 16.24, ""), ("IS", 17.04, ""), ("READY.", 17.36, "y")],
    [("THE", 18.80, ""), ("QUESTION", 19.12, ""), ("IS:", 19.60, ""), ("ARE", 20.09, ""), ("YOU?", 20.41, "r!")],
    [("BUSINESSES", 22.88, ""), ("GROW", 23.92, "y"), ("ONLY", 24.65, "")],
    [("WHEN", 25.36, ""), ("THE", 25.68, ""), ("FOUNDERS", 25.90, "y"), ("GROW.", 26.87, "y")],
    # 30.40-31.80 "Viplav the Coach" is carried by the name card.
    [("JO", 32.34, ""), ("BADAL", 32.60, "y"), ("DE", 32.96, ""), ("AAPKI", 33.34, ""), ("SOCH", 33.57, "y!")],
]
# A phrase stays up until the next one starts, but never more than this after its last word.
PHRASE_TAIL = 1.5
CAPTION_SIZE = 76  # px; the longest phrase fits two lines at this size

# Name card (shown from the "Viplav the Coach" line to the end).
NAMECARD = [("VIPLAV", ""), ("THE", ""), ("COACH", "r")]

# Full-screen graphics (sub-compositions): (id, output start, output end). Only two, with
# room to read them; the crore chart fades itself out, the founders chart is torn away.
NAME_SEG = 7  # the "Viplav the Coach" segment
BROLL = [
    ("broll-crore", out(5.52), out(5.52) + 5.7),
    ("broll-founders", out(22.86), SEG_OUT[NAME_SEG]),
]
# The paper rip tears a still of the finished founders chart away, revealing the speaker.
RIP_START = SEG_OUT[NAME_SEG]
RIP_DUR = 1.25

# Camera: per segment a base framing (scale) applied at the cut and a slow drift to the
# segment's end; gentle punch-ins eased over `dur` seconds. Scale is around the face
# (transform-origin 50% 26%); dy (px, negative raises the picture) keeps the mouth clear of
# the captions on the closer shots.
CAM_BASE = [1.0, 1.08, 1.0, 1.1, 1.0, 1.06, 1.0, 1.08, 1.0]
CAM_DRIFT = {0: 1.05, 1: 1.12, 2: 1.05, 3: 1.14, 4: 1.06, 5: 1.12, 7: 1.11, 8: 1.05}
PUNCHES = [  # (source time, scale, dy px, ease duration s)
    (2.32, 1.12, 0, 0.7),  # OUTGROWN
    (3.03, 1.18, -40, 0.6),  # YOU.
    (14.00, 1.22, -20, 0.7),  # LEADER
    (17.36, 1.12, 0, 0.6),  # READY
    (20.41, 1.26, -120, 0.6),  # YOU?
    (33.57, 1.14, -60, 0.7),  # SOCH
]


# Sound effects: a few soft accents only (Pixabay-licensed library bundled with HyperFrames,
# plus the synthesized paper-rip.wav). Each cue is placed so the sound's own transient ("hit",
# seconds into the file) lands on the visual event, well under the voice.
B = {cid: (s, e) for cid, s, e in BROLL}
HIT = {"whoosh": 0.16, "impact-bass-1": 0.06, "paper-rip": 0.0}
SFX = []  # (file, start, duration or None, media start, volume)


def cue(name, event, vol, media_start=0.0, dur=None, hit=None):
    ext = "wav" if name == "paper-rip" else "mp3"
    h = HIT.get(name, 0.0) if hit is None else hit
    SFX.append((f"assets/sfx/{name}.{ext}", round(max(0.0, event - h), 3), dur, media_start, vol))


cue("whoosh", B["broll-crore"][0] + 0.1, 0.22)  # crore chart eases in
cue("error", B["broll-crore"][0] + 2.06, 0.6, media_start=0.55, dur=1.0, hit=0.05)  # cross on SAME SKILLS
cue("whoosh", B["broll-crore"][0] + 5.15, 0.16)  # crore chart fades out
cue("whoosh", B["broll-founders"][0] + 0.1, 0.22)  # founders chart eases in
cue("paper-rip", RIP_START + 0.04, 0.6)  # tear
cue("riser", out(20.41), 0.1, media_start=1.5, dur=2.0, hit=1.5)  # builds into "you?"
cue("impact-bass-1", out(20.41), 0.1, dur=0.9)  # soft hit on "you?"
cue("whoosh", RIP_START + 1.05, 0.18)  # name card slides up
cue("whoosh", out(33.57) + 0.15, 0.14)  # circle draws round SOCH

# Calm music bed (tools/make_bgm.py, -22 LUFS) under the whole reel.
BGM = "assets/music/calm-bed.m4a"


def ensure_bgm():
    """(Re)generate the bed when it is missing or no longer matches the reel's length."""
    path = ROOT / BGM
    if path.exists():
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True,
            text=True,
        )
        if abs(float(probe.stdout.strip() or 0) - DURATION) < 0.05:
            return
    subprocess.run(["python3", str(ROOT / "tools" / "make_bgm.py"), f"{DURATION:.3f}"], check=True)


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
            f"data-automation='{json.dumps(lane, separators=(',', ':'))}' data-audio-group=\"voiceover\" playsinline data-has-audio=\"true\"></video>"
        )

    broll_html = []
    for k, (cid, s0, e0) in enumerate(BROLL):
        broll_html.append(
            f'      <div id="{cid}-host" class="broll" data-composition-id="{cid}" '
            f'data-composition-src="compositions/{cid}.html" data-start="{round(s0, 3)}" '
            f'data-duration="{round(e0 - s0, 3)}" data-track-index="{2 + k}" data-width="{W}" data-height="{H}"></div>'
        )

    cap_html = []
    cap_events = []
    for gi, phrase in enumerate(PHRASES):
        start = out(phrase[0][1])
        last = out(phrase[-1][1])
        nxt = out(PHRASES[gi + 1][0][1]) if gi + 1 < len(PHRASES) else DURATION
        end = DURATION if gi + 1 == len(PHRASES) else min(nxt - 0.1, last + PHRASE_TAIL)
        spans = []
        words = []
        for wi, (text, src, style) in enumerate(phrase):
            wid = f"w{gi}-{wi}"
            circled = style.endswith("!")
            color = style.rstrip("!")
            ring = ""
            if circled:
                ring = (
                    '<svg class="ring" viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">'
                    '<path d="M 22 7 C 58 1, 95 8, 97 20 C 99 31, 74 38, 44 37 C 16 36, 2 29, 3 19 C 4 10, 22 4, 52 4.5" /></svg>'
                )
            cls = "w ringed" if circled else "w"
            spans.append(f'<span id="{wid}" class="{cls}">{html.escape(text)}{ring}</span>')
            t_on = out(src)
            # lit until the next word starts; the last word settles shortly after it is said
            t_off = out(phrase[wi + 1][1]) if wi + 1 < len(phrase) else min(end, t_on + 0.7)
            words.append({"id": wid, "on": t_on, "off": t_off, "c": color, "ring": circled})
        cap_html.append(f'        <div id="cap-{gi}" class="cap">{" ".join(spans)}</div>')
        cap_events.append({"id": f"cap-{gi}", "start": start, "end": end, "words": words})

    sfx_html = []
    for i, (src, start, dur, mstart, vol) in enumerate(sorted(SFX, key=lambda c: c[1])):
        attrs = (
            f'id="sfx-{i + 1}" class="clip" src="{src}" data-start="{start}" '
            f'data-track-index="{100 + i}" data-audio-group="sfx"'
        )
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
                            {"t": round(max(dur * 0.6, dur - 0.4), 3), "v": vol},
                            {"t": dur, "v": 0},
                        ],
                    }
                ],
            }
            attrs += f' data-duration="{dur}" data-automation=\'{json.dumps(lane, separators=(",", ":"))}\''
        else:
            attrs += f' data-volume="{vol}"'
        sfx_html.append(f"      <audio {attrs}></audio>")
    ensure_bgm()
    sfx_html.append(
        f'      <audio id="bgm" class="clip" src="{BGM}" data-start="0" data-duration="{DURATION}" '
        f'data-track-index="50" data-audio-group="music" data-volume="1"></audio>'
    )

    nc_spans = " ".join(
        f'<span class="nc-w{(" " + style) if style else ""}">{html.escape(text)}</span>' for text, style in NAMECARD
    )

    cam_sets = []
    for i, o in enumerate(SEG_OUT):
        end = SEG_OUT[i + 1] if i + 1 < len(SEG_OUT) else DURATION
        cam_sets.append({"t": o, "s": CAM_BASE[i], "drift": CAM_DRIFT.get(i), "dur": round(end - o, 3)})

    data = {
        "duration": DURATION,
        "caps": cap_events,
        "cam": cam_sets,
        "punches": [{"t": out(src), "s": sc, "dy": dy, "d": d} for src, sc, dy, d in PUNCHES],
        "namecard": {"in": round(RIP_START + 1.0, 3)},  # once the tear has cleared the frame
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
    page = page.replace("__CAPTION_SIZE__", str(CAPTION_SIZE))
    page = page.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    # The timeline script is maintained in tools/reel-timeline.js and inlined here, because the
    # composition must register window.__timelines inline.
    js = (ROOT / "tools" / "reel-timeline.js").read_text(encoding="utf-8")
    page = page.replace("__TIMELINE_JS__", "\n".join(("      " + l) if l else l for l in js.rstrip("\n").split("\n")))
    (ROOT / "index.html").write_text(page, encoding="utf-8")
    carve_bgm()
    print(f"index.html written: {DURATION}s, {len(SEGMENTS)} cuts, {len(PHRASES)} caption phrases")
    for cid, s0, e0 in BROLL:
        print(f"  {cid}: {s0:.2f} -> {e0:.2f}")
    print(f"  paper rip: {RIP_START:.2f} -> {RIP_START + RIP_DUR:.2f}")
    print(f"  {len(SFX)} sound effects")


CARVE_STRENGTH = 0.25  # gentle: room for the voice without the bed pumping


def carve_bgm():
    """Carve the music bed around the voice (HyperFrames voiceover carve) in index.html.

    Needs `npm install` in this project (for @hyperframes/core) and the repo's
    .claude/skills/hyperframes-audio skill; without them the bed plays uncarved.
    """
    script = ROOT.parent.parent / ".claude" / "skills" / "hyperframes-audio" / "scripts" / "carve.mjs"
    if not (ROOT / "node_modules" / "@hyperframes" / "core").exists() or not script.exists():
        print("  music carve skipped (run npm install)")
        return
    res = subprocess.run(
        ["node", str(script), "--comp", "index.html", "--bed", "bgm", "--strength", str(CARVE_STRENGTH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise SystemExit(f"music carve failed:\n{res.stdout}\n{res.stderr}")
    print(f"  music carved under the voice (strength {CARVE_STRENGTH})")


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
      #cam-wrap {
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
      /* Phrase captions: 3-5 words, one calm size, the spoken word lights up. */
      .cap {
        position: absolute;
        left: 70px;
        right: 70px;
        top: 1140px;
        height: 220px;
        display: flex;
        flex-wrap: wrap;
        align-content: center;
        align-items: center;
        justify-content: center;
        column-gap: 0.28em;
        row-gap: 0.06em;
        font-size: __CAPTION_SIZE__px;
        font-weight: 900;
        line-height: 1.08;
        letter-spacing: -0.01em;
        text-align: center;
        opacity: 0;
      }
      .w {
        position: relative;
        display: inline-block;
        color: #ffffff;
        -webkit-text-stroke: 0.045em rgba(0, 0, 0, 0.9);
        paint-order: stroke fill;
        text-shadow: 0 0.06em 0.22em rgba(0, 0, 0, 0.55);
        white-space: nowrap;
      }
      .w.ringed {
        margin: 0 0.1em 0 0.16em;
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
        stroke-width: 2.6;
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
        font-size: 72px;
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
      <div id="cam-wrap">
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

      <div id="namecard-wrap">
        <div id="namecard">__NAMECARD__</div>
      </div>

      <div id="caps">
__CAPTIONS__
      </div>

      <!-- Sound effects and the music bed -->
__SFX__
    </div>

    <!-- Paper-rip slots: tear a still of the finished founders chart away, revealing the speaker. -->
    <template data-slot="torn-paper-rip-from"><img src="assets/founders-endframe.png" alt="" /></template>
    <template data-slot="torn-paper-rip-to"><div></div></template>

    <script>
      window.REEL_EDL = __DATA__;
__TIMELINE_JS__
    </script>
  </body>
</html>
"""

if __name__ == "__main__":
    build()
