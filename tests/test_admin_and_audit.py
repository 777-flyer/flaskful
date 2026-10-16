"""Tests for RBAC Admin endpoints and Security AuditLog trail."""


def test_rbac_admin_endpoints_and_audit_logs(client, auth_headers, admin_headers):
    """Standard users must receive 403 on /admin/* while admins can manage users and view audit logs."""
    # 1. Standard user cannot access /api/v1/admin/users -> 403 FORBIDDEN
    forbidden_res = client.get("/api/v1/admin/users", headers=auth_headers)
    assert forbidden_res.status_code == 403
    assert forbidden_res.get_json()["error"] == "FORBIDDEN"

    # 2. Admin can list users
    users_res = client.get("/api/v1/admin/users", headers=admin_headers)
    assert users_res.status_code == 200
    users_data = users_res.get_json()
    assert users_data["meta"]["total_items"] >= 2

    # Find standard user ID
    target_user = next(
        u for u in users_data["users"] if u["email"] == "test@example.com"
    )

    # 3. Admin can update user role or unlock account
    patch_res = client.patch(
        f"/api/v1/admin/users/{target_user['id']}",
        headers=admin_headers,
        json={"role": "admin", "unlock_account": True},
    )
    assert patch_res.status_code == 200
    assert patch_res.get_json()["role"] == "admin"

    # 4. Admin can query the security audit trail
    audit_res = client.get(
        "/api/v1/admin/audit-logs?action=ADMIN_USER_UPDATE",
        headers=admin_headers,
    )
    assert audit_res.status_code == 200
    audit_data = audit_res.get_json()
    assert len(audit_data["logs"]) >= 1
    assert audit_data["logs"][0]["action"] == "ADMIN_USER_UPDATE"

