"""Base agent class for the AI Agent Orchestration System."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import time
from utils.logger import get_logger
from utils.exceptions import AgentError, ValidationError


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the orchestration system.
    
    Provides common functionality for:
    - Execution with retry logic
    - Input/output validation
    - State management
    - Logging
    """
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        """
        Initialize the agent.
        
        Args:
            name: Unique name for this agent
            config: Configuration dictionary for this agent
        """
        self.name = name
        self.config = config or {}
        self.logger = get_logger(name)
        self.state = {}
        self.execution_count = 0
        self.last_execution_time = None
        self.last_result = None
    
    def execute(
        self,
        inputs: Dict[str, Any],
        max_retries: Optional[int] = None,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        Execute the agent with retry logic.
        
        Args:
            inputs: Input data for the agent
            max_retries: Maximum number of retry attempts (overrides config)
            retry_delay: Delay between retries in seconds
        
        Returns:
            Dictionary containing agent outputs
        
        Raises:
            AgentError: If execution fails after all retries
            ValidationError: If input/output validation fails
        """
        # Determine max retries from config or parameter
        retries = max_retries if max_retries is not None else self.config.get('max_retries', 3)
        
        self.logger.info(f"Starting execution with inputs: {list(inputs.keys())}")
        
        # Validate inputs
        try:
            self.validate_input(inputs)
        except Exception as e:
            raise ValidationError(
                self.name,
                f"Input validation failed: {str(e)}",
                invalid_data=inputs
            )
        
        # Execute with retries
        last_error = None
        for attempt in range(retries + 1):
            try:
                start_time = time.time()
                
                # Call the agent-specific implementation
                result = self._execute_impl(inputs)
                
                # Validate outputs
                self.validate_output(result)
                
                # Update state
                execution_time = time.time() - start_time
                self.execution_count += 1
                self.last_execution_time = execution_time
                self.last_result = result
                
                self.logger.info(
                    f"Execution completed successfully in {execution_time:.2f}s "
                    f"(attempt {attempt + 1}/{retries + 1})"
                )
                
                return result
                
            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"Execution failed on attempt {attempt + 1}/{retries + 1}: {str(e)}"
                )
                
                if attempt < retries:
                    self.logger.info(f"Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
        
        # All retries exhausted
        error_msg = f"Execution failed after {retries + 1} attempts"
        if last_error:
            error_msg += f": {str(last_error)}"
        
        self.logger.error(error_msg)
        raise AgentError(self.name, error_msg)
    
    @abstractmethod
    def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent-specific implementation to be overridden by subclasses.
        
        Args:
            inputs: Validated input data
        
        Returns:
            Dictionary containing execution results
        """
        pass
    
    def validate_input(self, inputs: Dict[str, Any]) -> None:
        """
        Validate agent inputs. Override in subclasses for custom validation.
        
        Args:
            inputs: Input dictionary to validate
        
        Raises:
            ValidationError: If validation fails
        """
        # Default: check that inputs is a dictionary
        if not isinstance(inputs, dict):
            raise ValidationError(
                self.name,
                f"Inputs must be a dictionary, got {type(inputs).__name__}"
            )
    
    def validate_output(self, outputs: Dict[str, Any]) -> None:
        """
        Validate agent outputs. Override in subclasses for custom validation.
        
        Args:
            outputs: Output dictionary to validate
        
        Raises:
            ValidationError: If validation fails
        """
        # Default: check that outputs is a dictionary
        if not isinstance(outputs, dict):
            raise ValidationError(
                self.name,
                f"Outputs must be a dictionary, got {type(outputs).__name__}"
            )
    
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the agent."""
        return {
            'name': self.name,
            'execution_count': self.execution_count,
            'last_execution_time': self.last_execution_time,
            'state': self.state.copy(),
            'last_result': self.last_result
        }
    
    def reset_state(self):
        """Reset the agent state."""
        self.logger.info("Resetting agent state")
        self.state = {}
        self.execution_count = 0
        self.last_execution_time = None
        self.last_result = None
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}', executions={self.execution_count})"
