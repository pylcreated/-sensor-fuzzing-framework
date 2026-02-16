"""模块说明：tests/test_security.py 的主要实现与辅助逻辑。"""

from sensor_fuzz.security import AccessController, AuditLog, VoltageCurrentGuard, encrypt, decrypt


def test_access_control():
    """方法说明：执行 test access control 相关逻辑。"""
    ac = AccessController()
    ac.assign_role("alice", "tester")
    assert ac.can_use_poc("alice") is True
    assert ac.can_manage_poc("alice") is False


def test_audit_log(tmp_path):
    """方法说明：执行 test audit log 相关逻辑。"""
    log = AuditLog(tmp_path / "audit.log")
    log.record("alice", "use_poc", "mqtt-1")
    assert len(log.entries()) == 1
    assert log.entries()[0]["user"] == "alice"


def test_voltage_guard():
    """方法说明：执行 test voltage guard 相关逻辑。"""
    guard = VoltageCurrentGuard(max_voltage=10.0, max_current=0.2)
    cut, msg = guard.evaluate({"voltage": 11.0, "current": 0.1})
    assert cut is True
    assert msg == "cut-off"


def test_crypto_roundtrip():
    """方法说明：执行 test crypto roundtrip 相关逻辑。"""
    salt, iv, ct = encrypt(b"hello", "pwd")
    pt = decrypt(salt, iv, ct, "pwd")
    assert pt == b"hello"
