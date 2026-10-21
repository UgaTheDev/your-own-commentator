# Record the VVD's own display through its emulator console (port 5554): 1920x1080 + app audio, unaffected by
# other windows covering the VVD (window capture dropped to <1 fps when covered). Max 180 s per file.
# Usage (sourced): erec_start <abs file.webm> [secs]; erec_stop
econ() { (sleep 0.4; echo "auth $(cat ~/.emulator_console_auth_token)"; sleep 0.4; echo "$1"; sleep 0.6; echo quit) | nc 127.0.0.1 5554 >/dev/null; }
erec_start() { rm -f "$1"; econ "screenrecord start --fps 30 --bit-rate 12M --time-limit ${2:-180} $1"; }
erec_stop() { econ "screenrecord stop"; sleep 2; }   # the emulator finalizes the webm after stop
