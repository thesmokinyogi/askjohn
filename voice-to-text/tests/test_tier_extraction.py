"""
Test tier extraction from model names.

Verifies that the tier extraction logic correctly identifies
'batch' vs 'standard' from model names like 'chirp_batch', 'long_standard', etc.
"""

import pytest
from app.services.orchestrator import TranscriptionOrchestrator
from unittest.mock import Mock


class TestTierExtraction:
    """Test tier extraction logic."""
    
    def setup_method(self):
        """Set up test orchestrator with mocked dependencies."""
        self.orchestrator = TranscriptionOrchestrator(
            storage_service=Mock(),
            transcription_service_factory=Mock(),
            pricing_service=Mock(),
            budget_service=Mock(),
            cost_calculation_service=Mock(),
            job_storage=Mock(),
            library_service=Mock(),
            processing_time_service=Mock(),
            audio_metadata_service=Mock(),
            provider="google",
            default_model="long_batch",
            project_id="test-project",
            speech_location="us-central1"
        )
    
    def test_chirp_batch_extracts_batch_tier(self):
        """Test that 'chirp_batch' extracts 'batch' tier."""
        google_model, ui_model, tier = self.orchestrator.map_model_name("chirp_batch")
        assert google_model == "chirp"
        assert ui_model == "chirp_batch"
        assert tier == "batch"
    
    def test_chirp_standard_extracts_standard_tier(self):
        """Test that 'chirp_standard' extracts 'standard' tier."""
        google_model, ui_model, tier = self.orchestrator.map_model_name("chirp_standard")
        assert google_model == "chirp"
        assert ui_model == "chirp_standard"
        assert tier == "standard"
    
    def test_long_batch_extracts_batch_tier(self):
        """Test that 'long_batch' extracts 'batch' tier."""
        google_model, ui_model, tier = self.orchestrator.map_model_name("long_batch")
        assert google_model == "long"
        assert ui_model == "long_batch"
        assert tier == "batch"
    
    def test_long_standard_extracts_standard_tier(self):
        """Test that 'long_standard' extracts 'standard' tier."""
        google_model, ui_model, tier = self.orchestrator.map_model_name("long_standard")
        assert google_model == "long"
        assert ui_model == "long_standard"
        assert tier == "standard"
    
    def test_short_batch_extracts_batch_tier(self):
        """Test that 'short_batch' extracts 'batch' tier."""
        google_model, ui_model, tier = self.orchestrator.map_model_name("short_batch")
        assert google_model == "short"
        assert ui_model == "short_batch"
        assert tier == "batch"
    
    def test_short_standard_extracts_standard_tier(self):
        """Test that 'short_standard' extracts 'standard' tier."""
        google_model, ui_model, tier = self.orchestrator.map_model_name("short_standard")
        assert google_model == "short"
        assert ui_model == "short_standard"
        assert tier == "standard"
    
    def test_legacy_model_defaults_to_batch(self):
        """Test that legacy model names (without _batch/_standard) default to 'batch'."""
        google_model, ui_model, tier = self.orchestrator.map_model_name("chirp")
        assert google_model == "chirp"
        assert ui_model == "chirp"
        assert tier == "batch"  # Default
    
    def test_none_uses_default_model(self):
        """Test that None uses the default model."""
        google_model, ui_model, tier = self.orchestrator.map_model_name(None)
        assert ui_model == "long_batch"  # From default_model in setup
        assert tier == "batch"
    
    def test_unknown_model_defaults_to_batch(self):
        """Test that unknown model names default to 'batch' tier."""
        google_model, ui_model, tier = self.orchestrator.map_model_name("unknown_model")
        assert google_model == "long"  # Default fallback
        assert ui_model == "unknown_model"
        assert tier == "batch"  # Default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

