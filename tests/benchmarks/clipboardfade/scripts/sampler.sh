#!/bin/bash
# Sampler: logs battery, /proc/stat busy, k10temp, and per-process counters of
# any running probe_bench (utime/stime, QSGRenderThread utime/stime,
# drm-engine-gfx). Usage: sampler.sh OUT.csv [INTERVAL_S]
OUT=$1
IV=${2:-0.5}
BAT=/sys/class/power_supply/BAT0
K10=$(grep -l k10temp /sys/class/hwmon/hwmon*/name 2>/dev/null | head -1 | xargs -r dirname)/temp1_input
echo "ts,charge,volt,current,cpu_busy,utime,stime,qsg_utime,qsg_stime,engine_gfx" > "$OUT"
end=$((SECONDS + 1200))
while [ "$SECONDS" -lt "$end" ]; do
    ts=$(date +%s.%N)
    c=$(cat "$BAT/charge_now" 2>/dev/null || echo NA)
    v=$(cat "$BAT/voltage_now" 2>/dev/null || echo NA)
    cur=$(cat "$BAT/current_now" 2>/dev/null || echo NA)
    busy=$(grep '^cpu ' /proc/stat | awk '{print $2+$3+$4+$6+$7+$8}')
    temp=$(cat "$K10" 2>/dev/null || echo NA)
    ut=NA; st=NA; qut=NA; qst=NA; eng=NA
    BPID=$(pgrep -x clipfadebench | head -1)
    [ -n "$BPID" ] || BPID=$(pgrep -x probe_bench | head -1)
    if [ -n "$BPID" ]; then
        # strip "(comm)" -> utime=field 13, stime=field 14
        line=$(sed 's/(.*) //' "/proc/$BPID/stat" 2>/dev/null)
        ut=$(echo "$line" | awk '{print $13}')
        st=$(echo "$line" | awk '{print $14}')
        qut=0; qst=0
        for t in /proc/$BPID/task/*; do
            comm=$(cat "$t/comm" 2>/dev/null)
            if [ "$comm" = "QSGRenderThread" ]; then
                line=$(sed 's/(.*) //' "$t/stat" 2>/dev/null)
                qut=$(echo "$line" | awk '{print $14}')
                qst=$(echo "$line" | awk '{print $15}')
            fi
        done
        for fdlink in /proc/$BPID/fd/*; do
            if readlink "$fdlink" 2>/dev/null | grep -q renderD128; then
                eng=$(grep 'drm-engine-gfx:' "/proc/$BPID/fdinfo/$(basename "$fdlink")" 2>/dev/null | awk '{print $2}')
                break
            fi
        done
    fi
    echo "$ts,$c,$v,$cur,$busy,$ut,$st,$qut,$qst,${eng:-NA}" >> "$OUT"
    sleep "$IV"
done
