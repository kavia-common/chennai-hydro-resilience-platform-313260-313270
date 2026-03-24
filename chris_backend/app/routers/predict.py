from fastapi import APIRouter, File, HTTPException, UploadFile

from app.ml import registry
from app.ml.model_a import predict_next_rainfall_mm
from app.ml.model_b import predict_segmentation
from app.schemas.predict import FloodRiskRequest, FloodRiskResponse, SegmentationResponse

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("/flood_risk", response_model=FloodRiskResponse)
def predict_flood_risk(req: FloodRiskRequest) -> FloodRiskResponse:
    try:
        if registry.MODEL_A is None:
            registry.load_all()
        if registry.MODEL_A is None:
            raise RuntimeError("Model A not configured/loaded")

        payload = [s.model_dump() for s in req.sequence]
        out = predict_next_rainfall_mm(registry.MODEL_A, payload)
        return FloodRiskResponse(**out)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/segmentation", response_model=SegmentationResponse)
async def predict_segmentation_api(file: UploadFile = File(...)) -> SegmentationResponse:
    try:
        if registry.MODEL_B is None:
            registry.load_all()
        if registry.MODEL_B is None:
            raise RuntimeError("Model B not configured/loaded")

        data = await file.read()
        out = predict_segmentation(registry.MODEL_B, data)
        return SegmentationResponse(**out)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
