import logging
import json
import uuid
from typing import Optional
from openai import AsyncOpenAI
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger("satquery")

class DocumentGenerator:
    """
    Generates professional Markdown reports from SATQUERY AI Brain JSON output.
    """
    
    def __init__(self, supabase_client, cloudinary_client):
        self.supabase = supabase_client
        self.cloudinary = cloudinary_client
        self.openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        ) if settings.openai_api_key else None
        
    async def generate_markdown_report(self, job_id: str, user_id: str) -> Optional[dict]:
        """
        Fetches job JSON data, generates a Markdown report via OpenAI,
        and uploads it to Cloudinary. Returns document metadata.
        """
        if not self.openai_client:
            raise ValueError("OPENAI_API_KEY is not configured")
            
        try:
            # 1. Fetch Job Data (The AI Brain JSON)
            job = self.supabase.get_user_client().table("jobs").select("*").eq("job_id", job_id).eq("user_id", user_id).single().execute()
            if not job.data:
                raise ValueError("Job not found or unauthorized")
                
            evidence = self.supabase.get_user_client().table("evidence").select("*").eq("job_id", job_id).execute()
            observations = self.supabase.get_user_client().table("observations").select("*").eq("job_id", job_id).execute()
            
            # Combine into a single JSON context precisely as produced by the Brain
            brain_json = {
                "query": job.data.get("query"),
                "status": job.data.get("status"),
                "final_answer": job.data.get("final_answer"),
                "confidence": job.data.get("confidence"),
                "evidence": evidence.data,
                "observations": observations.data,
                "created_at": job.data.get("created_at")
            }
            
            # 2. Call OpenAI to format into Markdown
            system_prompt = (
                "You are the SATQUERY Geospatial AI Reporter.\n"
                "Your task is to convert the provided raw AI analytical JSON into a highly professional, structured Markdown report.\n"
                "RULES:\n"
                "1. DO NOT invent, hallucinate, or add any facts, dates, measurements, or evidence that is not explicitly in the JSON.\n"
                "2. Structure the report beautifully with sections like Executive Summary, Key Findings, Methodology, and Evidence Trail, but ONLY if relevant data exists in the JSON.\n"
                "3. Output ONLY valid Markdown. Do not wrap in markdown code blocks (e.g., no ```markdown)."
            )
            
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(brain_json, default=str)}
                ],
                temperature=0.1,  # Keep it deterministic and factual
            )
            
            markdown_content = response.choices[0].message.content.strip()
            
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as temp_file:
                temp_file.write(markdown_content)
                temp_path = temp_file.name
                
            try:
                # 3. Upload to Cloudinary using existing artifact upload method
                upload_result = await self.cloudinary.upload_artifact(
                    file_path=temp_path,
                    artifact_type="analysis_json", # reuse existing raw type logic
                    job_id=job_id,
                    metadata={"doc_type": "markdown_report"}
                )
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
            if not upload_result:
                raise Exception("Cloudinary upload failed")
                
            # 4. Return document metadata
            return {
                "job_id": job_id,
                "doc_type": "analysis_report",
                "format": "md",
                "cloudinary_public_id": upload_result.get("cloudinary_public_id"),
                "url": upload_result.get("url"),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating document for job {job_id}: {str(e)}")
            raise
