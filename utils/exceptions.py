"""Custom exception classes for the AI Agent Orchestration System."""


class AgentError(Exception):
    """Base exception for agent-related errors."""
    
    def __init__(self, agent_name: str, message: str):
        self.agent_name = agent_name
        self.message = message
        super().__init__(f"[{agent_name}] {message}")


class OrchestratorError(Exception):
    """Exception raised by the orchestrator."""
    
    def __init__(self, message: str, workflow: str = None):
        self.workflow = workflow
        self.message = message
        error_msg = f"[Orchestrator] {message}"
        if workflow:
            error_msg = f"[Orchestrator:{workflow}] {message}"
        super().__init__(error_msg)


class ValidationError(AgentError):
    """Exception raised when agent input/output validation fails."""
    
    def __init__(self, agent_name: str, message: str, invalid_data=None):
        self.invalid_data = invalid_data
        super().__init__(agent_name, f"Validation failed: {message}")


class APIError(AgentError):
    """Exception raised when external API calls fail."""
    
    def __init__(self, agent_name: str, api_name: str, status_code: int = None, message: str = ""):
        self.api_name = api_name
        self.status_code = status_code
        error_msg = f"API call to {api_name} failed"
        if status_code:
            error_msg += f" (status: {status_code})"
        if message:
            error_msg += f": {message}"
        super().__init__(agent_name, error_msg)


class ConfigurationError(Exception):
    """Exception raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, config_key: str = None):
        self.config_key = config_key
        error_msg = f"Configuration error: {message}"
        if config_key:
            error_msg += f" (key: {config_key})"
        super().__init__(error_msg)
