import pytest


def create_product(request_api, **changes):
    data = {"sku": "SKU-1", "name": "Coffee Filter", "price": "9.90", "stock": 5}
    return request_api("POST", "/products", json=data | changes)


def test_product_crud(request_api):
    response = create_product(request_api, sku=" SKU-1 ")
    assert response.status_code == 201
    product = response.json()
    assert product["sku"] == "SKU-1"
    assert product["price"] == "9.90"
    assert product["created_at"].endswith("Z")
    path = f"/products/{product['id']}"
    assert request_api("GET", path).json() == product

    updated = request_api("PATCH", path, json={"stock": 8, "price": "10.50"})
    assert updated.status_code == 200
    assert updated.json()["stock"] == 8
    assert updated.json()["price"] == "10.50"
    assert updated.json()["name"] == product["name"]
    assert updated.json()["updated_at"] > product["updated_at"]

    deleted = request_api("DELETE", path)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert request_api("GET", path).status_code == 404


def test_duplicate_sku_and_invalid_patch(request_api):
    assert create_product(request_api).status_code == 201
    assert create_product(request_api).status_code == 409
    second = create_product(request_api, sku="SKU-2").json()
    path = f"/products/{second['id']}"

    assert request_api("PATCH", path, json={"sku": "SKU-1"}).status_code == 409
    assert request_api("PATCH", path, json={"stock": None}).status_code == 422
    assert request_api("PATCH", path, json={"id": 12}).status_code == 422
    assert request_api("GET", path).json()["sku"] == "SKU-2"


@pytest.mark.parametrize(
    "changes",
    [{"price": "-0.01"}, {"price": "1.234"}, {"stock": -1}, {"name": "   "}, {"sku": ""}],
)
def test_product_validation(request_api, changes):
    assert create_product(request_api, **changes).status_code == 422


def test_product_search_and_pagination(request_api):
    first = create_product(request_api, name="Filter 10%").json()
    second = create_product(request_api, sku="SKU-2", name="Filter 100", stock=9).json()
    create_product(request_api, sku="SKU-3", name="Filter 102", stock=10)
    create_product(request_api, sku="SKU-4", name="Scale", stock=5)

    page = request_api(
        "GET", "/products", params={"name": "fIlTeR", "stock_below": 10, "limit": 1, "offset": 1}
    ).json()
    assert page == {"items": [second], "total": 2, "limit": 1, "offset": 1}
    assert request_api("GET", "/products", params={"name": "%"}).json()["items"] == [first]
    assert request_api(
        "GET", "/products", params={"sku": "SKU-1", "min_stock": 5, "max_stock": 5}
    ).json()["items"] == [first]
    assert request_api("GET", "/products", params={"limit": 101}).status_code == 422
    assert request_api(
        "GET", "/products", params={"min_stock": 9, "max_stock": 5}
    ).status_code == 422
