# Dependency maintenance and security

The development branch requires Python 3.11+. Python 3.8, 3.9 and 3.10 are upstream end-of-life; the older interpreters also constrain available dependency fixes. Published 0.1.1 remains unchanged. Raising this minimum is a compatibility change for standalone clients and must be included in the next release notes; it does not raise the Home Assistant integration minimum (HA 2024.5 uses Python 3.12).

Runtime requirements live in pyproject.toml. requirements.txt installs that project rather than maintaining a second list of pinned transitive packages. HTTPX/Tenacity have bounded API ranges; AnyIO, certifi, HTTPcore and IDNA have explicit security floors. These floors address known advisories as of the update, not every possible future vulnerability. Do not bypass Home Assistant's dependency resolver or manually replace packages in a running HA container.

The Dependency security workflow installs the proposed runtime into a clean Python 3.14 environment. pip-audit runs from a separate tools environment and scans the runtime site-packages, without ignored vulnerability IDs or continue-on-error. It runs on pull requests, pushes, a weekly schedule and manual dispatch. It audits the resolved versions, not every version allowed by the metadata, and does not inspect users' installed systems. Database/network failures also fail the check.

Tests install requirements-test.txt and run python -m pytest. The Python 3.12 CI job also tests the HTTPX/Tenacity lower bounds. Package publication remains a separate manual operation: merging a dependency PR does not update PyPI or the integration's published requirement.

Dependabot groups Python and GitHub Actions version updates weekly. Every update requires review and relevant tests; there is no automatic merge or release. On a GitHub fork, the owner must explicitly enable Dependabot version updates under Settings > Advanced Security (wording may vary). Also enable the dependency graph, alerts and security updates. The configuration file alone does not prove these services are active.

To repeat an audit, create separate runtime and audit virtual environments, install the project into the former and requirements-audit.txt into the latter, then run the latter's python -m pip_audit --path <runtime-site-packages>. Do not install the scanner into a production HA container.
