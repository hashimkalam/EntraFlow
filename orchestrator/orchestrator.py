"""Main orchestrator for coordinating agent execution."""

import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from agents.base_agent import BaseAgent
from agents.data_fetcher import DataFetcher
from agents.analyzer import Analyzer
from agents.decision_maker import DecisionMaker
from agents.notifier import Notifier
from agents.supervisor import Supervisor
from .workflow import WorkflowManager
from .state_manager import StateManager
from utils.logger import get_logger, setup_logger
from utils.config import Config
from utils.exceptions import OrchestratorError, AgentError


class Orchestrator:
    """
    Main orchestrator for coordinating agent execution.
    
    Capabilities:
    - Workflow execution based on dependency graphs
    - Task assignment and scheduling
    - Global state management
    - Retry logic with exponential backoff
    - Conditional branching based on agent results
    - Agent failure recovery and fallback mechanisms
    - Progress tracking and status reporting
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the orchestrator.
        
        Args:
            config: Configuration object (creates default if not provided)
        """
        self.config = config or Config()
        
        # Setup logging
        log_config = self.config.get('logging', default={})
        setup_logger(
            log_level=log_config.get('level', 'INFO'),
            log_file=log_config.get('log_file') if log_config.get('log_to_file') else None,
            max_bytes=log_config.get('max_file_size', 10485760),
            backup_count=log_config.get('backup_count', 5),
            console_output=log_config.get('console_output', True)
        )
        
        self.logger = get_logger("Orchestrator")
        
        # Initialize components
        self.workflow_manager = WorkflowManager()
        self.state_manager = StateManager()
        
        # Initialize agents
        self.agents = self._initialize_agents()
        
        # Load workflows from config
        self._load_workflows()
        
        # Orchestrator state
        self.current_workflow = None
        self.current_workflow_id = None
        self.execution_history = []
        
        self.logger.info("Orchestrator initialized successfully")
    
    def _initialize_agents(self) -> Dict[str, BaseAgent]:
        """Initialize all agents with their configurations."""
        agents = {}
        
        # DataFetcher
        df_config = self.config.get_agent_config('data_fetcher')
        df_config.update({
            'weather_api_url': self.config.get('api', 'weather', 'base_url'),
            'news_api_url': self.config.get('api', 'news', 'base_url'),
            'api_timeout': self.config.get('api', 'weather', 'timeout', default=10)
        })
        agents['DataFetcher'] = DataFetcher(df_config)
        
        # Analyzer
        analyzer_config = self.config.get_agent_config('analyzer')
        agents['Analyzer'] = Analyzer(analyzer_config)
        
        # DecisionMaker
        dm_config = self.config.get_agent_config('decision_maker')
        agents['DecisionMaker'] = DecisionMaker(dm_config)
        
        # Notifier
        notifier_config = self.config.get_agent_config('notifier')
        agents['Notifier'] = Notifier(notifier_config)
        
        # Supervisor
        supervisor_config = self.config.get_agent_config('supervisor')
        agents['Supervisor'] = Supervisor(supervisor_config)
        
        self.logger.info(f"Initialized {len(agents)} agents: {list(agents.keys())}")
        return agents
    
    def _load_workflows(self):
        """Load workflow definitions from configuration."""
        workflows = self.config.get_all_workflows()
        
        for name, workflow_config in workflows.items():
            try:
                self.workflow_manager.register_workflow(name, workflow_config)
            except Exception as e:
                self.logger.error(f"Failed to load workflow '{name}': {str(e)}")
    
    def execute_workflow(
        self,
        workflow_name: str,
        initial_inputs: Dict[str, Any] = None,
        save_state: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a complete workflow.
        
        Args:
            workflow_name: Name of the workflow to execute
            initial_inputs: Initial input data for the workflow
            save_state: Whether to save workflow state
        
        Returns:
            Dictionary containing workflow results
        """
        self.logger.info(f"=" * 80)
        self.logger.info(f"Starting workflow: {workflow_name}")
        self.logger.info(f"=" * 80)
        
        start_time = time.time()
        self.current_workflow = workflow_name
        self.current_workflow_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        initial_inputs = initial_inputs or {}
        
        # Get workflow configuration
        workflow = self.workflow_manager.get_workflow(workflow_name)
        execution_order = self.workflow_manager.get_execution_order(workflow_name)
        
        self.logger.info(f"Execution plan: {len(execution_order)} level(s)")
        for i, level in enumerate(execution_order, 1):
            self.logger.info(f"  Level {i}: {', '.join(level)}")
        
        # Initialize workflow state
        workflow_state = {
            'outputs': {},
            'status': 'running',
            'completed_agents': [],
            'failed_agents': [],
            'start_time': datetime.now().isoformat()
        }
        
        # Add initial inputs to state
        workflow_state['outputs'].update(initial_inputs)
        
        try:
            # Execute each level
            for level_num, level_agents in enumerate(execution_order, 1):
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"Executing Level {level_num}/{len(execution_order)}")
                self.logger.info(f"{'='*60}")
                
                # Execute all agents in this level
                for agent_name in level_agents:
                    # Get step configuration
                    step = next((s for s in workflow['steps'] if s.agent_name == agent_name), None)
                    if not step:
                        raise OrchestratorError(f"Step configuration not found for agent: {agent_name}")

                    try:
                        result = self._execute_agent(
                            agent_name,
                            step,
                            workflow_state['outputs']
                        )
                        
                        # Store outputs based on configuration
                        if step.outputs:
                            for output_key in step.outputs:
                                workflow_state['outputs'][output_key] = result
                        else:
                            # Fallback to default naming convention
                            workflow_state['outputs'][agent_name.lower() + '_output'] = result
                        
                        workflow_state['completed_agents'].append(agent_name)
                        
                        # Check for conditional branching based on sentiment
                        if agent_name == 'Analyzer':
                            self._handle_conditional_logic(result, workflow_state)
                        
                    except AgentError as e:
                        self.logger.error(f"Agent {agent_name} failed: {str(e)}")
                        workflow_state['failed_agents'].append(agent_name)
                        
                        # Check if this is a critical failure
                        if self._is_critical_agent(agent_name):
                            raise OrchestratorError(
                                f"Critical agent '{agent_name}' failed: {str(e)}",
                                workflow=workflow_name
                            )
            
            # Workflow completed successfully
            execution_time = time.time() - start_time
            workflow_state['status'] = 'completed'
            workflow_state['end_time'] = datetime.now().isoformat()
            workflow_state['execution_time'] = execution_time
            
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"Workflow completed successfully in {execution_time:.2f}s")
            self.logger.info(f"{'='*80}")
            
        except Exception as e:
            execution_time = time.time() - start_time
            workflow_state['status'] = 'failed'
            workflow_state['end_time'] = datetime.now().isoformat()
            workflow_state['execution_time'] = execution_time
            workflow_state['error'] = str(e)
            
            self.logger.error(f"Workflow failed after {execution_time:.2f}s: {str(e)}")
            
            if save_state:
                self.state_manager.save_state(workflow_name, workflow_state, self.current_workflow_id)
            
            raise
        
        # Save final state
        if save_state:
            state_file = self.state_manager.save_state(
                workflow_name,
                workflow_state,
                self.current_workflow_id
            )
            workflow_state['state_file'] = state_file
        
        # Add to execution history
        self.execution_history.append({
            'workflow_name': workflow_name,
            'workflow_id': self.current_workflow_id,
            'status': workflow_state['status'],
            'execution_time': workflow_state['execution_time']
        })
        
        return workflow_state
    
    def _execute_agent(
        self,
        agent_name: str,
        step: Any,  # WorkflowStep
        available_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single agent with retry logic.
        
        Args:
            agent_name: Name of the agent to execute
            step: Workflow step configuration
            available_outputs: Available outputs from previous agents
        
        Returns:
            Agent execution result
        """
        if agent_name not in self.agents:
            raise OrchestratorError(f"Unknown agent: {agent_name}")
        
        agent = self.agents[agent_name]
        
        # Prepare inputs from available outputs
        agent_inputs = {}
        for input_key in step.inputs:
            if input_key in available_outputs:
                agent_inputs[input_key] = available_outputs[input_key]
        
        # Get retry configuration
        orchestrator_config = self.config.get('orchestrator', default={})
        max_retries = orchestrator_config.get('max_retries', 3)
        retry_delay = orchestrator_config.get('retry_delay', 2)
        
        self.logger.info(f"Executing agent: {agent_name}")
        
        try:
            result = agent.execute(
                agent_inputs,
                max_retries=max_retries,
                retry_delay=retry_delay
            )
            return result
            
        except Exception as e:
            self.logger.error(f"Agent execution failed: {agent_name}")
            raise
    
    def _handle_conditional_logic(self, analyzer_result: Dict[str, Any], workflow_state: Dict[str, Any]):
        """
        Handle conditional workflow branching based on analysis results.
        
        Args:
            analyzer_result: Result from Analyzer agent
            workflow_state: Current workflow state
        """
        sentiment = analyzer_result.get('sentiment', {}).get('news', {})
        if not sentiment:
            return
        
        sentiment_score = sentiment.get('overall_sentiment', 0)
        sentiment_label = sentiment.get('sentiment_label', 'neutral')
        
        self.logger.info(f"Conditional check: sentiment={sentiment_label} (score={sentiment_score:.2f})")
        
        # Example conditional logic
        if sentiment_score < -0.5:
            self.logger.warning("⚠️  CRITICAL negative sentiment detected - triggering alert workflow")
            workflow_state['conditional_branch'] = 'critical_alert'
        elif sentiment_score < -0.3:
            self.logger.warning("⚠️  Negative sentiment detected - heightened monitoring")
            workflow_state['conditional_branch'] = 'heightened_monitoring'
        else:
            workflow_state['conditional_branch'] = 'normal'
    
    def _is_critical_agent(self, agent_name: str) -> bool:
        """
        Determine if an agent is critical for workflow execution.
        
        Args:
            agent_name: Agent name
        
        Returns:
            True if agent is critical
        """
        # DataFetcher and Analyzer are critical
        critical_agents = ['DataFetcher', 'Analyzer']
        return agent_name in critical_agents
    
    def execute_agent_standalone(
        self,
        agent_name: str,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single agent standalone (for testing).
        
        Args:
            agent_name: Name of the agent
            inputs: Input dictionary
        
        Returns:
            Agent execution result
        """
        if agent_name not in self.agents:
            raise OrchestratorError(f"Unknown agent: {agent_name}")
        
        agent = self.agents[agent_name]
        
        self.logger.info(f"Executing agent standalone: {agent_name}")
        
        return agent.execute(inputs)
    
    def get_agent_status(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get status of one or all agents.
        
        Args:
            agent_name: Optional specific agent name
        
        Returns:
            Status dictionary
        """
        if agent_name:
            if agent_name not in self.agents:
                raise OrchestratorError(f"Unknown agent: {agent_name}")
            return self.agents[agent_name].get_state()
        
        # Return all agent statuses
        return {
            name: agent.get_state()
            for name, agent in self.agents.items()
        }
    
    def list_workflows(self) -> List[str]:
        """List all available workflows."""
        return self.workflow_manager.list_workflows()
    
    def get_workflow_info(self, workflow_name: str) -> Dict[str, Any]:
        """Get information about a workflow."""
        workflow = self.workflow_manager.get_workflow(workflow_name)
        execution_order = self.workflow_manager.get_execution_order(workflow_name)
        
        return {
            'name': workflow_name,
            'description': workflow.get('description', ''),
            'steps': [s.agent_name for s in workflow['steps']],
            'execution_order': execution_order,
            'total_levels': len(execution_order)
        }
    
    def reset_all_agents(self):
        """Reset state of all agents."""
        for agent in self.agents.values():
            agent.reset_state()
        self.logger.info("All agents reset")
