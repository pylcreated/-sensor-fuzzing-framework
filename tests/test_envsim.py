"""模块说明：tests/test_envsim.py 的主要实现与辅助逻辑。"""

# 导入环境模拟器接口
from sensor_fuzz.envsim.interfaces import EnvironmentSimulator

# 定义一个模拟环境的类，用于测试环境模拟器的功能
class DummySim:
    """模拟环境的类，用于测试环境模拟器的功能。"""

    def set_temperature(self, value_c: float) -> None:
        """设置温度的方法。"""
        self.t = value_c

    def set_light_intensity(self, lux: float) -> None:
        """设置光强的方法。"""
        self.l = lux

    def set_vibration(self, freq_hz: float, amplitude: float) -> None:
        """设置振动的方法。"""
        self.v = (freq_hz, amplitude)

# 测试环境模拟器协议的函数
def test_envsim_protocol():
    """测试环境模拟器协议的功能。"""
    # 创建DummySim实例并验证其方法是否正确设置属性
    sim = DummySim()

    # 设置温度并验证
    sim.set_temperature(25.0)
    assert sim.t == 25.0

    # 设置光强并验证
    sim.set_light_intensity(500.0)
    assert sim.l == 500.0

    # 设置振动并验证
    sim.set_vibration(60.0, 1.5)
    assert sim.v == (60.0, 1.5)
