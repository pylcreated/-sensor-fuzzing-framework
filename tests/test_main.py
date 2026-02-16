"""Test main application entry point."""
import sys
import signal
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import pytest

# 将src目录添加到Python路径中
# 这样可以导入src目录下的模块
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# 导入主程序模块中的相关函数和类
from sensor_fuzz.__main__ import (
    main, ApplicationError, setup_signal_handlers, validate_config_file,
    setup_logging, start_system_monitor, stop_system_monitor, start_exporter
)

# 定义测试主程序功能的测试类
class TestMainApplication:
    """测试主程序功能。"""

    def test_application_error(self):
        """测试ApplicationError异常。"""
        # 创建ApplicationError实例并验证其属性
        error = ApplicationError("Test error", 42)
        assert str(error) == "Test error"
        assert error.exit_code == 42

    def test_setup_signal_handlers(self):
        """测试信号处理程序的设置。"""
        # 验证设置信号处理程序是否不会抛出异常
        setup_signal_handlers()

    def test_validate_config_file_exists(self, tmp_path):
        """测试配置文件验证（文件存在）。"""
        # 创建临时配置文件
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("test: content")

        # 验证配置文件是否正确加载
        result = validate_config_file(str(config_file))
        assert result == config_file

    def test_validate_config_file_not_exists(self):
        """测试配置文件验证（文件不存在）。"""
        # 验证当配置文件不存在时是否抛出异常
        with pytest.raises(ApplicationError) as exc_info:
            validate_config_file("nonexistent.yaml")

        assert exc_info.value.exit_code == 2
        assert "not found" in str(exc_info.value)

    def test_validate_config_file_unreadable(self, tmp_path):
        """测试配置文件验证（文件不可读）。"""
        # 创建临时配置文件
        config_file = tmp_path / "unreadable.yaml"
        config_file.write_text("test: content")

        # 模拟文件不可读
        with patch('pathlib.Path.open') as mock_open:
            mock_open.side_effect = OSError("Permission denied")

            with pytest.raises(ApplicationError) as exc_info:
                validate_config_file(str(config_file))

            assert exc_info.value.exit_code == 2
            assert "Cannot read" in str(exc_info.value)

    def test_validate_config_file_invalid_encoding(self, tmp_path):
        """测试配置文件验证（编码无效）。"""
        # 创建包含无效UTF-8字节的文件
        config_file = tmp_path / "invalid.yaml"
        with open(config_file, 'wb') as f:
            f.write(b'\xff\xfe\xfd')

        # 验证是否抛出编码错误异常
        with pytest.raises(ApplicationError) as exc_info:
            validate_config_file(str(config_file))

        assert exc_info.value.exit_code == 2
        assert "Cannot read" in str(exc_info.value)

    def test_main_basic_import(self):
        """测试主函数的基本导入。"""
        # 验证主函数及相关函数是否可调用
        assert callable(main)
        assert callable(setup_signal_handlers)
        assert callable(validate_config_file)

    @patch('sensor_fuzz.__main__.setup_logging')
    @patch('sensor_fuzz.__main__.validate_config_file')
    def test_main_config_validation_failure(self, mock_validate, mock_logging):
        """测试主函数在配置验证失败时的行为。"""
        # 模拟配置验证失败
        mock_validate.side_effect = ApplicationError("Config error", 2)

        with patch('sys.exit') as mock_exit:
            main()

        # 验证程序是否正确退出
        mock_exit.assert_called_once_with(2)

    @patch('sensor_fuzz.__main__.setup_logging')
    @patch('sensor_fuzz.__main__.start_system_monitor')
    @patch('sensor_fuzz.__main__.start_exporter')
    @patch('sensor_fuzz.__main__.setup_signal_handlers')
    @patch('sensor_fuzz.__main__.validate_config_file')
    @patch('sensor_fuzz.__main__.ConfigLoader')
    @patch('sensor_fuzz.__main__.ConfigVersionStore')
    @patch('sensor_fuzz.__main__.ExecutionEngine')
    @patch('sensor_fuzz.__main__.ConfigReloader')
    @patch('sensor_fuzz.__main__.run_full')
    @patch('sensor_fuzz.__main__.stop_system_monitor')
    def test_main_full_execution_success(self, mock_stop_monitor, mock_run_full,
                                        mock_reloader_class, mock_engine_class,
                                        mock_version_store_class, mock_loader_class,
                                        mock_validate, mock_signal_handlers,
                                        mock_start_exporter, mock_start_monitor,
                                        mock_logging):
        """测试主函数的完整执行流程（成功）。"""
        # 设置模拟对象的行为
        mock_validate.return_value = Path("config/test.yaml")
        mock_loader_instance = MagicMock()
        mock_config = MagicMock()
        mock_config.sensors = {"temp": {}}
        mock_loader_instance.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader_instance

        mock_version_store_instance = MagicMock()
        mock_version_store_class.return_value = mock_version_store_instance

        mock_engine_instance = MagicMock()
        mock_engine_class.return_value = mock_engine_instance

        mock_reloader_instance = MagicMock()
        mock_reloader_class.return_value = mock_reloader_instance

        mock_exporter = MagicMock()
        mock_start_exporter.return_value = mock_exporter

        with patch('sys.exit') as mock_exit:
            main()

        # 验证所有组件是否正确启动
        mock_logging.assert_called_once()
        mock_start_monitor.assert_called_once()
        mock_start_exporter.assert_called_once_with(port=8000)
        mock_signal_handlers.assert_called_once()
        mock_validate.assert_called_once_with("config/sensor_protocol_config.yaml")
        mock_loader_instance.load.assert_called_once()
        mock_version_store_instance.save.assert_called_once()
        mock_engine_class.assert_called_once()
        mock_reloader_class.assert_called_once()
        mock_run_full.assert_called_once()
        mock_reloader_instance.stop.assert_called_once()
        mock_stop_monitor.assert_called_once()
        mock_exporter.stop.assert_called_once()

        mock_exit.assert_called_once_with(0)