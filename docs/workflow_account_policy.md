# One account and one product per workflow

Each workflow may contain at most one node exposing a `broker_connection`
output. This includes overseas stocks, overseas futures and domestic stocks,
unbound nodes, repeated references to the same credential and registered custom
broker nodes. One broker may supply multiple downstream consumers. Workflows
without a broker and unrelated LLM or messaging credentials remain valid.

`WorkflowDefinition.validate_structure` and the shared
`validate_broker_connections` helper emit blocking `DUPLICATE_BROKER_NODE` errors
for every additional connection, with node locations and all broker node IDs.
`ProgramGarden.validate`, deep validation, compilation and both run methods use
this boundary before broker login. Multiple products require separate workflows;
KRX and NXT are venues within the same domestic product, not separate accounts.

No saved workflow is automatically rewritten, and no running job is restarted.
Historical per-product telemetry fields remain readable for compatibility.
Global account reservation across running projects belongs to the server.

The editor, API and pg-ai use the same rule. A source commit does not update
installed validators: coordinated package pins, installed-artifact validation,
knowledge refresh and dev-to-prod rollout are required before publication.
