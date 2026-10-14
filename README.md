# boywithfashion

Video editing with [HyperFrames](https://github.com/heygen-com/hyperframes): videos are
HTML compositions that render to MP4 with headless Chrome and FFmpeg.

## Layout

- `videos/` — one HyperFrames project per video. `videos/starter` is a 1080×1920 (portrait)
  starter with an animated title.
- `.claude/skills/` — the HyperFrames agent skills (v0.8.157), committed so every
  Claude Code session has them. `skills-lock.json` records where they came from.
- `.claude/hooks/session-start.sh` — in Claude Code cloud sessions, points HyperFrames at
  the preinstalled Chrome headless shell and pre-fetches the CLI.

## Editing with Claude Code

Ask for what you want and mention `/hyperframes`, which routes to the right workflow:

- "Using /hyperframes, add captions to this clip" → `/embedded-captions`
- "Using /hyperframes, add titles and callouts to my talking-head video" → `/talking-head-recut`
- "Using /hyperframes, cut these outfit clips to the beat of this track" → `/music-to-video`
- "Using /hyperframes, make a 6-second logo sting" → `/motion-graphics`
- Anything else → `/general-video`

Your own footage and audio go in the project's `assets/` folder.

## CLI

Requires Node.js 22+ and FFmpeg.

```bash
cd videos/starter
npm run dev       # live preview in the browser
npm run check     # lint + runtime, layout, motion and contrast checks
npm run render    # render to renders/<name>.mp4
```

New project: `cd videos && npx hyperframes@0.8.157 init my-video --resolution portrait`
(use `--video path/to/clip.mp4` to start from footage).

## Cloud-session network access

Compositions load GSAP from `cdn.jsdelivr.net`, and transcription downloads Whisper models
from `huggingface.co`. In a Claude Code cloud environment with limited network access, add
those hosts under the environment's Network access → Allowed domains, or renders fail with
`net::ERR_TUNNEL_CONNECTION_FAILED`.
