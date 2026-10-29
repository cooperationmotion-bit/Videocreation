# Mobility × Strength — Instagram Reel

`output/mobility-x-strength-reel.mp4` — 1080×1920, 30 fps, 31.2 s, H.264 + AAC (-14 LUFS).
`output/darkwave-bed.wav` — the original music bed on its own (100 BPM, A minor).

## Rebuild
Put the source clips in a folder as `A.mov` (class / loaded straddle), `B.mov` (seated straddle, HLG),
`C.mov` (kettlebell 90/90, 60 fps), then:

```bash
pip install scipy numpy pillow
bash scripts/build_segments.sh <raw_dir> <seg_dir>      # cut, reframe 9:16, grade
python3 scripts/make_music.py <music.wav>               # synthesise darkwave bed
python3 scripts/compose.py <seg_dir> <music.wav> out.mp4  # type + music + encode
```

Cuts, timings and copy live in `SEGMENTS` (build_segments.sh) and `CUES` (compose.py).
