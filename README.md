# Рабочие конфигурации LinuxCNC + EtherCAT

Конфигурации, которые реально крутятся на нашем стенде: IgH EtherCAT Master, драйвер
`lcec` (linuxcnc-ethercat), компонент `cia402.comp`, LinuxCNC 2.9.

Это не теоретические примеры и не перепечатка документации. Каждый файл снят с
работающего железа, а в README рядом написано, обо что мы спотыкались.

## Что здесь

| папка | что внутри | железо |
|---|---|---|
| [`is620n-3axis/`](is620n-3axis/) | три оси в режиме CSP плюс дискретное IO | 3× Inovance IS620N, каплер Omron NX-ECC202 |
| [`is620n-single-axis/`](is620n-single-axis/) | минимальный пример с одной осью, с `.ini` | 1× Inovance IS620N |
| [`omron-nx-ecc202-io/`](omron-nx-ecc202-io/) | дискретные входы и выходы, петля аварийного останова | Omron NX-ECC202 + NX-OD5256 |
| [`measuring/`](measuring/) | как замерить отставание, задержки планировщика и ошибки на линии | штатные средства LinuxCNC |
| [`registry/`](registry/) | реестр устройств: идентификаторы, поддержка SDO-Info, грабли | 6 устройств |

## Прежде чем запускать

**Проверьте масштаб оси.** Во всех файлах он посчитан под нашу механику: ШВП с шагом
10 мм и энкодер на 23 бита, отсюда 838 860,8 импульса на миллиметр. У вас другая
передача и другой энкодер, значит другое число. Неверный масштаб означает, что ось
поедет не туда и не на столько, а на серво это дорого.

**Проверьте задержки реального времени.** До того как искать ошибку в профиле,
прогоните `cyclictest`. У нас приводы не выходили в состояние OP из-за перегруженного
процессора, и это выглядело как проблема настройки EtherCAT. Подробности в
[`measuring/`](measuring/).

**Проверьте пределы хода и направления.** Знаки и лимиты в наших файлах относятся к
нашему станку.

## Известные грабли

Собраны по устройствам в реестре: <https://synctwin.ru/ethercat/>

Самое частое, что стоит знать заранее:

- **IS620N назначает ровно один передающий PDO.** Либо `0x1A00`, либо один из
  `0x1B01…0x1B04`. Индекса `0x1A01` у привода нет вовсе, и попытка назначить второй
  PDO даёт ошибку сервисного обмена, после которой слейв не доходит до OP. Всё нужное
  кладётся в `0x1A00`, у него переменное отображение до десяти записей.
- **Объектный словарь IS620N по CoE SDO-Info не отдаёт.** Карту объектов берите из
  ESI или мануала, вычитать её с живого привода нельзя. У Mitsubishi MR-J4-TM,
  наоборот, отдаёт.
- **Имя устройства на шине IS620N не сообщает**, поле остаётся пустым. Опознавать
  модель нужно по объекту `0x1018`, а не по строке с названием прошивки.
- **Ошибка `Er.E08`** (потеря синхронизации) снимается только полным перезапуском
  питания привода, сброса ошибки недостаточно.

## Откуда это

Стенд компании SyncTwin: <https://synctwin.ru>

Разбор всего стека от сетевой карты до `joint.0.motor-pos-cmd` мы описали в статье
«Почему EtherCAT в LinuxCNC держится на компоненте из 9 коммитов»:
<https://habr.com/ru/articles/1068132/>

Реестр оборудования с пометкой источника у каждого факта, стенд или ESI:
<https://synctwin.ru/ethercat/>

Машиночитаемый срез того же реестра: <https://synctwin.ru/ethercat/devices.json>

## Пополнение

Новое устройство на стенде даёт новую папку. Если вы завели эти конфиги у себя и
что-то пошло иначе, напишите в issues: расхождение на другом железе само по себе
полезный факт.

## Лицензии

- конфигурации и HAL: GPL-2.0, как производные от примеров LinuxCNC
- реестр устройств `registry/devices.json`: CC BY 4.0, атрибуция
  «SyncTwin — https://synctwin.ru/ethercat/»

Файлы ESI производителей здесь не публикуются: это их произведения, распространение
регулирует ETG. Мы публикуем только собственные наблюдения и производные факты.

---

## English

Working LinuxCNC + EtherCAT configurations from our bench: IgH master, `lcec` driver,
`cia402.comp`, LinuxCNC 2.9. Not examples from documentation, but files taken from
running hardware, with the pitfalls we hit written next to them.

Hardware covered: Inovance IS620N servo drives (CSP mode), Omron NX-ECC202 coupler
with NX-OD5256 digital output modules.

**Before you run anything:** position scaling in these files is computed for our
mechanics (10 mm ballscrew pitch, 23-bit encoder, 838 860.8 counts per mm). Yours will
differ. Also run `cyclictest` first: our drives failed to reach OP because of realtime
scheduling delays, which looked exactly like an EtherCAT configuration problem.

Device registry with per-fact source marking (bench or ESI):
<https://synctwin.ru/ethercat/> · JSON: <https://synctwin.ru/ethercat/devices.json>

Licenses: configs and HAL under GPL-2.0 (derived from LinuxCNC examples), the device
registry under CC BY 4.0. Vendor ESI files are not redistributed here.
