import json
from unittest.mock import Mock
from uuid import uuid4

import httpx
import pytest

from backend.app.agent.orchestrator import MAX_TOOL_CALLS
from backend.app.api.agent import get_provider
from backend.app.main import app
from backend.app.services.llm import GroqProvider

START = "2026-10-19T00:00:00Z"
END = "2026-11-18T00:00:00Z"


@pytest.fixture
def groq_mock(monkeypatch):
    handler = Mock()
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setitem(
            app.dependency_overrides, get_provider, lambda: GroqProvider(client, "test-key")
        )
        yield handler


def reply(*, text=None, calls=None):
    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": text, "tool_calls": calls}}]},
    )


def tool_call(name, arguments, *, call_id="call_1"):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def create_product(request_api, sku, stock):
    created = request_api("POST", "/products", json={
        "sku": sku, "name": f"Product {sku}", "price": "9.90", "stock": stock,
    })
    assert created.status_code == 201
    return created.json()["id"]


def create_order(request_api, product_id, quantity, status="completed", ordered_at=START):
    created = request_api("POST", "/orders", json={
        "ordered_at": ordered_at, "status": status,
        "items": [{"product_id": product_id, "quantity": quantity}],
    })
    assert created.status_code == 201


def test_agent_runs_tools_and_persists_restock_result(request_api, groq_mock):
    eligible = create_product(request_api, "eligible", 4)
    stock_boundary = create_product(request_api, "stock-boundary", 10)
    sales_boundary = create_product(request_api, "sales-boundary", 3)
    create_order(request_api, eligible, 31)
    create_order(request_api, eligible, 100, status="cancelled")
    create_order(request_api, eligible, 100, ordered_at=END)
    create_order(request_api, stock_boundary, 50)
    create_order(request_api, sales_boundary, 20)

    calls = [
        tool_call("get_low_stock_products", {"threshold": 10}, call_id="stock"),
        tool_call("get_sales_summary", {
            "start": START, "end": END, "product_id": eligible,
        }, call_id="sales"),
        tool_call("calculate_restock", {
            "start": START, "end": END, "stock_below": 10, "units_sold_above": 20,
        }, call_id="restock"),
    ]
    groq_mock.side_effect = [*(reply(calls=[call]) for call in calls), reply(text="建議補貨 16 件。")]
    result = request_api("POST", "/agent/runs", json={"message": " 補貨建議 "})
    assert result.status_code == 201
    run = result.json()
    assert run["status"] == "completed"
    assert run["user_message"] == "補貨建議"
    assert run["response"] == "建議補貨 16 件。"
    assert run["completed_at"].endswith("Z")
    stock, sales, restock = run["tool_executions"]
    assert all(step["status"] == "success" for step in (stock, sales, restock))
    assert stock["result"]["total"] == 2
    assert sales["result"]["units_sold"] == 31
    assert sales["result"]["revenue"] == "306.90"
    assert restock["result"]["total"] == 1
    assert restock["result"]["items"] == [{
        "product_id": eligible, "sku": "eligible", "name": "Product eligible",
        "stock": 4, "units_sold": 31, "average_daily_units": "1.03",
        "lead_time_units": 15, "recommended_quantity": 16,
    }]

    outgoing = [json.loads(call.args[0].content) for call in groq_mock.call_args_list]
    assert [tool["function"]["name"] for tool in outgoing[0]["tools"]] == [
        "get_low_stock_products", "get_sales_summary", "calculate_restock",
    ]
    history = outgoing[-1]["messages"]
    assert [item["tool_call_id"] for item in history if item["role"] == "tool"] == [
        "stock", "sales", "restock",
    ]
    assert json.loads(history[-1]["content"])["data"] == restock["result"]
    assert request_api("GET", f"/agent/runs/{run['id']}").json() == run


def test_agent_rejects_unknown_and_invalid_tools_without_saving_raw_args(request_api, groq_mock):
    groq_mock.side_effect = [
        reply(calls=[tool_call("execute_sql", {"command": "private text"})]),
        reply(calls=[tool_call("get_low_stock_products", {
            "threshold": "wrong", "other": "private text",
        }, call_id="call_2")]),
        reply(text="無法查詢。"),
    ]

    result = request_api("POST", "/agent/runs", json={"message": "請查詢庫存"})
    steps = result.json()["tool_executions"]
    assert [step["status"] for step in steps] == ["failed", "failed"]
    assert all(step["arguments"] is None and step["result"] is None for step in steps)
    assert "不在允許清單" in steps[0]["error_message"]
    assert "threshold" in steps[1]["error_message"]
    assert "private text" not in result.text


def test_agent_enforces_tool_limit_and_persists_failure(request_api, groq_mock):
    groq_mock.side_effect = [
        reply(calls=[tool_call("get_low_stock_products", {"threshold": 10}, call_id=f"call_{i}")])
        for i in range(MAX_TOOL_CALLS + 1)
    ]

    run = request_api("POST", "/agent/runs", json={"message": "請查詢庫存"}).json()
    assert run["status"] == "failed"
    assert "上限" in run["error_message"]
    assert len(run["tool_executions"]) == MAX_TOOL_CALLS
    assert groq_mock.call_count == MAX_TOOL_CALLS + 1
    assert "tools" not in json.loads(groq_mock.call_args.args[0].content)
    assert request_api("GET", f"/agent/runs/{run['id']}").json() == run


def test_provider_error_leaves_auditable_run(request_api, groq_mock):
    groq_mock.side_effect = httpx.ReadTimeout("private transport details")

    result = request_api("POST", "/agent/runs", json={"message": "測試"})
    assert result.status_code == 201
    run = result.json()
    assert run["status"] == "failed"
    assert run["completed_at"]
    assert run["tool_executions"] == []
    assert "逾時" in run["error_message"]
    assert "private transport details" not in result.text


def test_agent_validates_message_and_run_id(request_api, groq_mock):
    assert request_api("POST", "/agent/runs", json={"message": "  "}).status_code == 422
    assert request_api("POST", "/agent/runs", json={"message": "a" * 2001}).status_code == 422
    assert request_api("GET", "/agent/runs/not-a-uuid").status_code == 422
    assert request_api("GET", f"/agent/runs/{uuid4()}").status_code == 404
    groq_mock.assert_not_called()
