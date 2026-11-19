# Code signing policy

> Status: **Pending approval**. This page exists so the repository satisfies the
> SignPath Foundation requirement that a code signing policy be specified on the
> project home page and on download/release pages. Until approval is granted,
> all published binaries are unsigned and are accompanied by SHA-256 checksums.

Free code signing provided by [SignPath.io](https://about.signpath.io),
certificate by [SignPath Foundation](https://signpath.org).

## What is signed

- Windows PE executables published on GitHub Releases:
  - `Setup-<product>.exe` (installer)
  - `<product>.exe` (main application, onedir)
  - `<product>.exe` embedded in the portable ZIP archive
- All signatures are Authenticode with SHA-256 and a trusted RFC 3161 timestamp.

## Build and signing process

- Release artifacts are built automatically from this public repository by
  GitHub Actions (`.github/workflows/release.yml`) on GitHub-hosted Windows
  runners.
- The unsigned executables are uploaded as a GitHub workflow artifact, then a
  signing request is submitted to SignPath.io. SignPath verifies the origin of
  the build (repository, branch, workflow, hosted runner) before signing.
- Only CI-built artifacts are submitted for signing. Nothing is signed on a
  developer machine. The private key never leaves SignPath's HSM; this project
  does not hold or store it.
- Every signing request is reviewed and **manually approved** by an Approver
  before the signed artifacts are published.
- Product name and product version are written into each PE version resource at
  build time and enforced by the SignPath artifact configuration
  (`.signpath/artifact-configurations/default.xml`).
- After signing, the signed executables are placed back into the onedir bundle
  and the portable ZIP is rebuilt (ZIP CRC changes when a member is replaced).
  Signatures are verified in CI before a release is created.

## Team roles (single-maintainer project)

- **Authors** (commit access, may modify the repository without additional review): `<GitHub 用户名>`
- **Reviewers** (review every change proposed by non-committers before merge): `<GitHub 用户名>`
- **Approvers** (approve each signing request in SignPath): `<GitHub 用户名>`

All three roles are held by the repository owner. Two-factor authentication is
enabled for both the GitHub and the SignPath accounts. All external pull
requests are reviewed before merge.

## Privacy policy

See [PRIVACY.md](PRIVACY.md).

This program will not transfer any information to other networked systems
unless specifically requested by the user or the person installing or operating
it. Weather lookups and the optional user-configured AI assistant endpoint only
run when the user invokes them. Third-party components are listed in the
repository; none of them introduces additional data collection by this project.

## Verification

```powershell
Get-AuthenticodeSignature .\Setup-<product>.exe | Format-List Status, SignerCertificate, TimeStamperCertificate
Get-FileHash .\Setup-<product>.exe -Algorithm SHA256
```

Expected signer: `CN=SignPath Foundation`. A valid signature with a trusted
timestamp remains verifiable after the certificate expires.

## Distribution

- GitHub Releases: `https://github.com/<your-account>/<repo>/releases`
- Project download page: `https://<your-account>.github.io/<repo>/download.html`

All binaries are distributed free of charge.
