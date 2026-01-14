"""Workflow definition and management."""

from typing import Any, Dict, List, Set
from utils.logger import get_logger
from utils.exceptions import OrchestratorError


class WorkflowStep:
    """Represents a single step in a workflow."""
    
    def __init__(
        self,
        agent_name: str,
        inputs: List[str],
        outputs: List[str],
        depends_on: List[str] = None
    ):
        """
        Initialize a workflow step.
        
        Args:
            agent_name: Name of the agent to execute
            inputs: List of required input keys
            outputs: List of output keys this step produces
            depends_on: List of agent names this step depends on
        """
        self.agent_name = agent_name
        self.inputs = inputs
        self.outputs = outputs
        self.depends_on = depends_on or []
        self.status = 'pending'  # pending, running, completed, failed
        self.result = None
        self.error = None
    
    def __repr__(self):
        return f"WorkflowStep(agent='{self.agent_name}', status='{self.status}')"


class WorkflowManager:
    """
    Manages workflow definitions and execution order.
    
    Capabilities:
    - Parse workflow configuration
    - Build dependency graphs (DAG)
    - Determine execution order
    - Validate workflow definitions
    """
    
    def __init__(self):
        self.logger = get_logger("WorkflowManager")
        self.workflows = {}
    
    def register_workflow(self, name: str, config: Dict[str, Any]):
        """
        Register a workflow configuration. 
        
        Args:
            name: Workflow name
            config: Workflow configuration dictionary
        """
        try:
            steps = self._parse_workflow_config(config)
            self._validate_workflow(steps)
            self.workflows[name] = {
                'config': config,
                'steps': steps,
                'description': config.get('description', '')
            }
            self.logger.info(f"Registered workflow '{name}' with {len(steps)} steps")
        except Exception as e:
            raise OrchestratorError(
                f"Failed to register workflow '{name}': {str(e)}",
                workflow=name
            )
    
    def get_workflow(self, name: str) -> Dict[str, Any]:
        """
        Get a registered workflow.
        
        Args:
            name: Workflow name
        
        Returns:
            Workflow dictionary
        """
        if name not in self.workflows:
            raise OrchestratorError(
                f"Workflow '{name}' not found",
                workflow=name
            )
        return self.workflows[name]
    
    def get_execution_order(self, workflow_name: str) -> List[List[str]]:
        """
        Get the execution order for a workflow based on dependencies.
        
        Returns a list of lists, where each inner list contains agent names
        that can be executed in parallel (no dependencies between them).
        
        Args:
            workflow_name: Name of the workflow
        
        Returns:
            List of execution levels (each level can run in parallel)
        """
        workflow = self.get_workflow(workflow_name)
        steps = workflow['steps']
        
        # Build dependency graph
        dependencies = {step.agent_name: set(step.depends_on) for step in steps}
        
        # Topological sort with levels
        execution_order = []
        completed = set()
        
        while len(completed) < len(steps):
            # Find steps with all dependencies satisfied
            ready = []
            for step in steps:
                if step.agent_name not in completed:
                    if all(dep in completed for dep in dependencies[step.agent_name]):
                        ready.append(step.agent_name)
            
            if not ready:
                # Circular dependency detected
                remaining = [s.agent_name for s in steps if s.agent_name not in completed]
                raise OrchestratorError(
                    f"Circular dependency detected in workflow. Remaining agents: {remaining}",
                    workflow=workflow_name
                )
            
            execution_order.append(ready)
            completed.update(ready)
        
        return execution_order
    
    def _parse_workflow_config(self, config: Dict[str, Any]) -> List[WorkflowStep]:
        """Parse workflow configuration into WorkflowStep objects."""
        steps = []
        step_configs = config.get('steps', [])
        
        for step_config in step_configs:
            step = WorkflowStep(
                agent_name=step_config['agent'],
                inputs=step_config.get('inputs', []),
                outputs=step_config.get('outputs', []),
                depends_on=step_config.get('depends_on', [])
            )
            steps.append(step)
        
        return steps
    
    def _validate_workflow(self, steps: List[WorkflowStep]):
        """
        Validate workflow configuration.
        
        Args:
            steps: List of workflow steps to validate
        
        Raises:
            OrchestratorError: If validation fails
        """
        # Check for unique agent names
        agent_names = [step.agent_name for step in steps]
        if len(agent_names) != len(set(agent_names)):
            raise OrchestratorError("Duplicate agent names in workflow")
        
        # Validate dependencies exist
        agent_set = set(agent_names)
        for step in steps:
            for dep in step.depends_on:
                if dep not in agent_set:
                    raise OrchestratorError(
                        f"Agent '{step.agent_name}' depends on unknown agent '{dep}'"
                    )
        
        # Check for cycles (basic check)
        # More thorough check happens in get_execution_order
        visited = set()
        
        def has_cycle(agent_name: str, path: Set[str]) -> bool:
            if agent_name in path:
                return True
            if agent_name in visited:
                return False
            
            visited.add(agent_name)
            path.add(agent_name)
            
            step = next((s for s in steps if s.agent_name == agent_name), None)
            if step:
                for dep in step.depends_on:
                    if has_cycle(dep, path.copy()):
                        return True
            
            return False
        
        for step in steps:
            if has_cycle(step.agent_name, set()):
                raise OrchestratorError("Circular dependency detected in workflow")
    
    def list_workflows(self) -> List[str]:
        """List all registered workflows."""
        return list(self.workflows.keys())
    
    def get_workflow_description(self, name: str) -> str:
        """Get workflow description."""
        workflow = self.get_workflow(name)
        return workflow.get('description', 'No description available')
