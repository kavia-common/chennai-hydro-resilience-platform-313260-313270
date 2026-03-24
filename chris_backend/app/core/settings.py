from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    chris_model_a_provider: str = "onnx"  # "onnx" | "tensorflow"
    # Default filenames match the backend README (and the Colab export snippets).
    chris_model_a_path: str = "models/model_a/rainfall_lstm.onnx"
    chris_model_a_meta_path: str = "models/model_a/meta.json"
    chris_model_a_scaler_x_path: str = "models/model_a/scaler_X.joblib"
    chris_model_a_scaler_y_path: str = "models/model_a/scaler_y.joblib"

    chris_model_b_provider: str = "onnx"
    # Default filename matches the backend README + notebook.
    chris_model_b_path: str = "models/model_b/unet.onnx"
    chris_model_b_meta_path: str = "models/model_b/meta.json"


settings = Settings()
