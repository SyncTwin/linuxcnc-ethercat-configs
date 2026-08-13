# Драйверы устройств для lcec: установка и настройка

Подробная инструкция: как поставить наши драйверы `linuxcnc-ethercat` (lcec),
подключить привод одной строкой вместо карты PDO и перевести на них уже
работающий конфиг.

Всё описанное снято с живого стенда, а не переписано из документации. Где
что-то не проверено — так и написано.

## Оглавление

1. [Какие драйверы есть](#1-какие-драйверы-есть)
2. [Что нужно до начала](#2-что-нужно-до-начала)
3. [Установка](#3-установка)
4. [Проверка, что приехал нужный модуль](#4-проверка-что-приехал-нужный-модуль)
5. [Минимальный конфиг](#5-минимальный-конфиг)
6. [Пины и привязка к оси](#6-пины-и-привязка-к-оси)
7. [Distributed Clocks](#7-distributed-clocks)
8. [Перевод существующего конфига с generic](#8-перевод-существующего-конфига-с-generic)
9. [Если не поднимается](#9-если-не-поднимается)
10. [Добавить свой привод](#10-добавить-свой-привод)

---

## 1. Какие драйверы есть

Ветка: <https://github.com/SyncTwin/linuxcnc-ethercat>, по ветке на вендора.

| драйвер | тип в XML | устройства | проверено |
|---|---|---|---|
| `lcec_inovance.c` | `IS620N`, `SV660` | Inovance IS620N, SV660 | IS620N доведён до `OP` на железе |
| `lcec_wecon.c` | `VD3E` | Wecon VD3E | доведён до `OP` на железе |
| `lcec_mitsubishi.c` | `MR-J4-TM` | Mitsubishi MR-J4 серии TM | опознан на шине, до `OP` НЕ доводили |
| `lcec_schneider.c` | `LXM28E` | Schneider Lexium 28 | опознан на шине, до `OP` НЕ доводили |

Последние два написаны по данным, снятым с живой шины, но проверить их до конца
нечем: на этих приводах нет моторов. В карточках устройств апстрима
(`documentation/devices/*.yml`) статус написан честно — по нему следующий
человек решает, доверять ли.

## 2. Что нужно до начала

- **LinuxCNC 2.9+** (uspace);
- **мастер EtherCAT IgH** — команда `ethercat master` отвечает;
- привод виден на шине:

```bash
ethercat slaves
# 3  0:3  PREOP  +  Wecon VD3E EtherCAT Servo v1.15
```

Если привода не видно — проблема не в драйвере, а в кабеле или мастере.
Драйвер тут ничем не поможет.

## 3. Установка

### Вариант А — собрать из исходников

**Заголовки обязаны совпадать по версии с установленным рантаймом.** Заголовок
из другой сборки хуже отсутствующего: соберётся, но работать не будет.

```bash
sudo apt-get install -y build-essential pkg-config git libexpat1-dev \
    libethercat-dev linuxcnc-uspace-dev
```

Проверьте, что версии сошлись:

```bash
dpkg -l libethercat-dev linuxcnc-uspace-dev | tail -2
ethercat version
```

Сборка (ветка `synctwin/bench` содержит все четыре драйвера сразу):

```bash
git clone -b synctwin/bench https://github.com/SyncTwin/linuxcnc-ethercat.git
cd linuxcnc-ethercat
make configure
make build
make test          # тесты апстрима, должны быть зелёными
```

Нужен драйвер только одного вендора — берите его ветку: `feat/wecon-vd3e`,
`feat/inovance-is620n-sv660`, `feat/mitsubishi-mr-j4`, `feat/schneider-lxm28e`.

### ⚠ Остановите LinuxCNC перед установкой

Подменять `lcec.so` под работающей машиной нельзя. Отказ выглядит не как
«файл занят», а как невнятная ошибка при следующем пуске.

```bash
pgrep -a linuxcncsvr && echo "LinuxCNC запущен — останавливать"
ethercat master | grep -E "Phase|Active"   # Operation / yes = шина занята
```

Когда свободно:

```bash
sudo make install
```

### Вариант Б — из нашего APT-репозитория

```bash
curl -fsSL https://synctwin.ru/apt/synctwin.gpg \
  | sudo tee /usr/share/keyrings/synctwin.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/synctwin.gpg] https://synctwin.ru/apt/ stable main" \
  | sudo tee /etc/apt/sources.list.d/synctwin.list
sudo apt-get update
sudo apt-get install -y linuxcnc-ethercat
```

Если пакет удерживается (`hold`), сначала снимите удержание:

```bash
sudo apt-mark unhold linuxcnc-ethercat
sudo apt-get install -y linuxcnc-ethercat
sudo apt-mark hold linuxcnc-ethercat
```

## 4. Проверка, что приехал нужный модуль

**Проверять по номеру версии недостаточно.** У нас был случай, когда apt
поставил чужой пакет и отчитался успехом: `dpkg` ранжирует snapshot-суффикс
(`1.42.2.g7fffa62-0`) **выше** обычной версии (`1.42.2-1+synctwin1`). Драйверов
в модуле не оказалось вовсе, а скрипт сказал «установлено».

Проверяйте по содержимому модуля:

```bash
strings /usr/lib/linuxcnc/modules/lcec.so | grep -xE "VD3E|IS620N|SV660|MR-J4-TM|LXM28E"
```

Пусто — приехала не та сборка, смотрите `apt-cache policy linuxcnc-ethercat`.

## 5. Минимальный конфиг

`ethercat-conf.xml`:

```xml
<masters>
  <master idx="0" appTimePeriod="1000000" refClockSyncCycles="-1">
    <slave idx="0" type="IS620N" name="x"/>
    <slave idx="1" type="IS620N" name="y"/>
    <slave idx="2" type="IS620N" name="z"/>
    <slave idx="3" type="VD3E" name="s"/>
  </master>
</masters>
```

- `idx` — позиция слейва в цепи, как в выводе `ethercat slaves`. Этим lcec
  сопоставляет конфиг с физическим прибором.
- `name` — имя, из которого строятся имена пинов (`lcec.0.x.*`). Задавайте
  всегда: без него подставляется номер, и при перестановке привода в цепи
  поедут все имена в HAL.
- `appTimePeriod` обязан совпадать с периодом servo-thread в `.ini`
  (1000000 нс = 1 кГц), иначе в лог пойдёт ошибка.

Карту PDO, лимиты записей и параметры DC драйвер знает сам.

## 6. Пины и привязка к оси

```bash
halcmd show pin lcec
```

| пин | что |
|---|---|
| `lcec.0.x.srv-target-position` | уставка позиции (CSP) |
| `lcec.0.x.srv-actual-position` | позиция с энкодера |
| `lcec.0.x.srv-actual-velocity` | скорость |
| `lcec.0.x.srv-actual-torque` | момент |
| `lcec.0.x.srv-actual-following-error` | отставание (**u32**) |
| `lcec.0.x.srv-cia-statusword` / `srv-cia-controlword` | слова состояния и команды |
| `lcec.0.x.srv-opmode` / `srv-opmode-display` | режим (8 = CSP, 9 = CSV) |
| `lcec.0.x.srv-supports-mode-csp` и родня | что привод объявил в `0x6502` |
| `lcec.0.x.slave-state-op` | слейв в `OP` |
| `lcec.0.all-op` | вся шина в `OP` |

Драйвер отдаёт сырые `statusword` и `controlword` — лесенку состояний CiA 402
он не крутит. Её по-прежнему ведёт компонент LinuxCNC `cia402.comp`:

```hal
loadrt cia402 count=4

net x-statusword       lcec.0.x.srv-cia-statusword  => cia402.0.statusword
net x-opmode-display   lcec.0.x.srv-opmode-display  => cia402.0.opmode-display
net x-drv-act-pos      lcec.0.x.srv-actual-position => cia402.0.drv-actual-position
net x-controlword      cia402.0.controlword         => lcec.0.x.srv-cia-controlword
net x-drv-target-pos   cia402.0.drv-target-position => lcec.0.x.srv-target-position
```

То есть драйвер отвечает за то, какие байты ездят по проводу, а `cia402.comp` —
за то, в каком состоянии привод и когда его включать. Одно другое не заменяет.

**Масштаб задаётся руками.** Некоторые приводы не сообщают разрешение энкодера
по шине: у Wecon VD3E объекты `0x608F` и `0x6092` просто отсутствуют, ответ —
«object does not exist». Значение берите из ESI или паспорта; у VD3E это
8 388 608 импульсов на оборот, проверено физически проворотом вала на пять
оборотов.

## 7. Distributed Clocks

Драйверы Inovance и Wecon подставляют DC сами (`assignActivate 0x300`, sync0
равен периоду мастера) — значения взяты из ESI. Драйверы Mitsubishi и Schneider
DC **не задают**: ESI у нас нет, а выдумывать значение хуже, чем оставить его
на усмотрение XML. Задать вручную:

```xml
<slave idx="0" type="MR-J4-TM" name="x">
  <dcConf assignActivate="0x300" sync0Cycle="*1"/>
</slave>
```

### `refClockSyncCycles` решает, сойдутся ли часы вообще

Замер на нашей шине (три IS620N + VD3E + каплер):

| | `refClockSyncCycles="1"` | `refClockSyncCycles="-1"` |
|---|---|---|
| `dc-sync-converged` | FALSE | **TRUE** |
| `dc-sync-diff` через 40 с | 1 175 551 нс | **103 нс** |
| `phase-jitter` | 22 634 | **0** |
| `pll-err` | 148 137 | 4 689 |

`-1` — мастер подстраивается под опорные часы шины. С положительным значением
часы расходятся линейно и не сходятся никогда.

### Опорный слейв обязан быть в конфиге

Опишете только один слейв из длинной цепи — получите:

```
Failed to get reference clock time: Input/output error
```

Слейв при этом выйдет в `OP`, но DC работать не будет. Опорные часы живут на
первом DC-способном слейве цепи, и он должен быть в вашем конфиге.

## 8. Перевод существующего конфига с generic

Две грабли, обе стоили нам запуска.

### 8.1. Имена пинов называет драйвер

В `generic` имена задавали вы сами через `halPin=`. Теперь их называет класс
`cia402`, с префиксом `srv-`:

| было | стало |
|---|---|
| `lcec.0.0.cia-statusword` | `lcec.0.x.srv-cia-statusword` |
| `lcec.0.0.actual-position` | `lcec.0.x.srv-actual-position` |
| `lcec.0.0.actual-velocity` | `lcec.0.x.srv-actual-velocity` |
| `lcec.0.0.actual-torque` | `lcec.0.x.srv-actual-torque` |
| `lcec.0.0.following-error` | `lcec.0.x.srv-actual-following-error` |
| `lcec.0.0.target-position` | `lcec.0.x.srv-target-position` |
| `lcec.0.0.opmode-display` | `lcec.0.x.srv-opmode-display` |

Заметьте: у `following-error` изменилось не только начало имени.

### 8.2. У пина меняется ТИП

Самое неочевидное. `following-error` мы объявляли в XML как `s32`. Класс
`cia402` экспортирует его как **`u32`**, и запуск падает уже на связывании:

```
HAL: ERROR: type mismatch 'sampler.0.pin.3' <- 'x-drv-ferr'
./machine.hal:148: link failed
```

Лечится на приёмной стороне. В нашем случае каналы `sampler` переведены в
`u32`:

```hal
loadrt sampler depth=3500 cfg=sssussssussssus
# каналы 3, 8, 13 — u32: сюда приходит srv-actual-following-error
```

**Правило: сверяйте не только имена, но и типы.** `halcmd show pin lcec`
показывает и то, и другое — второй столбец.

### Что даёт перевод

Наш рабочий конфиг фрезера, до и после:

| | было | стало |
|---|---|---|
| `ethercat-conf.xml` | 236 строк | **83** |
| записей PDO руками | 53 | **10** |

Оставшиеся десять принадлежат каплеру Omron: драйвера для него нет, а его карта
зависит от набора модулей в стеке, так что ручное описание там оправдано.

Целиком рабочий пример — [`../mill-3axis-named-drivers/`](../mill-3axis-named-drivers/).

## 9. Если не поднимается

По порядку, от дешёвого к дорогому:

```bash
ethercat master              # Phase, Active, линк
ethercat slaves              # в каком состоянии слейвы; E рядом = ошибка
ethercat slaves -p3 -v       # подробности по конкретному, AL Status Code
dmesg | grep -i lcec         # что сказал драйвер при старте
tail -30 ~/linuxcnc_debug.txt  # ошибки HAL: они НЕ идут в консоль
```

Частые случаи:

| симптом | причина |
|---|---|
| `link failed` при пуске | тип пина не совпал, см. 8.2 |
| слейв в `PREOP`, остальные в `OP` | этого слейва нет в конфиге |
| `OP` есть, DC не сходится | `refClockSyncCycles` или опорный слейв вне конфига |
| слейв не доходит до `OP` вовсе | карта PDO длиннее, чем принимает прибор |
| в модуле нет вашего типа | приехал не тот пакет, см. 4 |

⚠ Ошибки HAL пишутся в `~/linuxcnc_debug.txt`, а не в консоль и не в лог
запуска. Мы потеряли на этом полчаса: скрипт показывал пустой лог, а настоящая
ошибка лежала в домашнем каталоге.

## 10. Добавить свой привод

Драйвер вендора — примерно двадцать содержательных строк поверх класса
`cia402`, который уже написан. Сложность не в коде, а в том, чтобы узнать пять
фактов о приборе. Четыре из них снимаются с живой шины:

```bash
ethercat slaves -v                              # identity, мейлбокс-протоколы
ethercat pdos -p<N>                             # какие PDO назначены и что в них
ethercat upload -p<N> 0x6502 0x00 --type uint32 # какие режимы привод объявляет
ethercat upload -p<N> 0x1c12 0x00 --type uint8  # сколько RxPDO назначается
ethercat upload -p<N> 0x1600 0x00 --type uint8  # сколько записей в карте
ethercat sdos -p<N> | wc -l                     # читается ли словарь вообще
```

Последняя команда интереснее, чем кажется. На нашем стенде четыре привода
ответили **809, 109, 0 и 0** объектов — половина приборов не даёт перечислить
свой словарь, и один из них далеко не самый дешёвый.

Пятый факт — параметры DC (`assignActivate`) — без ESI не добыть, поэтому если
ESI нет, DC лучше не задавать в драйвере.

Пришлите этот вывод и ESI-файл, если он существует в машинном виде, — соберём
драйвер и отправим в апстрим с указанием приславшего. Issue сюда или прямо в
`linuxcnc-ethercat`.

---

Реестр устройств с идентификаторами и граблями: <https://synctwin.ru/ethercat/>
