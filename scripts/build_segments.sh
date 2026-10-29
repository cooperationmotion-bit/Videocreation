#!/usr/bin/env bash
# Cut, reframe (9:16, 1080x1920, 30fps) and colour grade every segment of the reel.
# Usage: build_segments.sh <raw_dir> <out_dir>
#   raw_dir must contain A.mov (class / loaded straddle), B.mov (HLG seated straddle),
#   C.mov (60fps kettlebell 90/90).
set -euo pipefail
RAW=$1
OUT=$2
mkdir -p "$OUT"

# Low-key cinematic grade (after the reference): dark, rolled-off highlights,
# teal-green cast in shadows/highlights, warm skin kept, greens killed, light vignette, fine grain.
GRADE="huesaturation=saturation=-0.6:colors=g+y:strength=1,\
eq=contrast=1.12:saturation=0.78:gamma=0.93,\
curves=master='0/0.03 0.3/0.18 0.6/0.47 0.85/0.70 1/0.80',\
colorbalance=rs=-0.07:gs=0.015:bs=0.035:rm=-0.03:gm=0.025:bm=0.0:rh=-0.02:gh=0.05:bh=0.01,\
vignette=PI/7,noise=alls=7:allf=t,format=yuv420p"

# Per-clip reframing / normalisation
pre() {
  case $1 in
    # crop out the burned-in caption at the bottom of A, keep 9:16
    A) echo "crop=612:1088:54:20,scale=1080:1920:flags=lanczos" ;;
    # HLG 10-bit -> SDR bt709
    B) echo "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,scale=1080:1920:flags=lanczos" ;;
    C) echo "scale=1080:1920:flags=lanczos" ;;
  esac
}

# id clip src_start out_duration speed(1 = realtime, 0.5 = half speed)
SEGMENTS="
01 C 0.0 4.8 0.5
02 A 1.6 2.4 1
03 A 5.0 2.4 1
04 C 3.0 2.4 0.5
05 B 0.0 4.8 1
06 C 7.0 2.4 0.5
07 A 11.0 2.4 1
08 A 15.2 2.4 1
09 B 9.0 2.4 1
10 B 13.6 2.4 1
"

echo "$SEGMENTS" | while read -r id clip ss dur speed; do
  [ -z "$id" ] && continue
  src_dur=$(python3 -c "print($dur*$speed+0.1)")
  pts=$(python3 -c "print(1/$speed)")
  ffmpeg -nostdin -v error -y -ss "$ss" -t "$src_dur" -i "$RAW/$clip.mov" -an \
    -vf "$(pre "$clip"),setpts=$pts*(PTS-STARTPTS),fps=30,trim=duration=$dur,setsar=1,$GRADE" \
    -c:v libx264 -preset slow -crf 12 "$OUT/seg$id.mp4"
  echo "seg$id done"
done
