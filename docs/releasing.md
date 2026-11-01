# Releasing

A release is a version tag on `main`. Pushing the tag runs the release job in
[.github/workflows/cicd.yml](../.github/workflows/cicd.yml), which publishes a GitHub release holding the wheel and
the source archive. GitHub releases and tags are the only distribution channel; nothing is published to PyPI.
Users install a release with `uv tool install git+https://github.com/jonatsu/lazy-skills-mcp@vX.Y.Z`.

## Choose the Version

The project follows semantic versioning, counted from 0.x. A change to anything in the README's interface contract
is breaking and raises the minor version while the major version is 0. Anything else raises the patch version.

## Cut the Release

1. Set `version` in `pyproject.toml` to `X.Y.Z`, then run `uv lock` so `uv.lock` records the same version.
2. In `CHANGELOG.md`, rename `## Unreleased` to `## X.Y.Z` and add a new, empty `## Unreleased` above it. The release
   job copies the section under exactly `## X.Y.Z` into the release notes, and fails when that heading is missing.
3. Run `just check` and `just test-all-pythons`.
4. Commit the three files as `chore: release X.Y.Z`, push `main`, and wait for CI to pass on that commit.
5. Tag the release commit and push the tag:

   ```bash
   git tag -a vX.Y.Z -m "lazy-skills-mcp X.Y.Z"
   git push origin vX.Y.Z
   ```

6. Watch the run with `gh run watch`. It repeats every check, builds the package, and refuses to publish when the
   tag does not match the built version.
7. Check the release with `gh release view vX.Y.Z`. It should hold `lazy_skills_mcp-X.Y.Z.tar.gz`, the wheel, and
   the changelog section as its notes.

A tag containing `rc`, such as `v0.3.0rc1`, publishes a prerelease with generated notes instead of the changelog
section. Its `pyproject.toml` version must match the tag without the `v`.

## When the Release Job Fails

If no GitHub release exists yet, fix the cause on `main`, then move the tag to the fixed commit:

```bash
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
```

Then repeat step 5. Once a release exists, someone may already have installed it, so do not move its tag. Fix the
problem in a new patch release instead.
