import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from openai import APIError, APITimeoutError
from pydantic import ValidationError

from app.config import MAX_FILE_BYTES
from app.llm.msme import extract as extract_msme
from app.llm.salary import extract
from app.msme_analyser import AnalyserError, AnalyserTimeout, analyse
from app.schemas import FailureResult, Result
from app.workbook import WorkbookError, WorkbookTooLargeError, to_text

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
def root():
    return {"service": "CAM Salary API", "version": "1.0.0"}


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/extract-salary", response_model=Result | FailureResult)
async def extract_salary(file: UploadFile = File(...)):
    try:
        if not (file.filename or "").lower().endswith(".xlsx"):
            raise HTTPException(status_code=400, detail="Upload an .xlsx CAM report.")

        data = await file.read(MAX_FILE_BYTES + 1)
        if not data:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="Uploaded file exceeds the size limit.")
    finally:
        await file.close()

    try:
        text = to_text(data)
        if not text.strip():
            raise HTTPException(status_code=400, detail="No readable cell data found.")

        payload = await run_in_threadpool(extract, text)
        if isinstance(payload, dict) and payload.get("success") is False:
            return FailureResult.model_validate(payload).model_dump(mode="json")
        return Result.model_validate(payload).model_dump(mode="json")
    except HTTPException:
        raise
    except WorkbookTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except WorkbookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValidationError as exc:
        issues = [
            {"loc": list(issue["loc"]), "msg": issue["msg"], "type": issue["type"]}
            for issue in exc.errors(include_input=False)
        ]
        raise HTTPException(
            status_code=502,
            detail={
                "error": "Model output did not match the salary response schema.",
                "issues": issues,
            },
        ) from exc
    except APITimeoutError as exc:
        log.warning("Salary model request timed out")
        raise HTTPException(status_code=504, detail="Salary model request timed out.") from exc
    except APIError as exc:
        log.exception("Salary model request failed")
        raise HTTPException(status_code=502, detail="Salary model request failed.") from exc
    except ValueError as exc:
        log.warning("Salary model returned invalid output: %s", str(exc))
        raise HTTPException(
            status_code=502, detail="Salary model returned invalid output."
        ) from exc
    except RuntimeError as exc:
        log.exception("Salary extraction is not configured correctly")
        raise HTTPException(
            status_code=500, detail="Salary extraction is not configured correctly."
        ) from exc
    except Exception as exc:
        log.exception("Salary extraction failed")
        raise HTTPException(status_code=500, detail="Salary extraction failed.") from exc


@router.post("/msme-income")
async def extract_msme_income(file: UploadFile = File(...)):
    filename = file.filename or ""

    try:
        if not filename.lower().endswith(".xlsx"):
            raise HTTPException(status_code=400, detail="Upload an .xlsx CAM report.")

        data = await file.read(MAX_FILE_BYTES + 1)
        if not data:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="Uploaded file exceeds the size limit.")
    finally:
        await file.close()

    try:
        draft = await run_in_threadpool(analyse, data, filename)
        return await run_in_threadpool(extract_msme, draft)
    except HTTPException:
        raise
    except WorkbookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AnalyserTimeout as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except AnalyserError as exc:
        log.exception("MSME analyser failed: %s", exc)
        raise HTTPException(status_code=500, detail="MSME analyser failed.") from exc
    except APITimeoutError as exc:
        log.warning("MSME model request timed out")
        raise HTTPException(status_code=504, detail="MSME model request timed out.") from exc
    except APIError as exc:
        log.exception("MSME model request failed")
        raise HTTPException(status_code=502, detail="MSME model request failed.") from exc
    except ValueError as exc:
        log.warning("MSME model returned invalid output: %s", str(exc))
        raise HTTPException(status_code=502, detail="MSME model returned invalid output.") from exc
    except RuntimeError as exc:
        log.exception("MSME extraction is not configured correctly")
        raise HTTPException(
            status_code=500, detail="MSME extraction is not configured correctly."
        ) from exc
    except Exception as exc:
        log.exception("MSME extraction failed")
        raise HTTPException(status_code=500, detail="MSME extraction failed.") from exc
