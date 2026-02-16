"""模块说明：tests/test_ai.py 的主要实现与辅助逻辑。"""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock

import sensor_fuzz.ai as ai

torch = ai.lstm.torch


def test_lstm_train_predict_optional_dep():
    """方法说明：执行 test lstm train predict optional dep 相关逻辑。"""
    data = np.random.rand(8, 5, 4)
    labels = np.random.randint(0, 2, size=(8,))
    if ai.lstm.torch is None:
        with pytest.raises(ImportError):
            ai.train_lstm(data, labels, epochs=1)
    else:
        model = ai.train_lstm(data, labels, epochs=1)
        scores = ai.predict(model, data)
        assert scores.shape[0] == data.shape[0]


def test_genetic_generate():
    """方法说明：执行 test genetic generate 相关逻辑。"""
    seeds = [ai.TestCase(payload={"a": 1}, fitness=1.0), ai.TestCase(payload={"b": 2}, fitness=0.5)]
    pop = ai.genetic_generate(seeds, population=4, generations=1)
    assert len(pop) == 4
    ai.rl_score(pop[0], 1.0)
    assert pop[0].fitness > 0


def test_lstm_require_torch_no_torch():
    """Test _require_torch when torch is not available."""
    with patch('sensor_fuzz.ai.lstm.torch', None):
        with pytest.raises(ImportError, match="torch is required"):
            ai.lstm._require_torch()


def test_lstm_require_torch_with_torch():
    """Test _require_torch when torch is available."""
    if ai.lstm.torch is not None:
        # Should not raise exception
        ai.lstm._require_torch()
    else:
        pytest.skip("PyTorch not available")


def test_lstm_anomaly_init_no_torch():
    """Test LSTMAnomaly initialization when torch is not available."""
    with patch('sensor_fuzz.ai.lstm.torch', None):
        with pytest.raises(ImportError):
            ai.lstm.LSTMAnomaly()


@pytest.mark.skipif(ai.lstm.torch is None, reason="PyTorch not available")
def test_lstm_anomaly_init_with_torch():
    """Test LSTMAnomaly initialization when torch is available."""
    model = ai.lstm.LSTMAnomaly(input_dim=4, hidden_dim=32, layers=1)

    assert model.input_dim == 4
    assert model.hidden_dim == 32
    assert model.layers == 1
    assert hasattr(model, 'lstm')
    assert hasattr(model, 'fc')


@pytest.mark.skipif(ai.lstm.torch is None, reason="PyTorch not available")
def test_lstm_anomaly_forward_single_timestep():
    """Test LSTMAnomaly forward pass with single timestep."""
    model = ai.lstm.LSTMAnomaly(input_dim=4, hidden_dim=32, layers=1)

    # Single timestep input: (batch_size, input_dim)
    x = ai.lstm.torch.randn(2, 4)
    output = model(x)

    assert output.shape == (2, 1)  # (batch_size, 1)


@pytest.mark.skipif(ai.lstm.torch is None, reason="PyTorch not available")
def test_lstm_anomaly_forward_sequence():
    """Test LSTMAnomaly forward pass with sequence."""
    model = ai.lstm.LSTMAnomaly(input_dim=4, hidden_dim=32, layers=1)

    # Sequence input: (batch_size, seq_len, input_dim)
    x = ai.lstm.torch.randn(2, 5, 4)
    output = model(x)

    assert output.shape == (2, 1)  # (batch_size, 1)


def test_train_lstm_no_torch():
    """Test train_lstm when torch is not available."""
    data = np.random.rand(8, 5, 4)
    labels = np.random.randint(0, 2, size=(8,))

    with patch('sensor_fuzz.ai.lstm.torch', None):
        with pytest.raises(ImportError):
            ai.train_lstm(data, labels, epochs=1)


@pytest.mark.skipif(ai.lstm.torch is None, reason="PyTorch not available")
def test_train_lstm_basic():
    """Test train_lstm basic functionality."""
    data = np.random.rand(8, 5, 4)
    labels = np.random.randint(0, 2, size=(8,))

    model = ai.train_lstm(data, labels, epochs=1, lr=1e-3)

    assert isinstance(model, ai.lstm.LSTMAnomaly)
    assert model.input_dim == data.shape[-1]


@pytest.mark.skipif(ai.lstm.torch is None, reason="PyTorch not available")
def test_train_lstm_custom_params():
    """Test train_lstm with custom parameters."""
    data = np.random.rand(8, 5, 4)
    labels = np.random.randint(0, 2, size=(8,))

    model = ai.train_lstm(data, labels, epochs=2, lr=1e-4, hidden_dim=64, layers=2)

    assert isinstance(model, ai.lstm.LSTMAnomaly)
    assert model.hidden_dim == 64
    assert model.layers == 2


@pytest.mark.skipif(ai.lstm.torch is None, reason="PyTorch not available")
def test_predict_no_torch():
    """Test predict when torch is not available."""
    model = MagicMock()
    data = np.random.rand(4, 5, 4)

    with patch('sensor_fuzz.ai.lstm.torch', None):
        with pytest.raises(ImportError):
            ai.predict(model, data)


@pytest.mark.skipif(ai.lstm.torch is None, reason="PyTorch not available")
def test_predict_single_timestep():
    """Test predict with single timestep data."""
    # Create a mock model
    model = MagicMock()
    model.return_value = ai.lstm.torch.tensor([[0.7], [0.3]])

    data = np.random.rand(2, 4)  # (batch_size, input_dim)

    scores = ai.predict(model, data)

    assert scores.shape == (2,)
    assert all(0 <= score <= 1 for score in scores)
    model.assert_called_once()


@pytest.mark.skipif(ai.lstm.torch is None, reason="PyTorch not available")
def test_train_lstm_enhanced():
    """Test enhanced LSTM training with better parameters."""
    data = np.random.rand(100, 5, 4)
    labels = np.random.randint(0, 2, size=(100,))

    model = ai.train_lstm(
        data,
        labels,
        epochs=5,
        lr=1e-3,
        hidden_dim=64,
        layers=2,
        dropout=0.2,
        patience=3
    )

    assert isinstance(model, ai.lstm.LSTMAnomaly)
    assert model.input_dim == data.shape[-1]
    assert model.hidden_dim == 64
    assert model.layers == 2
    assert model.bidirectional  # Should be True by default


@pytest.mark.skipif(ai.lstm.torch is None, reason="PyTorch not available")
def test_anomaly_detector_high_accuracy():
    """Test anomaly detector with target 99% accuracy."""
    # Create synthetic data with clear anomaly patterns
    np.random.seed(42)
    normal_data = np.random.normal(0, 1, (800, 5, 4))
    anomaly_data = np.random.normal(5, 2, (200, 5, 4))  # Clear anomalies

    data = np.vstack([normal_data, anomaly_data])
    labels = np.hstack([np.zeros(800), np.ones(200)])  # 0=normal, 1=anomaly

    detector = ai.AnomalyDetector(contamination=0.2, target_accuracy=0.99)
    detector.fit(data, labels, epochs=10)

    # Test on training data
    predictions = detector.predict(data)
    accuracy = np.mean(predictions == labels)

    print(f"Achieved accuracy: {accuracy:.4f}")
    assert accuracy >= 0.95  # Should achieve at least 95% accuracy

    # Test metrics
    metrics = detector.get_accuracy_metrics(data, labels)
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics
    assert metrics["accuracy"] >= 0.95


@pytest.mark.skipif(ai.lstm.torch is None, reason="PyTorch not available")
def test_anomaly_detector_metrics():
    """Test comprehensive anomaly detector metrics."""
    np.random.seed(123)
    data = np.random.rand(200, 5, 4)
    labels = np.random.randint(0, 2, size=200)

    detector = ai.AnomalyDetector()
    detector.fit(data, labels, epochs=5)

    metrics = detector.get_accuracy_metrics(data, labels)

    assert all(key in metrics for key in ["accuracy", "precision", "recall", "f1_score", "auc", "threshold"])
    assert all(0 <= metrics[key] <= 1 for key in ["accuracy", "precision", "recall", "f1_score", "auc"])
    assert 0.1 <= metrics["threshold"] <= 0.9  # Reasonable threshold range


@pytest.mark.skipif(ai.lstm.torch is None, reason="PyTorch not available")
def test_lstm_model_architecture():
    """Test enhanced LSTM model architecture."""
    model = ai.lstm.LSTMAnomaly(
        input_dim=4,
        hidden_dim=64,
        layers=2,
        dropout=0.2,
        bidirectional=True
    )

    # Test forward pass
    x = ai.lstm.torch.randn(10, 5, 4)  # (batch, seq, features)
    output = model(x)

    assert output.shape == (10, 1)  # (batch, 1) for binary classification
    assert torch.all((output >= 0) & (output <= 1))  # Sigmoid output


@pytest.mark.skipif(ai.lstm.torch is None, reason="PyTorch not available")
def test_predict_sequence():
    """Test predict with sequence data."""
    # Create a mock model
    model = MagicMock()
    model.return_value = ai.lstm.torch.tensor([[0.8], [0.2], [0.6]])

    data = np.random.rand(3, 5, 4)  # (batch_size, seq_len, input_dim)

    scores = ai.predict(model, data)

    assert scores.shape == (3,)
    assert all(0 <= score <= 1 for score in scores)
    model.assert_called_once()


@pytest.mark.skipif(ai.lstm.torch is None, reason="PyTorch not available")
def test_predict_error_handling():
    """Test predict error handling."""
    model = MagicMock()
    model.side_effect = RuntimeError("Model error")

    data = np.random.rand(2, 4)

    with pytest.raises(RuntimeError, match="Model error"):
        ai.predict(model, data)


@pytest.mark.skipif(ai.lstm.torch is None, reason="PyTorch not available")
def test_predict_tensor_conversion():
    """Test predict tensor conversion."""
    model = MagicMock()
    model.return_value = ai.lstm.torch.tensor([[0.5]])

    # Test with numpy array
    data = np.array([[1.0, 2.0, 3.0, 4.0]])

    scores = ai.predict(model, data)

    assert scores.shape == (1,)
    assert 0 <= scores[0] <= 1

    # Verify the model was called with tensor
    args, kwargs = model.call_args
    input_tensor = args[0]
    assert ai.lstm.torch.is_tensor(input_tensor)
