# ML Model Integration Guide

## Overview

The CHRIS backend now supports full ML model inference with proper scaffolding for ONNX, TorchScript, and Pickle models trained in Google Colab or locally.

## Supported Formats

1. **ONNX (.onnx)** - Recommended for production
   - Cross-platform, optimized inference
   - Best performance with ONNX Runtime
   
2. **PyTorch (.pt, .pth)** - TorchScript
   - Native PyTorch models
   - Good for PyTorch-trained models
   
3. **Pickle (.pkl)** - Compatibility
   - scikit-learn, TensorFlow/Keras models
   - Easy to export from Colab

## Quick Start

### 1. Export Your Model from Colab

#### ONNX Export (Recommended)
```python
import torch
import torch.onnx

# After training your LSTM model
dummy_input = torch.randn(1, 5, 4)  # (batch, sequence, features)
torch.onnx.export(
    lstm_model,
    dummy_input,
    "lstm_model_v1.onnx",
    export_params=True,
    input_names=['input'],
    output_names=['output'],
    dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
)
```

#### PyTorch Export
```python
# Save TorchScript
scripted_model = torch.jit.script(lstm_model)
scripted_model.save("lstm_model_v1.pt")
```

#### Pickle Export
```python
import pickle

with open("lstm_model_v1.pkl", "wb") as f:
    pickle.dump(lstm_model, f)
```

### 2. Create Model Metadata

Create a JSON file with the same name as your model (e.g., `lstm_model_v1.json`):

```json
{
  "version": "v1.0",
  "created_at": "2026-02-02T12:00:00Z",
  "description": "LSTM model trained on 100 years Chennai rainfall data",
  "input_shape": [1, 5, 4],
  "output_shape": [1, 5, 1],
  "framework": "PyTorch",
  "training_info": {
    "epochs": 100,
    "dataset_size": 100,
    "features": ["year_norm", "oni_anomaly", "iod_anomaly", "rainfall_mm"]
  }
}
```

### 3. Deploy Model

Place both files in the `models/` directory:

```bash
mkdir -p models
mv lstm_model_v1.onnx models/
mv lstm_model_v1.json models/
```

### 4. Configure Environment

Add to `.env`:

```env
LSTM_MODEL_PATH=models/lstm_model_v1.onnx
UNET_MODEL_PATH=models/unet_model_v1.onnx  # If you have U-Net
```

### 5. Install ML Dependencies

```bash
pip install -r requirements-ml.txt
```

### 6. Restart Backend

```bash
# Backend will auto-load models on startup
python -m uvicorn src.api.main:app --reload
```

## API Endpoints

### Check Model Status

```bash
GET /api/v1/models/info?model_type=all
```

Response:
```json
{
  "lstm": {
    "model_type": "lstm",
    "status": "loaded",
    "format": "onnx",
    "version": "v1.0",
    "loaded_at": "2026-02-02T12:00:00Z",
    "capabilities": {
      "inference": true,
      "batch_prediction": true,
      "real_time": true
    }
  }
}
```

### Generate Forecast (Uses Loaded Model)

```bash
POST /api/v1/forecast/
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "years": 5,
  "include_climate_factors": true
}
```

## Model Input/Output Specifications

### LSTM Model

**Input Shape:** `(batch_size, sequence_length, features)`
- `batch_size`: Usually 1 for single predictions
- `sequence_length`: Number of years to forecast (1-10)
- `features`: 4 features [year_norm, oni, iod, rainfall_mm]

**Output Shape:** `(batch_size, sequence_length, 1)`
- Risk scores normalized to 0-1 (will be scaled to 0-100)

**Preprocessing:**
```python
# Input features are normalized:
year_norm = (year - 2000) / 100.0      # Scale to 0-1
oni_norm = oni_anomaly / 3.0            # ONI: -3 to +3
iod_norm = iod_anomaly / 2.0            # IOD: -2 to +2
rainfall_norm = rainfall_mm / 2000.0    # Rainfall: 0-2000mm
```

**Postprocessing:**
```python
# Output is denormalized:
risk_score = model_output * 100          # Scale to 0-100
risk_category = categorize(risk_score)   # Low/Moderate/High/Critical
```

### U-Net Model (Future)

**Input Shape:** `(batch_size, channels, height, width)`
- Satellite imagery (Sentinel-1/2)
- Typical: `(1, 3, 256, 256)` for RGB

**Output Shape:** `(batch_size, classes, height, width)`
- Segmentation mask for sponge zones

## Inference Pipeline

The complete inference flow:

```
User Request → API Endpoint → Model Loader
                                    ↓
                            Check Cache (model loaded?)
                                    ↓
                            Preprocess Input
                                    ↓
                            Run Inference (ONNX/PyTorch/Pickle)
                                    ↓
                            Postprocess Output
                                    ↓
                            Return API Response
```

## Testing Your Model

```python
# Test locally before deployment
from src.ml.model_loader import predict_flood_risk

predictions = predict_flood_risk(
    years=5,
    climate_data={
        'oni_anomaly': 1.2,
        'iod_anomaly': 0.5,
        'rainfall_mm': 1300
    }
)

print(predictions)
```

## Troubleshooting

### Model Not Loading

1. Check file path in `.env`
2. Verify file exists: `ls -la models/`
3. Check logs: Look for "Loading LSTM model" messages
4. Verify format: Use `.onnx` for best results

### Import Errors

```bash
# Install missing dependencies
pip install onnxruntime  # For ONNX
pip install torch        # For PyTorch
```

### Inference Errors

1. Check input shape matches training
2. Verify preprocessing matches training normalization
3. Check model metadata JSON
4. Test with `/api/v1/models/info` endpoint

## Performance Tips

1. **Use ONNX** for fastest inference
2. **Cache models** (done automatically)
3. **Batch predictions** when possible
4. **Monitor memory** for large models

## Next Steps

1. Train your LSTM model in Colab
2. Export to ONNX format
3. Create metadata JSON
4. Deploy and test with `/api/v1/models/info`
5. Generate forecasts with `/api/v1/forecast/`

For questions, check logs or the model loader source: `src/ml/model_loader.py`
