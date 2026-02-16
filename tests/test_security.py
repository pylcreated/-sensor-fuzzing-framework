"""模块说明：tests/test_security.py 的主要实现与辅助逻辑。"""

# 导入安全模块中的相关类和函数
from sensor_fuzz.security import AccessController, AuditLog, VoltageCurrentGuard, encrypt, decrypt


# 测试访问控制功能的函数
def test_access_control():
    """测试访问控制功能。"""
    # 创建访问控制实例并分配角色
    ac = AccessController()
    ac.assign_role("alice", "tester")

    # 验证角色权限
    assert ac.can_use_poc("alice") is True
    assert ac.can_manage_poc("alice") is False


# 测试审计日志功能的函数
def test_audit_log(tmp_path):
    """测试审计日志功能。"""
    # 创建审计日志实例并记录日志
    log = AuditLog(tmp_path / "audit.log")
    log.record("alice", "use_poc", "mqtt-1")

    # 验证日志记录是否正确
    assert len(log.entries()) == 1
    assert log.entries()[0]["user"] == "alice"


# 测试电压保护功能的函数
def test_voltage_guard():
    """测试电压保护功能。"""
    # 创建电压保护实例并评估输入
    guard = VoltageCurrentGuard(max_voltage=10.0, max_current=0.2)
    cut, msg = guard.evaluate({"voltage": 11.0, "current": 0.1})

    # 验证保护机制是否正确触发
    assert cut is True
    assert msg == "cut-off"


# 测试加密和解密功能的函数
def test_crypto_roundtrip():
    """测试加密和解密功能。"""
    # 定义测试数据
    plaintext = "Hello, World!"
    key = "secret_key"

    # 加密数据
    ciphertext = encrypt(plaintext, key)

    # 解密数据并验证结果
    decrypted = decrypt(ciphertext, key)
    assert decrypted == plaintext
