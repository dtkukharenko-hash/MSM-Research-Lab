# EXP-004A — F1 Rule Validation

## Scope

This note validates only the fixed rule found on F1 case #29 against the other confirmed F1 cases:

- case #1
- case #4
- case #5
- case #7
- case #17
- case #22

No doubtful F1 cases are checked. No new cases are searched. No TradingView markup is changed. No
definition is changed. This is not a trading strategy.

Source data:

- `experiments/EXP-004_MARCH_FEATURES/EXP-004A_FAMILY_DISCOVERY/artifacts/F1_cases.csv`
- read-only OHLC from `Irobot/backtester` feature export:
  `/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv`

All six checked cases are UP movements, so the case #29 DOWN rule is applied in mirror form.

## Fixed Mirror Rule For UP Movements

The rule was not changed during validation:

1. There is a last active reference UP candle.
2. The first counter DOWN movement overlaps more than 50% of that candle's body.
3. After the first overlap, the market attempts to continue UP.
4. That attempt is weak and does not update the reference candle high.
5. Then a repeated strong DOWN overlap happens.
6. The counter candle closes below the open of the active UP candle, meaning it overlaps the whole body.

For this validation, the active reference candle is the last UP candle that holds the current expert end
of the confirmed F1 movement. This keeps the rule fixed and avoids moving the reference after seeing the
outcome.

## Results Table

| case_id | active reference | first overlap | continuation attempt | extreme updated? | repeat overlap | close beyond reference body? | matches expert end? | result |
|---:|---|---|---|---|---|---|---|---|
| 1 | 2023-12-09 04:00 | 2023-12-09 12:00, wick only | 2023-12-10 00:00 | no | 2023-12-10 04:00 | no | no | PARTIAL |
| 4 | 2023-12-06 12:00 | 2023-12-06 16:00, wick only | 2023-12-07 00:00 | yes | 2023-12-07 08:00 | yes | no | PARTIAL |
| 5 | 2023-11-02 16:00 | not found in 2023 scope | n/a | n/a | n/a | no | no | NO_REPEAT |
| 7 | 2023-11-16 04:00 | 2023-11-16 12:00, wick/close/body | 2023-11-16 20:00 | no | 2023-11-17 04:00 | yes | no | PARTIAL |
| 17 | 2023-12-21 20:00 | 2023-12-22 04:00, wick/close/body | 2023-12-22 08:00 | no | 2023-12-22 16:00 | no | no | PARTIAL |
| 22 | 2023-10-26 04:00 | 2023-10-26 08:00, wick/close/body | 2023-10-26 20:00 | no | 2023-10-27 00:00 | yes | no | PARTIAL |

Detailed machine-readable artifact:

- `artifacts/F1_rule_validation.csv`

## Case Notes

### Case #1

- Active reference UP candle: 2023-12-09 04:00 UTC.
- Reference body: open `0.5783`, close `0.6249`, midpoint `0.6016`.
- First overlap: 2023-12-09 12:00 UTC, wick reaches below midpoint; close remains above midpoint.
- Continuation attempt: 2023-12-10 00:00 UTC, UP candle.
- The attempt does not update the reference high `0.6287`.
- Repeat overlap: 2023-12-10 04:00 UTC, wick/close/body are below midpoint.
- It does not close below reference open `0.5783`.
- It does not coincide with expert end `2023-12-09 04:00`.

Assessment: partial repeat only. The weak continuation part appears, but the final close beyond the
reference body is absent.

### Case #4

- Active reference UP candle: 2023-12-06 12:00 UTC.
- Reference body: open `0.4373`, close `0.4511`, midpoint `0.4442`.
- First overlap: 2023-12-06 16:00 UTC, wick reaches below midpoint; close remains above midpoint.
- Continuation attempt: 2023-12-07 00:00 UTC, UP candle.
- The attempt updates the reference high: `0.4561` versus reference high `0.4514`.
- Repeat overlap: 2023-12-07 08:00 UTC, wick/close/body are below midpoint.
- It closes below reference open `0.4373`.
- It does not coincide with expert end `2023-12-06 12:00`.

Assessment: partial repeat only. The final break exists, but the required weak failed continuation is not
present because the continuation made a new high.

### Case #5

- Active reference UP candle: 2023-11-02 16:00 UTC.
- Reference body: open `0.3001`, close `0.3245`, midpoint `0.3123`.
- First overlap: not found inside the 2023 ADA 4H scope after the expert end.
- Continuation attempt: n/a.
- Repeat overlap: n/a.
- It does not coincide with expert end `2023-11-02 16:00`.

Assessment: no repeat in the experiment scope.

### Case #7

- Active reference UP candle: 2023-11-16 04:00 UTC.
- Reference body: open `0.3819`, close `0.3968`, midpoint `0.38935`.
- First overlap: 2023-11-16 12:00 UTC, wick/close/body are below midpoint.
- Continuation attempt: 2023-11-16 20:00 UTC, UP candle.
- The attempt does not update the reference high `0.3987`.
- Repeat overlap: 2023-11-17 04:00 UTC, wick/close/body are below midpoint.
- It closes below reference open `0.3819`.
- It does not coincide with expert end `2023-11-16 04:00`.

Assessment: the local sequence repeats most clearly here, but it happens after the expert end rather than
at the expert end. Therefore it is not a direct validation of the case #29 ending rule.

### Case #17

- Active reference UP candle: 2023-12-21 20:00 UTC.
- Reference body: open `0.6151`, close `0.6359`, midpoint `0.6255`.
- First overlap: 2023-12-22 04:00 UTC, wick/close/body are below midpoint.
- Continuation attempt: 2023-12-22 08:00 UTC, UP candle.
- The attempt does not update the reference high `0.6404`.
- Repeat overlap: 2023-12-22 16:00 UTC, wick/close/body are below midpoint.
- It does not close below reference open `0.6151`.
- It does not coincide with expert end `2023-12-21 20:00`.

Assessment: partial repeat only. The first overlap and failed continuation appear, but the repeated
counter candle does not reclaim the whole reference body.

### Case #22

- Active reference UP candle: 2023-10-26 04:00 UTC.
- Reference body: open `0.2899`, close `0.2954`, midpoint `0.29265`.
- First overlap: 2023-10-26 08:00 UTC, wick/close/body are below midpoint.
- The first overlap already closes below reference open `0.2899`.
- Continuation attempt: 2023-10-26 20:00 UTC, UP candle.
- The attempt does not update the reference high `0.2960`.
- Repeat overlap: 2023-10-27 00:00 UTC, wick/close/body are below midpoint.
- It closes below reference open `0.2899`.
- It does not coincide with expert end `2023-10-26 04:00`.

Assessment: partial repeat only. The elements are present, but the sequence is not the same as case #29:
the first overlap is already a full-body break, so the two-stage distinction is not clean.

## Summary

- Full repeats: 0 / 6.
- Partial repeats: 5 / 6.
- No repeat inside the 2023 scope: 1 / 6.
- Cases where the repeated break closes beyond the reference body: #4, #7, #22.
- Cases where the continuation attempt is weak and does not update the reference high: #1, #7, #17, #22.
- Cases where both weak continuation and full-body repeated break appear: #7 and #22.
- Cases where the repeated break coincides with the existing expert end: 0 / 6.

The fixed rule from case #29 does not repeat as a complete expert-ending rule across the other confirmed
F1 cases. It does recur as a partial post-reference reversal pattern, especially in cases #7 and #22, but
the timing and sequence are not stable enough to treat it as the confirmed F1 ending rule.

## Verdict

# PARTIAL_REPEAT
