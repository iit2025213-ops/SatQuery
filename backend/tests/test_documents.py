# tests/test_documents.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.document_generator import DocumentGenerator

@pytest.mark.asyncio
async def test_document_generator_success():
    """Test generating a markdown document via OpenAI"""
    
    # Mock Supabase
    mock_supabase = MagicMock()
    mock_supabase.get_user_client().table().select().eq().eq().single().execute.return_value = MagicMock(
        data={"query": "Test query", "status": "completed"}
    )
    mock_supabase.get_user_client().table().select().eq().execute.return_value = MagicMock(
        data=[{"evidence_id": "123"}]
    )
    
    # Mock Cloudinary
    mock_cloudinary = AsyncMock()
    mock_cloudinary.upload_artifact.return_value = {
        "cloudinary_public_id": "test_public_id",
        "url": "https://res.cloudinary.com/test.md"
    }
    
    # Initialize generator
    generator = DocumentGenerator(mock_supabase, mock_cloudinary)
    
    # Mock OpenAI
    generator.openai_client = AsyncMock()
    
    mock_message = MagicMock()
    mock_message.content = "# Test Report\n\nThis is a test report."
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    
    generator.openai_client.chat.completions.create.return_value = mock_response
    
    # Run
    result = await generator.generate_markdown_report("job-123", "user-123")
    
    # Verify
    assert result is not None
    assert result["doc_type"] == "analysis_report"
    assert result["format"] == "md"
    assert result["cloudinary_public_id"] == "test_public_id"
    assert result["url"] == "https://res.cloudinary.com/test.md"
    
    # Verify Cloudinary upload was called
    mock_cloudinary.upload_artifact.assert_called_once()
    
    # Verify OpenAI was called
    generator.openai_client.chat.completions.create.assert_called_once()
    
@pytest.mark.asyncio
async def test_document_generator_missing_api_key():
    """Test missing OpenAI API key"""
    mock_supabase = MagicMock()
    mock_cloudinary = AsyncMock()
    
    generator = DocumentGenerator(mock_supabase, mock_cloudinary)
    generator.openai_client = None  # Simulate missing key
    
    with pytest.raises(ValueError, match="OPENAI_API_KEY is not configured"):
        await generator.generate_markdown_report("job-123", "user-123")
