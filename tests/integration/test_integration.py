"""
Integration tests for HR AI system.
"""

import pytest
import tempfile
import asyncio
from pathlib import Path
from datetime import datetime

# Add src to path for testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hr_ai.analyzers.hr_analyzer import HRAnalyzer
from hr_ai.api.query_processor import QueryProcessor
from hr_ai.notifications.notifier import NotificationManager

class TestIntegration:
    """Integration tests for the complete HR AI workflow."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.database_url = f"sqlite:///{self.temp_db.name}"
    
    def teardown_method(self):
        """Clean up test environment."""
        import os
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_document_analysis_workflow(self):
        """Test complete document analysis workflow."""
        # Skip if no documents available
        docs_path = Path("docs")
        if not docs_path.exists() or not list(docs_path.glob("*.docx")):
            pytest.skip("No test documents available")
        
        analyzer = HRAnalyzer(self.database_url)
        
        try:
            # Run analysis
            results = analyzer.analyze_all_documents(force_reanalyze=True)
            
            # Verify results structure
            assert 'total_files' in results
            assert 'processed' in results
            assert 'meetings_detected' in results
            assert 'meetings_missed' in results
            assert 'hr_attention_required' in results
            
            # Should process at least one file
            assert results['processed'] > 0
            
            # Test summary generation
            summary = analyzer.get_analysis_summary(days=30)
            assert 'total_documents' in summary
            assert 'employees' in summary
            
        finally:
            analyzer.close()
    
    def test_query_processing_integration(self):
        """Test query processing with real data."""
        # Skip if no documents available
        docs_path = Path("docs")
        if not docs_path.exists() or not list(docs_path.glob("*.docx")):
            pytest.skip("No test documents available")
        
        # First run analysis to populate database
        analyzer = HRAnalyzer(self.database_url)
        analyzer.analyze_all_documents(force_reanalyze=True)
        analyzer.close()
        
        # Test query processing
        processor = QueryProcessor()
        # Update the processor to use test database
        processor.engine = analyzer.engine
        processor.session = analyzer.session
        
        try:
            # Test simple query
            result = asyncio.run(processor.process_query("обучение"))
            
            assert result['success'] == True
            assert 'total_results' in result
            assert 'results' in result
            assert 'summary' in result
            
        finally:
            processor.close()
    
    def test_notification_system_configuration(self):
        """Test notification system configuration and connection testing."""
        notifier = NotificationManager()
        
        # Test connection checking (should not fail even if not configured)
        results = notifier.test_connections()
        
        assert isinstance(results, dict)
        assert 'teams' in results
        assert 'email' in results
        
        # Results should be boolean
        assert isinstance(results['teams'], bool)
        assert isinstance(results['email'], bool)
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        # Skip if no documents available
        docs_path = Path("docs")
        if not docs_path.exists() or not list(docs_path.glob("*.docx")):
            pytest.skip("No test documents available")
        
        # 1. Analyze documents
        analyzer = HRAnalyzer(self.database_url)
        analysis_results = analyzer.analyze_all_documents(force_reanalyze=True)
        
        assert analysis_results['processed'] > 0
        
        # 2. Test querying analyzed data
        processor = QueryProcessor()
        processor.engine = analyzer.engine
        processor.session = analyzer.session
        
        # Test different types of queries
        test_queries = [
            "training",
            "meeting", 
            "feedback"
        ]
        
        for query in test_queries:
            result = asyncio.run(processor.process_query(query))
            assert result['success'] == True
        
        # 3. Test notification preparation (without sending)
        if analysis_results['hr_attention_required']:
            notifier = NotificationManager()
            # Just test that notification formatting works
            first_case = analysis_results['hr_attention_required'][0]
            
            # This should not raise an exception
            alert_data = {
                'notifications': [{
                    'type': 'test',
                    'message': f"Test for {first_case.get('employee', 'unknown')}",
                    'priority': 'medium'
                }]
            }
            
            # Test HTML email formatting
            html_content = notifier._create_html_email("Test message", alert_data)
            assert '<html>' in html_content
            assert 'Test message' in html_content
        
        # Cleanup
        processor.close()
        analyzer.close()

if __name__ == "__main__":
    pytest.main([__file__])