import os
import queue
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from contextlib import suppress
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar, final

from dev_utils.common import trim_and_plain_text
from dev_utils.guards import all_dict_keys_are_str
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from sqlalchemy_profiler.containers import QueryInfo
from sqlalchemy_profiler.types import NoLog, NoLogStub, ReportPath
from sqlalchemy_profiler.utils import pretty_query_info

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection
    from sqlalchemy.engine.cursor import CursorResult
    from sqlalchemy.sql import ClauseElement
    from sqlalchemy.sql.compiler import SQLCompiler
    from sqlalchemy.util import immutabledict

    from sqlalchemy_profiler.types import LogFunctionProtocol


T = TypeVar("T")


class BaseSQLAlchemyProfiler(ABC, Generic[T]):
    """Abstract base sqlalchemy profiling class.

    It is a generic class, so use it with typing. Generic uses in:

    * ``__init__``: self.collector - queue of ``<Generic>`` objects. For example, it could be
        queue of QueryInfo objects.
    * ``collect``: return value - Sequence of ``<Generic>``.
    """

    def __init__(
        self,
        engine: "type[Engine] | Engine | AsyncEngine" = Engine,
        *,
        request_id: str | uuid.UUID | None = None,
        log_function: "LogFunctionProtocol | NoLogStub" = NoLog,
        log_query_stats: bool = False,
    ) -> None:
        self.started = False
        if isinstance(engine, AsyncEngine):
            self.engine = engine.sync_engine
        else:
            self.engine = engine
        self.log_function = log_function
        self.log_query_stats = log_query_stats

        self.request_id = str(request_id) if request_id is not None else str(uuid.uuid4())

        self._result: T | None = None
        self.collector: queue.Queue[T] = queue.Queue()

    @abstractmethod
    def _before_exec(
        self,
        conn: "Connection",
        clause: "SQLCompiler",
        multiparams: "Sequence[Mapping[str, Any]]",
        params: "Mapping[str, Any]",
        execution_options: "immutabledict[str, Any]",
    ) -> None:
        """Method, which will be bounded to `before_execute` handler in SQLAlchemy."""  # noqa: D401
        raise NotImplementedError

    @abstractmethod
    def _after_exec(  # noqa: PLR0913
        self,
        conn: "Connection",
        clause: "ClauseElement",
        multiparams: "Sequence[Mapping[str, Any]]",
        params: "Mapping[str, Any]",
        execution_options: "immutabledict[str, Any]",
        results: "CursorResult[Any]",
    ) -> None:
        """Method, which will be bounded to `after_execute` handler in SQLAlchemy."""  # noqa: D401
        raise NotImplementedError

    @final
    def _extract_parameters_from_results(
        self,
        query_results: "CursorResult[Any]",
    ) -> dict[str, Any]:
        """Get parameters from query results object."""
        params_dict: dict[str, Any] = {}
        compiled_parameters = getattr(query_results.context, "compiled_parameters", [])
        if not compiled_parameters or not isinstance(  # pragma: no cover
            compiled_parameters,
            Sequence,
        ):
            return {}
        for compiled_param_dict in compiled_parameters:
            if not isinstance(compiled_param_dict, dict):  # pragma: no cover
                continue
            if not all_dict_keys_are_str(compiled_param_dict):  # type: ignore  pragma: no cover
                continue
            params_dict.update(compiled_param_dict)
        return params_dict

    def start(self) -> None:
        """Start the profiling process.

        Add engine-level handlers from events, which will fill collector with data.
        """
        if self.started is False and not isinstance(
            self.log_function,
            NoLogStub,
        ):
            msg = f"Profiling session is already started! {self.request_id=}"
            self.log_function(msg)

        self.started = True
        if not event.contains(self.engine, "before_execute", self._before_exec):
            event.listen(self.engine, "before_execute", self._before_exec)
        if not event.contains(self.engine, "after_execute", self._after_exec):
            event.listen(self.engine, "after_execute", self._after_exec)

    def stop(self) -> None:
        """Stop the profiling process.

        Remove engine-level handlers from events - no other data will be put in collector.
        """
        if self.started is False and not isinstance(
            self.log_function,
            NoLogStub,
        ):
            msg = f"Profiling session is already stopped. {self.request_id=}"
            self.log_function(msg)

        self.started = False
        if event.contains(self.engine, "before_execute", self._before_exec):
            event.remove(self.engine, "before_execute", self._before_exec)
        if event.contains(self.engine, "after_execute", self._after_exec):
            event.remove(self.engine, "after_execute", self._after_exec)

    def __enter__(self) -> Self:
        """Enter of context manager.

        Start the profiler by executing ``self.start()`` method.
        """
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,  # noqa: F401, F841, RUF100
        exc: BaseException | None,  # noqa: F401, F841, RUF100
        traceback: TracebackType | None,  # noqa: F401, F841, RUF100
    ) -> None:
        """Exit of context manager.

        Stop the profiler by executing ``self.stop()`` method.
        """
        self.stop()

    def collect(self) -> Sequence[T]:
        """Collect all information from queue.

        Collect means "transform to list". You can override this method, if you want to return
        other type. Use self._result as return value and assign this attribute in profiling methods.
        """
        queries: list[T] = []
        with suppress(queue.Empty):
            while True:
                queries.append(self.collector.get(block=False))

        return queries

    def report(
        self,
        stdout: "ReportPath | None" = None,  # noqa: ARG002, F401, RUF100
    ) -> None:
        """Make report about profiling."""
        return  # pragma: no coverage


class SQLAlchemyQueryProfiler(BaseSQLAlchemyProfiler[QueryInfo]):
    """SQLAlchemy query profiler."""

    def _before_exec(
        self,
        conn: "Connection",
        clause: "SQLCompiler",
        multiparams: "Sequence[Mapping[str, Any]]",  # noqa: ARG002, F401, F841, RUF100
        params: "Mapping[str, Any]",
        execution_options: "immutabledict[str, Any]",  # noqa: ARG002, F401, F841, RUF100
    ) -> None:
        conn.info.setdefault("query_start_time", []).append(time.time())
        if self.log_query_stats and not isinstance(
            self.log_function,
            NoLogStub,
        ):
            msg = (
                f"Query started: {trim_and_plain_text(str(clause))}. Params: {params}. "
                f"{self.request_id=}"
            )
            self.log_function(msg)

    def _after_exec(  # noqa: PLR0913
        self,
        conn: "Connection",
        clause: "ClauseElement",
        multiparams: "Sequence[Mapping[str, Any]]",  # noqa: ARG002, F401, F841, RUF100
        params: "Mapping[str, Any]",
        execution_options: "immutabledict[str, Any]",  # noqa: ARG002, F401, F841, RUF100
        results: "CursorResult[Any]",
    ) -> None:
        end_time = time.time()
        start_time = conn.info["query_start_time"].pop(-1)
        if self.log_query_stats and not isinstance(
            self.log_function,
            NoLogStub,
        ):
            msg = (
                f'Query "{trim_and_plain_text(str(clause))}" (params: {params}) '
                f"finished in {(end_time - start_time) * 1000} milliseconds. "
                f"{self.request_id=}"
            )
            self.log_function(msg)

        text = clause
        with suppress(AttributeError):
            text = clause.compile(dialect=conn.engine.dialect)

        params_dict = self._extract_parameters_from_results(results)

        stack = traceback.extract_stack()[:-1]
        query_info = QueryInfo(
            text=text,
            stack=stack,
            start_time=start_time,
            end_time=end_time,
            params_dict=params_dict,
            results=results,
        )

        self.collector.put(query_info)

    def report(  # type: ignore[reportIncompatibleMethodOverride] # noqa: D102
        self,
        stdout: "ReportPath | None" = None,
    ) -> None:
        data = pretty_query_info(self.collect())
        if stdout is None:
            if isinstance(self.log_function, NoLogStub):
                return
            self.log_function(data)
            return
        if isinstance(stdout, str):
            stdout = Path(stdout)
        if isinstance(stdout, Path | os.PathLike):
            Path(stdout).write_text(data)
        else:
            stdout.write(data)


class SQLAlchemyQueryCounter(BaseSQLAlchemyProfiler[int]):
    """SQLAlchemy query counter."""

    def collect(self) -> int:  # type: ignore[reportIncompatibleMethodOverride] # noqa: D102
        if self._result is None:  # pragma: no cover
            return 0
        return self._result

    def _before_exec(
        self,
        conn: "Connection",  # noqa: ARG002, F401, F841, RUF100
        clause: "SQLCompiler",  # noqa: ARG002, F401, F841, RUF100
        multiparams: "Sequence[Mapping[str, Any]]",  # noqa: ARG002, F401, F841, RUF100
        params: "Mapping[str, Any]",  # noqa: ARG002, F401, F841, RUF100
        execution_options: "immutabledict[str, Any]",  # noqa: ARG002, F401, F841, RUF100
    ) -> None:
        self._result = 0

    def _after_exec(  # noqa: PLR0913
        self,
        conn: "Connection",  # noqa: ARG002, F401, F841, RUF100
        clause: "ClauseElement",  # noqa: ARG002, F401, F841, RUF100
        multiparams: "Sequence[Mapping[str, Any]]",  # noqa: ARG002, F401, F841, RUF100
        params: "Mapping[str, Any]",  # noqa: ARG002, F401, F841, RUF100
        execution_options: "immutabledict[str, Any]",  # noqa: ARG002, F401, F841, RUF100
        results: "CursorResult[Any]",  # noqa: ARG002, F401, F841, RUF100
    ) -> None:
        if self._result is None:  # pragma: no cover
            self._result = 0
        self._result += 1

    def start(self) -> None:  # noqa: D102
        if not self.started:  # pragma: no cover
            self._result = 0
        return super().start()
