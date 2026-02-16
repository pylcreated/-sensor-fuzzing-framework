"""模块说明：tests/test_envsim.py 的主要实现与辅助逻辑。"""

from sensor_fuzz.envsim.interfaces import EnvironmentSimulator


class DummySim:
    """类说明：封装 DummySim 的相关行为。"""
    def set_temperature(self, value_c: float) -> None:
        """方法说明：执行 set temperature 相关逻辑。"""
        self.t = value_c

    def set_light_intensity(self, lux: float) -> None:
        """方法说明：执行 set light intensity 相关逻辑。"""
        self.l = lux

    def set_vibration(self, freq_hz: float, amplitude: float) -> None:
        """方法说明：执行 set vibration 相关逻辑。"""
        self.v = (freq_hz, amplitude)


def test_envsim_protocol():
    """方法说明：执行 test envsim protocol 相关逻辑。"""
    sim: EnvironmentSimulator = DummySim()
    sim.set_temperature(25.0)
    sim.set_light_intensity(100.0)
    sim.set_vibration(5.0, 0.1)
    assert getattr(sim, "t", 0) == 25.0
