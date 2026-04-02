"""Shared test fixtures and MongoDB mock setup."""

import asyncio
import pytest
import mongomock
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class AsyncCursor:
    """Async cursor wrapper for mongomock results."""

    def __init__(self, cursor):
        self._cursor = cursor
        self._limit_val = None

    def limit(self, n):
        self._cursor = self._cursor.limit(n)
        self._limit_val = n
        return self

    def sort(self, *args, **kwargs):
        self._cursor = self._cursor.sort(*args, **kwargs)
        return self

    async def to_list(self, length=None):
        if length:
            self._cursor = self._cursor.limit(length)
        return list(self._cursor)

    def __aiter__(self):
        self._iter = iter(list(self._cursor))
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class AsyncCollection:
    """Async wrapper around a mongomock collection."""

    def __init__(self, collection):
        self._col = collection

    async def insert_one(self, doc):
        return self._col.insert_one(doc)

    async def insert_many(self, docs):
        return self._col.insert_many(docs)

    async def find_one(self, filter=None, *args, **kwargs):
        return self._col.find_one(filter, *args, **kwargs)

    def find(self, filter=None, *args, **kwargs):
        cursor = self._col.find(filter, *args, **kwargs)
        return AsyncCursor(cursor)

    async def update_one(self, filter, update, upsert=False):
        return self._col.update_one(filter, update, upsert=upsert)

    async def update_many(self, filter, update, upsert=False):
        return self._col.update_many(filter, update, upsert=upsert)

    async def delete_many(self, filter):
        return self._col.delete_many(filter)

    async def count_documents(self, filter):
        return self._col.count_documents(filter)

    def aggregate(self, pipeline):
        result = list(self._col.aggregate(pipeline))
        return AsyncCursor(iter([]))  # mongomock aggregate returns list directly

    async def drop(self):
        self._col.drop()


class AsyncAggregateResult:
    """Wrapper to make aggregate results async-iterable."""

    def __init__(self, results):
        self._results = results

    async def to_list(self, length=None):
        if length:
            return self._results[:length]
        return self._results


class AsyncMongoCollection:
    """
    Full async MongoDB collection mock using mongomock.

    Supports aggregate with $match, $addFields, $sort, $filter, $size, etc.
    """

    def __init__(self, name="test_collection"):
        self._client = mongomock.MongoClient()
        self._db = self._client["test_db"]
        self._col = self._db[name]
        self.name = name

    async def insert_one(self, doc):
        return self._col.insert_one(doc)

    async def insert_many(self, docs):
        return self._col.insert_many(docs)

    async def find_one(self, filter=None, *args, **kwargs):
        return self._col.find_one(filter, *args, **kwargs)

    def find(self, filter=None, *args, **kwargs):
        cursor = self._col.find(filter, *args, **kwargs)
        return AsyncCursor(cursor)

    async def update_one(self, filter, update, upsert=False):
        return self._col.update_one(filter, update, upsert=upsert)

    async def update_many(self, filter, update, upsert=False):
        return self._col.update_many(filter, update, upsert=upsert)

    async def delete_many(self, filter):
        return self._col.delete_many(filter)

    async def count_documents(self, filter):
        return self._col.count_documents(filter)

    def aggregate(self, pipeline):
        """Execute aggregate pipeline manually since mongomock has limited support."""
        docs = list(self._col.find())
        results = _run_pipeline(docs, pipeline)
        return AsyncAggregateResult(results)

    async def drop(self):
        self._col.drop()


def _run_pipeline(docs: list, pipeline: list) -> list:
    """Execute a simplified MongoDB aggregation pipeline on a list of docs."""
    results = list(docs)
    for stage in pipeline:
        if "$match" in stage:
            results = [d for d in results if _matches(d, stage["$match"])]
        elif "$addFields" in stage:
            for doc in results:
                for field, expr in stage["$addFields"].items():
                    doc[field] = _eval_expr(expr, doc)
        elif "$sort" in stage:
            for key, direction in reversed(list(stage["$sort"].items())):
                results.sort(key=lambda d: d.get(key, 0) or 0, reverse=(direction == -1))
        elif "$limit" in stage:
            results = results[: stage["$limit"]]
    return results


def _matches(doc: dict, query: dict) -> bool:
    """Check if a document matches a query filter."""
    for key, condition in query.items():
        val = doc.get(key)
        if isinstance(condition, dict):
            for op, operand in condition.items():
                if op == "$ne" and val == operand:
                    return False
                if op == "$gte" and (val is None or val < operand):
                    return False
                if op == "$lte" and (val is None or val > operand):
                    return False
                if op == "$in" and val not in operand:
                    return False
                if op == "$exists" and operand and val is None and key not in doc:
                    return False
        else:
            if val != condition:
                return False
    return True


def _eval_expr(expr, doc):
    """Evaluate a MongoDB aggregation expression."""
    if isinstance(expr, str) and expr.startswith("$"):
        return doc.get(expr[1:])
    if isinstance(expr, dict):
        if "$filter" in expr:
            f = expr["$filter"]
            input_val = _eval_expr(f["input"], doc) or []
            as_name = f.get("as", "this")
            cond = f["cond"]
            return [
                item for item in input_val
                if _eval_cond(cond, {f"${as_name}": item}, doc)
            ]
        if "$ifNull" in expr:
            for candidate in expr["$ifNull"]:
                val = _eval_expr(candidate, doc)
                if val is not None:
                    return val
            return None
        if "$size" in expr:
            arr = _eval_expr(expr["$size"], doc)
            return len(arr) if arr else 0
        if "$max" in expr:
            path = expr["$max"]
            if isinstance(path, str) and "." in path:
                parts = path.lstrip("$").split(".")
                arr = doc.get(parts[0], [])
                if arr:
                    vals = [item.get(parts[1]) for item in arr if item.get(parts[1]) is not None]
                    return max(vals) if vals else None
            return None
        if "$gte" in expr:
            left = _eval_expr(expr["$gte"][0], doc)
            right = _eval_expr(expr["$gte"][1], doc)
            if left is None or right is None:
                return False
            return left >= right
    return expr


def _eval_cond(cond, variables, doc):
    """Evaluate a condition expression with variables."""
    if isinstance(cond, dict):
        if "$gte" in cond:
            left = _resolve_var(cond["$gte"][0], variables, doc)
            right = _resolve_var(cond["$gte"][1], variables, doc)
            if left is None or right is None:
                return False
            return left >= right
        if "$lte" in cond:
            left = _resolve_var(cond["$lte"][0], variables, doc)
            right = _resolve_var(cond["$lte"][1], variables, doc)
            if left is None or right is None:
                return False
            return left <= right
    return True


def _resolve_var(expr, variables, doc):
    """Resolve a variable reference like $$sig.date."""
    if isinstance(expr, str):
        if expr.startswith("$$"):
            parts = expr.split(".")
            var_name = parts[0]  # e.g. "$$sig"
            obj = variables.get(var_name.replace("$", "$", 1))
            if obj is None:
                # Try lookup: $$sig -> $sig in variables
                obj = variables.get("$" + var_name[2:])
            if obj and len(parts) > 1:
                return obj.get(parts[1])
            return obj
        if expr.startswith("$"):
            return doc.get(expr[1:])
    return expr


@pytest.fixture
def mock_db():
    """Provide a dict-like mock database that returns AsyncMongoCollection instances."""

    class MockDB:
        def __init__(self):
            self._collections = {}

        def __getitem__(self, name):
            if name not in self._collections:
                self._collections[name] = AsyncMongoCollection(name)
            return self._collections[name]

    return MockDB()
