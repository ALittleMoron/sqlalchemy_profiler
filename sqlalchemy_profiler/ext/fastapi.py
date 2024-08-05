import uuid

from fastapi import FastAPI, Request
from sqlalchemy import Engine
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from sqlalchemy_profiler.profilers import SQLAlchemyQueryCounter, SQLAlchemyQueryProfiler
from sqlalchemy_profiler.types import LogFunctionProtocol, ReportPath


def add_query_profiling_middleware(  # noqa: PLR0913
    app: FastAPI,
    engine: Engine | type[Engine] = Engine,
    *,
    request_id: str | uuid.UUID | None = None,
    log_function: LogFunctionProtocol = print,
    report_to: "ReportPath | None" = None,
    log_query_stats: bool = False,
) -> FastAPI:
    """Add query profiling middleware to FastAPI.

    Note: this function also can be used with starlette instance, but only before version 1.0.0,
    because `middleware` decorator is deprecated and will be (or, maybe, already removed) in this
    version.
    """

    async def _profiling_middleware(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        with SQLAlchemyQueryProfiler(
            engine=engine,
            request_id=request_id,
            log_function=log_function,
            log_query_stats=log_query_stats,
        ) as profiler:
            log_function(f"Profiler {request.url}: start profiling. {request_id=}")
            response = await call_next(request)
        profiler.report(report_to)
        log_function(f"Profiler {profiler.request_id} finished.")
        return response

    app.middleware("http")(_profiling_middleware)
    return app


def add_query_counter_middleware(
    app: FastAPI,
    engine: Engine | type[Engine] = Engine,
    *,
    request_id: str | uuid.UUID | None = None,
    log_function: LogFunctionProtocol = print,
    log_query_stats: bool = False,
) -> FastAPI:
    """Add query counting middleware to FastAPI.

    Note: this function also can be used with starlette instance, but only before version 1.0.0,
    because `middleware` decorator is deprecated and will be (or, maybe, already removed) in this
    version.
    """

    async def _counter_middleware(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        with SQLAlchemyQueryCounter(
            engine=engine,
            request_id=request_id,
            log_function=log_function,
            log_query_stats=log_query_stats,
        ) as profiler:
            log_function(
                f"Counter {request.url}: start counting queries.",
            )
            response = await call_next(request)
        log_function(
            f"Counter {request.url}: finish with count {profiler.collect()}. {request_id=}",
        )
        return response

    app.middleware("http")(_counter_middleware)
    return app
