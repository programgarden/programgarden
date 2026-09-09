# Local futures execution observations

`parse_futures_execution_history` in
`programgarden_finance.ls.overseas_futureoption.extension.execution_history`
accepts CIDBQ02400 response rows or mappings and returns separate `executions`
and `issues`. It makes no request, places no order and establishes no complete
query coverage or financial accounting result.

Positive execution observations require explicitly supplied broker order and
execution identifiers, `OrdDt`, `ExecDt`, a valid 17-digit `ExecDttm`, execution
symbol/direction/quantity/quote price. Numeric identifiers ignore leading zeros;
opaque identifiers retain case. Other identifier namespaces are never fallbacks.
`ExecBnsTpCode` maps 1 to sell and 2 to buy. The output order status is retained,
not used as a universal 1-only execution filter. Zero and negative futures quote
prices are valid supplied prices. Missing model defaults are not evidence.

Order date, broker execution date and execution wall time remain independent.
`execution_wall_time` is a naive datetime preserving the actual milliseconds.
This API supplies no implicit timezone or inferred UTC instant. A caller must
provide its broker-timezone configuration and provenance before normalizing time
for a server. Do not manufacture a date from the order date or claim millisecond
precision from a seconds-only real-time message.

An ordinary zero execution quantity does not create a fill. A `체결취소` label
creates `execution_cancellation_effect_unverified` even with zero quantity.
Other invalid positive rows create an issue with whatever explicit order identity
is available. Issues must survive downstream reconciliation; ignoring one could
incorrectly present an earlier fill as current, complete evidence. No cancellation
netting, deletion or replacement execution is inferred.

The parser retains repeated execution observations. Durable consumers must apply
source-scoped identity checks and surface conflicting facts, with account,
credential, mode, order and broker execution date in their documented domain.
TC3 exchange execution IDs are not interchangeable with CIDBQ02400 LS execution
IDs. Using both as independent FIFO writers can double-count one economic fill.

Only a narrow status/date/media whitelist is retained as evidence. Entire broker
payloads, account identifiers, passwords and user registration fields are not
copied. Local telemetry remains unverified and cannot populate official contest
or financial accounting results by itself.
