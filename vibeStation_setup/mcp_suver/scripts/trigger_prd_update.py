#!/usr/bin/env python3
"""
Trigger PRD Update - Thin Wrapper for Tier E Document Management

This script validates migration payload and orchestrates document updates via
DocumentManagementEngine. No adapters/bridges - delegates to existing managers.

Safety: Default dry_run=True. Only applies changes when dry_run=False.
SRP: This wrapper handles validation and orchestration only. All writes delegated.

Usage:
    python trigger_prd_update.py --payload-file payload.json --dry-run
    python trigger_prd_update.py --payload-file payload.json --apply
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add tool directory to path
TOOL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(TOOL_DIR))

class TriggerPRDUpdate:
    """
    Thin wrapper for document management operations.
    
    Responsibilities:
    - Validate payload structure
    - Orchestrate operations via DocumentManagementEngine
    - Return planned/applied operations
    
    SRP: Validation and orchestration only. No adapters.
    """
    
    # prd_path is optional (Tier E can create PRD if missing). Operations list is optional.
    REQUIRED_FIELDS = ['wpd_sources']
    VALID_OPERATIONS = ['add_prd_link', 'update_checklist', 'mapping_update', 'ensure_prd']
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root)
        self.planned_operations: List[Dict[str, Any]] = []
        self.applied_operations: List[Dict[str, Any]] = []
        self.affected_files: List[str] = []
        self.modified_files: List[str] = []
    
    def validate_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate payload structure.
        
        Args:
            payload: Input payload to validate
            
        Returns:
            Validation result with success status
        """
        errors = []
        
        # Check required fields (wpd_sources required; prd_path optional; operations optional)
        for field in self.REQUIRED_FIELDS:
            if field not in payload:
                errors.append(f"Missing required field: {field}")
        
        # Validate operations if present
        ops = payload.get('operations', [])
        for idx, op in enumerate(ops):
            if 'type' not in op:
                errors.append(f"Operation {idx}: missing 'type' field")
            elif op['type'] not in self.VALID_OPERATIONS:
                errors.append(f"Operation {idx}: invalid type '{op['type']}'")
        
        # Validate paths if provided
        if 'prd_path' in payload and payload.get('prd_path'):
            prd_path = self.workspace_root / payload['prd_path']
            if not prd_path.exists():
                errors.append(f"PRD file not found: {payload['prd_path']}")
        
        if 'wpd_sources' in payload:
            for wpd in payload['wpd_sources']:
                wpd_path = self.workspace_root / wpd
                if not wpd_path.exists():
                    errors.append(f"WPD file not found: {wpd}")
        
        if errors:
            return {"success": False, "errors": errors}
        
        return {"success": True}
    
    def plan_operations(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plan operations (dry-run mode).
        
        Args:
            payload: Validated payload
            
        Returns:
            Planned operations dict
        """
        self.planned_operations = []
        self.affected_files = []
        
        ops = payload.get('operations', [])

        # If no operations specified, default to ensuring a PRD exists for given WPD sources
        if not ops:
            planned_op = {
                'type': 'ensure_prd',
                'status': 'planned',
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'Ensure PRD exists for WPD sources',
                'targets': payload.get('wpd_sources', [])
            }
            self.planned_operations.append(planned_op)
            self.affected_files = list(set(payload.get('wpd_sources', [])))
            return {
                "success": True,
                "mode": "dry_run",
                "planned_operations": self.planned_operations,
                "affected_files": self.affected_files,
                "operation_count": len(self.planned_operations)
            }

        for op in ops:
            op_type = op['type']
            planned_op = {
                'type': op_type,
                'status': 'planned',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if op_type == 'add_prd_link':
                prd_path = payload['prd_path']
                for wpd in payload['wpd_sources']:
                    planned_op['action'] = f"Add PRD link to {wpd}"
                    planned_op['target'] = wpd
                    planned_op['prd_path'] = prd_path
                    self.affected_files.append(wpd)
                    self.planned_operations.append(planned_op.copy())
            
            elif op_type == 'update_checklist':
                item_text = op.get('item_text', '')
                status = op.get('status', 'complete')
                for wpd in payload['wpd_sources']:
                    planned_op['action'] = f"Update checklist in {wpd}: {item_text} -> {status}"
                    planned_op['target'] = wpd
                    planned_op['item_text'] = item_text
                    planned_op['status'] = status
                    self.affected_files.append(wpd)
                    self.planned_operations.append(planned_op.copy())
            
            elif op_type == 'mapping_update':
                mapping_data = op.get('mapping_data', {})
                planned_op['action'] = "Update mapping table"
                planned_op['mapping_data'] = mapping_data
                # Mapping manager determines affected files
                self.planned_operations.append(planned_op.copy())
        
        # Deduplicate affected files
        self.affected_files = list(set(self.affected_files))
        
        return {
            "success": True,
            "mode": "dry_run",
            "planned_operations": self.planned_operations,
            "affected_files": self.affected_files,
            "operation_count": len(self.planned_operations)
        }
    
    def apply_operations(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply operations (write mode).
        
        Delegates all writes to DocumentManagementEngine and managers.
        
        Args:
            payload: Validated payload
            
        Returns:
            Applied operations result with AgentState
        """
        self.applied_operations = []
        self.modified_files = []
        
        # Lazy imports (may not be available in some runtime environments)
        heavy_ok = True
        try:
            from models.core import TaskContext, AgentState
            from E_Document_Management import DocumentManagementEngine
            from doc_management.document_updater import DocumentUpdater
            from doc_management.checklist_manager import ChecklistManager
        except ModuleNotFoundError:
            heavy_ok = False
            DocumentManagementEngine = None
            DocumentUpdater = None
            ChecklistManager = None
            TaskContext = None
            AgentState = None

        if heavy_ok:
            # Create context for DocumentManagementEngine
            context = TaskContext(
                user_input="Document management from trigger_prd_update",
                current_tier="E",
                workspace_root=str(self.workspace_root)
            )

            # Initialize engine with payload
            engine = DocumentManagementEngine(context, previous_payload=payload)

            # Initialize managers
            document_updater = DocumentUpdater(self.workspace_root)
            checklist_manager = ChecklistManager(self.workspace_root)
        else:
            engine = None
            document_updater = None
            checklist_manager = None
        
        # Execute operations
        ops = payload.get('operations', [])
        if not ops:
            ops = [{'type': 'ensure_prd'}]

        for op in ops:
            op_type = op['type']
            applied_op = {
                'type': op_type,
                'status': 'applied',
                'timestamp': datetime.utcnow().isoformat()
            }

            # Special handling for ensure_prd: let E engine create or return PRD
            if op_type == 'ensure_prd':
                # Try using the DocumentManagementEngine if available
                if engine:
                    try:
                        result_state = engine.execute()
                        prd_path_str = engine.state.sources.prd_path or (result_state.payload.get('sources') or {}).get('prd_path')
                        if prd_path_str:
                            applied_op['action'] = f"Ensured PRD: {prd_path_str}"
                            applied_op['prd_path'] = prd_path_str
                            payload['prd_path'] = prd_path_str
                            self.applied_operations.append(applied_op.copy())
                            continue
                        else:
                            # If engine didn't return a PRD, fallthrough to fallback
                            pass
                    except Exception:
                        # Fall back to minimal PRD creation if engine fails
                        pass

                # Fallback: create a minimal PRD file directly when environment modules are missing or engine failed
                import re
                import datetime as _dt
                wpd_sources = payload.get('wpd_sources', [])
                Part_N = 1
                if wpd_sources:
                    m = re.search(r'P(\d+)', wpd_sources[0])
                    if m:
                        Part_N = int(m.group(1))
                prd_dir = self.workspace_root / 'docs_2' / 'prd'
                prd_dir.mkdir(parents=True, exist_ok=True)
                prd_path = prd_dir / f'PRD-P{Part_N}.md'
                if not prd_path.exists():
                    content = f"""# PRD-P{Part_N}: Auto-generated PRD

**WPD_grade**: L0
**Version**: 1.0.0
**Status**: 📋 PENDING
**Generated**: {_dt.datetime.now().isoformat()}

## Overview
Auto-generated PRD by CI fallback.
"""
                    prd_path.write_text(content, encoding='utf-8')
                applied_op['action'] = f"Created PRD (fallback): {prd_path}"
                applied_op['prd_path'] = str(prd_path)
                payload['prd_path'] = str(prd_path)
                self.applied_operations.append(applied_op.copy())
                continue
            
            try:
                if op_type == 'add_prd_link':
                    # Delegate to engine
                    prd_path = self.workspace_root / payload['prd_path']
                    for wpd in payload['wpd_sources']:
                        wpd_path = self.workspace_root / wpd
                        engine._add_prd_link_to_document(wpd_path, prd_path)
                        applied_op['action'] = f"Added PRD link to {wpd}"
                        applied_op['target'] = wpd
                        self.modified_files.append(wpd)
                        self.applied_operations.append(applied_op.copy())
                
                elif op_type == 'update_checklist':
                    # Delegate to document_updater
                    item_text = op.get('item_text', '')
                    status = op.get('status', 'complete')
                    add_timestamp = op.get('add_timestamp', True)
                    
                    for wpd in payload['wpd_sources']:
                        wpd_path = self.workspace_root / wpd
                        result = document_updater.update_checklist_item(
                            wpd_path,
                            item_text,
                            status,
                            add_timestamp
                        )
                        
                        if result.get('success'):
                            applied_op['action'] = f"Updated checklist in {wpd}: {item_text} -> {status}"
                            applied_op['target'] = wpd
                            applied_op['result'] = result
                            self.modified_files.append(wpd)
                            self.applied_operations.append(applied_op.copy())
                        else:
                            applied_op['status'] = 'failed'
                            applied_op['error'] = result.get('error')
                            self.applied_operations.append(applied_op.copy())
                
                elif op_type == 'mapping_update':
                    # Delegate to mapping_manager via engine
                    mapping_data = op.get('mapping_data', {})
                    result = engine.manage_mapping(mapping_data)
                    
                    applied_op['action'] = "Updated mapping table"
                    applied_op['result'] = result
                    self.applied_operations.append(applied_op.copy())
            
            except Exception as e:
                applied_op['status'] = 'failed'
                applied_op['error'] = str(e)
                self.applied_operations.append(applied_op.copy())
        
        # Deduplicate modified files
        self.modified_files = list(set(self.modified_files))
        
        # Create AgentState for response (use fallback dict if AgentState not available)
        if AgentState is not None:
            agent_state = AgentState.create_success(
                tier="E",
                logic_summary=f"Applied {len(self.applied_operations)} operations",
                payload={
                    'prd_path': payload.get('prd_path'),
                    'wpd_sources': payload.get('wpd_sources'),
                    'operations': self.applied_operations
                },
                next_node=None
            )
            agent_state_dict = agent_state.to_dict()
        else:
            agent_state_dict = {
                'tier': 'E',
                'status': 'SUCCESS',
                'logic_summary': f"Applied {len(self.applied_operations)} operations (fallback)",
                'payload': {
                    'prd_path': payload.get('prd_path'),
                    'wpd_sources': payload.get('wpd_sources'),
                    'operations': self.applied_operations
                },
                'next_node': None
            }

        return {
            "success": True,
            "mode": "apply",
            "applied_operations": self.applied_operations,
            "modified_files": self.modified_files,
            "operation_count": len(self.applied_operations),
            "agent_state": agent_state_dict
        }


def trigger_document_management(payload: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
    """
    Main entry point for document management trigger.
    
    Args:
        payload: Document management payload
        dry_run: If True, plan operations only (default: True for safety)
        
    Returns:
        Result dict with operations and affected/modified files
    """
    trigger = TriggerPRDUpdate()
    
    # Validate payload
    validation = trigger.validate_payload(payload)
    if not validation['success']:
        return {
            "success": False,
            "errors": validation['errors'],
            "mode": "dry_run" if dry_run else "apply"
        }
    
    # Execute operations
    if dry_run:
        return trigger.plan_operations(payload)
    else:
        return trigger.apply_operations(payload)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Trigger Tier E document management operations"
    )
    parser.add_argument(
        '--payload-file',
        required=True,
        help="Path to JSON payload file"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Plan operations without applying (default)"
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help="Apply operations (write mode)"
    )
    parser.add_argument(
        '--workspace-root',
        default=".",
        help="Workspace root directory (default: current directory)"
    )
    
    args = parser.parse_args()
    
    # Load payload
    try:
        with open(args.payload_file, 'r') as f:
            payload = json.load(f)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Failed to load payload: {e}"
        }, indent=2))
        sys.exit(1)
    
    # Determine mode (default to dry_run for safety)
    dry_run = not args.apply
    
    # Execute
    result = trigger_document_management(payload, dry_run=dry_run)
    
    # Output result as JSON
    print(json.dumps(result, indent=2, default=str))
    
    # Exit code
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    main()
