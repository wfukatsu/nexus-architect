# Dependency Version Selection

Applies whenever a skill **emits a file that pins a version**: `build.gradle` / `pom.xml`,
`package.json`, `requirements.txt`, `Dockerfile` / `compose.yaml` image tags, Helm `Chart.yaml`
(`version` / `appVersion`), Kubernetes `apiVersion` and cluster version, Terraform
`required_version` / provider constraints, CI runner images, and the version numbers quoted in
generated docs.

Two rules, in order: **look the version up before writing it**, and **choose a stable one**.

## 1. Never write a version from memory

A version number recalled from training data, or copied out of a SKILL.md / rules example, is an
**unverified claim** — model knowledge has a cutoff and the examples in this repo are dated snapshots
that drift (this repo's own ScalarDB examples read `3.16.0` while the current stable line is well past
it). Resolve the real current state first, from the registry of record:

| Ecosystem | Authoritative lookup |
|-----------|----------------------|
| Maven / Gradle | `curl -s https://repo1.maven.org/maven2/<group/as/path>/<artifact>/maven-metadata.xml` — the full published list. Prefer this over `search.maven.org/solrsearch`, whose default ordering is *not* by version and will hand you an older release as if it were newest. |
| npm | `npm view <pkg> dist-tags --json` → the `latest` tag is the stable answer; `next` / `canary` / `beta` / `experimental` are not. `npm view <pkg> versions --json` for the full list. |
| GitHub-released tools (ScalarDB, CLIs, operators) | `gh release list -R <owner>/<repo> --limit 10` — the `Pre-release` marker is explicit, and `Latest` is the vendor's own designation. |
| Container images | `curl -s "https://hub.docker.com/v2/repositories/<ns>/<image>/tags?page_size=25&ordering=last_updated"` (official images: `ns` = `library`), or the registry's own tag API. |
| Terraform providers/modules | `curl -s https://registry.terraform.io/v1/providers/<ns>/<name>/versions` — the array is **unsorted**; sort by semver yourself, never take the last element. |
| Helm charts | `helm search repo <repo>/<chart> --versions` (after `helm repo update`). |
| Runtime support windows (Node, Java, K8s, Postgres, …) | `curl -s https://endoflife.date/api/<product>.json` — gives each cycle's LTS date and EOL date, which is how you tell "newest" from "supported". |
| Library docs / compatibility statements | context7 MCP (`resolve-library-id` → `query-docs`), then the vendor's release notes via WebFetch. |

Record the command or URL you used. If a lookup is impossible (no network, private registry, no
auth), **do not invent a number**: fall back in this order — the version already pinned in the target
project → the version in this repo's examples — and mark the entry `verified: false` with the reason,
then surface it to the user. An unverified pin is reported as unverified, never presented as current.

## 2. Choose stable, not merely newest

- **Exclude prereleases.** Anything carrying `-alpha`, `-beta`, `-rc`, `-M<n>`, `-SNAPSHOT`, `-dev`,
  `-canary`, `-next`, `-nightly`, or a `0.0.0-experimental-*` shape. Also never pin the moving tags
  `latest` / `stable` / `main` in an image reference — resolve them to a concrete version.
- **Prefer the ecosystem's LTS when it defines one**, and note that LTS is usually *not* the highest
  number: a just-cut Node/Java major is `Current`, not LTS, until its LTS date passes. Take the LTS
  and EOL dates from the lookup, not from assumption.
- **Never pin an EOL line.** If the version already in the project is past EOL, say so and propose the
  nearest supported line — that is a finding, not a silent upgrade.
- **A brand-new major is a flag, not a default.** A major released within roughly the last month, or
  one with no patch release yet, is adopted only when the user asks for it or the project already
  requires it; otherwise choose the previous stable major and say why.
- **The project wins over "latest".** An existing lockfile, BOM, parent POM, `dependencyManagement`,
  or platform constraint in the target project is binding: pin what it dictates and never bump
  unrelated dependencies as a side effect of the task at hand. Only the versions this task actually
  introduces are chosen fresh.
- **Compatibility gates the choice.** Cross-check the versions against each other and against any
  published matrix before settling: ScalarDB edition ↔ Java / backend versions (see
  @rules/scalardb-edition-profiles.md), Spring Boot ↔ Java ↔ Gradle, React ↔ Vite ↔ Storybook ↔
  TypeScript, Helm chart ↔ Kubernetes API, provider ↔ Terraform core. The newest of each is often not
  a working set; a mutually compatible slightly-older set beats a broken newest.

## 3. Record the decision

Write a **version decision table** into the artifact the skill already produces (generated docs /
report / `shared-context/decisions.md`), with one row per pinned dependency:

| Dependency | Chosen | Latest stable | Released | Source | Why this one | Rejected |
|------------|--------|---------------|----------|--------|--------------|----------|

Mirror it to `work/version-decisions.json` so later skills in the same project reuse the same
answers instead of re-resolving (and drifting):

```json
{
  "schema_version": 1,
  "checked_at": "2026-07-27T00:00:00Z",
  "confirmed_by_user": true,
  "entries": [
    {
      "name": "com.scalar-labs:scalardb", "ecosystem": "maven",
      "chosen": "3.18.0", "latest_stable": "3.18.0", "released": "2026-05-01",
      "source": "https://repo1.maven.org/maven2/com/scalar-labs/scalardb/maven-metadata.xml",
      "verified": true, "lts": false,
      "why": "newest stable on the published line; matches the Cluster SDK version in use",
      "rejected": [{"version": "3.18.0-alpha.1", "why": "prerelease"}]
    }
  ]
}
```

Reuse an entry whose `checked_at` is under 7 days old; re-resolve when it is older, when the user
passes `--refresh-versions`, or when the dependency set changes.

## 4. Confirming the choice with the user (configurable)

Whether the resolved set is **confirmed with the user or adopted silently** is the user's choice:

| Setting | Effect |
|---------|--------|
| `--confirm-versions` | Always present the version decision table and get an explicit answer (AskUserQuestion) before writing any pinned file. |
| `--no-confirm-versions` | Adopt the resolved stable versions without asking. The table is still written and printed. |
| `options.confirm_versions: true \| false` in `work/pipeline-progress.json` | Project-level default, so the choice is made once instead of per invocation. |
| neither set | Interactive runs **ask**; `--auto` runs adopt without asking. |

Precedence: explicit flag → `options.confirm_versions` → the default above.

Regardless of the setting, **always ask** — even under `--auto` / `--no-confirm-versions` — when the
choice is not routine:

- a lookup failed and the pin would be unverified;
- the only current option is a brand-new major, or the project's existing pin is EOL;
- no mutually compatible set exists without downgrading something the project already uses;
- a paid/licensed edition or a private registry is required to obtain the version.

`--dry-run` resolves and reports the table but writes no pinned file.
