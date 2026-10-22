import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from openai import APIError, APITimeoutError
from pydantic import ValidationError

from app.config import MAX_FILE_BYTES
from app.llm.salary import extract
from app.schemas import Result
from app.workbook import to_text

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
def root():
    return {"service": "CAM Salary API", "version": "1.0.0"}


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/extract-salary")
async def extract_salary(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Upload an .xlsx CAM report.")

    data = await file.read(MAX_FILE_BYTES + 1)
    await file.close()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the size limit.")

    try:
        text = to_text(data)
        if not text.strip():
            raise HTTPException(status_code=400, detail="No readable cell data found.")
        result = extract(text)
        return Result.model_validate(result).model_dump(mode="json")
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "Model output did not match the salary response schema.",
                "issues": exc.errors(include_input=False),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except APITimeoutError as exc:
        log.warning("Salary model request timed out")
        raise HTTPException(status_code=504, detail="Salary model request timed out.") from exc
    except APIError as exc:
        log.warning("Salary model request failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Salary model request failed.") from exc
    except Exception as exc:
        log.exception("Salary extraction failed")
        raise HTTPException(status_code=500, detail="Salary extraction failed.") from exc
