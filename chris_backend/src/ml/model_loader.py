"""
Machine Learning model loader for CHRIS with ONNX/TorchScript support.

This module provides complete inference scaffolding for:
- Loading LSTM (temporal) and U-Net (spatial) models
- Preprocessing input data for model inference
- Postprocessing model outputs to API-ready format
- Model metadata and versioning

Supported Formats:
- .pkl (pickle) - scikit-learn, TensorFlow/Keras
- .onnx (ONNX Runtime) - production inference
- .pt/.pth (PyTorch/TorchScript) - PyTorch models
"""
import os
import json
from typing import Optional, Dict, Any, List, Tuple
import logging
import numpy as np
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Global model cache
_lstm_model: Optional[Any] = None
_unet_model: Optional[Any] = None
_lstm_metadata: Optional[Dict] = None
_unet_metadata: Optional[Dict] = None


class ModelLoader:
    """
    Unified model loader for LSTM and U-Net models.
    Supports multiple formats: .pkl, .onnx, .pt/.pth
    """
    
    @staticmethod
    def detect_format(model_path: str) -> str:
        """
        Detect model format from file extension.
        
        Args:
            model_path: Path to model file
            
        Returns:
            Format string: 'pickle', 'onnx', 'pytorch', or 'unknown'
        """
        ext = Path(model_path).suffix.lower()
        if ext == '.pkl':
            return 'pickle'
        elif ext == '.onnx':
            return 'onnx'
        elif ext in ['.pt', '.pth']:
            return 'pytorch'
        else:
            return 'unknown'
    
    @staticmethod
    def load_pickle_model(model_path: str) -> Any:
        """
        Load pickle model (scikit-learn, TensorFlow, etc.)
        
        Args:
            model_path: Path to .pkl file
            
        Returns:
            Loaded model object
        """
        try:
            import pickle
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            logger.info(f"✅ Loaded pickle model from {model_path}")
            return model
        except Exception as e:
            logger.error(f"Failed to load pickle model: {e}")
            raise
    
    @staticmethod
    def load_onnx_model(model_path: str) -> Any:
        """
        Load ONNX model using ONNX Runtime.
        
        Args:
            model_path: Path to .onnx file
            
        Returns:
            ONNX InferenceSession
        """
        try:
            import onnxruntime as ort
            session = ort.InferenceSession(model_path)
            logger.info(f"✅ Loaded ONNX model from {model_path}")
            logger.info(f"Input names: {[input.name for input in session.get_inputs()]}")
            logger.info(f"Output names: {[output.name for output in session.get_outputs()]}")
            return session
        except ImportError:
            logger.error("onnxruntime not installed. Install with: pip install onnxruntime")
            raise
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            raise
    
    @staticmethod
    def load_pytorch_model(model_path: str) -> Any:
        """
        Load PyTorch/TorchScript model.
        
        Args:
            model_path: Path to .pt/.pth file
            
        Returns:
            Loaded PyTorch model
        """
        try:
            import torch
            model = torch.jit.load(model_path) if model_path.endswith('.pt') else torch.load(model_path)
            model.eval()
            logger.info(f"✅ Loaded PyTorch model from {model_path}")
            return model
        except ImportError:
            logger.error("torch not installed. Install with: pip install torch")
            raise
        except Exception as e:
            logger.error(f"Failed to load PyTorch model: {e}")
            raise


def load_model_metadata(model_path: str) -> Dict[str, Any]:
    """
    Load model metadata from adjacent .json file.
    Expected format: model_name.onnx -> model_name.json
    
    Args:
        model_path: Path to model file
        
    Returns:
        Metadata dictionary with version, input_shape, etc.
    """
    metadata_path = Path(model_path).with_suffix('.json')
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            logger.info(f"✅ Loaded metadata from {metadata_path}")
            return metadata
        except Exception as e:
            logger.warning(f"Failed to load metadata: {e}")
    
    # Return default metadata
    return {
        "version": "unknown",
        "created_at": None,
        "input_shape": None,
        "output_shape": None,
        "framework": "unknown",
        "description": "No metadata available"
    }


# PUBLIC_INTERFACE
def load_lstm_model(model_path: Optional[str] = None) -> Optional[Any]:
    """
    Load LSTM model for temporal flood risk prediction.
    Supports .pkl, .onnx, .pt/.pth formats.
    
    Args:
        model_path: Path to model file. If None, checks LSTM_MODEL_PATH env var.
        
    Returns:
        Loaded model object or None if not available
    """
    global _lstm_model, _lstm_metadata
    
    if _lstm_model is not None:
        return _lstm_model
    
    if model_path is None:
        model_path = os.getenv("LSTM_MODEL_PATH")
    
    if not model_path or not os.path.exists(model_path):
        logger.warning("No LSTM model found. Using pre-computed predictions from database.")
        return None
    
    try:
        logger.info(f"Loading LSTM model from {model_path}")
        format_type = ModelLoader.detect_format(model_path)
        
        if format_type == 'pickle':
            _lstm_model = ModelLoader.load_pickle_model(model_path)
        elif format_type == 'onnx':
            _lstm_model = ModelLoader.load_onnx_model(model_path)
        elif format_type == 'pytorch':
            _lstm_model = ModelLoader.load_pytorch_model(model_path)
        else:
            raise ValueError(f"Unsupported model format: {format_type}")
        
        _lstm_metadata = load_model_metadata(model_path)
        _lstm_metadata['format'] = format_type
        _lstm_metadata['loaded_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"✅ LSTM model loaded successfully (format: {format_type})")
        return _lstm_model
    
    except Exception as e:
        logger.error(f"Failed to load LSTM model: {e}", exc_info=True)
        return None


# PUBLIC_INTERFACE
def load_unet_model(model_path: Optional[str] = None) -> Optional[Any]:
    """
    Load U-Net model for spatial sponge zone segmentation.
    Supports .pkl, .onnx, .pt/.pth formats.
    
    Args:
        model_path: Path to model file. If None, checks UNET_MODEL_PATH env var.
        
    Returns:
        Loaded model object or None if not available
    """
    global _unet_model, _unet_metadata
    
    if _unet_model is not None:
        return _unet_model
    
    if model_path is None:
        model_path = os.getenv("UNET_MODEL_PATH")
    
    if not model_path or not os.path.exists(model_path):
        logger.warning("No U-Net model found. Using pre-computed zone data from database.")
        return None
    
    try:
        logger.info(f"Loading U-Net model from {model_path}")
        format_type = ModelLoader.detect_format(model_path)
        
        if format_type == 'pickle':
            _unet_model = ModelLoader.load_pickle_model(model_path)
        elif format_type == 'onnx':
            _unet_model = ModelLoader.load_onnx_model(model_path)
        elif format_type == 'pytorch':
            _unet_model = ModelLoader.load_pytorch_model(model_path)
        else:
            raise ValueError(f"Unsupported model format: {format_type}")
        
        _unet_metadata = load_model_metadata(model_path)
        _unet_metadata['format'] = format_type
        _unet_metadata['loaded_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"✅ U-Net model loaded successfully (format: {format_type})")
        return _unet_model
    
    except Exception as e:
        logger.error(f"Failed to load U-Net model: {e}", exc_info=True)
        return None


# PUBLIC_INTERFACE
def preprocess_lstm_input(
    years: int,
    climate_data: Optional[Dict[str, Any]] = None
) -> np.ndarray:
    """
    Preprocess input data for LSTM model inference.
    
    Args:
        years: Number of years to forecast
        climate_data: Optional dict with 'oni_anomaly', 'iod_anomaly', 'rainfall_mm'
        
    Returns:
        Preprocessed numpy array ready for model input
        
    Expected LSTM Input Shape: (batch_size, sequence_length, features)
    Features typically include: [year_norm, oni, iod, rainfall_mm, ...]
    """
    if climate_data is None:
        climate_data = {}
    
    # Extract features with defaults
    oni = climate_data.get('oni_anomaly', 0.0)
    iod = climate_data.get('iod_anomaly', 0.0)
    rainfall = climate_data.get('rainfall_mm', 1200.0)
    
    # Normalize features (example normalization)
    # In production, use same normalization as training
    current_year = datetime.now().year
    years_norm = np.array([[(current_year + i - 2000) / 100.0] for i in range(years)])
    oni_norm = np.array([[oni / 3.0] for _ in range(years)])  # ONI typically -3 to +3
    iod_norm = np.array([[iod / 2.0] for _ in range(years)])  # IOD typically -2 to +2
    rainfall_norm = np.array([[rainfall / 2000.0] for _ in range(years)])  # Normalize to 0-1
    
    # Combine features: shape (years, 4)
    features = np.hstack([years_norm, oni_norm, iod_norm, rainfall_norm])
    
    # Reshape for LSTM: (batch_size=1, sequence_length=years, features=4)
    lstm_input = features.reshape(1, years, 4).astype(np.float32)
    
    logger.debug(f"Preprocessed LSTM input shape: {lstm_input.shape}")
    return lstm_input


# PUBLIC_INTERFACE
def postprocess_lstm_output(
    raw_output: np.ndarray,
    years: int
) -> List[Dict[str, Any]]:
    """
    Postprocess LSTM model output to API-ready format.
    
    Args:
        raw_output: Raw model output numpy array
        years: Number of years forecasted
        
    Returns:
        List of prediction dicts with year, risk_score, risk_category, etc.
    """
    predictions = []
    current_year = datetime.now().year
    
    # Handle different output shapes
    if raw_output.ndim == 3:
        raw_output = raw_output[0]  # Remove batch dimension
    
    for i in range(min(years, len(raw_output))):
        risk_score = float(raw_output[i][0] * 100)  # Assuming output is 0-1, scale to 0-100
        risk_score = max(0, min(100, risk_score))  # Clamp to 0-100
        
        # Categorize risk
        if risk_score >= 85:
            risk_category = "Critical"
        elif risk_score >= 65:
            risk_category = "High"
        elif risk_score >= 40:
            risk_category = "Moderate"
        else:
            risk_category = "Low"
        
        predictions.append({
            "year": current_year + i + 1,
            "risk_score": round(risk_score, 2),
            "risk_category": risk_category,
            "predicted_rainfall_mm": round(1000 + risk_score * 8, 1),  # Estimate
            "confidence": round(min(0.95, 0.75 + (100 - abs(risk_score - 50)) / 200), 2)
        })
    
    logger.debug(f"Postprocessed {len(predictions)} predictions")
    return predictions


# PUBLIC_INTERFACE
def predict_flood_risk(
    years: int = 5,
    climate_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Generate flood risk predictions using LSTM model.
    Performs full inference pipeline: load -> preprocess -> predict -> postprocess
    
    Args:
        years: Number of years to forecast (1-10)
        climate_data: Optional climate driver data (ONI, IOD, rainfall)
        
    Returns:
        List of predictions with risk scores and metadata
        Empty list if model not available
    """
    model = load_lstm_model()
    
    if model is None:
        logger.info("LSTM model not loaded. Using database predictions.")
        return []
    
    try:
        # Preprocess input
        model_input = preprocess_lstm_input(years, climate_data)
        
        # Run inference based on model type
        if _lstm_metadata and _lstm_metadata.get('format') == 'onnx':
            # ONNX Runtime inference
            input_name = model.get_inputs()[0].name
            output = model.run(None, {input_name: model_input})
            raw_output = output[0]
        elif _lstm_metadata and _lstm_metadata.get('format') == 'pytorch':
            # PyTorch inference
            import torch
            with torch.no_grad():
                raw_output = model(torch.from_numpy(model_input)).numpy()
        else:
            # Pickle model (scikit-learn, Keras, etc.)
            raw_output = model.predict(model_input)
        
        # Postprocess output
        predictions = postprocess_lstm_output(raw_output, years)
        
        logger.info(f"✅ Generated {len(predictions)} predictions using LSTM model")
        return predictions
    
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        return []


# PUBLIC_INTERFACE
def get_model_info(model_type: str = "lstm") -> Dict[str, Any]:
    """
    Get information about loaded model.
    
    Args:
        model_type: 'lstm' or 'unet'
        
    Returns:
        Dictionary with model metadata, status, capabilities
    """
    if model_type.lower() == "lstm":
        model = _lstm_model
        metadata = _lstm_metadata or {}
    elif model_type.lower() == "unet":
        model = _unet_model
        metadata = _unet_metadata or {}
    else:
        return {"error": "Invalid model_type. Use 'lstm' or 'unet'"}
    
    return {
        "model_type": model_type,
        "status": "loaded" if model is not None else "not_loaded",
        "format": metadata.get('format', 'unknown'),
        "version": metadata.get('version', 'unknown'),
        "loaded_at": metadata.get('loaded_at'),
        "description": metadata.get('description', 'No description available'),
        "input_shape": metadata.get('input_shape'),
        "output_shape": metadata.get('output_shape'),
        "framework": metadata.get('framework', 'unknown'),
        "capabilities": {
            "inference": model is not None,
            "batch_prediction": model is not None,
            "real_time": metadata.get('format') == 'onnx'
        }
    }


# PUBLIC_INTERFACE
def save_uploaded_model(
    file_path: str,
    model_type: str,
    version: str,
    metadata: Optional[Dict] = None
) -> Tuple[bool, str]:
    """
    Save uploaded model to persistent storage with validation.
    
    Args:
        file_path: Temporary path of uploaded file
        model_type: 'lstm' or 'unet'
        version: Model version string (e.g., 'v1.0')
        metadata: Optional metadata dict
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Validate model type
        if model_type.lower() not in ['lstm', 'unet']:
            return False, "Invalid model_type. Must be 'lstm' or 'unet'"
        
        # Detect format
        format_type = ModelLoader.detect_format(file_path)
        if format_type == 'unknown':
            return False, "Unsupported format. Use .pkl, .onnx, or .pt/.pth"
        
        # Create models directory
        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)
        
        # Generate destination path
        filename = f"{model_type}_{version}{Path(file_path).suffix}"
        dest_path = models_dir / filename
        
        # Copy file
        import shutil
        shutil.copy(file_path, dest_path)
        
        # Save metadata
        if metadata:
            metadata['uploaded_at'] = datetime.utcnow().isoformat()
            metadata['format'] = format_type
            metadata['version'] = version
            metadata_path = dest_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        # Try to load model as smoke test
        if model_type.lower() == 'lstm':
            test_model = load_lstm_model(str(dest_path))
        else:
            test_model = load_unet_model(str(dest_path))
        
        if test_model is None:
            return False, "Model loaded but failed smoke test"
        
        logger.info(f"✅ Model saved successfully: {dest_path}")
        return True, f"Model saved to {dest_path}"
    
    except Exception as e:
        logger.error(f"Failed to save model: {e}", exc_info=True)
        return False, f"Failed to save model: {str(e)}"
