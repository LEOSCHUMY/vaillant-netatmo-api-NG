# Dependency maintenance and security

Version 0.2.0 and later require Python 3.11+. Python 3.8, 3.9 and 3.10 are upstream end-of-life; the older interpreters also constrain available dependency fixes. Release 0.1.1 remains unchanged. Raising this minimum is a compatibility change for standalone clients; it does not raise the Home Assistant integration minimum (HA 2024.5 uses Python 3.12).

Runtime requirements live in pyproject.toml. requirements.txt installs that project rather than maintaining a second list of pinned transitive packages. HTTPX/Tenacity have bounded API ranges; AnyIO, certifi, HTTPcore and IDNA have explicit security floors. These floors address known advisories as of the update, not every possible future vulnerability. Do not bypass Home Assistant's dependency resolver or manually replace packages in a running HA container.

The Dependency security workflow installs the proposed runtime into a clean Python 3.14 environment. The runtime exports every installed external package and version, including transitive dependencies and pip. pip-audit runs from a separate tools environment against this complete resolved snapshot, with strict collection, no ignored vulnerability IDs and no continue-on-error. Only the project itself is excluded: the local release candidate may not exist on PyPI yet, and this workflow audits its external dependencies rather than the project's own source. No external dependency is excluded. It runs on pull requests, pushes, a weekly schedule and manual dispatch. It audits the resolved versions, not every version allowed by the metadata, and does not inspect users' installed systems. Database/network failures also fail the check.

Tests install requirements-test.txt and run python -m pytest. The Python 3.12 CI job also tests the HTTPX/Tenacity lower bounds. Package publication remains a separate manual operation: merging a dependency PR does not update PyPI or the integration's published requirement.

Dependabot groups Python and GitHub Actions version updates weekly. Every update requires review and relevant tests; there is no automatic merge or release. On a GitHub fork, the owner must explicitly enable Dependabot version updates under Settings > Advanced Security (wording may vary). Also enable the dependency graph, alerts and security updates. The configuration file alone does not prove these services are active.

To repeat an audit, follow the versioned security workflow: create separate runtime/audit environments, install the project into the former, export every installed external distribution including pip (excluding only this local project), then audit that pinned snapshot with --strict --no-deps --disable-pip. Do not install the scanner into a production HA container.

## Next-Gen import namespace (0.3.0+)

Version 0.3.0 uses `vaillant_netatmo_api_ng`. NG 0.2.0 and earlier provides upstream `vaillant_netatmo_api` and must not be installed alongside the original distribution. The version preparation changes no runtime Python files from the field-tested 0.3.0.dev0 candidate.

CI checks that built NG and original 0.13.1 own disjoint files and retain separate client/token/exception classes in both import orders. A secondary HA 2026.11.1 setup also demonstrated initial separate configuration and registries, with original files unchanged. These observations do not validate sustained authentication/updates, every control, compatible upgrades or rollback.

Both new-domain and compatible-domain integrations use the same new library. Older NG component code must move to the new imports together with its dependency requirement; a library-only upgrade is incompatible. Stable publication remains an explicit manual step after review.
