from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# TODO: tests for logs.  # noqa: FIX002, TD002, TD003


# def test_middlewares_correct_install(test_sync_app: "TestClient") -> None:
#     result = test_sync_app.get("/")
#     jsn = result.json()
#     assert isinstance(jsn, list)
#     assert len(jsn) == 10  # type: ignore[reportUnknownArgumentType] # noqa: PLR2004
