"""模块说明：tests/test_envsim.py 的主要实现与辅助逻辑。"""

# 导入环境模拟器接口
from sensor_fuzz.envsim.interfaces import EnvironmentSimulator
from sensor_fuzz.envsim.simulator import SimulatedEnvironment

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


def test_simulated_environment_snapshot_no_noise():
    """验证仿真器在无噪声时的快照输出。"""
    sim = SimulatedEnvironment(seed=7)
    sim.set_temperature(31.2)
    sim.set_light_intensity(500.0)
    sim.set_vibration(20.0, 0.3)
    sim.advance(2.5)

    sample = sim.snapshot()
    assert sample["timestamp_s"] == 2.5
    assert sample["temperature_c"] == 31.2
    assert sample["light_lux"] == 500.0
    assert sample["vibration_freq_hz"] == 20.0
    assert sample["vibration_amplitude"] == 0.3


def test_simulated_environment_scenario_replay():
    """验证仿真器支持步骤化场景回放。"""
    sim = SimulatedEnvironment(seed=123)
    timeline = sim.run_scenario(
        [
            {"temperature_c": 22.0, "light_lux": 260.0, "dt_s": 1.0},
            {
                "temperature_c": 24.0,
                "vibration_freq_hz": 50.0,
                "vibration_amplitude": 0.8,
                "dt_s": 2.0,
            },
        ]
    )

    assert len(timeline) == 2
    assert timeline[0]["timestamp_s"] == 1.0
    assert timeline[1]["timestamp_s"] == 3.0
    assert timeline[1]["vibration_freq_hz"] == 50.0
    assert timeline[1]["vibration_amplitude"] == 0.8


def test_simulated_environment_noise_injection_changes_value():
    """验证开启噪声后采样值会偏离理想值。"""
    sim = SimulatedEnvironment(seed=99)
    sim.set_temperature(25.0)
    sample = sim.snapshot(temperature_noise_std=0.8)
    assert sample["temperature_c"] != 25.0
