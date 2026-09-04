import os
import json
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Any
from google import genai
from google.genai import types

def parse_document(file_bytes: bytes, filename: str, mime_type: str) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    client = genai.Client(api_key=api_key)
    
    prompt_text = """You are a financial document parser. Extract ALL transactions from this document.
For each transaction, extract: date, description/narration, reference_number (if visible), amount, type (credit/debit).

Return a JSON object with this exact structure:
{
  "document_type": "bank_statement" | "invoice" | "receipt",
  "source": "extracted text identifying the bank/vendor",
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "description": "transaction description",
      "reference": "reference number or null",
      "amount_rupees": 1234.56,
      "type": "credit" | "debit"
    }
  ],
  "summary": {
    "total_credits": 0.00,
    "total_debits": 0.00,
    "transaction_count": 0
  }
}
Return ONLY valid JSON. No markdown fences.
"""

    response = client.models.generate_content(
        model=model_name,
        contents=[
            types.Content(
                role='user',
                parts=[
                    types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                    types.Part.from_text(text=prompt_text)
                ]
            )
        ],
        config=types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=0.1
        )
    )
    
    text = response.text
    # Remove markdown formatting if the model still outputs it despite instructions
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
        
    return json.loads(text.strip())


def match_extracted_to_ledger(extracted_transactions: List[Dict[str, Any]], ledger_path: str) -> Dict[str, Any]:
    ledger_entries = []
    
    # Check if ledger exists
    if not os.path.exists(ledger_path):
        return {
            "matched": [],
            "unmatched_document": extracted_transactions,
            "unmatched_ledger": [],
            "match_rate": 0.0,
            "error": "Ledger file not found"
        }
    
    # Load ledger
    with open(ledger_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ledger_entries.append(row)
            
    matched = []
    unmatched_document = []
    unmatched_ledger = list(ledger_entries)
    
    for ext_tx in extracted_transactions:
        ext_amount = float(ext_tx.get('amount_rupees', 0))
        ext_date_str = ext_tx.get('date', '')
        
        try:
            ext_date = datetime.strptime(ext_date_str, '%Y-%m-%d')
        except ValueError:
            unmatched_document.append(ext_tx)
            continue
            
        match_found = False
        
        for i, ledger_tx in enumerate(unmatched_ledger):
            # Try to get ledger amount
            ledger_amount_str = ledger_tx.get('amount', ledger_tx.get('Amount', '0'))
            # Clean amount string if it has symbols
            ledger_amount_str = str(ledger_amount_str).replace(',', '').replace('₹', '').strip()
            
            try:
                ledger_amount = float(ledger_amount_str)
            except ValueError:
                continue
                
            # Try to get ledger date
            ledger_date_str = ledger_tx.get('date', ledger_tx.get('Date', ''))
            try:
                # Try common formats
                if '-' in ledger_date_str:
                    ledger_date = datetime.strptime(ledger_date_str, '%Y-%m-%d')
                elif '/' in ledger_date_str:
                    try:
                        ledger_date = datetime.strptime(ledger_date_str, '%m/%d/%Y')
                    except ValueError:
                        ledger_date = datetime.strptime(ledger_date_str, '%d/%m/%Y')
                else:
                    continue
            except ValueError:
                continue
                
            # Check conditions: amount within 1% and date within 7 days
            amount_diff = abs(ext_amount - ledger_amount)
            amount_tolerance = ext_amount * 0.01
            
            date_diff = abs((ext_date - ledger_date).days)
            
            if amount_diff <= amount_tolerance and date_diff <= 7:
                matched.append({
                    "document_transaction": ext_tx,
                    "ledger_transaction": ledger_tx
                })
                unmatched_ledger.pop(i)
                match_found = True
                break
                
        if not match_found:
            unmatched_document.append(ext_tx)
            
    total_extracted = len(extracted_transactions)
    match_rate = len(matched) / total_extracted if total_extracted > 0 else 0
    
    return {
        "matched": matched,
        "unmatched_document": unmatched_document,
        "unmatched_ledger": unmatched_ledger,
        "match_rate": match_rate
    }
