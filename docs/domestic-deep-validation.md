# Domestic account evidence in virtual validation

Author: Codex. Engine1.38.2 corrects only offline account fixtures; finance1.10.2,
core1.29.0 and community1.15.3 remain unchanged. No broker request or order is
introduced by this change.

Actual pg-ai generation and selected-draft repair passed18 intercepted execution
cases each, but deep validation rejected both because its AccountNode fixture
omitted held_symbols. Domestic fixtures also inherited AAPL/NASDAQ and USD from
the generic account fixture. A strict entry guard correctly rejected that input;
the repair loop incorrectly attributed the failure to the generated code.

REST account fixtures now include held_symbols derived from their positions and
an explicit false partial-failure marker. Domestic fixtures use KRX/KRW and a
synthetic six-digit default. Pending fixtures explicitly report no error. Custom
incomplete observations continue to fail. Existing foreign-stock identity and
currency defaults remain intact.

Regression coverage runs complete and empty domestic account scenarios through
virtual validation with socket connections and broker login forbidden. Missing
holdings, foreign identities and pending-read errors remain blocking. Recheck
generated drafts through the installed wheel and deployed sandbox before closing
the pg-ai release. This fix does not validate NXT workflow routing or live fills.

Validation:45 focused source tests and45 tests against the TestPyPI-installed
wheel pass. Both actual pg-ai drafts pass installed deep validation with network
connections forbidden. TestPyPI artifact hashes match the built wheel and sdist;
production package and consumer rollout are the remaining release steps.
