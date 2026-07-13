# MSM Research Queue

Центральный список задач для исследовательской лаборатории.

## Правила

- ChatGPT формирует исследовательские задачи.
- Claude Code выполняет задачи.
- Результат всегда сохраняется в GitHub.
- Каждая задача имеет TASK.md и REPORT.md.
- Изменения ядра модели требуют отдельного решения.

---

## ACTIVE

Пока нет.

---

## DONE / REPORT_READY

### EXP-006D_FROZEN_HOLDOUT

Статус: DONE / REPORT_READY

Вердикт: HOLDOUT_REJECTED — финальный независимый holdout для замороженной системы `ENTRY_A + STOP_A +
EXIT_R5` открыт один раз и не подтвердил систему. Holdout `2025-07-01 04:00 UTC → 2026-07-01 00:00 UTC`
теперь считается использованным для ветки EXP-006. EXIT_R5: 31 сделка, PF 0.656, total return -10.6%,
max DD -14.2%, costs x2 PF 0.509, return without top-1 -14.6%, top-3 profit share 48.5%. Causality audit
PASS; 4 intrabar ambiguity cases resolved conservatively and не меняют verdict. Следствие: `ENTRY_A +
STOP_A + EXIT_R5` закрывается, не дорабатывать на этом holdout. Детали:
`experiments/EXP-006_EMA_TRADING_CYCLE/EXP-006D_FROZEN_HOLDOUT/REPORT.md`.

Цель:
Один раз проверить полностью замороженную EMA trading cycle систему на настоящем нетронутом holdout.

Исполнитель:
Claude Code

Результат:
REPORT.md создан; paper trading не разрешён, параметры/правила не менять по этому holdout.

---

### EXP-006C_FROZEN_EXIT_ROBUSTNESS

Статус: DONE / REPORT_READY

Вердикт: EXIT_RULE_FROZEN_READY — аудит замороженных `EXIT_R2` и `EXIT_R5` без изменения `ENTRY_A`,
`STOP_A`, EMA27/EMA200 и порогов подтвердил готовность кандидата `EXIT_R5` к отдельному frozen holdout-шагу.
MFE capture пересчитан по буквальному правилу EXP-006C до `exit_time` включительно: manual audit mismatches = 0;
одинаковая reused temporal median capture из EXP-006B оказалась артефактом прежней metric convention и после
аудита не сохраняется. По всему research `EXIT_R5`: PF 1.827, total return 85.7%, max DD -14.4%, median MFE
capture 0.141 против baseline -0.401, GOOD_ENTRY_BAD_EXIT 0.0% против baseline 13.2%, PF x2 = 1.593.
Настоящий holdout не открыт. Детали:
`experiments/EXP-006_EMA_TRADING_CYCLE/EXP-006C_FROZEN_EXIT_ROBUSTNESS/REPORT.md`.

Цель:
Проверить устойчивость уже найденных механизмов выхода `EXIT_R2` и `EXIT_R5` на блоках, rolling-origin,
парных сделках, концентрации, LONG/SHORT и cost stress без изменения правил.

Исполнитель:
Claude Code

Результат:
REPORT.md создан; `EXIT_R5` можно рассматривать как frozen-ready кандидат для отдельного следующего шага.

---

### EXP-006B_EXIT_RETENTION

Статус: DONE / REPORT_READY

Вердикт: EXIT_RETENTION_FOUND — при фиксированных `ENTRY_A + STOP_A` варианты удержания MFE показали
улучшение именно механизма выхода. На DEVELOPMENT прошли `EXIT_R2` и `EXIT_R5`; на EXIT VALIDATION лучший
перенос дал `EXIT_R5`: PF 3.135, median MFE capture 0.166 против baseline -0.008, GOOD_ENTRY_BAD_EXIT 0.0%
против baseline 8.3%, max DD не ухудшился относительно baseline. REUSED TEMPORAL TEST не является
независимым OOS, но показал согласованное улучшение PF относительно baseline. Настоящий holdout не открыт.
Детали: `experiments/EXP-006_EMA_TRADING_CYCLE/EXP-006B_EXIT_RETENTION/REPORT.md`.

Цель:
Проверить, можно ли защитить уже возникший MFE после неизменного ENTRY_A, не меняя вход, EMA-режим и
начальный STOP_A.

Исполнитель:
Claude Code

Результат:
REPORT.md создан; найден кандидат механизма удержания для отдельного следующего решения/проверки, без
самовольного открытия holdout.

---

### EXP-006A_ENTRY_EXIT_DIAGNOSIS

Статус: DONE / REPORT_READY

Вердикт: ENTRY_VALID_EXIT_FAILURE — диагностика трёх shortlisted комбинаций EXP-006 показала, что
`ENTRY_A_STOP_A_EXIT_B` на TEMPORAL TEST всё ещё давал доступный положительный путь: на горизонте 24 бара
`+1 ATR` достигался раньше `-1 ATR` в 55.6% сделок, BAD_ENTRY = 0.0%, но GOOD_ENTRY_BAD_EXIT = 44.4%,
а средняя отдача MFE до фактического выхода выросла до 147.3%. Главная проблема — удержание/выход, а не
немедленный отказ входа. Настоящий holdout не открыт. Детали:
`experiments/EXP-006_EMA_TRADING_CYCLE/EXP-006A_ENTRY_EXIT_DIAGNOSIS/REPORT.md`.

Цель:
Понять, почему сильный TRAIN-результат EXP-006 не перенёсся на TEMPORAL TEST: вход, выход, stop, режим или
сочетание факторов.

Исполнитель:
Claude Code

Результат:
REPORT.md создан; следующий эксперимент можно ставить только по диагностированной причине, без немедленного
придумывания новых правил.

---

### EXP-006_EMA_TRADING_CYCLE

Статус: DONE / REPORT_READY

Вердикт: WEAK_EMA_CYCLE — 24 фиксированные комбинации EMA27/EMA200 торгового цикла были проверены на
research-only данных ADAUSDT 4H. На TRAIN прошли shortlist-комбинации `ENTRY_A_STOP_A_EXIT_B`,
`ENTRY_A_STOP_B_EXIT_B`, `ENTRY_A_STOP_A_EXIT_A`, но на TEMPORAL TEST ни одна не сохранила PF > 1.10:
лучший PF temporal test = 0.784, max DD = -14.65%, total return = -8.40%. Настоящий holdout не открыт.
Детали: `experiments/EXP-006_EMA_TRADING_CYCLE/REPORT.md`.

Цель:
Проверить полный практический EMA27/EMA200 цикл: режим, подготовка, вход, стоп, сопровождение и выход.

Исполнитель:
Claude Code

Результат:
REPORT.md создан; система не готова к отдельному holdout-тесту.

---

### EXP-005H_CAUSAL_EVENT_GENERATOR

Статус: DONE / BLOCKED

Вердикт: EVENT_DEFINITION_BLOCKED — причинный generator зафиксирован и запущен на research-only
DEVELOPMENT/PSEUDO-HOLDOUT, но основной тест Model 3 заблокирован: EXP-005A не содержит точного числового
major/non-major/censored outcome definition. Pseudo-holdout candidates: 41; labels остаются UNKNOWN/BLOCKED.
Настоящий holdout не открыт. Детали:
`experiments/EXP-005_PRECURSORS_OF_MAJOR_MOVES/EXP-005H_CAUSAL_EVENT_GENERATOR/REPORT.md`.

Цель:
Формализовать causal candidate event generator для EXP-005F перед любым повторным holdout-тестом.

Исполнитель:
Claude Code

Результат:
REPORT.md создан; нужен отдельный research-only шаг по формализации outcome label definition.

---

### EXP-005G_FROZEN_HOLDOUT_TEST

Статус: DONE / BLOCKED

Вердикт: HOLDOUT_BLOCKED_BY_EVENT_DEFINITION — замороженная Model 3 из EXP-005F не запускалась на holdout
outcomes, потому что EXP-005A/EXP-005B не содержат точного причинного алгоритма генерации полного набора
holdout candidate event points и label rules. Holdout labels не открывались; результат не подтверждает и не
отвергает EMA-гипотезу. Детали:
`experiments/EXP-005_PRECURSORS_OF_MAJOR_MOVES/EXP-005G_FROZEN_HOLDOUT_TEST/REPORT.md`.

Цель:
Один раз проверить полностью замороженную спецификацию Model 3 на нетронутом holdout-периоде, если event
generation можно воспроизвести причинно и однозначно.

Исполнитель:
Claude Code

Результат:
REPORT.md создан; holdout test заблокирован до формализации event-generation на research.

---

### EXP-005F_EMA_CONTEXT_INCREMENT

Статус: DONE / REPORT_READY

Вердикт: EMA_INCREMENT_FOUND — EMA-контекст дал прирост над `pre_net_return_atr`: temporal ROC-AUC Model 3
`0.773` против Model 0 `0.533`, group-aware OOF ROC-AUC Model 3 `0.782`, temporal PR-AUC `0.614` выше
prevalence `0.250`. Holdout не открыт; зафиксирована кандидатная спецификация Model 3 для отдельного
будущего holdout-теста. Детали:
`experiments/EXP-005_PRECURSORS_OF_MAJOR_MOVES/EXP-005F_EMA_CONTEXT_INCREMENT/REPORT.md`.

Цель:
Проверить, добавляет ли EMA27/EMA200 контекст причинно доступную информацию сверх OHLC baseline для
отличия major starts от matched non-major events.

Исполнитель:
Claude Code

Результат:
REPORT.md создан.

---

### EXP-005E_TEMPORAL_VALIDATION

Статус: DONE / REPORT_READY

Вердикт: WEAK_TEMPORAL_SIGNAL — Model A (`pre_net_return_atr`, 30 баров, linear regression) сохранила
положительный Spearman на позднем research-сегменте (`0.376`) и положительный знак коэффициента, но test R²
остался отрицательным (`-0.332`). Настоящий holdout не открыт; правило для holdout не заморожено. Детали:
`experiments/EXP-005_PRECURSORS_OF_MAJOR_MOVES/EXP-005E_TEMPORAL_VALIDATION/REPORT.md`.

Цель:
Проверить временной перенос слабой связи EXP-005D без новых признаков, пересбора событий, подбора горизонта
или усложнения модели.

Исполнитель:
Claude Code

Результат:
REPORT.md создан.

---

### EXP-005D_CONTINUOUS_OUTCOME_SEVERITY

Статус: DONE / REPORT_READY

Вердикт: WEAK_CONTINUOUS_SEVERITY_SIGNAL — использовано 60 событий (15 major + 45 matched non-major).
Лучший group-aware OOF Spearman = 0.205 (`pre_net_return_only`), лучший OOF R² = -0.006 (`forest`).
После удаления top-1/top-3 severity Spearman сохраняется около 0.27/0.22, но сильный критерий не пройден:
R² остаётся слабым/около нуля, а связь чувствительна к выбору event point. Holdout не открыт. Детали:
`experiments/EXP-005_PRECURSORS_OF_MAJOR_MOVES/EXP-005D_CONTINUOUS_OUTCOME_SEVERITY/REPORT.md`.

Цель:
Проверить, можно ли по OHLC-состоянию до matched event объяснить непрерывную силу последующего движения без
искусственной дискретной классификации.

Исполнитель:
Claude Code

Результат:
REPORT.md создан.

---

### EXP-005C_TAXONOMY_OF_MATCHED_OUTCOMES

Статус: DONE / REPORT_READY

Вердикт: WEAK_OUTCOME_TAXONOMY — 45 matched non-major outcomes не образовали устойчивую многоклассовую
таксономию. Основной H=30 clustering дал один широкий кластер 41/45 (`RANGE_WHIPSAW`) и два малых
trend-continuation/outlier кластера 3/45 и 1/45. Delayed major moves: 0. Следующий шаг не открывать
автоматически; рекомендовано изучать continuous outcome severity вместо классификатора. Commit: см. историю
git для этого изменения. Детали:
`experiments/EXP-005_PRECURSORS_OF_MAJOR_MOVES/EXP-005C_TAXONOMY_OF_MATCHED_OUTCOMES/REPORT.md`.

Цель:
Построить описательную post-event таксономию исходов после 45 matched non-major событий EXP-005B без
предиктивной интерпретации.

Исполнитель:
Claude Code

Результат:
REPORT.md создан.

---

### EXP-005B_SELECTION_BIAS_TEST

Статус: DONE / REPORT_READY

Вердикт: OPPOSITE_STATE_IS_SELECTION_ARTIFACT — matched-turn контроль нашёл 45 failed turns, по 3 на каждый
major start EXP-005A. На основном 30-барном окне OPPOSITE_TREND встречается у 12/15 major starts и у 38/45
failed turns, то есть преимущество не сохраняется. Нужен дополнительный OHLC-признак перед использованием
holdout. Детали:
`experiments/EXP-005_PRECURSORS_OF_MAJOR_MOVES/EXP-005B_SELECTION_BIAS_TEST/REPORT.md`.

Цель:
Проверить, является ли OPPOSITE_TREND реальным предвестником крупных движений или артефактом ретроспективного
выбора start_time около локального разворота.

Исполнитель:
Claude Code

Результат:
REPORT.md создан.

---

### EXP-005A_PRICE_STATE_BEFORE_MAJOR_MOVES

Статус: DONE / REPORT_READY

Вердикт: OPPOSITE_STATE_CANDIDATE_FOUND — после исключения последних 12 месяцев как holdout в research-периоде
2023-07-01 — 2025-07-01 найдено 15 завершённых крупных движений и 1 CENSORED-кандидат у правой границы.
В 12/15 завершённых случаев 30-барное OHLC-окно до старта классифицировано как OPPOSITE_TREND против 11/75
контрольных окон. Главная слабость: устойчивость к сдвигу start_time только 7/15. Детали:
`experiments/EXP-005_PRECURSORS_OF_MAJOR_MOVES/EXP-005A_PRICE_STATE_BEFORE_MAJOR_MOVES/REPORT.md`.

Цель:
Проверить, из какого OHLC-состояния цены рождаются крупные движения ADAUSDT 4H, полностью исключив последние
12 месяцев данных как нетронутый holdout.

Исполнитель:
Claude Code

Результат:
REPORT.md создан.

---

### EXP-005_PRECURSORS_OF_MAJOR_MOVES

Статус: DONE / REPORT_READY

Вердикт: PRECURSOR_CANDIDATES_FOUND — в доступном периоде ADAUSDT 4H с 2023-07-01 по 2026-07-01 найдено
21 крупное ретроспективно размеченное движение. Главный кандидат состояния-предвестника: перед LONG окно
30 баров имело нисходящий уклон и цену ниже EMA27/EMA200; перед SHORT окно 30 баров имело восходящий уклон
и цену выше EMA27/EMA200. Это не сигнал и не изменение модели. Детали:
`experiments/EXP-005_PRECURSORS_OF_MAJOR_MOVES/REPORT.md`.

Цель:
Понять, какие состояния рынка регулярно предшествуют крупным движениям ADAUSDT 4H в доступном историческом
периоде backtester.

Исполнитель:
Claude Code

Результат:
REPORT.md создан.

---

### EXP-005_GLOBAL_LADDERS_2023

Статус: DONE / REPORT_READY

Вердикт: DATA_INSUFFICIENT — полный год ADA/USDT 4H за январь-июнь 2023 не найден в доступном read-only
источнике Irobot, поэтому полную годовую карту подтвердить нельзя. Для доступного окна с 2023-07-01 по
2024-01-08 построена ретроспективная кандидатная карта из 7 глобальных лестниц; старые 50 локальных движений
наложены только после выбора границ и покрывают лишь части лестниц. Детали:
`experiments/EXP-005_GLOBAL_LADDERS_2023/REPORT.md`.

Цель:
Построить ретроспективную карту глобальных лестниц ADA/USDT 4H за доступную часть 2023 года и определить,
куда попадают локальные движения EXP-004.

Исполнитель:
Claude Code

Результат:
REPORT.md создан.

---

### EXP-004B_F1_START_STRUCTURE

Статус: DONE / REPORT_READY

Вердикт: PARTIAL_COMMON_START — подтверждённые F1 случаи имеют частично общий старт: в 6/7 случаев первые
5 баров дают минимум 4 тела по направлению и минимум 3 направленных close-step; в 5/7 случаев есть обновление
предыдущего 10-барного экстремума и предварительное сжатие. Полного общего механизма нет: #22 и #29 являются
контрпримерами. Детали: `experiments/EXP-004_MARCH_FEATURES/EXP-004B_F1_START_STRUCTURE/REPORT.md`.

Цель:
Проверить, имеют ли подтверждённые случаи F1 повторяющуюся структуру начала движения.

Исполнитель:
Claude Code

Результат:
REPORT.md создан.

---

### EXP-004A_FAMILY_DISCOVERY

Статус: DONE / REPORT_READY

Вердикт: FAMILY_FOUND — среди 38 движений EXP-004 без стартовой сильной свечи найдено 6 описательных
семейств. Крупнейшее F1 покрывает 22/38 случаев: умеренный/мягкий направленный старт без большой свечи,
серия продолжений и окончание у направленного края с последующей паузой/встречным ходом. Детали:
`experiments/EXP-004_MARCH_FEATURES/EXP-004A_FAMILY_DISCOVERY/REPORT.md`.

Цель:
Найти естественные семейства начала и окончания сильных направленных движений без заранее заданных классов.

Исполнитель:
Claude Code

Результат:
REPORT.md создан.

---

### EXP-004_MARCH_FEATURES

Статус: DONE / REPORT_READY

Вердикт: REJECT — H-MARCH-001 не подтверждена в строгом виде. На 50 сильных направленных движениях ADA 4H
за доступную часть 2023 полный признак стартовой сильной свечи найден в 12/50 случаев; 38/50 движений не
имели такого старта. Детали: `experiments/EXP-004_MARCH_FEATURES/REPORT.md`.

Цель:
Провести практический визуальный эксперимент по наблюдаемым признакам участка, который человек называет
«марш», начиная с проверки H-MARCH-001 о стартовой сильной направленной свече.

Исполнитель:
Claude Code

Результат:
REPORT.md создан.

---

### EXP-003_MINIMAL_OBJECT_REVIEW

Статус: DONE / REPORT_READY

Вердикт: методологическая ревизия. EXP-002 отклонил КЛАСС «локализованная зона», а не только площадку.
Локализованные кандидаты (строгая площадка, переход/марш) несут высокий риск повторить EXP-002; переход/марш
дополнительно производен от отклонённой площадки. Рекомендация: следующим формализовать **направление/режим**
(EXP-004) — процессное, не локализованное состояние, поддержанное дугой «геометрия держит направление» — с
обязательным null-контролем (N1 shuffle, N2 block-boot). «Отсутствие локализованного объекта» держать как
ведущую альтернативную гипотезу. Детали: `experiments/EXP-003_MINIMAL_OBJECT_REVIEW/REPORT.md`.

Цель:
Провести методологическую ревизию кандидатов минимального объекта после REJECT площадки в EXP-002.

Исполнитель:
Claude Code

Результат:
REPORT.md создан.

---

## DONE / REJECT

### EXP-002_PLATFORM_EXISTENCE

Статус: DONE / REJECT

Вердикт: ❌ REJECT — площадки статистически НЕ отличаются от null-моделей (shuffle/block-boot, p=0.22–0.92);
объект близок к вырожденному (покрытие 0.88 и на реале, и на шуме), UNKNOWN(live)=0.38. Площадка не принята
как минимальный объект. Детали: `experiments/EXP-002_PLATFORM_EXISTENCE/REPORT.md`.

Цель:
Проверить, является ли площадка устойчивым объектом рынка или артефактом визуального восприятия.

Исполнитель:
Claude Code

Результат:
REPORT.md создан.

---

## NEXT

Пока нет.
