"""DBSCAN-based anomaly clustering and labeling."""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
from sklearn.cluster import DBSCAN


def cluster_anomalies(
    features: List[List[float]], eps: float = 0.5, min_samples: int = 5
) -> Tuple[np.ndarray, DBSCAN]:
    """Run DBSCAN on feature vectors and return labels and model."""
    model = DBSCAN(eps=eps, min_samples=min_samples)
    labels = model.fit_predict(np.asarray(features))
    return labels, model


def label_defects(labels: np.ndarray) -> Dict[int, str]:
    """Map cluster labels to defect categories (simple heuristic placeholder)."""
    mapping: Dict[int, str] = {}
    for lbl in set(labels.tolist()):
        if lbl == -1:
            mapping[lbl] = "noise"
        else:
            mapping[lbl] = "anomaly-cluster"
    return mapping
