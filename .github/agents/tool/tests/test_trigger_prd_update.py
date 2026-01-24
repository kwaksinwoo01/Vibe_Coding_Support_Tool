"""
Unit tests for trigger_prd_update.py

Tests the thin wrapper for Tier E document management operations.
"""

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.trigger_prd_update import TriggerPRDUpdate, trigger_document_management


class TestTriggerPRDUpdate(unittest.TestCase):
    """Test cases for TriggerPRDUpdate wrapper."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temp workspace
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        
        # Create test files
        self.prd_file = self.workspace / "docs_2" / "prd" / "PRD-Test.md"
        self.wpd_file = self.workspace / "docs_2" / "P1" / "P1-Test.md"
        
        self.prd_file.parent.mkdir(parents=True, exist_ok=True)
        self.wpd_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.prd_file.write_text("# PRD Test\n\n## Status\n")
        self.wpd_file.write_text("# WPD Test\n\n## Checklist\n- [ ] Task 1\n- [ ] Task 2\n")
        
        # Create trigger instance
        self.trigger = TriggerPRDUpdate(workspace_root=str(self.workspace))
    
    def tearDown(self):
        """Clean up temp directory."""
        self.temp_dir.cleanup()
    
    def test_validate_payload_success(self):
        """Test successful payload validation."""
        payload = {
            'prd_path': 'docs_2/prd/PRD-Test.md',
            'wpd_sources': ['docs_2/P1/P1-Test.md'],
            'operations': [
                {'type': 'update_checklist', 'item_text': 'Task 1', 'status': 'complete'}
            ]
        }
        
        result = self.trigger.validate_payload(payload)
        self.assertTrue(result['success'])
    
    def test_validate_payload_missing_field(self):
        """Test validation with missing required field."""
        payload = {
            'prd_path': 'docs_2/prd/PRD-Test.md',
            # Missing wpd_sources
            'operations': []
        }
        
        result = self.trigger.validate_payload(payload)
        self.assertFalse(result['success'])
        self.assertIn('Missing required field: wpd_sources', result['errors'])
    
    def test_validate_payload_invalid_operation(self):
        """Test validation with invalid operation type."""
        payload = {
            'prd_path': 'docs_2/prd/PRD-Test.md',
            'wpd_sources': ['docs_2/P1/P1-Test.md'],
            'operations': [
                {'type': 'invalid_op'}
            ]
        }
        
        result = self.trigger.validate_payload(payload)
        self.assertFalse(result['success'])
        self.assertTrue(any('invalid type' in err for err in result['errors']))
    
    def test_validate_payload_file_not_found(self):
        """Test validation when file doesn't exist."""
        payload = {
            'prd_path': 'docs_2/prd/NonExistent.md',
            'wpd_sources': ['docs_2/P1/P1-Test.md'],
            'operations': []
        }
        
        result = self.trigger.validate_payload(payload)
        self.assertFalse(result['success'])
        self.assertTrue(any('not found' in err for err in result['errors']))
    
    def test_plan_operations_dry_run(self):
        """Test planning operations in dry-run mode."""
        payload = {
            'prd_path': 'docs_2/prd/PRD-Test.md',
            'wpd_sources': ['docs_2/P1/P1-Test.md'],
            'operations': [
                {
                    'type': 'update_checklist',
                    'item_text': 'Task 1',
                    'status': 'complete'
                }
            ]
        }
        
        result = self.trigger.plan_operations(payload)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['mode'], 'dry_run')
        self.assertEqual(len(result['planned_operations']), 1)
        self.assertIn('docs_2/P1/P1-Test.md', result['affected_files'])
        self.assertEqual(result['planned_operations'][0]['type'], 'update_checklist')
    
    def test_plan_operations_add_prd_link(self):
        """Test planning add_prd_link operation."""
        payload = {
            'prd_path': 'docs_2/prd/PRD-Test.md',
            'wpd_sources': ['docs_2/P1/P1-Test.md'],
            'operations': [
                {'type': 'add_prd_link'}
            ]
        }
        
        result = self.trigger.plan_operations(payload)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['planned_operations']), 1)
        self.assertEqual(result['planned_operations'][0]['type'], 'add_prd_link')
        self.assertIn('prd_path', result['planned_operations'][0])
    
    def test_plan_operations_mapping_update(self):
        """Test planning mapping_update operation."""
        payload = {
            'prd_path': 'docs_2/prd/PRD-Test.md',
            'wpd_sources': [],
            'operations': [
                {
                    'type': 'mapping_update',
                    'mapping_data': {'module': 'test', 'flow': 'test_flow'}
                }
            ]
        }
        
        result = self.trigger.plan_operations(payload)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['planned_operations']), 1)
        self.assertEqual(result['planned_operations'][0]['type'], 'mapping_update')
    
    @patch('scripts.trigger_prd_update.DocumentManagementEngine')
    @patch('scripts.trigger_prd_update.DocumentUpdater')
    def test_apply_operations_update_checklist(self, MockDocUpdater, MockEngine):
        """Test applying update_checklist operation."""
        # Mock document_updater
        mock_updater = MockDocUpdater.return_value
        mock_updater.update_checklist_item.return_value = {'success': True}
        
        payload = {
            'prd_path': 'docs_2/prd/PRD-Test.md',
            'wpd_sources': ['docs_2/P1/P1-Test.md'],
            'operations': [
                {
                    'type': 'update_checklist',
                    'item_text': 'Task 1',
                    'status': 'complete'
                }
            ]
        }
        
        result = self.trigger.apply_operations(payload)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['mode'], 'apply')
        self.assertEqual(len(result['applied_operations']), 1)
        self.assertIn('docs_2/P1/P1-Test.md', result['modified_files'])
        mock_updater.update_checklist_item.assert_called_once()
    
    @patch('scripts.trigger_prd_update.DocumentManagementEngine')
    def test_apply_operations_add_prd_link(self, MockEngine):
        """Test applying add_prd_link operation."""
        mock_engine = MockEngine.return_value
        
        payload = {
            'prd_path': 'docs_2/prd/PRD-Test.md',
            'wpd_sources': ['docs_2/P1/P1-Test.md'],
            'operations': [
                {'type': 'add_prd_link'}
            ]
        }
        
        result = self.trigger.apply_operations(payload)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['applied_operations']), 1)
        mock_engine._add_prd_link_to_document.assert_called_once()
    
    def test_trigger_document_management_dry_run(self):
        """Test main entry point with dry-run."""
        payload = {
            'prd_path': 'docs_2/prd/PRD-Test.md',
            'wpd_sources': ['docs_2/P1/P1-Test.md'],
            'operations': [
                {'type': 'update_checklist', 'item_text': 'Task 1', 'status': 'complete'}
            ]
        }
        
        # Override workspace_root for this test
        with patch.object(TriggerPRDUpdate, '__init__', lambda self, workspace_root=".": (
            setattr(self, 'workspace_root', self.workspace),
            setattr(self, 'planned_operations', []),
            setattr(self, 'applied_operations', []),
            setattr(self, 'affected_files', []),
            setattr(self, 'modified_files', [])
        )[-1]):
            result = trigger_document_management(payload, dry_run=True)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['mode'], 'dry_run')
    
    def test_trigger_document_management_validation_failure(self):
        """Test main entry point with invalid payload."""
        payload = {
            'prd_path': 'docs_2/prd/PRD-Test.md',
            # Missing wpd_sources and operations
        }
        
        result = trigger_document_management(payload, dry_run=True)
        
        self.assertFalse(result['success'])
        self.assertIn('errors', result)


if __name__ == '__main__':
    unittest.main()
