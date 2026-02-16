"""聚类分析模块：使用 DBSCAN 对异常样本进行聚类。"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
from sklearn.cluster import DBSCAN


def cluster_anomalies(
    features: List[List[float]], eps: float = 0.5, min_samples: int = 5
) -> Tuple[np.ndarray, DBSCAN]:
    """对特征向量执行 DBSCAN 并返回标签与模型。"""
    model = DBSCAN(eps=eps, min_samples=min_samples)
    labels = model.fit_predict(np.asarray(features))
    return labels, model


def label_defects(labels: np.ndarray) -> Dict[int, str]:
    """将聚类标签映射为缺陷类别（启发式规则）。"""
    mapping: Dict[int, str] = {}
    for lbl in set(labels.tolist()):
        if lbl == -1:
            mapping[lbl] = "noise"
        else:
            mapping[lbl] = "anomaly-cluster"
    return mapping
