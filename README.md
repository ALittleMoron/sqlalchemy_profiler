
# Dev utils

![coverage](./coverage.svg)

## For what?

I made this project to avoid copy-pasting with utils in my projects. I was aiming to simplify
working with sqlalchemy, FastAPI and other libraries.

## Install

With pip:

```bash
pip install sqlalchemy_profiler
```

With pdm:

```bash
pdm install sqlalchemy_profiler
```

With poetry:

```bash
poetry add sqlalchemy_profiler
```

## Profiling

Profiling utils. Now available 2 profilers and 2 middlewares (FastAPI) for such profilers:

1. SQLAlchemyQueryProfiler - profile entire sqlalchemy query - it text, params, duration.
2. SQLAlchemyQueryCounter - count sqlalchemy queries.
