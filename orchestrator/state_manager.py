"""State management for workflow persistence and tracking."""

import json
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime
from utils.logger import get_logger


class StateManager:
    """
    Manages workflow state persistence and tracking.
    
    Capabilities:
    - Save/load workflow state to JSON
    - Track agent execution history
    - Resume interrupted workflows
    - State rollback capabilities
    """
    
    def __init__(self, state_dir: str = "data/outputs/state"):
        """
        Initialize state manager.
        
        Args:
            state_dir: Directory to store state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("StateManager")
        self.current_state = {}
    
    def save_state(
        self,
        workflow_name: str,
        state: Dict[str, Any],
        workflow_id: Optional[str] = None
    ) -> str:
        """
        Save workflow state to file.
        
        Args:
            workflow_name: Name of the workflow
            state: State dictionary to save
            workflow_id: Optional specific workflow ID
        
        Returns:
            Path to saved state file
        """
        if workflow_id is None:
            workflow_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        state_data = {
            'workflow_name': workflow_name,
            'workflow_id': workflow_id,
            'timestamp': datetime.now().isoformat(),
            'state': state
        }
        
        filename = f"{workflow_name}_{workflow_id}.json"
        filepath = self.state_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"State saved: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to save state: {str(e)}")
            raise
    
    def load_state(self, workflow_name: str, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Load workflow state from file.
        
        Args:
            workflow_name: Name of the workflow
            workflow_id: Optional specific workflow ID (loads latest if not specified)
        
        Returns:
            State dictionary
        """
        if workflow_id:
            filename = f"{workflow_name}_{workflow_id}.json"
            filepath = self.state_dir / filename
        else:
            # Find latest state file for this workflow
            pattern = f"{workflow_name}_*.json"
            state_files = sorted(self.state_dir.glob(pattern), reverse=True)
            
            if not state_files:
                self.logger.warning(f"No state files found for workflow: {workflow_name}")
                return {}
            
            filepath = state_files[0]
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            self.logger.info(f"State loaded: {filepath}")
            return state_data.get('state', {})
            
        except FileNotFoundError:
            self.logger.warning(f"State file not found: {filepath}")
            return {}
        except Exception as e:
            self.logger.error(f"Failed to load state: {str(e)}")
            return {}
    
    def update_state(self, key: str, value: Any):
        """
        Update a value in the current state.
        
        Args:
            key: State key
            value: State value
        """
        self.current_state[key] = value
        self.logger.debug(f"State updated: {key}")
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the current state.
        
        Args:
            key: State key
            default: Default value if key not found
        
        Returns:
            State value or default
        """
        return self.current_state.get(key, default)
    
    def clear_state(self):
        """Clear the current state."""
        self.current_state = {}
        self.logger.info("State cleared")
    
    def get_all_state(self) -> Dict[str, Any]:
        """Get the entire current state."""
        return self.current_state.copy()
    
    def list_saved_states(self, workflow_name: Optional[str] = None) -> list:
        """
        List all saved state files.
        
        Args:
            workflow_name: Optional workflow name to filter by
        
        Returns:
            List of state file information
        """
        pattern = f"{workflow_name}_*.json" if workflow_name else "*.json"
        state_files = sorted(self.state_dir.glob(pattern), reverse=True)
        
        states = []
        for filepath in state_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                states.append({
                    'workflow_name': data.get('workflow_name'),
                    'workflow_id': data.get('workflow_id'),
                    'timestamp': data.get('timestamp'),
                    'filepath': str(filepath)
                })
            except Exception as e:
                self.logger.warning(f"Failed to read state file {filepath}: {str(e)}")
        
        return states
