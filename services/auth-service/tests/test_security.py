from app.security import hash_password, verify_password


def test_password_hash_is_salted_and_not_plain():
    first, second = hash_password("password123"), hash_password("password123")
    assert "password123" not in first and first != second          
    assert verify_password("password123", first) and verify_password("password123", second)
    assert not verify_password("password124", first)
    assert not verify_password("password123", "broken-hash")
