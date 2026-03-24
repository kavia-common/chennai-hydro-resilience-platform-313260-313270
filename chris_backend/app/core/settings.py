from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Frontend integration / CORS ---
    # This is present in the container env list and is a convenient default for CORS,
    # but CHRIS_CORS_ALLOW_ORIGINS remains the canonical override.
    react_app_frontend_url: str | None = None  # REACT_APP_FRONTEND_URL
    chris_cors_allow_origins: str | None = None  # comma-separated origins or "*"
    chris_cors_allow_credentials: bool = False

    # --- Model A (rainfall + flood risk) ---
    chris_model_a_provider: str = "onnx"  # "onnx" | "tensorflow"
    chris_model_a_mock_mode: bool = False  # if true, run deterministic mock instead of loading artifacts

    # Default filenames match the backend README (and the Colab export snippets).
    chris_model_a_path: str = "models/model_a/rainfall_lstm.onnx"
    chris_model_a_meta_path: str = "models/model_a/meta.json"
    chris_model_a_scaler_x_path: str = "models/model_a/scaler_X.joblib"
    chris_model_a_scaler_y_path: str = "models/model_a/scaler_y.joblib"

    # Mock config (env-controlled; used only when CHRIS_MODEL_A_MOCK_MODE=true)
    chris_model_a_mock_seq_len: int = 12
    chris_model_a_mock_flood_threshold_mm: float = 250.0
    chris_model_a_mock_baseline_mm: float = 200.0

    # --- Model B (U-Net segmentation) ---
    chris_model_b_provider: str = "onnx"
    # Default filename matches the backend README + notebook.
    chris_model_b_path: str = "models/model_b/unet.onnx"
    chris_model_b_meta_path: str = "models/model_b/meta.json"


settings = Settings()
