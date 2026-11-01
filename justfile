# List the recipes.
default:
    @just --list

# Run the test suite. *args forwards to pytest.
test *args:
    uv run --locked pytest {{ args }}

# Run every pre-commit hook over the whole tree. *args forwards to `pre-commit run` (e.g. a hook id).
check *args:
    uv run --locked pre-commit run --all-files {{ args }}

# Run the test suite on every supported Python, from the 3.12 minimum up. *args forwards to pytest.
test-all-pythons *args:
    for v in 3.12 3.13 3.14; do echo "== Python $v"; uv run --locked --isolated --python "$v" pytest {{ args }} || exit 1; done
