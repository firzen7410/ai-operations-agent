import pytest

START = "2026-11-01T00:00:00Z"
END = "2026-12-01T00:00:00Z"


def product(request_api, sku, price):
    response = request_api(
        "POST", "/products", json={"sku": sku, "name": sku, "price": price, "stock": 3}
    )
    assert response.status_code == 201
    return response.json()["id"]


def order(request_api, items, *, ordered_at=START, status="completed"):
    return request_api(
        "POST", "/orders", json={"ordered_at": ordered_at, "status": status, "items": items}
    )


def test_create_and_read_order_preserves_stock_and_price(request_api):
    product_id = product(request_api, "A", "10.20")
    other_id = product(request_api, "B", "4.00")
    response = order(
        request_api,
        [{"product_id": product_id, "quantity": 8}, {"product_id": other_id, "quantity": 1}],
        ordered_at="2026-11-01T08:00:00+08:00",
    )
    assert response.status_code == 201
    created = response.json()
    assert created["status"] == "completed"
    assert created["ordered_at"] == START
    assert [item["unit_price"] for item in created["items"]] == ["10.20", "4.00"]

    product_path = f"/products/{product_id}"
    assert request_api("GET", product_path).json()["stock"] == 3
    assert request_api("PATCH", product_path, json={"price": "99.00"}).status_code == 200
    assert request_api("GET", f"/orders/{created['id']}").json() == created
    assert request_api("DELETE", product_path).status_code == 409
    assert request_api("GET", product_path).status_code == 200
    assert request_api("GET", "/orders/999").status_code == 404


def test_bad_order_does_not_create_an_order(request_api):
    product_id = product(request_api, "A", "2.00")
    valid_item = {"product_id": product_id, "quantity": 1}
    assert order(
        request_api, [valid_item, {"product_id": 999, "quantity": 2}]
    ).status_code == 404
    assert order(request_api, [valid_item, valid_item]).status_code == 422
    assert order(request_api, [valid_item | {"quantity": 0}]).status_code == 422
    assert order(request_api, [], status="invalid").status_code == 422
    assert order(request_api, [valid_item], ordered_at="2026-11-01T00:00:00").status_code == 422
    assert request_api("GET", "/orders").json()["total"] == 0
    assert request_api("DELETE", f"/products/{product_id}").status_code == 204


def test_order_pagination_and_sales_summary(request_api):
    first = product(request_api, "A", "9.90")
    second = product(request_api, "B", "2.25")
    first_item = {"product_id": first, "quantity": 3}
    second_item = {"product_id": second, "quantity": 2}

    for timestamp, status, items in [
        (START, "completed", [first_item, second_item]),
        (START, "completed", [first_item]),
        (START, "pending", [first_item]),
        (START, "cancelled", [first_item]),
        ("2026-10-31T23:59:59Z", "completed", [first_item]),
        (END, "completed", [first_item]),
    ]:
        assert order(request_api, items, ordered_at=timestamp, status=status).status_code == 201

    params = {"start": "2026-11-01T08:00:00+08:00", "end": END}
    page = request_api(
        "GET", "/orders", params=params | {"status": "completed", "limit": 1, "offset": 1}
    ).json()
    assert page["total"] == 2
    assert page["items"][0]["id"] == 1

    summary = request_api("GET", "/sales/summary", params=params).json()
    assert summary == {
        "start": START, "end": END, "units_sold": 8, "revenue": "63.90",
        "items": [
            {"product_id": first, "sku": "A", "name": "A", "units_sold": 6, "revenue": "59.40"},
            {"product_id": second, "sku": "B", "name": "B", "units_sold": 2, "revenue": "4.50"},
        ],
    }
    filtered = request_api("GET", "/sales/summary", params=params | {"product_id": second}).json()
    assert filtered["units_sold"] == 2
    assert filtered["revenue"] == "4.50"
    assert filtered["items"] == [summary["items"][1]]

    empty = request_api("GET", "/sales/summary", params=params | {"product_id": 999}).json()
    assert empty["units_sold"] == 0
    assert empty["revenue"] == "0.00"
    assert empty["items"] == []


@pytest.mark.parametrize("endpoint", ["/orders", "/sales/summary"])
def test_rejects_invalid_date_range(request_api, endpoint):
    assert request_api("GET", endpoint, params={"start": END, "end": START}).status_code == 422
    assert request_api(
        "GET", endpoint, params={"start": "2026-11-01T00:00:00", "end": END}
    ).status_code == 422
