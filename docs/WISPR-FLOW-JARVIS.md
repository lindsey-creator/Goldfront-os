# Wispr Flow + JARVIS command line

**Wispr Flow** (sometimes spoken as “Whisper Flow”) is **OS-level voice dictation** on Lindsey’s **Revolution One** machine. It is **not** a Goldfront-os connector, Railway env var, or Brain API.

## How it fits Jarvis on Railway

- **Jarvis** = the Command Center in the browser at `https://jarvis-brain-production-8def.up.railway.app` (Brain + UI on Railway).
- **Iron Man voice** = put the text cursor in the **JARVIS command line** in that UI, then dictate with **Wispr Flow** on the Mac.
- Wispr sends keystrokes/text into whatever field is focused — same as typing, but spoken.

## What we do not do

- No `WISPR_*` secrets on Railway.
- No server-side speech-to-text in the Brain for this path (unless a future explicit product decision adds one).
- Do not treat Wispr as a second “chief” — it is input hardware for the sole Jarvis glass.

## Quick workflow

1. Open Jarvis in the browser (Railway URL).
2. Click into the command / chat input at the bottom of the HUD.
3. Activate Wispr Flow dictation on the Mac.
4. Speak; review text in the field; submit as usual (human gate on sends unchanged).

## Lock

Per operating lock: Wispr lives on **Revolution One**, not on Manus hosting and not inside the Docker image.
