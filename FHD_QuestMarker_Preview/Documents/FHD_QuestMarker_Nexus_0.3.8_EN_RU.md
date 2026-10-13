# FHD Quest Marker — Government Mission Targets on the Galactic Map

**Version:** 0.3.8 Preview
**Game:** Space Rangers HD: A War Apart
**Author:** Prolog_D

## About this mod

EN: Adds an animated map marker for government mission targets, even before you accept a mission. Right-click an active mission to locate its objective.

RU: Добавляет анимированную метку целей правительственных заданий, в том числе до принятия. ПКМ по активному заданию показывает цель на карте.

## Description

**EN**

Ever accepted a government mission only to spend time searching the galaxy for its destination? FHD Quest Marker makes mission navigation clearer and more convenient.

When a government offers you a special assignment, a new **“Показать на карте” (Show on Map)** dialogue option lets you see its objective on the galactic map **before accepting the mission**. For an already accepted mission, right-click its entry in the information panel to locate its current target.

The mod uses a distinctive animated mission marker without replacing the game's standard player-position marker. You can remove the mission marker using a control on the galactic map.

**RU**

Получили правительственное задание, но не хотите вручную искать нужную систему? **FHD Quest Marker** помогает быстро определить цель задания на галактической карте.

После запроса специального задания в правительстве появляется дополнительный пункт **«Показать на карте»**. Он позволяет увидеть местоположение цели **ещё до принятия задания**. Если задание уже принято, достаточно нажать **ПКМ по его записи в информационной панели**, чтобы открыть карту с нужной меткой.

Для цели используется отдельная анимированная метка. Штатная метка расположения игрока сохраняется. При необходимости метку задания можно убрать кнопкой на галактической карте.

## Installation instructions

**EN**

1. Close the game.
2. Open the downloaded archive and copy **only** `Mods/FHD_MODS/FHD_QuestMarker_Preview` into the matching `Mods/FHD_MODS/` folder in your game directory.
3. Enable **FHD_QuestMarker_Preview** in the game's mod configuration.
4. Disable any older/Xeno-based copy of FHD Quest Marker; do not run two versions together.
5. Launch the game and load a save (or start a new game). Visit a planetary government and ask for a special assignment.

**RU**

1. Полностью закройте игру.
2. Откройте архив и скопируйте **только** папку `Mods/FHD_MODS/FHD_QuestMarker_Preview` в соответствующий каталог установленной игры.
3. Включите **FHD_QuestMarker_Preview** в настройках модификаций игры.
4. Отключите старую/Xeno-версию FHD Quest Marker: одновременно запускать две версии нельзя.
5. Запустите игру, загрузите сохранение или начните новую партию. Откройте правительство планеты и запросите специальное задание.

## Main features

**EN**

- **Preview targets before accepting:** the government dialogue gains a Show on Map option.
- **Locate accepted missions:** right-click a mission in the information panel.
- **Animated objective marker:** clearly identifies the destination on the galactic map.
- **Vanilla player marker preserved:** the mission marker does not replace your ship's normal marker.
- **Clear marker control:** remove the mission marker from the galactic map when it is no longer needed.
- **Source code included:** configuration sources and native DLL source are provided for reference.

**RU**

- **Просмотр цели до принятия задания:** дополнительный пункт «Показать на карте» в диалоге правительства.
- **Поиск цели принятого задания:** ПКМ по заданию в информационной панели.
- **Анимированная метка цели:** хорошо заметна на галактической карте.
- **Сохранение штатной метки игрока:** новая метка не подменяет стандартную.
- **Сброс метки:** возможность убрать её с галактической карты.
- **Исходники в архиве:** доступны исходные файлы конфигурации и DLL.

## Requirements

**EN**

- **Space Rangers HD: A War Apart**, with the supported **Rangers.exe 2.1.2500** executable. The native hook is designed for a specific executable build and may not work with other builds.
- **No XenoNativeLoader required** for version 0.3.8. Its DLL loads through the game's built-in `ScriptLibs` mechanism, but it still uses native code and modifies game handlers in memory.
- Do not use this alongside an older Xeno-based version of the same mod.
- **Preview status:** 0.3.8 is an experimental build. The preceding 0.3.7 version was the last user-confirmed working baseline; in-game validation of 0.3.8 is still needed.
- The new government dialogue option currently appears in **Russian** even when this page is read in English.

**RU**

- **Космические рейнджеры HD: Революция**, поддерживаемый файл **Rangers.exe версии 2.1.2500**. DLL рассчитана на конкретную сборку EXE; на других версиях перехваты могут не работать.
- **XenoNativeLoader не требуется** в версии 0.3.8. DLL загружается штатным механизмом `ScriptLibs`, однако нативные перехваты игровых обработчиков в памяти по-прежнему используются.
- Не устанавливайте одновременно старую Xeno-версию того же мода.
- **Статус Preview:** версия 0.3.8 экспериментальная. Последняя подтверждённая в игре основа — 0.3.7; версию 0.3.8 ещё необходимо окончательно проверить в игре.
- Новый пункт диалога правительства пока отображается **на русском языке**.

## Shout outs

**EN**

Created by **Prolog_D**. Thanks to the creators of Space Rangers, the modding community, and everyone who has helped test and improve the earlier versions. Your feedback helps make galactic navigation more convenient.

**RU**

Автор мода — **Prolog_D**. Спасибо создателям «Космических рейнджеров», сообществу моддеров и всем, кто помогал проверять и улучшать предыдущие версии. Ваши отзывы помогают делать путешествия по галактике удобнее!
