help:	## Show all Makefile targets.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[33m%-30s\033[0m %s\n", $$1, $$2}'

format:	## Run the code autoformatter (ruff).
	uv run ruff format .

lint:	## Run linters.
	uv run ruff check .
	uv run ruff format --check .

test:	## Run tests via pytest.
	uv run pytest tests
