#!/usr/bin/env bash
# Cut, reframe (9:16, 1080x1920, 30fps) and colour grade every segment of the reel.
# Usage: build_segments.sh <raw_dir> <out_dir>
#   raw_dir must contain A.mov (class / loaded straddle), B.mov (HLG seated straddle),
#   C.mov (60fps kettlebell 90/90).
set -euo pipefail
RAW=$1
OUT=$2
mkdir -p "$OUT"

# Minimal cinematic grade: muted saturation, lifted/cool matte blacks,
# warm-neutral highlights with a soft roll-off, greens pulled way down, gentle vignette.
GRADE="huesaturation=hue=0:saturation=-0.55:intensity=-0.04:colors=g+y:strength=1,\
eq=contrast=1.07:saturation=0.70:gamma=0.97,\
curves=r='0/0.04 0.25/0.21 0.5/0.49 0.8/0.84 1/0.95':g='0/0.045 0.25/0.22 0.5/0.49 0.8/0.83 1/0.94':b='0/0.065 0.25/0.245 0.5/0.5 0.8/0.81 1/0.92',\
colorbalance=rs=-0.03:bs=0.04:rh=0.03:bh=-0.03,\
vignette=PI/5,noise=alls=7:allf=t,format=yuv420p"

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
