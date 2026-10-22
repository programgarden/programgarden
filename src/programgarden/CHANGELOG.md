# Changelog

## [3.0.0] - 2026-10-22

First release from the public ProgramGarden repository. Earlier versions remain
available on PyPI.

### Changed

- Deep validation (`WorkflowExecutor.deep_validate`), runtime identity and workflow
  replay run only on the ProgramGarden platform. Calling `deep_validate` in this
  package raises `NotImplementedError`. Structural validation (`validate`) and
  `dry_run` are unchanged.
- CodeNode execution runs only on the ProgramGarden platform. Workflows that contain
  a CodeNode still parse and pass structural validation; executing the node fails
  with `CodeNode runs on the ProgramGarden platform only.`
- Broker startup checks perform the generic checks only (transport, complete
  response, standard success code). Responses outside that path return the generic
  startup error.
- Requires `programgarden-core`, `programgarden-finance` and
  `programgarden-community` 3.0.0.
