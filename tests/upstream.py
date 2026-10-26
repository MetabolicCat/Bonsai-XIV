"""A fake of the sources' web services, serving data the tests set."""

import csv
import io
import json
from typing import Any

import httpx

DATAMINING_RAW = "raw.githubusercontent.com/xivapi/ffxiv-datamining"
TEAMCRAFT_RAW = "raw.githubusercontent.com/ffxiv-teamcraft/ffxiv-teamcraft"
TEAMCRAFT_EXTRACTS = "libs/data/src/lib/extracts/extracts.json"

Row = dict[str, Any]


class Upstream:
    """Serves sheets, Teamcraft extracts and market data at a commit.

    Sheets not set are served with a header and no rows. `requests`
    records every path served, to check what was fetched.
    """

    def __init__(self) -> None:
        self.datamining_commit = "d" * 40
        self.teamcraft_commit = "t" * 40
        self.sheets: dict[str, list[Row]] = {}
        self.extracts: dict[str, Any] = {}
        self.market: dict[int, Row] = {}
        self.requests: list[str] = []

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self._handle))

    def _handle(self, request: httpx.Request) -> httpx.Response:
        url = request.url
        self.requests.append(f"{url.host}{url.path}")
        if url.host == "api.github.com":
            return self._head_commit(url.path)
        if url.host == "raw.githubusercontent.com":
            return self._raw(f"{url.host}{url.path}")
        if url.host == "universalis.app":
            return self._aggregated(url.path)
        return httpx.Response(404)

    def _head_commit(self, path: str) -> httpx.Response:
        commits = {
            "/repos/xivapi/ffxiv-datamining/commits/HEAD": self.datamining_commit,
            "/repos/ffxiv-teamcraft/ffxiv-teamcraft/commits/HEAD": (
                self.teamcraft_commit
            ),
        }
        if path not in commits:
            return httpx.Response(404)
        return httpx.Response(200, text=commits[path])

    def _raw(self, path: str) -> httpx.Response:
        prefix = f"{DATAMINING_RAW}/{self.datamining_commit}/csv/en/"
        if path.startswith(prefix) and path.endswith(".csv"):
            sheet = path.removeprefix(prefix).removesuffix(".csv")
            return httpx.Response(200, text=_csv(self.sheets.get(sheet, [])))
        if path == f"{TEAMCRAFT_RAW}/{self.teamcraft_commit}/{TEAMCRAFT_EXTRACTS}":
            return httpx.Response(200, text=json.dumps(self.extracts))
        return httpx.Response(404)

    def _aggregated(self, path: str) -> httpx.Response:
        ids = path.rsplit("/", 1)[1]
        results, failed = [], []
        for item_id in (int(i) for i in ids.split(",")):
            if item_id in self.market:
                results.append({"itemId": item_id, **self.market[item_id]})
            else:
                failed.append(item_id)
        return httpx.Response(200, json={"results": results, "failedItems": failed})


def _csv(rows: list[Row]) -> str:
    columns = ["#"] + sorted({key for row in rows for key in row} - {"#"})
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns, restval="0")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()
