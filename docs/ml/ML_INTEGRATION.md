# ML Integration Guide

This document provides a comprehensive guide for machine learning engineers to work with the firefighter activity recognition system, from data collection through model training and inference integration.

---

## Table of Contents

1. [Overview](#overview)
2. [ML Pipeline Stages](#ml-pipeline-stages)
3. [Vector Structure (270 Dimensions)](#vector-structure-270-dimensions)
4. [Session-Based Labeling](#session-based-labeling)
5. [Exporting Training Data](#exporting-training-data)
6. [Data Preprocessing Recommendations](#data-preprocessing-recommendations)
7. [Recommended ML Architectures](#recommended-ml-architectures)
8. [Training/Validation/Test Split](#trainingvalidationtest-split)
9. [Example Code: Loading Exported Data](#example-code-loading-exported-data)
10. [Inference Integration Points](#inference-integration-points)

---

## Overview

The firefighter activity recognition system uses wearable sensors (foot pressure insoles and IMU accelerometer) to classify firefighter activities in real-time. The ML pipeline follows a staged approach:

```
Stage 1 (Current): Supervised Data Collection
  - User creates a session with a single activity type
  - Firefighter performs ONLY that activity during the session
  - All sensor data is automatically labeled with the session's activity
  - Builds a ground truth training dataset in Qdrant

Stage 2+: Model Training & Deployment
  - Export labeled vectors from Qdrant
  - Train classification models offline
  - Deploy models for real-time inference
  - Continuous improvement with new labeled data
```

**Key Principle:** 1 session = 1 activity label = supervised ground truth for all vectors in that session.

---

## ML Pipeline Stages

### Stage 1: Data Collection (Current Implementation)

The system is currently in Stage 1, focused on building a high-quality labeled dataset.

**Data Flow:**
```
Sensors (BLE) --> Sensor Hub (Pi) --> Server (Socket.IO) --> Qdrant (Vectors)
                                            |
                                            v
                                    PostgreSQL (Sessions)
```

**What Gets Stored:**
- **PostgreSQL**: Session metadata (ID, activity type, start/end times)
- **Qdrant**: 270-dimensional vectors with session_id and label in payload

### Stage 2: Model Training (Future)

Once sufficient labeled data is collected:
1. Export vectors grouped by activity label
2. Preprocess and split into train/val/test sets
3. Train classifier (see [Recommended ML Architectures](#recommended-ml-architectures))
4. Evaluate and tune hyperparameters

### Stage 3: Inference Deployment (Future)

Deploy trained models for real-time activity classification:
1. Load model into inference service
2. Receive live sensor vectors
3. Classify and emit predictions
4. Optional: Feedback loop for model improvement

---

## Vector Structure (270 Dimensions)

Each vector represents a **500ms time window** of sensor data, containing up to 10 readings from each sensor type.

### Dimension Breakdown

```
Total: 270 dimensions
|
+-- Foot Pressure Segment: 180 dimensions (indices 0-179)
|   |
|   +-- 10 readings x 18 sensor values = 180
|   |
|   +-- Each reading contains 18 pressure values from active foot sensors
|   +-- Readings are flattened sequentially: [reading_0_values, reading_1_values, ...]
|   +-- If fewer than 10 readings in window, remaining slots are zero-padded
|
+-- Accelerometer Segment: 90 dimensions (indices 180-269)
    |
    +-- 10 readings x 9 values = 90
    |
    +-- Each reading contains 9 values:
    |   - acc.x, acc.y, acc.z (acceleration in g)
    |   - gyro.x, gyro.y, gyro.z (angular velocity in deg/s)
    |   - angle.roll, angle.pitch, angle.yaw (orientation in degrees)
    |
    +-- Readings are flattened sequentially
    +-- If fewer than 10 readings in window, remaining slots are zero-padded
```

### Vector Composition Details

The vector is composed in `VectorStore._window_to_vector()`:

```python
# Foot segment (180 dimensions)
# indices 0-17:   foot reading 0 (18 pressure values)
# indices 18-35:  foot reading 1 (18 pressure values)
# ...
# indices 162-179: foot reading 9 (18 pressure values)

# Accelerometer segment (90 dimensions)
# indices 180-188: accel reading 0 (9 values: acc_xyz, gyro_xyz, angle_rpy)
# indices 189-197: accel reading 1 (9 values)
# ...
# indices 261-269: accel reading 9 (9 values)
```

### Normalization

Vectors are L2-normalized before storage in Qdrant:

```python
def _normalize_vector(self, values: List[float]) -> List[float]:
    arr = np.array(values, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr.tolist()
```

**Note:** The raw sensor values can be recovered from the `raw_data` field in the Qdrant payload.

---

## Session-Based Labeling

### Activity Types

The system supports 10 firefighter activity types (defined in `firefighter-server/lib/constants.py`):

| Activity | Description |
|----------|-------------|
| `Walking` | Normal walking pace |
| `Running` | Fast movement/jogging |
| `Crawling` | Low crawl on hands and knees |
| `Climbing` | Ascending/descending stairs or ladders |
| `Standing` | Stationary upright position |
| `Kneeling` | On one or both knees |
| `Sitting` | Seated position |
| `Carrying` | Walking while carrying equipment |
| `Hose_Operation` | Operating fire hose (stance and movement) |
| `Idle` | Minimal activity / rest |

### How Labels Are Applied

1. User creates a recording session via the web UI, selecting ONE activity type
2. Session is stored in PostgreSQL with the activity label
3. All sensor data received during the session is windowed into vectors
4. Each vector is stored in Qdrant with `label` = session's activity type
5. Session ends, and all vectors in that session share the same label

**Best Practice for Data Collection:**
- Perform only the labeled activity during the session
- Keep sessions focused (2-5 minutes of pure activity)
- Record multiple sessions per activity for diversity
- Vary conditions (different users, speeds, equipment)

---

## Exporting Training Data

### Method 1: REST API Export

The server provides an export endpoint for session data:

**Endpoint:** `GET /api/sessions/{session_id}/export`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | `json` | Output format: `json` or `csv` |
| `include_raw` | boolean | `false` | Include raw sensor readings |

**JSON Response Structure:**
```json
{
  "session": {
    "id": "abc123",
    "activity_type": "Walking",
    "start_time": "2025-01-15T10:30:00",
    "end_time": "2025-01-15T10:35:00",
    "device_key": "pi_001"
  },
  "windows": [
    {
      "id": "window-uuid-1",
      "start_time": 1705312200000,
      "end_time": 1705312200500,
      "foot_count": 8,
      "accel_count": 10,
      "label": "Walking",
      "raw_data": {
        "foot": [...],
        "accel": [...]
      }
    }
  ],
  "window_count": 120
}
```

**Example Usage:**
```bash
# Export single session as JSON with raw data
curl "http://localhost:4100/api/sessions/abc123/export?include_raw=true"

# Export as CSV (metadata only)
curl "http://localhost:4100/api/sessions/abc123/export?format=csv" > session.csv
```

### Method 2: Direct Qdrant Query

For bulk export across multiple sessions:

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import numpy as np

client = QdrantClient(host="localhost", port=6333)
COLLECTION = "sensor_windows"

def export_by_label(label: str, limit: int = 10000):
    """Export all vectors with a specific activity label."""
    vectors = []
    metadata = []
    offset = None

    while True:
        results = client.scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(key="label", match=MatchValue(value=label))]
            ),
            limit=100,
            offset=offset,
            with_vectors=True,
            with_payload=True
        )

        points, next_offset = results
        if not points:
            break

        for point in points:
            vectors.append(point.vector)
            metadata.append(point.payload)

        if next_offset is None or len(vectors) >= limit:
            break
        offset = next_offset

    return np.array(vectors), metadata

# Export all activities
def export_all_activities():
    ACTIVITIES = [
        "Walking", "Running", "Crawling", "Climbing", "Standing",
        "Kneeling", "Sitting", "Carrying", "Hose_Operation", "Idle"
    ]

    X_all, y_all = [], []

    for activity in ACTIVITIES:
        X, meta = export_by_label(activity)
        if len(X) > 0:
            X_all.append(X)
            y_all.extend([activity] * len(X))
            print(f"{activity}: {len(X)} vectors")

    return np.vstack(X_all), np.array(y_all)
```

---

## Data Preprocessing Recommendations

### 1. Handle Normalized vs Raw Vectors

Vectors in Qdrant are L2-normalized. For training, you may want to:
- Use normalized vectors directly (good for cosine similarity-based methods)
- Reconstruct raw values from `raw_data` payload (better for magnitude-sensitive models)

### 2. Outlier Removal

Remove windows with incomplete sensor data:

```python
def remove_incomplete_windows(X, metadata):
    """Remove windows with too few sensor readings."""
    mask = []
    for m in metadata:
        foot_count = m.get("foot_count", 0)
        accel_count = m.get("accel_count", 0)
        # Require at least 5 readings of each type
        mask.append(foot_count >= 5 and accel_count >= 5)

    mask = np.array(mask)
    return X[mask], [m for m, keep in zip(metadata, mask) if keep]
```

### 3. Feature Scaling

If using raw (un-normalized) vectors, apply standardization:

```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Save scaler for inference
import joblib
joblib.dump(scaler, "scaler.pkl")
```

### 4. Class Balancing

Check for class imbalance and address if needed:

```python
from collections import Counter
from imblearn.over_sampling import SMOTE

# Check distribution
print(Counter(y_train))

# Apply SMOTE if imbalanced
if min(Counter(y_train).values()) < 100:
    smote = SMOTE(random_state=42)
    X_balanced, y_balanced = smote.fit_resample(X_train, y_train)
```

---

## Recommended ML Architectures

### For 10 Activity Classes

Given the 270-dimensional fixed-size vectors and 10 activity classes, several architectures are suitable:

### 1. Random Forest (Baseline)

**Pros:** Fast to train, interpretable, no GPU needed
**Expected Accuracy:** 75-85%

```python
from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=30,
    min_samples_split=5,
    random_state=42,
    n_jobs=-1
)
rf.fit(X_train, y_train)
```

### 2. XGBoost (Best for Tabular Data)

**Pros:** State-of-the-art for structured data, handles imbalance well
**Expected Accuracy:** 80-90%

```python
import xgboost as xgb

params = {
    'objective': 'multi:softmax',
    'num_class': 10,
    'max_depth': 10,
    'learning_rate': 0.1,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'eval_metric': 'mlogloss'
}

dtrain = xgb.DMatrix(X_train, label=y_train_encoded)
dval = xgb.DMatrix(X_val, label=y_val_encoded)

model = xgb.train(
    params, dtrain,
    num_boost_round=500,
    evals=[(dval, 'val')],
    early_stopping_rounds=20
)
```

### 3. 1D CNN (Spatial Patterns)

**Pros:** Captures local patterns in sensor arrangement
**Expected Accuracy:** 82-90%

```python
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Dense, Dropout, Flatten

model = Sequential([
    Conv1D(64, 5, activation='relu', input_shape=(270, 1)),
    MaxPooling1D(2),
    Conv1D(128, 5, activation='relu'),
    MaxPooling1D(2),
    Conv1D(256, 3, activation='relu'),
    Flatten(),
    Dense(128, activation='relu'),
    Dropout(0.4),
    Dense(10, activation='softmax')
])

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
```

### 4. LSTM (Temporal Patterns)

**Pros:** Best for sequential patterns (gait cycles, periodic motion)
**Expected Accuracy:** 85-95% (with sufficient data)

Requires creating sequences from consecutive windows:

```python
from tensorflow.keras.layers import LSTM, BatchNormalization

def create_sequences(X, y, seq_length=10):
    """Create sequences of consecutive windows."""
    X_seq, y_seq = [], []
    for i in range(len(X) - seq_length + 1):
        X_seq.append(X[i:i+seq_length])
        y_seq.append(y[i+seq_length-1])  # Label from last window
    return np.array(X_seq), np.array(y_seq)

# Input shape: (batch, seq_length, 270)
model = Sequential([
    LSTM(128, return_sequences=True, input_shape=(10, 270)),
    BatchNormalization(),
    Dropout(0.3),
    LSTM(64),
    BatchNormalization(),
    Dropout(0.3),
    Dense(64, activation='relu'),
    Dense(10, activation='softmax')
])
```

---

## Training/Validation/Test Split

### Recommended Split Ratios

```
Total Data
+-- 70% Training (fit model parameters)
+-- 15% Validation (hyperparameter tuning, early stopping)
+-- 15% Test (final evaluation only)
```

### Split Strategies

**Option 1: Random Split (Simple)**
```python
from sklearn.model_selection import train_test_split

X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, stratify=y, random_state=42)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=42)
```

**Option 2: Session-Based Split (Recommended)**

Prevents data leakage by keeping entire sessions together:

```python
def session_based_split(X, y, metadata, test_ratio=0.15, val_ratio=0.15):
    """Split by session to prevent data leakage."""
    session_ids = list(set(m['session_id'] for m in metadata))
    np.random.shuffle(session_ids)

    n_sessions = len(session_ids)
    n_test = int(n_sessions * test_ratio)
    n_val = int(n_sessions * val_ratio)

    test_sessions = set(session_ids[:n_test])
    val_sessions = set(session_ids[n_test:n_test+n_val])
    train_sessions = set(session_ids[n_test+n_val:])

    train_mask = [m['session_id'] in train_sessions for m in metadata]
    val_mask = [m['session_id'] in val_sessions for m in metadata]
    test_mask = [m['session_id'] in test_sessions for m in metadata]

    return (
        X[train_mask], X[val_mask], X[test_mask],
        y[train_mask], y[val_mask], y[test_mask]
    )
```

**Option 3: Time-Based Split (Production Realistic)**

Train on older data, test on newer data:

```python
def time_based_split(X, y, metadata):
    """Split by time to simulate production conditions."""
    # Sort by timestamp
    sorted_indices = np.argsort([m['start_time'] for m in metadata])
    X_sorted = X[sorted_indices]
    y_sorted = y[sorted_indices]

    n = len(X_sorted)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)

    return (
        X_sorted[:train_end], X_sorted[train_end:val_end], X_sorted[val_end:],
        y_sorted[:train_end], y_sorted[train_end:val_end], y_sorted[val_end:]
    )
```

---

## Example Code: Loading Exported Data

### Complete Data Loading Pipeline

```python
import numpy as np
import json
from qdrant_client import QdrantClient
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split

# Configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION = "sensor_windows"

ACTIVITIES = [
    "Walking", "Running", "Crawling", "Climbing", "Standing",
    "Kneeling", "Sitting", "Carrying", "Hose_Operation", "Idle"
]

def load_training_data():
    """Load all labeled vectors from Qdrant."""
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    X_all, y_all, meta_all = [], [], []

    for activity in ACTIVITIES:
        vectors = []
        offset = None

        while True:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            results = client.scroll(
                collection_name=COLLECTION,
                scroll_filter=Filter(
                    must=[FieldCondition(key="label", match=MatchValue(value=activity))]
                ),
                limit=100,
                offset=offset,
                with_vectors=True,
                with_payload=True
            )

            points, next_offset = results
            if not points:
                break

            for p in points:
                vectors.append(p.vector)
                meta_all.append(p.payload)

            if next_offset is None:
                break
            offset = next_offset

        if vectors:
            X_all.extend(vectors)
            y_all.extend([activity] * len(vectors))
            print(f"Loaded {len(vectors)} vectors for {activity}")

    return np.array(X_all), np.array(y_all), meta_all


def prepare_for_training(X, y):
    """Prepare data for model training."""
    # Encode labels
    le = LabelEncoder()
    le.fit(ACTIVITIES)
    y_encoded = le.transform(y)

    # Split data
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y_encoded, test_size=0.3, stratify=y_encoded, random_state=42
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=42
    )

    # Scale features (vectors are already normalized, but this helps with different scales)
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    X_test = scaler.transform(X_test)

    print(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    return X_train, X_val, X_test, y_train, y_val, y_test, le, scaler


# Usage
if __name__ == "__main__":
    X, y, metadata = load_training_data()
    X_train, X_val, X_test, y_train, y_val, y_test, label_encoder, scaler = prepare_for_training(X, y)

    # Train your model here
    # ...
```

---

## Inference Integration Points

### Where to Integrate Real-Time Inference

The system provides several integration points for deploying trained models:

### Option 1: Server-Side Inference

Add inference to the firefighter-server when vectors are created:

```python
# In firefighter-server/lib/vector_store.py
# After _store_window(), call inference

class VectorStore:
    def __init__(self, config, classifier=None):
        # ... existing init ...
        self.classifier = classifier  # Loaded ML model

    def _store_window(self, window):
        point_id = str(uuid.uuid4())
        vector = self._window_to_vector(window)

        # Run inference if classifier is loaded
        if self.classifier:
            prediction = self.classifier.predict(vector)
            # Emit prediction via Socket.IO or store in DB

        # ... rest of existing code ...
```

### Option 2: Separate Inference Service

Create a dedicated inference microservice:

```python
# inference_service.py
from flask import Flask, request, jsonify
import numpy as np
import joblib

app = Flask(__name__)

# Load model and preprocessing artifacts
model = joblib.load("model.pkl")
scaler = joblib.load("scaler.pkl")
label_encoder = joblib.load("label_encoder.pkl")

@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    vector = np.array(data["vector"]).reshape(1, -1)

    # Preprocess
    vector_scaled = scaler.transform(vector)

    # Predict
    prediction_idx = model.predict(vector_scaled)[0]
    prediction_label = label_encoder.inverse_transform([prediction_idx])[0]

    # Confidence (if available)
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(vector_scaled)[0]
        confidence = float(probs[prediction_idx])
    else:
        confidence = None

    return jsonify({
        "activity": prediction_label,
        "confidence": confidence
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

### Option 3: Edge Inference (Sensor Hub)

For low-latency inference, deploy a lightweight model on the Raspberry Pi:

```python
# In sensor-hub, create local inference
import tflite_runtime.interpreter as tflite

class EdgeClassifier:
    def __init__(self, model_path):
        self.interpreter = tflite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def predict(self, vector):
        input_data = np.array([vector], dtype=np.float32)
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_details[0]['index'])
        return np.argmax(output)
```

---

## Related Documentation

- [DATA_REFERENCE.md](./DATA_REFERENCE.md) - Complete data schemas and field definitions
- [firefighter-server/README.md](../../firefighter-server/README.md) - Server setup and API reference
- [sensor-hub/README.md](../../sensor-hub/README.md) - Sensor configuration and data collection
