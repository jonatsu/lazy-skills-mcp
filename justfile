# List the recipes.
default:
    @just --list

# Run the test suite. *args forwards to pytest.
test *args:
    uv run --locked pytest {{ args }}

# Run every pre-commit hook over the whole tree. *args forwards to `pre-commit run` (e.g. a hook id).
check *args:
    pre-commit run --all-files {{ args }}
