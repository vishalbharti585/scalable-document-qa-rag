import io


def test_cross_tenant_document_isolation(client, user_a, user_b):
    # User A uploads a document
    file_bytes = b"Classified revenue projections for Q4 belong strictly to User Alpha."
    data = {"file": (io.BytesIO(file_bytes), "alpha_confidential.txt")}
    r_upload = client.post(
        "/api/v1/documents",
        data=data,
        content_type="multipart/form-data",
        headers=user_a["headers"]
    )
    assert r_upload.status_code == 201
    doc_a_id = r_upload.get_json()["data"]["document"]["id"]

    # User B tries to access User A's document directly by ID
    r_b_view = client.get(f"/api/v1/documents/{doc_a_id}", headers=user_b["headers"])
    assert r_b_view.status_code == 404

    # User B lists their documents (must not include User A's document)
    r_b_list = client.get("/api/v1/documents", headers=user_b["headers"])
    assert r_b_list.status_code == 200
    doc_ids = [d["id"] for d in r_b_list.get_json()["data"]["documents"]]
    assert doc_a_id not in doc_ids

    # User B tries to delete User A's document
    r_b_del = client.post(f"/api/v1/documents/{doc_a_id}", headers=user_b["headers"])
    assert r_b_del.status_code in (404, 405)


def test_cross_tenant_chat_isolation(client, user_a, user_b):
    # User A creates a conversation
    r_conv = client.post("/api/v1/conversations", json={"title": "Alpha Chat"}, headers=user_a["headers"])
    conv_a_id = r_conv.get_json()["data"]["conversation"]["id"]

    # User B tries to view User A's conversation
    r_b_conv = client.get(f"/api/v1/conversations/{conv_a_id}", headers=user_b["headers"])
    assert r_b_conv.status_code == 404

    # User B tries to post a message into User A's conversation
    r_b_msg = client.post(
        f"/api/v1/conversations/{conv_a_id}/messages",
        json={"message": "Infiltrating query"},
        headers=user_b["headers"]
    )
    assert r_b_msg.status_code == 404
