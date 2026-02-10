import pytest

@pytest.mark.asyncio
async def test_create_url(client):

    user_data = {
        "target_url": "http://test",
    }

    response = await client.post("/urls", json=user_data)

    assert response.status_code == 200

    data = response.json()
    key = data['key']

    assert data["target_url"] == "http://test/"



@pytest.mark.asyncio
async def test_get_key(client):

    user_data = {
        "target_url": "http://test",
    }

    response = await client.post("/urls", json=user_data)

    assert response.status_code == 200

    data = response.json()
    key = data['key']

    result = await client.get(f"/{key}")

    # 3. Перевіряємо (Assert) Редірект - це 307
    assert result.status_code == 307


@pytest.mark.asyncio
async def test_cliks(client):

    user_data = {
        "target_url": "http://test",
    }

    response = await client.post("/urls", json=user_data)

    data = response.json()

    key = data['key']

    assert data['clicks'] == 0

    result = await client.get(f"/{key}")

    response_stats = await client.get("/all_urls")
    assert response_stats.status_code == 200

    all_urls = response_stats.json()
    # Шукаємо наш URL у списку (бо там їх може бути багато)
    # Ми фільтруємо список, щоб знайти той, де key співпадає з нашим
    my_url_stats = next(item for item in all_urls if item["key"] == key)

    # 4. Перевіряємо лічильник у СВІЖИХ даних
    assert my_url_stats['clicks'] == 1


@pytest.mark.asyncio
async def test_put_url(client):

    user_data = {
        "target_url": "http://test",
    }

    response = await client.post("/urls", json=user_data)

    data = response.json()

    key = data['key']

    user_put = {
        "target_url": "http://gogle.com/",
    }

    response_stats = await client.put(f"/{key}", json=user_put)

    assert response_stats.status_code == 200

    updated_data = response_stats.json()

    assert updated_data["target_url"] == "http://gogle.com/"


@pytest.mark.asyncio
async def test_delete_url(client):

    user_data = {
        "target_url": "http://test",
    }

    response = await client.post("/urls", json=user_data)

    data = response.json()

    key = data['key']

    response_stats = await client.delete(f"/{key}")

    assert response_stats.status_code == 200

    updated_data = response_stats.json()

    assert updated_data == {'message':f'Url {key} deleted'}

    response_check = await client.get(f"/{key}")

    # Ми очікуємо 404, бо лінка вже не має існувати
    assert response_check.status_code == 404

@pytest.mark.asyncio
async def test_curr_url(client):

    user_data = {
        "target_url": "http://test/",
    }

    response = await client.post("/urls", json=user_data)

    data = response.json()

    key = data['key']

    response_stats = await client.get(f"/urls/{key}")

    assert response_stats.status_code == 200

    updated_data = response_stats.json()

    assert updated_data["target_url"] == "http://test/"

    assert updated_data["key"] == key
