#!/bin/zsh
# Screenshot only the VVD's TV picture (works even when other windows cover it): shot.sh out.png [width=1280]
WID=$(osascript -l JavaScript -e 'ObjC.import("CoreGraphics"); var l=ObjC.deepUnwrap(ObjC.castRefToObject($.CGWindowListCopyWindowInfo(0,0))); var w=l.find(w=>w.kCGWindowName=="Vega Virtual Device"); w?w.kCGWindowNumber:""')
[ -n "$WID" ] || { echo "VVD window not found"; exit 1; }
T=$(mktemp -t vvd).png
screencapture -x -o -l$WID $T && ffmpeg -v error -y -i $T -vf "crop=trunc((ih-56)*16/9/2)*2:ih-56:0:56,scale=${2:-1280}:-2" "$1"; rm -f $T
