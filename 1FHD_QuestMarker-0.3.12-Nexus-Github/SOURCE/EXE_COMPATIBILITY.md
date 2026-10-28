# Перенос привязок EXE: 0.3.11 → 0.3.12

Целевая версия ресурса: 2.1.2500. SHA-256: `e43a4b15503c705eebe2d8ce5778c2a2fb090db515a3fd86d319e5c5aa692ebf`.
SizeOfImage: `0x461000`. TimeDateStamp: `0x6AC53B97`. База EXE: `0x400000`.

Адреса ниже — RVA относительно базы. Функции сопоставлены через одноимённые Delphi VMT, связи вызовов, назначение обработчиков и сравнение дизассемблированных тел. Глобальные переменные сопоставлены через одинаковые позиции в таблице ссылок `.data` и проверены по новому коду. Поле списка заданий игрока остаётся `+0x520`; структуру предложения правительства, параметры регистровых вызовов и аргументы обработчиков сохранено.

| Привязка | Старый RVA | Новый RVA |
|---|---|---|
| TList.Add | `0x161c0` | `0x161c0` |
| SetText | `0x90104` | `0x9e0d0` |
| SetDisabled | `0xa1b30` | `0xad12c` |
| ExecuteOnPressCode | `0xa2844` | `0xad910` |
| SetActive | `0xc9eac` | `0xc11bc` |
| GetByName | `0xcefc8` | `0xc5940` |
| Government.ClearChoices | `0x1276ec` | `0x11ee30` |
| Government.AddChoice | `0x127768` | `0x11ee88` |
| Government.OfferChoices | `0x129e34` | `0x1211b8` |
| Government.Easy | `0x12b518` | `0x122760` |
| Government.Hard | `0x12b810` | `0x122a18` |
| Galaxy.Open | `0x2a0160` | `0x274bb8` |
| Galaxy.MouseUp | `0x2a300c` | `0x2777b0` |
| Galaxy.PathChanged | `0x2a339c` | `0x277ac4` |
| Galaxy.Highlight | `0x2a5078` | `0x2793ac` |
| Ship.GetFuelTank | `0x30e5fc` | `0x2d6558` |
| Ship.GetEngine | `0x30e618` | `0x2d6560` |
| Ship.EquipmentReady | `0x30e764` | `0x2d6604` |
| Ship.HyperRange | `0x30f230` | `0x2d6e6c` |
| Ship.DeparturePoint | `0x31c4b4` | `0x2e25c0` |
| Ship.ArrivalPoint | `0x31c590` | `0x2e2694` |
| Ship.JumpCounter | `0x31c634` | `0x2e2734` |
| Ship.ArtefactCount | `0x325a74` | `0x2eab98` |
| Ship.CanBoostArtefact | `0x325cb8` | `0x2ead84` |
| Ship.Speed | `0x32c8dc` | `0x2f10e8` |
| Ship.Bonus | `0x32d804` | `0x2f1ec8` |
| Planet.Position | `0x379d1c` | `0x33684c` |
| Planet.Relation | `0x37d484` | `0x339988` |
| GetPlayer | `0x38c078` | `0x347300` |
| Message.CallbackSlotInstruction | `0x3a3cde` | `0x35c3a2` |
| Message.OriginalRightClick | `0x3a4810` | `0x35cdb4` |
| Star.Visible | `0x461934` | `0x3f3a84` |
| QuestList.FieldOperand | `0x12bba2` | `0x122d59` |
| Galaxy.Global | `0x48c288` | `0x41d2a0` |
| GalaxyScreen.Global | `0x48bf14` | `0x41cbb4` |
| FuelRegen.BaseGlobal | `0x489e28` | `0x41ba28` |
| FuelRegen.BoostGlobal | `0x489e98` | `0x41ba98` |

Точка присваивания обработчика ПКМ теперь использует `EBX` (`C7 83 ...`) вместо `EAX` (`C7 80 ...`); заменяется только адрес в операнде, без замены инструкции.

| Перехват | Новый RVA | Число перезаписанных байтов |
|---|---|---|
| ClearChoices | `0x11ee30` | 10 |
| OfferChoices | `0x1211b8` | 5 |
| Easy | `0x122760` | 5 |
| Hard | `0x122a18` | 5 |
| Galaxy.Open | `0x274bb8` | 8 |
| Galaxy.PathChanged | `0x277ac4` | 6 |
| Galaxy.MouseUp | `0x2777b0` | 6 |

Новый пролог карты резервирует другое число локальных переменных. Скопированы именно новые инструкции; трамплины не содержат относительных переходов или адресных операндов из EXE. `verify_exe_integration.py` сравнивает их эффекты с реальными прологами.

## Повторение проверок

Из папки мода:

```sh
bash SOURCE/Native/build.sh
python3 SOURCE/verify_release.py /path/to/Rangers.exe
python3 SOURCE/verify_exe_integration.py /path/to/Rangers.exe
FHD_TEST_EMULATE=1 bash SOURCE/Native/test_native.sh
gcc -std=c11 -O2 SOURCE/Native/test_route.c -lm -o /tmp/fhd_test_route
/tmp/fhd_test_route
```

Эмуляторные проверки требуют `unicorn==2.1.4`; проверка реальных PE также требует `pefile==2024.8.26`. Проверка `verify_release.py` использует только стандартную библиотеку Python. CFG не пересобирались, поскольку изменения касаются EXE/DLL. Интерактивный запуск игры этими проверками не выполняется.
