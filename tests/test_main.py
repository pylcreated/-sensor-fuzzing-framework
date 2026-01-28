"""Test main application entry point."""
import sys
import signal
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from sensor_fuzz.__main__ import (
    main, ApplicationError, setup_signal_handlers, validate_config_file,
    setup_logging, start_system_monitor, stop_system_monitor, start_exporter
)


class TestMainApplication:
    """Test main application functionality."""

    def test_application_error(self):
        """Test ApplicationError exception."""
        error = ApplicationError("Test error", 42)
        assert str(error) == "Test error"
        assert error.exit_code == 42

    def test_setup_signal_handlers(self):
        """Test signal handler setup."""
        # This should not raise any exceptions
        setup_signal_handlers()

    def test_validate_config_file_exists(self, tmp_path):
        """Test config file validation with existing file."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("test: content")

        result = validate_config_file(str(config_file))
        assert result == config_file

    def test_validate_config_file_not_exists(self):
        """Test config file validation with non-existing file."""
        with pytest.raises(ApplicationError) as exc_info:
            validate_config_file("nonexistent.yaml")

        assert exc_info.value.exit_code == 2
        assert "not found" in str(exc_info.value)

    def test_validate_config_file_unreadable(self, tmp_path):
        """Test config file validation with unreadable file."""
        config_file = tmp_path / "unreadable.yaml"
        config_file.write_text("test: content")

        # On Windows, we can't easily make files unreadable, so we'll mock the open
        with patch('pathlib.Path.open') as mock_open:
            mock_open.side_effect = OSError("Permission denied")

            with pytest.raises(ApplicationError) as exc_info:
                validate_config_file(str(config_file))

            assert exc_info.value.exit_code == 2
            assert "Cannot read" in str(exc_info.value)

    def test_validate_config_file_invalid_encoding(self, tmp_path):
        """Test config file validation with invalid encoding."""
        config_file = tmp_path / "invalid.yaml"
        # Write some invalid UTF-8 bytes
        with open(config_file, 'wb') as f:
            f.write(b'\xff\xfe\xfd')

        with pytest.raises(ApplicationError) as exc_info:
            validate_config_file(str(config_file))

        assert exc_info.value.exit_code == 2
        assert "Cannot read" in str(exc_info.value)

    def test_main_basic_import(self):
        """Test that main function can be imported and basic functions work."""
        # This test ensures the main module can be imported without issues
        assert callable(main)
        assert callable(setup_signal_handlers)
        assert callable(validate_config_file)

    @patch('sensor_fuzz.__main__.setup_logging')
    @patch('sensor_fuzz.__main__.validate_config_file')
    def test_main_config_validation_failure(self, mock_validate, mock_logging):
        """Test main with config validation failure."""
        mock_validate.side_effect = ApplicationError("Config error", 2)

        with patch('sys.exit') as mock_exit:
            main()

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
        """Test successful full main execution."""
        # Setup mocks
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

        # Verify all components were started
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

    @patch('sensor_fuzz.__main__.setup_logging')
    @patch('sensor_fuzz.__main__.start_system_monitor')
    @patch('sensor_fuzz.__main__.start_exporter')
    @patch('sensor_fuzz.__main__.setup_signal_handlers')
    @patch('sensor_fuzz.__main__.validate_config_file')
    @patch('sensor_fuzz.__main__.ConfigLoader')
    @patch('sensor_fuzz.__main__.ConfigVersionStore')
    def test_main_monitor_startup_failure(self, mock_version_store_class,
                                         mock_loader_class, mock_validate,
                                         mock_signal_handlers, mock_start_exporter,
                                         mock_start_monitor, mock_logging):
        """Test main with system monitor startup failure."""
        mock_validate.return_value = Path("config/test.yaml")
        mock_loader_instance = MagicMock()
        mock_config = MagicMock()
        mock_config.sensors = {"temp": {}}
        mock_loader_instance.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader_instance

        mock_version_store_instance = MagicMock()
        mock_version_store_class.return_value = mock_version_store_instance

        mock_start_monitor.side_effect = Exception("Monitor failed")

        with patch('sys.exit') as mock_exit, \
             patch('sensor_fuzz.__main__.ExecutionEngine') as mock_engine_class, \
             patch('sensor_fuzz.__main__.ConfigReloader') as mock_reloader_class, \
             patch('sensor_fuzz.__main__.run_full') as mock_run_full, \
             patch('sensor_fuzz.__main__.stop_system_monitor') as mock_stop_monitor:

            mock_engine_instance = MagicMock()
            mock_engine_class.return_value = mock_engine_instance
            mock_reloader_instance = MagicMock()
            mock_reloader_class.return_value = mock_reloader_instance
            mock_exporter = MagicMock()
            mock_start_exporter.return_value = mock_exporter

            main()

        # Should continue despite monitor failure
        mock_run_full.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch('sensor_fuzz.__main__.setup_logging')
    @patch('sensor_fuzz.__main__.start_system_monitor')
    @patch('sensor_fuzz.__main__.start_exporter')
    @patch('sensor_fuzz.__main__.setup_signal_handlers')
    @patch('sensor_fuzz.__main__.validate_config_file')
    @patch('sensor_fuzz.__main__.ConfigLoader')
    @patch('sensor_fuzz.__main__.ConfigVersionStore')
    def test_main_exporter_startup_failure(self, mock_version_store_class,
                                          mock_loader_class, mock_validate,
                                          mock_signal_handlers, mock_start_exporter,
                                          mock_start_monitor, mock_logging):
        """Test main with metrics exporter startup failure."""
        mock_validate.return_value = Path("config/test.yaml")
        mock_loader_instance = MagicMock()
        mock_config = MagicMock()
        mock_config.sensors = {"temp": {}}
        mock_loader_instance.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader_instance

        mock_version_store_instance = MagicMock()
        mock_version_store_class.return_value = mock_version_store_instance

        mock_start_exporter.side_effect = Exception("Exporter failed")

        with patch('sys.exit') as mock_exit, \
             patch('sensor_fuzz.__main__.ExecutionEngine') as mock_engine_class, \
             patch('sensor_fuzz.__main__.ConfigReloader') as mock_reloader_class, \
             patch('sensor_fuzz.__main__.run_full') as mock_run_full, \
             patch('sensor_fuzz.__main__.stop_system_monitor') as mock_stop_monitor:

            mock_engine_instance = MagicMock()
            mock_engine_class.return_value = mock_engine_instance
            mock_reloader_instance = MagicMock()
            mock_reloader_class.return_value = mock_reloader_instance

            main()

        # Should continue despite exporter failure
        mock_run_full.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch('sensor_fuzz.__main__.setup_logging')
    @patch('sensor_fuzz.__main__.start_system_monitor')
    @patch('sensor_fuzz.__main__.start_exporter')
    @patch('sensor_fuzz.__main__.setup_signal_handlers')
    @patch('sensor_fuzz.__main__.validate_config_file')
    @patch('sensor_fuzz.__main__.ConfigLoader')
    def test_main_version_store_failure(self, mock_loader_class, mock_validate,
                                       mock_signal_handlers, mock_start_exporter,
                                       mock_start_monitor, mock_logging):
        """Test main with version store failure."""
        mock_validate.return_value = Path("config/test.yaml")
        mock_loader_instance = MagicMock()
        mock_config = MagicMock()
        mock_config.sensors = {"temp": {}}
        mock_loader_instance.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader_instance

        with patch('sensor_fuzz.__main__.ConfigVersionStore') as mock_version_store_class:
            mock_version_store_instance = MagicMock()
            mock_version_store_instance.save.side_effect = Exception("Version store failed")
            mock_version_store_class.return_value = mock_version_store_instance

            with patch('sys.exit') as mock_exit, \
                 patch('sensor_fuzz.__main__.ExecutionEngine') as mock_engine_class, \
                 patch('sensor_fuzz.__main__.ConfigReloader') as mock_reloader_class, \
                 patch('sensor_fuzz.__main__.run_full') as mock_run_full, \
                 patch('sensor_fuzz.__main__.stop_system_monitor') as mock_stop_monitor:

                mock_engine_instance = MagicMock()
                mock_engine_class.return_value = mock_engine_instance
                mock_reloader_instance = MagicMock()
                mock_reloader_class.return_value = mock_reloader_instance
                mock_exporter = MagicMock()
                mock_start_exporter.return_value = mock_exporter

                main()

        # Should continue despite version store failure
        mock_run_full.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch('sensor_fuzz.__main__.setup_logging')
    @patch('sensor_fuzz.__main__.start_system_monitor')
    @patch('sensor_fuzz.__main__.start_exporter')
    @patch('sensor_fuzz.__main__.setup_signal_handlers')
    @patch('sensor_fuzz.__main__.validate_config_file')
    @patch('sensor_fuzz.__main__.ConfigLoader')
    @patch('sensor_fuzz.__main__.ConfigVersionStore')
    @patch('sensor_fuzz.__main__.ExecutionEngine')
    def test_main_engine_initialization_failure(self, mock_engine_class, mock_version_store_class,
                                               mock_loader_class, mock_validate,
                                               mock_signal_handlers, mock_start_exporter,
                                               mock_start_monitor, mock_logging):
        """Test main with engine initialization failure."""
        mock_validate.return_value = Path("config/test.yaml")
        mock_loader_instance = MagicMock()
        mock_config = MagicMock()
        mock_config.sensors = {"temp": {}}
        mock_loader_instance.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader_instance

        mock_version_store_instance = MagicMock()
        mock_version_store_class.return_value = mock_version_store_instance

        # Make ExecutionEngine initialization fail
        mock_engine_class.side_effect = Exception("Engine init failed")

        with patch('sys.exit') as mock_exit:
            main()

        mock_exit.assert_called_once_with(4)

    @patch('sensor_fuzz.__main__.setup_logging')
    @patch('sensor_fuzz.__main__.start_system_monitor')
    @patch('sensor_fuzz.__main__.start_exporter')
    @patch('sensor_fuzz.__main__.setup_signal_handlers')
    @patch('sensor_fuzz.__main__.validate_config_file')
    @patch('sensor_fuzz.__main__.ConfigLoader')
    @patch('sensor_fuzz.__main__.ConfigVersionStore')
    @patch('sensor_fuzz.__main__.ExecutionEngine')
    def test_main_reloader_startup_failure(self, mock_engine_class, mock_version_store_class,
                                          mock_loader_class, mock_validate,
                                          mock_signal_handlers, mock_start_exporter,
                                          mock_start_monitor, mock_logging):
        """Test main with configuration reloader startup failure."""
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

        with patch('sensor_fuzz.__main__.ConfigReloader') as mock_reloader_class:
            mock_reloader_instance = MagicMock()
            mock_reloader_instance.start.side_effect = Exception("Reloader failed")
            mock_reloader_class.return_value = mock_reloader_instance

            with patch('sys.exit') as mock_exit, \
                 patch('sensor_fuzz.__main__.run_full') as mock_run_full, \
                 patch('sensor_fuzz.__main__.stop_system_monitor') as mock_stop_monitor:

                mock_exporter = MagicMock()
                mock_start_exporter.return_value = mock_exporter

                main()

        # Should continue despite reloader failure
        mock_run_full.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch('sensor_fuzz.__main__.setup_logging')
    @patch('sensor_fuzz.__main__.start_system_monitor')
    @patch('sensor_fuzz.__main__.start_exporter')
    @patch('sensor_fuzz.__main__.setup_signal_handlers')
    @patch('sensor_fuzz.__main__.validate_config_file')
    @patch('sensor_fuzz.__main__.ConfigLoader')
    @patch('sensor_fuzz.__main__.ConfigVersionStore')
    @patch('sensor_fuzz.__main__.ExecutionEngine')
    @patch('sensor_fuzz.__main__.ConfigReloader')
    def test_main_fuzzing_execution_failure(self, mock_reloader_class, mock_engine_class,
                                           mock_version_store_class, mock_loader_class,
                                           mock_validate, mock_signal_handlers,
                                           mock_start_exporter, mock_start_monitor,
                                           mock_logging):
        """Test main with fuzzing execution failure."""
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

        with patch('sensor_fuzz.__main__.run_full') as mock_run_full:
            mock_run_full.side_effect = Exception("Fuzzing failed")

            with patch('sys.exit') as mock_exit, \
                 patch('sensor_fuzz.__main__.stop_system_monitor') as mock_stop_monitor:

                main()

        mock_exit.assert_called_once_with(5)

    @patch('sensor_fuzz.__main__.setup_logging')
    @patch('sensor_fuzz.__main__.start_system_monitor')
    @patch('sensor_fuzz.__main__.start_exporter')
    @patch('sensor_fuzz.__main__.setup_signal_handlers')
    @patch('sensor_fuzz.__main__.validate_config_file')
    @patch('sensor_fuzz.__main__.ConfigLoader')
    @patch('sensor_fuzz.__main__.ConfigVersionStore')
    @patch('sensor_fuzz.__main__.ExecutionEngine')
    @patch('sensor_fuzz.__main__.ConfigReloader')
    def test_main_keyboard_interrupt(self, mock_reloader_class, mock_engine_class,
                                    mock_version_store_class, mock_loader_class,
                                    mock_validate, mock_signal_handlers,
                                    mock_start_exporter, mock_start_monitor,
                                    mock_logging):
        """Test main with keyboard interrupt during fuzzing."""
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

        with patch('sensor_fuzz.__main__.run_full') as mock_run_full:
            mock_run_full.side_effect = KeyboardInterrupt()

            with patch('sys.exit') as mock_exit, \
                 patch('sensor_fuzz.__main__.stop_system_monitor') as mock_stop_monitor:

                main()

        # KeyboardInterrupt should exit with code 0
        mock_exit.assert_called_once_with(0)

    @patch('sensor_fuzz.__main__.setup_logging')
    @patch('sensor_fuzz.__main__.start_system_monitor')
    @patch('sensor_fuzz.__main__.start_exporter')
    @patch('sensor_fuzz.__main__.setup_signal_handlers')
    @patch('sensor_fuzz.__main__.validate_config_file')
    @patch('sensor_fuzz.__main__.ConfigLoader')
    @patch('sensor_fuzz.__main__.ConfigVersionStore')
    @patch('sensor_fuzz.__main__.ExecutionEngine')
    @patch('sensor_fuzz.__main__.ConfigReloader')
    def test_main_unexpected_exception(self, mock_reloader_class, mock_engine_class,
                                      mock_version_store_class, mock_loader_class,
                                      mock_validate, mock_signal_handlers,
                                      mock_start_exporter, mock_start_monitor,
                                      mock_logging):
        """Test main with unexpected exception."""
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

        # Simulate an unexpected exception in main
        with patch('sensor_fuzz.__main__.run_full') as mock_run_full:
            mock_run_full.side_effect = RuntimeError("Unexpected error")

            with patch('sys.exit') as mock_exit, \
                 patch('sensor_fuzz.__main__.stop_system_monitor') as mock_stop_monitor:

                main()

        mock_exit.assert_called_once_with(5)

    @patch('sensor_fuzz.__main__.setup_logging')
    @patch('sensor_fuzz.__main__.start_system_monitor')
    @patch('sensor_fuzz.__main__.start_exporter')
    @patch('sensor_fuzz.__main__.setup_signal_handlers')
    @patch('sensor_fuzz.__main__.validate_config_file')
    @patch('sensor_fuzz.__main__.ConfigLoader')
    @patch('sensor_fuzz.__main__.ConfigVersionStore')
    @patch('sensor_fuzz.__main__.ExecutionEngine')
    @patch('sensor_fuzz.__main__.ConfigReloader')
    def test_main_cleanup_with_errors(self, mock_reloader_class, mock_engine_class,
                                     mock_version_store_class, mock_loader_class,
                                     mock_validate, mock_signal_handlers,
                                     mock_start_exporter, mock_start_monitor,
                                     mock_logging):
        """Test main cleanup logic when components fail to stop."""
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

        with patch('sensor_fuzz.__main__.run_full') as mock_run_full, \
             patch('sensor_fuzz.__main__.stop_system_monitor') as mock_stop_monitor, \
             patch('sys.exit') as mock_exit:

            mock_run_full.side_effect = Exception("Fuzzing failed")
            mock_stop_monitor.side_effect = Exception("Stop monitor failed")
            mock_reloader_instance.stop.side_effect = Exception("Stop reloader failed")
            mock_exporter.stop.side_effect = Exception("Stop exporter failed")

            main()

        # Should still exit with error code despite cleanup failures
        mock_exit.assert_called_once_with(5)