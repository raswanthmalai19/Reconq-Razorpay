from fastapi import APIRouter, UploadFile, File, HTTPException
import os
from llm.document_parser import parse_document, match_extracted_to_ledger

router = APIRouter()

@router.post("/documents/parse")
async def api_parse_document(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        mime_type = file.content_type or "application/octet-stream"
        
        parsed_data = parse_document(
            file_bytes=contents,
            filename=file.filename,
            mime_type=mime_type
        )
        return parsed_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/match")
async def api_match_document(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        mime_type = file.content_type or "application/octet-stream"
        
        # 1. Parse document
        parsed_data = parse_document(
            file_bytes=contents,
            filename=file.filename,
            mime_type=mime_type
        )
        
        # 2. Match against ledger
        # Construct path to internal_ledger.csv
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ledger_path = os.path.join(base_dir, "data", "internal_ledger.csv")
        
        extracted_transactions = parsed_data.get("transactions", [])
        
        match_results = match_extracted_to_ledger(
            extracted_transactions=extracted_transactions,
            ledger_path=ledger_path
        )
        
        # Add the document metadata to the response
        match_results["document_type"] = parsed_data.get("document_type")
        match_results["source"] = parsed_data.get("source")
        match_results["summary"] = parsed_data.get("summary")
        
        return match_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
