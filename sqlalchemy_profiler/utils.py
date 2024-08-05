from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy_profiler.containers import QueryInfo


def pretty_query_info(info: "QueryInfo | Sequence[QueryInfo]") -> str:
    """Pretty text from QueryInfo.

    Make string from information to log it.
    """
    query_template = (
        "index: {query_index}\n"
        "query text: {query_text}\n"
        "query params: {query_params}\n"
        "query duration: {query_duration}\n"
        "query rowcount (may be incorrect): {query_rowcount}\n"
    )
    if not isinstance(info, Sequence):
        info = [info]
    return "\n".join(
        query_template.format(
            query_index=idx,
            query_text=query.text,
            query_params=query.params,
            query_duration=query.duration,
            query_rowcount=query.rowcount,
        )
        for idx, query in enumerate(info)
    )
