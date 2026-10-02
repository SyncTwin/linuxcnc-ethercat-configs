# SFC на HAL: учебные задачи автоматики без ПЛК

Четыре классические задачи SFC (МЭК 61131-3), каждая исполняется штатным `halrun` из пакета
`linuxcnc-uspace`: без LinuxCNC motion, без станка, без нашего кода. Шаги и переходы считает
ClassicLadder (`classicladder_rt`) в потоке HAL с периодом 1 мс.

| папка | задача | что показывает |
|---|---|---|
| [`traffic_light/`](traffic_light/) | светофор | три шага по таймерам, время шага — живая ручка, удержание |
| [`tank/`](tank/) | бак: налить, перемешать, слить | фронт кнопки, датчики уровня в переходах, таймер шага |
| [`sorter/`](sorter/) | сортировка с корзиной брака | две развилки выбора, счётчик CTU |
| [`feeder/`](feeder/) | питатель с осью | `MC_MoveAbsolute` на оси-заглушке из штатных компонентов, `Done` по фронту |

В каждой папке одно и то же:

- `<имя>.sfc` — программа текстом SFC, её пишет автор;
- `<имя>.clp` — та же программа в формате ClassicLadder (Grafcet + рунги). Файл напечатан нашим
  генератором из `.sfc`; генератор здесь не публикуется. Это обычный `.clp`, его можно открыть
  в редакторе `classicladder <имя>.clp` и править руками;
- `<имя>.hal` — поток, загрузка ClassicLadder, проводка входов и выходов;
- `run_demo.hal` — сценарий прогона, входы ставятся руками командой `sets`;
- `run-log.txt` — настоящий вывод `halrun -f run_demo.hal`.

## Как запустить

```bash
sudo apt install linuxcnc-uspace
git clone https://github.com/SyncTwin/linuxcnc-ethercat-configs
cd linuxcnc-ethercat-configs/sfc-on-hal/traffic_light
halrun -f run_demo.hal
```

В Docker (под `root` `halrun` без этих переменных не стартует):

```bash
cd linuxcnc-ethercat-configs
docker run --rm -v "$PWD":/w -w /w debian:12 bash -c '
  apt-get update -qq && apt-get install -y -qq --no-install-recommends linuxcnc-uspace >/dev/null
  export RTAPI_UID=1000 RTAPI_FIFO_PATH=/tmp/.rtapi_fifo
  cd sfc-on-hal/traffic_light && halrun -f run_demo.hal'
```

## Общие пределы ClassicLadder

- Шагов и переходов на программу — не больше констант сборки `sequential.h`
  (128 и 256 в LinuxCNC 2.9), это не параметр `loadrt`.
- Таймер `%T` старого типа с основой 100 мс: точность — 100 мс, а не такт потока.
- Арифметика внутри ClassicLadder целочисленная.
- Удержанных переменных (retain), online change и отладчика шагов нет.
  Программа меняется перезагрузкой `.clp`.
- Массивы пинов `numS32in`, `numS32out`, `numFloatIn`, `numFloatOut` должны быть не меньше 1:
  с нулём `classicladder_rt` роняет HAL на первом такте (Debian 12, `linuxcnc-uspace`
  2.9.0~pre1, 02.10.2026).
- Прогоны сняты без RT-ядра: они доказывают логику последовательности, а не джиттер.

Строительные блоки по отдельности (TON, TOF, R_TRIG, CTU, PID, watchdog и другие) —
18 кейсов в соседней папке [`../hal-plc-testcases/`](../hal-plc-testcases/).

## Лицензия

GPL-2.0, как и остальные файлы репозитория.
