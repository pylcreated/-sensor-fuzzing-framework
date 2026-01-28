from sensor_fuzz.security import AccessController, AuditLog, VoltageCurrentGuard, encrypt, decrypt


def test_access_control():
    ac = AccessController()
    ac.assign_role("alice", "tester")
    assert ac.can_use_poc("alice") is True
    assert ac.can_manage_poc("alice") is False


def test_audit_log(tmp_path):
    log = AuditLog(tmp_path / "audit.log")
    log.record("alice", "use_poc", "mqtt-1")
    assert len(log.entries()) == 1
    assert log.entries()[0]["user"] == "alice"


def test_voltage_guard():
    guard = VoltageCurrentGuard(max_voltage=10.0, max_current=0.2)
    cut, msg = guard.evaluate({"voltage": 11.0, "current": 0.1})
    assert cut is True
    assert msg == "cut-off"


def test_crypto_roundtrip():
    salt, iv, ct = encrypt(b"hello", "pwd")
    pt = decrypt(salt, iv, ct, "pwd")
    assert pt == b"hello"
