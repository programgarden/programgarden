# Version 2.6.4 release candidate validation

The candidate is based on merged upstream 2.6.3. It prepares engine 2.6.4 only;
core 2.6.2, finance 2.0.2 and community 2.3.1 are unchanged, and so are the
engine's dependency requirements. The root and engine lock files need no change
and `poetry check --lock` reports both as fresh. This document does not
establish package publication or hosted installation.

The [paper futures account correction](paper-futures-business-date.md#account-node-and-rejection-messages-264-candidate)
describes the change. OverseasFuturesAccountNode accepts the paper `02679`
empty-account answer under the same strict envelope checks as the 2.6.3 startup
path. Unaccepted response codes now carry the broker message in the server
preparation gate's format; the prefix up to the code is unchanged. Live-account
acceptance, request parameters and all other evidence guards are retained.

Local Python 3.12 verification used a fresh virtual environment with the
candidate source packages installed in editable mode:

- 28 new offline cases build real SDK response models for paper/live 02679,
  other messages, nonempty rows, missing rows, partial pages, echo mismatch,
  another TR, a non-boolean paper flag, the account node, the startup snapshot,
  the paper pending-order path, message bounds and server-format parity.
- 301 focused cases covering paper business dates, startup evidence, futures
  read evidence, account balances, order lifecycle and reconciliation passed.
- The complete engine suite reported 3379 passed, 25 skipped, 3 xfailed and
  5 failed. The same 5 cases (three cancel-order port assertions and two replay
  contract cases) fail identically with the unchanged 2.6.3 source in the same
  environment and do not involve the changed modules.

No wheel or sdist was built for this preparation. The release owner builds the
reviewed merged main commit, inspects the artifacts, publishes the engine only
and tags that commit. Core, finance and community are not rebuilt or published.

No broker request, order or account change was performed. The explicit-date
CIDBQ01500 form of the paper empty answer was not separately observed; only the
exact envelope already observed on the current-date request is accepted.
Package publication, clean index installation, consumer adoption and desktop
packaging remain separate release steps.
