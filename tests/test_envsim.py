from sensor_fuzz.envsim.interfaces import EnvironmentSimulator


class DummySim:
    def set_temperature(self, value_c: float) -> None:
        self.t = value_c

    def set_light_intensity(self, lux: float) -> None:
        self.l = lux

    def set_vibration(self, freq_hz: float, amplitude: float) -> None:
        self.v = (freq_hz, amplitude)


def test_envsim_protocol():
    sim: EnvironmentSimulator = DummySim()
    sim.set_temperature(25.0)
    sim.set_light_intensity(100.0)
    sim.set_vibration(5.0, 0.1)
    assert getattr(sim, "t", 0) == 25.0
