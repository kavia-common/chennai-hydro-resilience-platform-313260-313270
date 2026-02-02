"""
Machine Learning model integration module.

This package contains stubs for loading and running LSTM and U-Net models
trained in Google Colab. Currently returns placeholder predictions.
"""
from .model_loader import load_lstm_model, load_unet_model, predict_flood_risk

__all__ = ["load_lstm_model", "load_unet_model", "predict_flood_risk"]
