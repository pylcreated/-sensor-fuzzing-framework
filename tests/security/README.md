# 安全与硬件保护测试指引

- POC 覆盖率目标>=90%：运行内置/自定义 POC，记录成功/失败。
- 硬件保护：使用可调电源模拟过压/过流，验证 VoltageCurrentGuard 触发率>=99.9%。
- 数据安全：验证 AES-256 加密解密正确，审计日志记录 POC 使用行为。

## 建议步骤
1) 启用 AccessController，限制 POC 权限用户。
2) 运行 POC 注入（MQTT/HTTP/OPCUA/Profinet），记录命中情况。
3) 触发硬件保护阈值，检查 cut-off 信号。
