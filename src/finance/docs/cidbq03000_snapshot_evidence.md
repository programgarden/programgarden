# CIDBQ03000 deposit/balance snapshots

The supplied LS contract names this TR overseas futures deposit/balance status.
`AcntTpCode="1"` selects a consignment account. `TrdDt` is the requested trading
date. The repository example `example/overseas_futureoption/run_CIDBQ03000.py`
uses a paper account with `RecCnt=1`, `AcntTpCode="1"`, and `TrdDt=""`.

## Observed paper responses, 2026-09-09

Two read-only requests used that same SDK query builder and the platform's shared
token provider. No order or independent OAuth request was submitted. The blank
date request completed at18:46:13 KST; the `20260908` request at18:46:14 KST.
Both returned HTTP200, `rsp_cd="00136"`, and the original message
`모의투자 조회가 완료되었습니다.`. Both parsed as five balance rows.

The blank request retained blank dates in the echo and each row; do not replace
those fields with a purported broker-confirmed date. The dated request echoed
`20260908`. USD, JPY, HKD, CHF and CAD rows were returned. No aggregate target was
returned in these two responses; the separately supplied LS example has `TOT(USD)`.

| HKD field | Blank date request | `20260908` request |
| --- | ---: | ---: |
| `OvrsFutsDps` | 999840.00 | 999840.00 |
| `CustmMnyioAmt` | 0.00 | 0.00 |
| `AbrdFutsLqdtPnlAmt` | 0.00 | 0.00 |
| `AbrdFutsCmsnAmt` | 40.00 | 0.00 |
| `PrexchDps` | 999800.00 | 999840.00 |
| `EvalAssetAmt` | 998910.00 | 999840.00 |
| `AbrdFutsEvalPnlAmt` | -890.00 | 0.00 |
| `LastSettPnlAmt` | 0.00 | 0.00 |

For this observed HKD snapshot, `999840 - 40 = 999800` and
`999800 - 890 = 998910`. The change from the dated snapshot's evaluated assets is
`-930`, matching the observed commission and valuation loss. Adding those
components again to `EvalAssetAmt` would double count them in this example.

This establishes a working date-specific query and the stated numerical
relationships in these responses. It does not establish a universal accounting
formula, historical retention, intraday reset boundary, or the inclusion of
commission/final settlement in liquidation P&L: both liquidation and final
settlement values were zero. It is not a verified contest return or MDD.

## Field metadata corrections

The supplied table specifies `OvrsFutsDps` as23.2 and the other monetary fields
as19.2, `CrcyObjCode` length12, date length8, account number length20 and password
length8. These are wire metadata, not new runtime validation constraints.
`LastSettPnlAmt` is labelled final settlement P&L (`최종결제손익금액`); the former
description “last daily settlement” asserted more than the supplied label.
Keep native currency and aggregate rows distinct, and preserve missing raw
fields before typed defaults when deciding whether financial evidence exists.
