# Container Compliance

CalTopo History includes an automated container-compliance workflow for releases and changes that affect the Docker image.

## What the workflow does

The GitHub Actions workflow `.github/workflows/container-compliance.yml`:

1. builds the container image from the current repository;
2. generates an SPDX JSON Software Bill of Materials (SBOM) with Anchore Syft;
3. runs a full Aqua Security Trivy license scan against the built image;
4. uploads both the machine-readable JSON report and a human-readable table as workflow artifacts.

The workflow runs when relevant container/application files change on `main`, on matching pull requests, and can also be started manually with `workflow_dispatch`.

## Artifacts

A successful run produces:

- `caltopo-history-sbom.spdx.json` — SPDX JSON SBOM generated from the built container image;
- `trivy-license-report.json` — machine-readable full container license scan;
- `trivy-license-report.txt` — human-readable full container license scan.

The Trivy reports are retained as GitHub Actions artifacts for 30 days by the workflow configuration.

## Why the license scan is review-oriented

Trivy provides an opinionated risk classification for detected licenses. This is useful for identifying components that deserve review, but it is not itself a legal compatibility determination.

For example, reciprocal or GPL-family licenses can legitimately occur in normal Debian operating-system packages inside a container while still requiring a case-specific distribution/compliance analysis rather than an automatic rejection.

For that reason:

- the container license scan produces complete review artifacts and fails only if the scan itself cannot complete;
- the separate Python runtime dependency license guard remains the automated gate for newly introduced/unreviewed application dependency license families;
- maintainers should review the container license report before publishing binary images.

## Public-image release checklist

Before publishing a CalTopo History container image:

1. confirm the normal test and dependency-license workflow passes;
2. confirm the container-compliance workflow passes;
3. download and retain the SPDX SBOM for the release;
4. review the Trivy license report for new or unexpected licenses/packages;
5. update `THIRD-PARTY-NOTICES.md` when material dependencies or license conclusions change;
6. ensure the published image identifies `AGPL-3.0-only` and the source repository through OCI labels;
7. make Corresponding Source for the exact published version available to users as required by the AGPL;
8. retain the SBOM and license report together with the release records.

## Tools

The workflow currently uses:

- Anchore `sbom-action` / Syft for SPDX SBOM generation;
- Aqua Security Trivy for full container license discovery and classification.

Tool versions are pinned in the workflow and should be reviewed periodically.

## Scope

The SBOM and Trivy report cover the built container image, including application dependencies and operating-system packages discoverable by the scanners. They complement, rather than replace, the source-level dependency review documented in `THIRD-PARTY-NOTICES.md`.

This process is a technical compliance aid and does not constitute legal advice.
