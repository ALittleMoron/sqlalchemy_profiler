import traceback
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from dev_utils.common import get_object_class_absolute_name, trim_and_plain_text

if TYPE_CHECKING:
    from sqlalchemy.engine.cursor import CursorResult
    from sqlalchemy.sql import ClauseElement
    from sqlalchemy.sql.compiler import Compiled

T = TypeVar("T")


class QueryInfo:
    """Data class (not actually has @dataclass decorator) for profiling results.

    Contains full info about query itself, but not any additional context.
    """

    repr_full_query_text: ClassVar[bool] = False
    repr_template: ClassVar[str] = (
        "<class {cls_path} text='{text}' params={params} duration={duration:3f} "
        "rowcount={rowcount}>"
    )

    def __init__(  # noqa: PLR0913
        self,
        *,
        text: "ClauseElement | Compiled",
        stack: list[traceback.FrameSummary],
        start_time: float,
        end_time: float,
        params_dict: dict[Any, Any],
        results: "CursorResult[Any]",
    ) -> None:
        self.text = trim_and_plain_text(str(text))
        self.params = params_dict
        self.stack = self.stack_text = stack
        self.start_time = start_time
        self.end_time = end_time
        self.duration = end_time - start_time
        # BUG: results.rowcount is always -1. Remove or fix it.
        self.rowcount = results.rowcount

    def __repr__(self) -> str:  # noqa: D105
        return self.repr_template.format(
            cls_path=get_object_class_absolute_name(self.__class__),
            text=str(self.text)[:40] if self.repr_full_query_text else str(self.text),
            params=self.params,
            duration=self.duration,
            rowcount=self.rowcount,
        )
