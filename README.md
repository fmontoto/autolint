# autolint
Run your linters automatically.

autolint is a command line utility for running code style enforcers (linters) on the files of a repository.

# Quickstart use
autolint includes a default configuration, ready to run the linters on your directory:
```sh
autolint .
```
It will run and print out the linters' output. It will return 0 if every run returned 0 or 1 otherwise. This makes it perfectly suitable as pre-commit hook of your repository. Configure to run before every commit using
```sh
printf '#!/bin/sh\nautolint .\n' >> .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```
