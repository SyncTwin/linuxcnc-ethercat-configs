#!/bin/bash
# Прогон тест-кейсов «HAL против CODESYS» в halrun.
#
# Каждый кейс — самодостаточный .hal, исполняемый в halrun без LinuxCNC.
# Выхлоп сохраняется целиком: он и есть доказательство, читать глазами.
set -u
cd "$(dirname "$0")"

# Гейт: halrun поднимает свой HAL и снимает realtime за собой. Если на стенде
# сейчас работает LinuxCNC, прогон убьёт живой контур — отказываем до запуска.
if pgrep -x linuxcnc >/dev/null || pgrep -x milltask >/dev/null || pgrep -x rtapi >/dev/null; then
    echo "ОТКАЗ: на этой машине поднят LinuxCNC. Прогон снял бы живой HAL." >&2
    exit 2
fi

mkdir -p results
pass=0; fail=0
for f in [0-9]*.hal; do
    name="${f%.hal}"
    printf '=== %-24s ' "$name"
    if timeout 30 halrun -f "$f" > "results/$name.log" 2>&1; then
        echo "OK   (results/$name.log)"; pass=$((pass+1))
    else
        echo "FAIL (results/$name.log)"; fail=$((fail+1))
    fi
    halrun -U >/dev/null 2>&1   # снять остатки realtime, если кейс упал
done
echo "---"
echo "прогнано: $((pass+fail)), поднялось: $pass, отказ: $fail"
echo "версия LinuxCNC: $(halcmd -s version 2>/dev/null || echo '?')"
echo "ядро: $(uname -r)"
