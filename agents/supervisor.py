"""Supervisor agent for validation and conflict resolution."""

from typing import Any, Dict, List
from .base_agent import BaseAgent
from utils.exceptions import ValidationError


class Supervisor(BaseAgent):
    """
    Agent responsible for validating outputs and resolving conflicts.
    
    Capabilities:
    - Validate consistency of agent outputs
    - Detect conflicting results
    - Apply quality assurance checks
    - Override decisions when necessary
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("Supervisor", config)
        self.validation_enabled = self.config.get('validation_enabled', True)
        self.conflict_resolution = self.config.get('conflict_resolution', 'latest')
    
    def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and supervise the workflow outputs.
        
        Args:
            inputs: Dictionary containing:
                - report: Output from Notifier (required)
                - decisions: Output from DecisionMaker (optional)
        
        Returns:
            Dictionary containing:
                - validated_report: Validated and potentially modified report
                - validation_results: Validation checks performed
                - conflicts_found: List of any conflicts detected
                - supervisor_notes: Notes from supervisor
                - approval_status: Whether the workflow is approved
        """
        report = inputs.get('report')
        if not report:
            raise ValidationError(self.name, "Missing 'report' in inputs")
        
        decisions = inputs.get('decisions', {})
        
        self.logger.info("Starting supervision and validation...")
        
        results = {
            'validated_report': report.copy(),
            'validation_results': {},
            'conflicts_found': [],
            'supervisor_notes': [],
            'approval_status': 'pending'
        }
        
        # Perform validation checks
        if self.validation_enabled:
            validation_checks = self._perform_validation_checks(report, decisions)
            results['validation_results'] = validation_checks
            
            # Check for critical issues
            if validation_checks.get('critical_issues', []):
                results['supervisor_notes'].append(
                    f"⚠️ {len(validation_checks['critical_issues'])} critical issue(s) found"
                )
                results['approval_status'] = 'rejected'
            else:
                results['supervisor_notes'].append("✓ No critical issues found")
        
        # Check for conflicts
        conflicts = self._detect_conflicts(report, decisions)
        results['conflicts_found'] = conflicts
        
        if conflicts:
            self.logger.warning(f"Detected {len(conflicts)} conflict(s)")
            results['supervisor_notes'].append(f"Found {len(conflicts)} conflict(s) - review required")
            
            # Resolve conflicts if configured
            if self.conflict_resolution != 'manual':
                resolved_report = self._resolve_conflicts(report, conflicts)
                results['validated_report'] = resolved_report
                results['supervisor_notes'].append(
                    f"Conflicts resolved using '{self.conflict_resolution}' strategy"
                )
        
        # Quality assurance
        qa_results = self._quality_assurance(report)
        results['validation_results']['quality_assurance'] = qa_results
        
        if qa_results.get('passed', False):
            results['supervisor_notes'].append("✓ Quality assurance checks passed")
        else:
            results['supervisor_notes'].append("⚠️ Some quality checks need attention")
        
        # Final approval decision
        if results['approval_status'] != 'rejected':
            if not conflicts and qa_results.get('passed', False):
                results['approval_status'] = 'approved'
                results['supervisor_notes'].append("✓ Workflow approved for delivery")
            else:
                results['approval_status'] = 'approved_with_notes'
                results['supervisor_notes'].append("Approved with notes - manual review recommended")
        
        # Add supervisor summary
        results['supervisor_summary'] = self._generate_supervisor_summary(results)
        
        self.logger.info(f"Supervision complete: Status={results['approval_status']}")
        
        return results
    
    def _perform_validation_checks(
        self,
        report: Dict[str, Any],
        decisions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive validation checks.
        
        Args:
            report: Report to validate
            decisions: Decision data
        
        Returns:
            Validation results dictionary
        """
        checks = {
            'completeness': {},
            'consistency': {},
            'critical_issues': [],
            'warnings': []
        }
        
        # Check report completeness
        required_fields = ['metadata', 'executive_summary', 'priority', 'decisions', 'analysis', 'strategic_advisory']
        missing_fields = [field for field in required_fields if field not in report.get('report', {})]
        
        if missing_fields:
            checks['completeness']['missing_fields'] = missing_fields
            checks['warnings'].append(f"Missing fields in report: {', '.join(missing_fields)}")
        else:
            checks['completeness']['status'] = 'complete'
        
        # Check data consistency
        report_data = report.get('report', {})
        report_priority = report_data.get('priority', '').lower()
        decision_priority = decisions.get('priority', '').lower()
        
        if report_priority != decision_priority:
            checks['consistency']['priority_mismatch'] = {
                'report': report_priority,
                'decisions': decision_priority
            }
            checks['warnings'].append(
                f"Priority mismatch: report='{report_priority}', decisions='{decision_priority}'"
            )
        else:
            checks['consistency']['priority'] = 'consistent'
        
        # Check for critical conditions
        alerts = report_data.get('decisions', {}).get('alerts', [])
        critical_alerts = [a for a in alerts if a.get('severity') == 'critical']
        
        if critical_alerts and report_priority not in ['critical', 'high']:
            checks['critical_issues'].append(
                "Critical alerts present but priority not set to critical/high"
            )
        
        # Validate sentiment data
        sentiment = report_data.get('analysis', {}).get('sentiment', {}).get('news', {})
        if sentiment:
            confidence = sentiment.get('confidence', 0)
            if confidence < 0.3:
                checks['warnings'].append(
                    f"Low confidence in sentiment analysis: {confidence:.2f}"
                )
        
        return checks
    
    def _detect_conflicts(
        self,
        report: Dict[str, Any],
        decisions: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicts or inconsistencies.
        
        Args:
            report: Report data
            decisions: Decision data
        
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        report_data = report.get('report', {})
        
        # Check for conflicting sentiment vs priority
        sentiment = report_data.get('analysis', {}).get('sentiment', {}).get('news', {})
        if sentiment:
            sentiment_score = sentiment.get('overall_sentiment', 0)
            priority = report_data.get('priority', 'medium').lower()
            
            # Negative sentiment but low priority?
            if sentiment_score < -0.4 and priority in ['low', 'medium']:
                conflicts.append({
                    'type': 'sentiment_priority_conflict',
                    'description': f'Negative sentiment ({sentiment_score:.2f}) but priority is {priority}',
                    'severity': 'medium',
                    'recommendation': 'Consider increasing priority level'
                })
            
            # Positive sentiment but high priority?
            if sentiment_score > 0.4 and priority in ['critical', 'high']:
                conflicts.append({
                    'type': 'sentiment_priority_conflict',
                    'description': f'Positive sentiment ({sentiment_score:.2f}) but priority is {priority}',
                    'severity': 'low',
                    'recommendation': 'Review priority rationale'
                })
        
        # Check for action conflicts
        actions = report_data.get('decisions', {}).get('recommended_actions', [])
        action_text = ' '.join(actions).lower()
        
        if 'immediate' in action_text and 'monitor' in action_text:
            conflicts.append({
                'type': 'action_conflict',
                'description': 'Conflicting actions: immediate action and monitoring recommended',
                'severity': 'low',
                'recommendation': 'Clarify action priorities'
            })
        
        return conflicts
    
    def _resolve_conflicts(
        self,
        report: Dict[str, Any],
        conflicts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Resolve detected conflicts based on configured strategy.
        
        Args:
            report: Original report
            conflicts: List of conflicts
        
        Returns:
            Resolved report
        """
        resolved_report = report.copy()
        
        for conflict in conflicts:
            if conflict['type'] == 'sentiment_priority_conflict':
                # Apply automatic resolution based on strategy
                if self.conflict_resolution == 'latest':
                    # Keep current values but add note
                    self.logger.info(f"Conflict noted: {conflict['description']}")
                
                # Could add more sophisticated resolution strategies here
        
        return resolved_report
    
    def _quality_assurance(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform quality assurance checks.
        
        Args:
            report: Report to check
        
        Returns:
            QA results dictionary
        """
        qa_results = {
            'checks_performed': [],
            'passed': True,
            'issues': []
        }
        
        report_data = report.get('report', {})
        
        # Check 1: Report has content
        qa_results['checks_performed'].append('content_check')
        if not report_data.get('executive_summary'):
            qa_results['issues'].append('Empty executive summary')
            qa_results['passed'] = False
        
        # Check 2: Metadata is present
        qa_results['checks_performed'].append('metadata_check')
        if not report_data.get('metadata'):
            qa_results['issues'].append('Missing metadata')
            qa_results['passed'] = False
        
        # Check 3: Has actionable items
        qa_results['checks_performed'].append('actionability_check')
        actions = report_data.get('decisions', {}).get('recommended_actions', [])
        if not actions:
            qa_results['issues'].append('No recommended actions provided')
            qa_results['passed'] = False
        
        # Check 4: Priority is set
        qa_results['checks_performed'].append('priority_check')
        if not report_data.get('priority'):
            qa_results['issues'].append('Priority not set')
            qa_results['passed'] = False
        
        return qa_results
    
    def _generate_supervisor_summary(self, results: Dict[str, Any]) -> str:
        """Generate human-readable supervisor summary."""
        lines = []
        lines.append(f"Approval Status: {results['approval_status'].upper()}")
        
        if results['supervisor_notes']:
            lines.append("\nSupervisor Notes:")
            for note in results['supervisor_notes']:
                lines.append(f"  • {note}")
        
        conflicts = results.get('conflicts_found', [])
        if conflicts:
            lines.append(f"\nConflicts Detected: {len(conflicts)}")
            for conflict in conflicts[:3]:  # Show top 3
                lines.append(f"  • {conflict.get('description', 'Unknown conflict')}")
        
        return '\n'.join(lines)
    
    def validate_input(self, inputs: Dict[str, Any]) -> None:
        """Validate supervisor inputs."""
        super().validate_input(inputs)
        
        if 'report' not in inputs:
            raise ValidationError(self.name, "Missing required input 'report'")
