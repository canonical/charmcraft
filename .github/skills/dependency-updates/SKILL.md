---
name: dependency-updates
description: "Updates Charmcraft dependency constraints and lockfiles for release work. Use when bumping craft-* and related dependencies in project manifests."
---

# Dependency updates

## Scope

Dependency maintenance only:

- Update dependency constraints in project manifests.
- Regenerate lockfiles so resolved metadata stays in sync.
- Keep changes focused on dependency files.
- When release notes are requested, generate the contributors list from commit
  history using the Starflow contributors tool.

## Inputs

- Repository root.
- Target dependencies and version constraints.
- Release comparison refs when contributors are needed
  (for example `--old-ref=4.3.0 --new-ref=HEAD`).

## Actions

1. **Find dependency sources**:

   - `pyproject.toml`
   - `uv.lock`
   - Other dependency files only when explicitly requested

2. **Apply dependency updates**:

   - Update only the requested dependencies.
   - Preserve existing constraint style unless a change is required.

3. **Regenerate lockfile state**:

   - Run `uv lock` after manifest updates.
   - Ensure lockfile metadata reflects updated constraints.

4. **Keep scope tight**:

   - Do not modify unrelated files.
   - Do not perform opportunistic refactors.

5. **Generate contributors for release notes** (when requested):

   - Run:
     `python ../starflow/tools/contributors.py --project charmcraft --old-ref=<old-ref> --new-ref=<new-ref>`
   - Use the generated `contributors.html` in the current working directory as
     the source of truth for contributor names.
   - Extract and deduplicate contributor handles, then format them as
     `:literalref:` entries for release notes.
   - Use this generated list to populate the contributors section instead of
     manually collecting usernames.

6. **Filter cross-repo non-feature PRs** (when generating contributors/features):

   - Parse repository sections and commit/PR rows from `contributors.html`.
   - For repositories other than the main project repository (for example, for
     a Charmcraft release, any repo where `repo != charmcraft`), mark rows as
     excluded when the commit title starts with one of these tags:
     - `ci:`
     - `chore:`
     - `build:`
     - `ci(...)`
     - `chore(...)`
     - `build(...)`
     - `fix(tests)...`
     - `feat(Makefile)...`
   - For cross-repo `docs:` / `docs(...)` rows, include them only if the PR
     touches `docs/common/`. Otherwise, exclude them.
   - Equivalent matching rule:
     `(?i)^(ci|chore|build)(\\(|:|\\b)`
   - Additional equivalent matching rules:
     - `(?i)^fix\\(tests?\\)(\\(|:|\\b)`
     - `(?i)^feat\\(makefile\\)(\\(|:|\\b)`
     - `(?i)^docs(\\(|:|\\b)` (conditionally included only with `docs/common/` changes)
   - To evaluate the `docs/common/` condition, inspect PR changed files via the
     GitHub API/CLI when a PR link is present.
   - If a docs PR has no PR link (`n/a`) or changed-file lookup fails, exclude
     it by default (cannot verify `docs/common/`).
   - Exclude these rows from:
     - contributor aggregation
     - "What's new" / feature candidate extraction
   - Keep a visible exclusion log (repo, PR link, title, reason) while
     drafting release notes, so filtering is auditable.
   - These exclusion rules apply only to cross-repo rows (`repo != <project>`),
     and do not apply to rows from the main project repository.

7. **Filter main-project maintenance PRs** (when generating contributors/features):

   - For rows from the main project repository (for example, for Charmcraft
     releases, rows where `repo == charmcraft`), mark rows as excluded when the
     commit title starts with:
     - `test:`
     - `ci:`
     - `build:`
     - `test(...)`
     - `ci(...)`
     - `build(...)`
   - Equivalent matching rule:
     `(?i)^(test|ci|build)(\\(|:|\\b)`
   - Exclude these rows from:
     - contributor aggregation
     - "What's new" / feature candidate extraction
   - Keep these exclusions in the same audit log with explicit reason
     (`main-project maintenance tag`).

8. **Build fixed-bugs content for release notes** (when requested):

   - If asked to carry patch-release fixes forward (for example, include 4.3.1
     fixes in 4.4.0 notes), copy the fix text exactly from the prior release
     notes page section for that patch release.
   - Do not expand that section with additional fixes unless explicitly asked.
   - Do not include commit-hash-only bug-fix bullets unless explicitly asked.

9. **Build known-issues content from source of truth**:

   - For each known issue ID included in release notes, fetch the current issue
     title from GitHub (for example via `gh issue view <id>`).
   - Use the fetched title text verbatim in the bullet description.
   - Do not paraphrase known-issue titles.

## Constraints

- Do not add release-note, changelog, or announcement text about dependency bumps.
- Keep communication about updated dependencies internal to PR/commit context only.
- Prefer a single focused commit for dependency changes unless the user asks otherwise.
- If `../starflow/tools/contributors.py` is unavailable, report the blocker
  clearly and do not invent contributor names.
- Do not treat cross-repo `ci`/`chore`/`build` PRs as feature work.
- Do not treat cross-repo `fix(tests)` or `feat(Makefile)` PRs as feature work.
- Do not treat main-project `test`/`ci`/`build` rows as feature work.
- Do not include contributors who only appear in excluded rows.
- Do not invent known-issue descriptions; use GitHub issue titles as the source
  of truth.

## Output

A minimal dependency-update change set that updates manifests and lockfiles without
documentation/announcement edits. When requested for release notes, also provide
the contributor list derived from `contributors.html`, filtered to exclude
cross-repo and main-project maintenance-tag rows per the filter rules above.
The final contributors section must be generated from this filtered set only
(that is, filtering can reduce the contributor list).
