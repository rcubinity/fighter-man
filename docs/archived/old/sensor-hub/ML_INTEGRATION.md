# ML Integration Guide

This document provides a comprehensive guide for machine learning engineers to integrate with the sensor-hub data collection system, export training data, and build activity detection models.

---

## Table of Contents

1. [Overview](#overview)
2. [Data Storage Architecture](#data-storage-architecture)
3. [Vector Structure (270 Dimensions)](#vector-structure-270-dimensions)
4. [Exporting Training Data](#exporting-training-data)
5. [Session-Based Labeling](#session-based-labeling)
6. [Data Preprocessing Pipeline](#data-preprocessing-pipeline)
7. [Recommended ML Architectures](#recommended-ml-architectures)
8. [Training/Validation/Test Split](#trainingvalidationtest-split)
9. [Model Training Examples](#model-training-examples)
10. [Inference Integration](#inference-integration)

---

## Overview

The sensor-hub system is designed for **supervised learning** using session-based labeling:

```
Stage 1 (Current): Data Collection
├── User creates session with activity type
├── Firefighter performs ONLY that activity
├── All data labeled with session's activity type
└── Builds ground truth training dataset

Stage 2-4 (Future): ML Development
├── Export labeled vectors from Qdrant
├── Train classification models
├── Deploy for real-time inference
└── Continuous improvement with new data
```

**Key Principle:** 1 session = 1 activity = supervised labels for all vectors in that session

---

## Data Storage Architecture

### Storage Layers

```
┌─────────────────────────────────────────────────────┐
│  Sensor-Hub (Raspberry Pi)                          │
│  ├── SQLite (local backup, retry queue)             │
│  └── Socket.IO → Firefighter Server                 │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  Firefighter Server                                  │
│  ├── PostgreSQL (session metadata)                  │
│  │   └── sessions table (id, activity, timestamps)  │
│  └── Qdrant Vector DB (sensor data vectors)         │
│      └── sensor_data collection (270-dim vectors)   │
└─────────────────────────────────────────────────────┘
```

### PostgreSQL Sessions Table

```sql
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(50) UNIQUE NOT NULL,
    device_key VARCHAR(50) NOT NULL,
    activity_type VARCHAR(50) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Activity Types (Validated from Archived Script):**
- Standing, Sitting, Bent_Forward, Lying_Down, Jumping

**Note:** These 5 activities have been validated with real sensor data from `archived/accelerator/blue/analyze.py`. Additional activities require real-world testing before deployment.

### Qdrant Vector Collection

**Collection Name:** `sensor_data`

**Vector Dimensions:** 270 (see next section)

**Payload Schema:**
```json
{
  "session_id": "session_1234567890",
  "activity": "Standing",
  "device_key": "firefighter_pi_001",
  "timestamp": "2025-12-19T14:23:45.123456",
  "window_index": 42,
  "sensor_type": "combined"
}
```

---

## Vector Structure (270 Dimensions)

Each vector represents a **500ms time window** of sensor data with 270 total dimensions.

### Dimension Breakdown

```
Total: 270 dimensions
├── Foot Pressure: 180 dimensions (60 + 60 + 60)
│   ├── Left Foot (60): 18 sensors × 3 aggregations + 6 metadata
│   │   ├── [0-17]: Sensor values (18 active sensors)
│   │   ├── [18-35]: Delta from previous window (18 deltas)
│   │   ├── [36-53]: Normalized values (18 normalized)
│   │   ├── [54]: Max pressure
│   │   ├── [55]: Average pressure
│   │   ├── [56]: Active count
│   │   ├── [57]: Pressure variance
│   │   ├── [58]: Center of pressure X
│   │   └── [59]: Center of pressure Y
│   │
│   └── Right Foot (60): Same structure as left
│       └── [60-119]: Right foot dimensions
│
├── Foot Metrics: 60 dimensions
│   ├── [120-129]: Left-right asymmetry features (10)
│   ├── [130-139]: Toe-heel balance features (10)
│   ├── [140-159]: Time-domain statistics (20)
│   └── [160-179]: Frequency-domain features (20)
│
└── Accelerometer (IMU): 90 dimensions
    ├── [180-197]: Acceleration X/Y/Z (18 = 3 axes × 6 stats)
    ├── [198-215]: Gyroscope X/Y/Z (18 = 3 axes × 6 stats)
    ├── [216-233]: Angle Roll/Pitch/Yaw (18 = 3 axes × 6 stats)
    ├── [234-251]: Derived metrics (18)
    │   ├── Acceleration magnitude
    │   ├── Angular velocity magnitude
    │   ├── Jerk (derivative of acceleration)
    │   └── Orientation indicators
    └── [252-269]: Frequency-domain features (18)
```

### Statistical Aggregations (per axis)

For each sensor axis (e.g., acc.x, gyro.y, angle.roll), we compute **6 statistics** over the 500ms window:

```python
def compute_stats(values):
    return [
        np.mean(values),      # Average
        np.std(values),       # Standard deviation
        np.min(values),       # Minimum
        np.max(values),       # Maximum
        np.percentile(values, 25),  # 25th percentile
        np.percentile(values, 75)   # 75th percentile
    ]
```

### Windowing Strategy

**Window Size:** 500ms (half-second)

**Overlap:** 250ms (50% overlap)

**Example:**
```
Time:     [0.0s ────── 0.5s]
Window 1:  ████████████████
           [0.25s ────── 0.75s]
Window 2:        ████████████████
                 [0.5s ────── 1.0s]
Window 3:              ████████████████
```

This creates ~2 vectors per second, providing good temporal resolution without excessive data volume.

---

## Exporting Training Data

### Method 1: Direct Qdrant Query (Python)

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import numpy as np

# Connect to Qdrant
client = QdrantClient(host="localhost", port=6333)
collection_name = "sensor_data"

# Export all vectors for a specific activity
def export_activity_data(activity: str, limit: int = 10000):
    """
    Export vectors for a specific activity type.

    Args:
        activity: Activity type (e.g., "Standing", "Sitting")
        limit: Max number of vectors to retrieve

    Returns:
        X: numpy array of shape (N, 270)
        y: numpy array of labels (N,)
        metadata: list of payload dictionaries
    """
    # Scroll through all matching vectors
    vectors = []
    labels = []
    metadata = []

    offset = None
    while True:
        results = client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="activity",
                        match=MatchValue(value=activity)
                    )
                ]
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
            labels.append(point.payload['activity'])
            metadata.append(point.payload)

        if next_offset is None or len(vectors) >= limit:
            break

        offset = next_offset

    X = np.array(vectors)
    y = np.array(labels)

    return X, y, metadata


# Export all activities
def export_all_data():
    """
    Export vectors for all activities.

    Returns:
        X: numpy array of shape (N, 270)
        y: numpy array of labels (N,)
        metadata: list of payload dictionaries
    """
    # Validated activities from archived/accelerator/blue/analyze.py
    activities = [
        'Standing', 'Sitting', 'Bent_Forward',
        'Lying_Down', 'Jumping'
    ]

    all_X = []
    all_y = []
    all_metadata = []

    for activity in activities:
        print(f"Exporting {activity}...")
        X, y, meta = export_activity_data(activity)
        all_X.append(X)
        all_y.append(y)
        all_metadata.extend(meta)
        print(f"  Found {len(X)} samples")

    X = np.vstack(all_X)
    y = np.hstack(all_y)

    return X, y, all_metadata


# Usage
X, y, metadata = export_all_data()
print(f"Total samples: {X.shape[0]}")
print(f"Vector dimensions: {X.shape[1]}")
print(f"Unique activities: {np.unique(y)}")
```

### Method 2: Export by Session ID

```python
def export_session_data(session_id: str):
    """
    Export all vectors from a specific session.
    Useful for analyzing individual training sessions.
    """
    vectors = []

    offset = None
    while True:
        results = client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="session_id",
                        match=MatchValue(value=session_id)
                    )
                ]
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
            vectors.append({
                'vector': point.vector,
                'timestamp': point.payload['timestamp'],
                'window_index': point.payload['window_index'],
                'activity': point.payload['activity']
            })

        if next_offset is None:
            break

        offset = next_offset

    # Sort by window_index to maintain temporal order
    vectors.sort(key=lambda x: x['window_index'])

    return vectors


# Usage
session_vectors = export_session_data("session_1734614625")
print(f"Session has {len(session_vectors)} windows")
```

### Method 3: Export to CSV/Parquet (for non-Python tools)

```python
import pandas as pd

def export_to_csv(output_path: str = "training_data.csv"):
    """
    Export all data to CSV format.
    Warning: Large file size for many vectors!
    """
    X, y, metadata = export_all_data()

    # Create DataFrame
    df = pd.DataFrame(X, columns=[f'dim_{i}' for i in range(270)])
    df['activity'] = y
    df['session_id'] = [m['session_id'] for m in metadata]
    df['timestamp'] = [m['timestamp'] for m in metadata]
    df['device_key'] = [m['device_key'] for m in metadata]

    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Exported to {output_path}")
    print(f"File size: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")


def export_to_parquet(output_path: str = "training_data.parquet"):
    """
    Export all data to Parquet format (more efficient than CSV).
    """
    X, y, metadata = export_all_data()

    df = pd.DataFrame(X, columns=[f'dim_{i}' for i in range(270)])
    df['activity'] = y
    df['session_id'] = [m['session_id'] for m in metadata]
    df['timestamp'] = [m['timestamp'] for m in metadata]
    df['device_key'] = [m['device_key'] for m in metadata]

    # Save to Parquet with compression
    df.to_parquet(output_path, compression='snappy', index=False)
    print(f"Exported to {output_path}")
```

---

## Session-Based Labeling

### Labeling Strategy

**Principle:** All vectors within a session share the same activity label.

```python
# Example: Query PostgreSQL for session metadata
import psycopg2

def get_session_info(session_id: str):
    """
    Retrieve session metadata from PostgreSQL.
    """
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="firefighter",
        user="firefighter_user",
        password="dev_password"
    )

    cursor = conn.cursor()
    cursor.execute("""
        SELECT session_id, activity_type, start_time, end_time, device_key
        FROM sessions
        WHERE session_id = %s
    """, (session_id,))

    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            'session_id': result[0],
            'activity': result[1],
            'start_time': result[2],
            'end_time': result[3],
            'device_key': result[4]
        }
    return None


# Usage
session_info = get_session_info("session_1734614625")
print(f"Activity: {session_info['activity']}")
print(f"Duration: {session_info['end_time'] - session_info['start_time']}")
```

### Label Encoding

```python
from sklearn.preprocessing import LabelEncoder

# Define activity order (for consistent encoding)
# These 5 activities are validated from archived/accelerator/blue/analyze.py
ACTIVITY_ORDER = [
    'Standing',
    'Sitting',
    'Bent_Forward',
    'Lying_Down',
    'Jumping'
]

# Create label encoder
label_encoder = LabelEncoder()
label_encoder.fit(ACTIVITY_ORDER)

# Encode labels
y_encoded = label_encoder.transform(y)

# Decode predictions
predictions = model.predict(X_test)
predicted_labels = label_encoder.inverse_transform(predictions.argmax(axis=1))
```

### One-Hot Encoding (for Neural Networks)

```python
from tensorflow.keras.utils import to_categorical

# Convert to one-hot vectors
num_classes = len(ACTIVITY_ORDER)
y_one_hot = to_categorical(y_encoded, num_classes=num_classes)

# Shape: (N, 9) for 9 activity classes
print(y_one_hot.shape)
```

---

## Data Preprocessing Pipeline

### Complete Preprocessing Example

```python
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import numpy as np

def preprocess_data(X, y, test_size=0.2, val_size=0.1):
    """
    Complete preprocessing pipeline:
    1. Remove outliers
    2. Normalize features
    3. Split into train/val/test

    Args:
        X: Raw feature vectors (N, 270)
        y: Activity labels (N,)
        test_size: Fraction for test set
        val_size: Fraction of train set for validation

    Returns:
        X_train, X_val, X_test, y_train, y_val, y_test, scaler
    """
    # Step 1: Remove outliers (vectors with extreme values)
    # Use IQR method on each dimension
    Q1 = np.percentile(X, 25, axis=0)
    Q3 = np.percentile(X, 75, axis=0)
    IQR = Q3 - Q1

    lower_bound = Q1 - 3 * IQR  # 3× IQR for outliers
    upper_bound = Q3 + 3 * IQR

    # Keep only samples within bounds for ALL dimensions
    mask = np.all((X >= lower_bound) & (X <= upper_bound), axis=1)
    X_clean = X[mask]
    y_clean = y[mask]

    print(f"Removed {len(X) - len(X_clean)} outliers ({100*(1-len(X_clean)/len(X)):.2f}%)")

    # Step 2: Split into train+val and test
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X_clean, y_clean, test_size=test_size, stratify=y_clean, random_state=42
    )

    # Step 3: Split train+val into train and val
    val_size_adjusted = val_size / (1 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval, test_size=val_size_adjusted, stratify=y_trainval, random_state=42
    )

    # Step 4: Normalize features (fit on train only!)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    print(f"Train: {len(X_train)} samples")
    print(f"Val:   {len(X_val)} samples")
    print(f"Test:  {len(X_test)} samples")

    return X_train_scaled, X_val_scaled, X_test_scaled, y_train, y_val, y_test, scaler


# Usage
X, y, _ = export_all_data()
X_train, X_val, X_test, y_train, y_val, y_test, scaler = preprocess_data(X, y)
```

### Handling Class Imbalance

```python
from imblearn.over_sampling import SMOTE
from collections import Counter

def balance_classes(X_train, y_train):
    """
    Use SMOTE to balance class distribution.
    Useful if some activities have much less data.
    """
    print("Original distribution:")
    print(Counter(y_train))

    # Apply SMOTE
    smote = SMOTE(random_state=42)
    X_balanced, y_balanced = smote.fit_resample(X_train, y_train)

    print("\nBalanced distribution:")
    print(Counter(y_balanced))

    return X_balanced, y_balanced


# Usage (optional, only if needed)
# X_train, y_train = balance_classes(X_train, y_train)
```

---

## Recommended ML Architectures

### 1. LSTM (Best for Temporal Patterns)

**Use Case:** Activities with strong temporal patterns (walking gait, running rhythm)

```python
import tensorflow as tf
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.models import Sequential

def build_lstm_model(sequence_length=10, num_features=270, num_classes=9):
    """
    LSTM model for sequential activity classification.

    Args:
        sequence_length: Number of consecutive windows (e.g., 10 = 5 seconds)
        num_features: Vector dimensions (270)
        num_classes: Number of activities (9)

    Returns:
        Keras model
    """
    model = Sequential([
        # Input: (batch, sequence_length, num_features)
        LSTM(128, return_sequences=True, input_shape=(sequence_length, num_features)),
        BatchNormalization(),
        Dropout(0.3),

        LSTM(64, return_sequences=False),
        BatchNormalization(),
        Dropout(0.3),

        Dense(64, activation='relu'),
        BatchNormalization(),
        Dropout(0.2),

        Dense(32, activation='relu'),
        Dense(num_classes, activation='softmax')
    ])

    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    return model


# Create sequences from vectors
def create_sequences(X, y, sequence_length=10):
    """
    Convert flat vectors into sequences.

    Example:
        Input: 1000 vectors of shape (270,)
        Output: ~990 sequences of shape (10, 270)
    """
    X_seq = []
    y_seq = []

    for i in range(len(X) - sequence_length + 1):
        X_seq.append(X[i:i+sequence_length])
        y_seq.append(y[i+sequence_length-1])  # Label is from last window

    return np.array(X_seq), np.array(y_seq)


# Usage
X_train_seq, y_train_seq = create_sequences(X_train, y_train)
X_val_seq, y_val_seq = create_sequences(X_val, y_val)

lstm_model = build_lstm_model()
lstm_model.summary()

history = lstm_model.fit(
    X_train_seq, to_categorical(y_train_seq),
    validation_data=(X_val_seq, to_categorical(y_val_seq)),
    epochs=50,
    batch_size=32,
    callbacks=[
        tf.keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=5)
    ]
)
```

### 2. 1D CNN (Best for Spatial Patterns)

**Use Case:** Activities with distinctive spatial patterns in foot pressure distribution

```python
from tensorflow.keras.layers import Conv1D, MaxPooling1D, GlobalAveragePooling1D

def build_cnn_model(num_features=270, num_classes=9):
    """
    1D CNN model for spatial pattern recognition.
    Treats 270-dim vector as 1D signal.
    """
    model = Sequential([
        # Input: (batch, num_features, 1)
        Conv1D(64, kernel_size=5, activation='relu', input_shape=(num_features, 1)),
        BatchNormalization(),
        MaxPooling1D(pool_size=2),
        Dropout(0.3),

        Conv1D(128, kernel_size=5, activation='relu'),
        BatchNormalization(),
        MaxPooling1D(pool_size=2),
        Dropout(0.3),

        Conv1D(256, kernel_size=3, activation='relu'),
        BatchNormalization(),
        GlobalAveragePooling1D(),

        Dense(128, activation='relu'),
        BatchNormalization(),
        Dropout(0.4),

        Dense(num_classes, activation='softmax')
    ])

    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    return model


# Reshape for CNN (add channel dimension)
X_train_cnn = X_train.reshape(X_train.shape[0], X_train.shape[1], 1)
X_val_cnn = X_val.reshape(X_val.shape[0], X_val.shape[1], 1)

cnn_model = build_cnn_model()
cnn_model.fit(X_train_cnn, to_categorical(y_train), validation_data=(X_val_cnn, to_categorical(y_val)), epochs=50)
```

### 3. Random Forest (Best for Interpretability)

**Use Case:** When you need to understand which features are most important

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt

def train_random_forest(X_train, y_train, X_val, y_val):
    """
    Train Random Forest classifier with feature importance analysis.
    """
    # Train model
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=30,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        verbose=1
    )

    rf.fit(X_train, y_train)

    # Evaluate
    y_pred = rf.predict(X_val)
    print("\nClassification Report:")
    print(classification_report(y_val, y_pred, target_names=ACTIVITY_ORDER))

    # Feature importance
    feature_importance = rf.feature_importances_

    # Find top 20 most important features
    top_indices = np.argsort(feature_importance)[-20:][::-1]
    top_features = feature_importance[top_indices]

    print("\nTop 20 Most Important Features:")
    for idx, importance in zip(top_indices, top_features):
        print(f"  Dimension {idx}: {importance:.4f}")

    # Plot
    plt.figure(figsize=(10, 6))
    plt.bar(range(20), top_features)
    plt.xlabel('Feature Rank')
    plt.ylabel('Importance')
    plt.title('Top 20 Feature Importances')
    plt.tight_layout()
    plt.savefig('feature_importance.png')

    return rf


# Usage
rf_model = train_random_forest(X_train, y_train, X_val, y_val)
```

### 4. XGBoost (Best Overall Performance)

**Use Case:** When you want state-of-the-art accuracy

```python
import xgboost as xgb
from sklearn.metrics import accuracy_score

def train_xgboost(X_train, y_train, X_val, y_val):
    """
    Train XGBoost classifier.
    Often achieves best performance on tabular/vector data.
    """
    # Create DMatrix for XGBoost
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)

    # Parameters
    params = {
        'objective': 'multi:softmax',
        'num_class': len(ACTIVITY_ORDER),
        'max_depth': 10,
        'learning_rate': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'eval_metric': 'mlogloss',
        'seed': 42
    }

    # Train with early stopping
    evals = [(dtrain, 'train'), (dval, 'val')]
    bst = xgb.train(
        params,
        dtrain,
        num_boost_round=500,
        evals=evals,
        early_stopping_rounds=20,
        verbose_eval=10
    )

    # Evaluate
    y_pred = bst.predict(dval)
    accuracy = accuracy_score(y_val, y_pred)
    print(f"\nValidation Accuracy: {accuracy:.4f}")

    return bst


# Usage
xgb_model = train_xgboost(X_train, y_train, X_val, y_val)
```

---

## Training/Validation/Test Split

### Recommended Split Strategy

```
Total Data
├── 70% Training (fit model parameters)
├── 10% Validation (tune hyperparameters, early stopping)
└── 20% Test (final evaluation, never touched during training)
```

### Time-Based Splitting (Recommended for Production)

```python
def time_based_split(X, y, metadata, train_ratio=0.7, val_ratio=0.1):
    """
    Split data based on timestamp to simulate real-world scenario.
    Ensures model is tested on future data it hasn't seen.

    Example:
        Train: January - March
        Val:   April
        Test:  May
    """
    # Sort by timestamp
    timestamps = [m['timestamp'] for m in metadata]
    sorted_indices = np.argsort(timestamps)

    X_sorted = X[sorted_indices]
    y_sorted = y[sorted_indices]

    # Calculate split points
    n = len(X_sorted)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    X_train = X_sorted[:train_end]
    y_train = y_sorted[:train_end]

    X_val = X_sorted[train_end:val_end]
    y_val = y_sorted[train_end:val_end]

    X_test = X_sorted[val_end:]
    y_test = y_sorted[val_end:]

    print(f"Train: {len(X_train)} samples (oldest)")
    print(f"Val:   {len(X_val)} samples (middle)")
    print(f"Test:  {len(X_test)} samples (newest)")

    return X_train, X_val, X_test, y_train, y_val, y_test


# Usage
X_train, X_val, X_test, y_train, y_val, y_test = time_based_split(X, y, metadata)
```

### Cross-Validation for Small Datasets

```python
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score

def cross_validate_model(X, y, model_builder, n_folds=5):
    """
    Perform k-fold cross-validation.
    Useful when you have limited data.
    """
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

    fold_scores = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), 1):
        print(f"\nFold {fold}/{n_folds}")

        X_train_fold = X[train_idx]
        y_train_fold = y[train_idx]
        X_val_fold = X[val_idx]
        y_val_fold = y[val_idx]

        # Normalize
        scaler = StandardScaler()
        X_train_fold = scaler.fit_transform(X_train_fold)
        X_val_fold = scaler.transform(X_val_fold)

        # Train model
        model = model_builder()
        model.fit(X_train_fold, y_train_fold)

        # Evaluate
        y_pred = model.predict(X_val_fold)
        accuracy = accuracy_score(y_val_fold, y_pred)
        fold_scores.append(accuracy)
        print(f"Fold {fold} Accuracy: {accuracy:.4f}")

    print(f"\nMean Accuracy: {np.mean(fold_scores):.4f} ± {np.std(fold_scores):.4f}")
    return fold_scores


# Usage
def build_rf():
    return RandomForestClassifier(n_estimators=100, random_state=42)

scores = cross_validate_model(X, y_encoded, build_rf, n_folds=5)
```

---

## Model Training Examples

### Complete Training Pipeline

```python
import joblib
from datetime import datetime

def full_training_pipeline():
    """
    End-to-end training pipeline from data export to model deployment.
    """
    print("="*60)
    print("SENSOR-HUB ML TRAINING PIPELINE")
    print("="*60)

    # Step 1: Export data from Qdrant
    print("\n[1/7] Exporting data from Qdrant...")
    X, y, metadata = export_all_data()
    print(f"Loaded {len(X)} samples with {X.shape[1]} features")

    # Step 2: Encode labels
    print("\n[2/7] Encoding labels...")
    label_encoder = LabelEncoder()
    label_encoder.fit(ACTIVITY_ORDER)
    y_encoded = label_encoder.transform(y)
    print(f"Classes: {label_encoder.classes_}")

    # Step 3: Preprocess
    print("\n[3/7] Preprocessing data...")
    X_train, X_val, X_test, y_train, y_val, y_test, scaler = preprocess_data(
        X, y_encoded, test_size=0.2, val_size=0.1
    )

    # Step 4: Train models
    print("\n[4/7] Training models...")

    # Random Forest
    print("\n  Training Random Forest...")
    rf_model = RandomForestClassifier(n_estimators=200, max_depth=30, random_state=42, n_jobs=-1)
    rf_model.fit(X_train, y_train)
    rf_acc = accuracy_score(y_val, rf_model.predict(X_val))
    print(f"  Random Forest Val Accuracy: {rf_acc:.4f}")

    # XGBoost
    print("\n  Training XGBoost...")
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    xgb_params = {
        'objective': 'multi:softmax',
        'num_class': len(ACTIVITY_ORDER),
        'max_depth': 10,
        'learning_rate': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'eval_metric': 'mlogloss',
        'seed': 42
    }
    xgb_model = xgb.train(xgb_params, dtrain, num_boost_round=200, evals=[(dval, 'val')], verbose_eval=False)
    xgb_acc = accuracy_score(y_val, xgb_model.predict(dval))
    print(f"  XGBoost Val Accuracy: {xgb_acc:.4f}")

    # Select best model
    best_model = rf_model if rf_acc > xgb_acc else xgb_model
    best_model_name = "RandomForest" if rf_acc > xgb_acc else "XGBoost"
    print(f"\n  Best Model: {best_model_name}")

    # Step 5: Final evaluation on test set
    print("\n[5/7] Evaluating on test set...")
    if best_model_name == "RandomForest":
        y_test_pred = best_model.predict(X_test)
    else:
        dtest = xgb.DMatrix(X_test)
        y_test_pred = best_model.predict(dtest)

    test_acc = accuracy_score(y_test, y_test_pred)
    print(f"Test Accuracy: {test_acc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_test_pred, target_names=label_encoder.classes_))

    # Step 6: Save model
    print("\n[6/7] Saving model...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = f"models/{best_model_name}_{timestamp}"
    os.makedirs(model_dir, exist_ok=True)

    if best_model_name == "RandomForest":
        joblib.dump(best_model, f"{model_dir}/model.pkl")
    else:
        best_model.save_model(f"{model_dir}/model.json")

    joblib.dump(scaler, f"{model_dir}/scaler.pkl")
    joblib.dump(label_encoder, f"{model_dir}/label_encoder.pkl")

    # Save metadata
    with open(f"{model_dir}/metadata.json", 'w') as f:
        json.dump({
            'model_type': best_model_name,
            'train_samples': len(X_train),
            'val_samples': len(X_val),
            'test_samples': len(X_test),
            'val_accuracy': float(rf_acc if best_model_name == "RandomForest" else xgb_acc),
            'test_accuracy': float(test_acc),
            'classes': label_encoder.classes_.tolist(),
            'timestamp': timestamp
        }, f, indent=2)

    print(f"Model saved to {model_dir}/")

    # Step 7: Summary
    print("\n[7/7] Training complete!")
    print("="*60)
    print(f"Model Type: {best_model_name}")
    print(f"Test Accuracy: {test_acc:.4f}")
    print(f"Model Path: {model_dir}/")
    print("="*60)

    return best_model, scaler, label_encoder


# Run the pipeline
model, scaler, label_encoder = full_training_pipeline()
```

---

## Inference Integration

### Real-Time Inference with Deployed Model

```python
import joblib
import numpy as np

class ActivityClassifier:
    """
    Wrapper for deployed activity classification model.
    """
    def __init__(self, model_dir: str):
        """
        Load trained model, scaler, and label encoder.

        Args:
            model_dir: Path to saved model directory
        """
        self.model = joblib.load(f"{model_dir}/model.pkl")
        self.scaler = joblib.load(f"{model_dir}/scaler.pkl")
        self.label_encoder = joblib.load(f"{model_dir}/label_encoder.pkl")

        with open(f"{model_dir}/metadata.json", 'r') as f:
            self.metadata = json.load(f)

        print(f"Loaded {self.metadata['model_type']} model")
        print(f"Test Accuracy: {self.metadata['test_accuracy']:.4f}")

    def predict(self, vector: np.ndarray):
        """
        Predict activity from a single 270-dim vector.

        Args:
            vector: Single vector of shape (270,) or batch of shape (N, 270)

        Returns:
            activity_label: String label (e.g., "Standing")
            confidence: Probability of predicted class
        """
        # Ensure 2D shape
        if vector.ndim == 1:
            vector = vector.reshape(1, -1)

        # Normalize
        vector_scaled = self.scaler.transform(vector)

        # Predict
        if hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(vector_scaled)
            predicted_idx = probabilities.argmax(axis=1)[0]
            confidence = probabilities[0, predicted_idx]
        else:
            # XGBoost
            dmatrix = xgb.DMatrix(vector_scaled)
            predicted_idx = int(self.model.predict(dmatrix)[0])
            confidence = None  # XGBoost in softmax mode doesn't return probabilities

        activity_label = self.label_encoder.inverse_transform([predicted_idx])[0]

        return activity_label, confidence

    def predict_batch(self, vectors: np.ndarray):
        """
        Predict activities for multiple vectors.

        Args:
            vectors: Batch of shape (N, 270)

        Returns:
            labels: Array of predicted labels (N,)
            confidences: Array of confidences (N,)
        """
        vectors_scaled = self.scaler.transform(vectors)

        if hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(vectors_scaled)
            predicted_indices = probabilities.argmax(axis=1)
            confidences = probabilities[np.arange(len(predicted_indices)), predicted_indices]
        else:
            dmatrix = xgb.DMatrix(vectors_scaled)
            predicted_indices = self.model.predict(dmatrix).astype(int)
            confidences = np.full(len(predicted_indices), None)

        labels = self.label_encoder.inverse_transform(predicted_indices)

        return labels, confidences


# Usage example
classifier = ActivityClassifier(model_dir="models/RandomForest_20250101_120000")

# Single prediction
test_vector = X_test[0]  # Shape: (270,)
activity, confidence = classifier.predict(test_vector)
print(f"Predicted: {activity} (confidence: {confidence:.2f})")

# Batch prediction
batch_vectors = X_test[:100]  # Shape: (100, 270)
activities, confidences = classifier.predict_batch(batch_vectors)
for activity, conf in zip(activities[:10], confidences[:10]):
    print(f"  {activity}: {conf:.2f}")
```

### Integration with Sensor-Hub (Real-Time Classification)

```python
# This code would be added to sensor-hub/main.py or a new inference module

from activity_classifier import ActivityClassifier
import numpy as np

class RealtimeActivityDetector:
    """
    Manages real-time activity detection using sliding windows.
    """
    def __init__(self, model_dir: str, window_size: int = 500):
        """
        Args:
            model_dir: Path to trained model
            window_size: Window size in milliseconds (default: 500ms)
        """
        self.classifier = ActivityClassifier(model_dir)
        self.window_size = window_size

        # Buffers for constructing 270-dim vectors
        self.foot_buffer = []
        self.accel_buffer = []

        self.current_activity = "Unknown"
        self.confidence = 0.0

    def add_foot_data(self, foot_data: dict):
        """Add new foot pressure data to buffer."""
        self.foot_buffer.append(foot_data)
        self._try_predict()

    def add_accel_data(self, accel_data: dict):
        """Add new accelerometer data to buffer."""
        self.accel_buffer.append(accel_data)
        self._try_predict()

    def _try_predict(self):
        """
        Check if we have enough data for a 500ms window, then predict.
        """
        # Check if we have enough data
        # (This is simplified - real implementation would check timestamps)
        if len(self.foot_buffer) < 10 or len(self.accel_buffer) < 10:
            return

        # Extract features from buffers to create 270-dim vector
        # (This is a placeholder - actual implementation would match vector structure)
        vector = self._construct_vector()

        # Predict
        activity, confidence = self.classifier.predict(vector)

        # Update state
        self.current_activity = activity
        self.confidence = confidence

        print(f"Detected: {activity} (confidence: {confidence:.2f})")

        # Clear old data from buffers
        self.foot_buffer = self.foot_buffer[-10:]
        self.accel_buffer = self.accel_buffer[-10:]

    def _construct_vector(self) -> np.ndarray:
        """
        Construct 270-dim vector from buffered sensor data.
        Must match the exact structure used during training.
        """
        # Placeholder - implement based on vectorization.py logic
        vector = np.zeros(270)

        # Extract foot pressure features (dims 0-179)
        # ... (extract from self.foot_buffer)

        # Extract accelerometer features (dims 180-269)
        # ... (extract from self.accel_buffer)

        return vector


# Usage in main.py
detector = RealtimeActivityDetector(model_dir="models/best_model")

# In notification callbacks
def on_foot_data(data):
    detector.add_foot_data(data)

def on_accel_data(data):
    detector.add_accel_data(data)
```

---

## Summary

This guide provides everything needed to:

1. **Export** training data from Qdrant (270-dim vectors + labels)
2. **Preprocess** data (normalization, outlier removal, splitting)
3. **Train** models (LSTM, CNN, Random Forest, XGBoost)
4. **Evaluate** performance (validation, test sets, cross-validation)
5. **Deploy** models for real-time inference

**Recommended Starting Point:**
1. Export data using `export_all_data()`
2. Train a Random Forest model (easiest, interpretable)
3. Evaluate feature importance to understand key sensors
4. If accuracy is insufficient, try XGBoost or LSTM
5. Deploy best model using `ActivityClassifier` wrapper

**Expected Performance:**
- Random Forest: ~75-85% accuracy
- XGBoost: ~80-90% accuracy
- LSTM: ~85-95% accuracy (with enough data)

**Key Success Factors:**
- Collect balanced data for all 9 activities
- Ensure high-quality labeling (1 session = 1 activity)
- Use time-based splitting for realistic evaluation
- Monitor for overfitting with validation set

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture and data flow
- [SENSOR_SPECIFICATIONS.md](./SENSOR_SPECIFICATIONS.md) - Hardware specs and protocols
- [DATA_DICTIONARY.md](./DATA_DICTIONARY.md) - Complete data field reference
- [ACTIVITY_DETECTION_GUIDE.md](./ACTIVITY_DETECTION_GUIDE.md) - Feature engineering guide
