"""模块说明：tests/conftest.py 的主要实现与辅助逻辑。"""

import asyncio
import inspect
import warnings

# Silence noisy warnings (notably sqlite ResourceWarning) across the test suite
warnings.filterwarnings("ignore")


def pytest_configure(config):
	"""注册项目内使用的 pytest 标记。"""
	config.addinivalue_line("markers", "asyncio: mark test to run in asyncio loop")


def pytest_pyfunc_call(pyfuncitem):
	"""在无 pytest-asyncio 插件时，执行 coroutine 测试函数。"""
	if not inspect.iscoroutinefunction(pyfuncitem.obj):
		return None

	fixture_args = {
		name: pyfuncitem.funcargs[name] for name in pyfuncitem._fixtureinfo.argnames
	}
	asyncio.run(pyfuncitem.obj(**fixture_args))
	return True
