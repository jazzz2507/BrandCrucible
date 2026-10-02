import datetime
import json
import os
import re
import asyncio
from typing import Type, TypeVar, Any, Dict

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

class LLMError(RuntimeError):
    pass

def clean_provider_schema(schema: dict) -> dict:
    keys_to_remove = ["$schema", "$id", "title", "minItems", "maxItems", "minLength", "maxLength"]
    if isinstance(schema, dict):
        return {k: clean_provider_schema(v) for k, v in schema.items() if k not in keys_to_remove}
    elif isinstance(schema, list):
        return [clean_provider_schema(item) for item in schema]
    return schema

async def call_stage_llm(stage: str, prompt: str, schema: Type[T], session: BaseModel = None, client: Any = None) -> T:
    try:
        from google import genai
        from google.genai import types
        from google.genai import errors
    except ImportError as exc:
        raise LLMError("The google-genai package is required when USE_MOCK_LLM=false") from exc

    if client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise LLMError("GEMINI_API_KEY must be set when USE_MOCK_LLM=false")
        client = genai.Client(api_key=api_key)
    
    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

    cleaned_schema = clean_provider_schema(schema.model_json_schema())
    
    retry_prompt = prompt
    last_error = ""
    
    attempt = 1
    max_attempts = 8
    retries_429 = 0
    
    while attempt <= max_attempts:
        raw = ""
        error_msg = None
        result = None
        
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=cleaned_schema,
                temperature=0.7
            )
            
            response = client.models.generate_content(
                model=model_name,
                contents=retry_prompt,
                config=config,
            )
            raw = response.text or ""
            parsed_json = json.loads(raw)
            result = schema.model_validate(parsed_json)
            
        except errors.APIError as exc:
            code = getattr(exc, "code", None)
            err_msg = str(exc)
            if code == 429 or "429" in err_msg or "ResourceExhausted" in err_msg:
                failure_kind = "429"
                retries_429 += 1
                if retries_429 > 3:
                    raise LLMError(f"Exceeded 3 429 retries: {err_msg}")
                
                match = re.search(r"(?:retryDelay|retry_delay)['\"]?\s*[:=]\s*['\"]?([0-9.]+)\s*s?", err_msg, re.IGNORECASE)
                if not match:
                    match = re.search(r"(?:retry|wait)\s+(?:in|after)\s+([0-9.]+)\s*(?:s|seconds)?", err_msg, re.IGNORECASE)
                
                if match:
                    delay = float(match.group(1)) + 1.0
                else:
                    delay = [20.0, 40.0, 60.0][retries_429 - 1]
                    
                entry = {
                    "stage": stage,
                    "attempt": attempt,
                    "prompt": retry_prompt,
                    "rawResponse": raw,
                    "error": err_msg,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
                if session is not None:
                    session.trace.append(entry)
                    
                await asyncio.sleep(delay)
                continue
            elif code in (400, 401, 403, 404) or "API_KEY_INVALID" in err_msg or "not found" in err_msg.lower():
                raise LLMError(f"Fatal API error: {err_msg}")
            elif code == 503 or "503" in err_msg or "ServiceUnavailable" in err_msg or "connection" in err_msg.lower():
                failure_kind = "503"
                error_msg = err_msg
                delay = min(attempt * 15.0, 60.0)
                await asyncio.sleep(delay)
            else:
                failure_kind = "unknown_api_error"
                error_msg = err_msg
        except (ValidationError, json.JSONDecodeError) as exc:
            failure_kind = "validation"
            error_msg = str(exc)
        except Exception as exc:
            err_msg = str(exc)
            if "503" in err_msg or "ServiceUnavailable" in err_msg or "connection" in err_msg.lower():
                failure_kind = "503"
                error_msg = err_msg
                delay = min(attempt * 15.0, 60.0)
                await asyncio.sleep(delay)
            else:
                failure_kind = "unknown"
                error_msg = err_msg

        last_error = error_msg
        
        entry = {
            "stage": stage,
            "attempt": attempt,
            "prompt": retry_prompt,
            "rawResponse": raw,
            "error": error_msg,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        if session is not None:
            session.trace.append(entry)
            
        if result is not None and error_msg is None:
            return result
            
        if failure_kind == "validation":
            retry_prompt = f"{prompt}\n\nYour previous output failed: {error_msg}. Fix the problem and return corrected JSON only."
        
        attempt += 1

    raise LLMError(f"LLM failed to produce valid {stage} output after {max_attempts} attempts: {last_error}")
