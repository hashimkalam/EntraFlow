"""Notifier agent for generating reports and alerts."""

import json
from typing import Any, Dict, List
from datetime import datetime
from pathlib import Path
from .base_agent import BaseAgent
from utils.exceptions import ValidationError


class Notifier(BaseAgent):
    """
    Agent responsible for generating reports, alerts, and notifications.
    
    Capabilities:
    - Generate formatted reports (JSON, text, HTML)
    - Create alert logs
    - Produce summary statistics
    - Save outputs to files
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("Notifier", config)
        self.output_format = self.config.get('output_format', 'json')
        self.output_dir = Path("data/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _execute_impl(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate reports and notifications based on decisions.
        
        Args:
            inputs: Dictionary containing:
                - decisions: Output from DecisionMaker (required)
                - analysis_results: Output from Analyzer (optional)
        
        Returns:
            Dictionary containing:
                - report: Generated report content
                - report_file: Path to saved report file
                - alerts_file: Path to saved alerts file (if alerts exist)
                - summary: Executive summary
        """
        # Extract inputs
        decisions = inputs.get('decisions')
        if not decisions:
            raise ValidationError(self.name, "Missing 'decisions' in inputs")
        
        analysis_results = inputs.get('analysis_results', {})
        
        self.logger.info("Generating reports and notifications...")
        
        # Generate main report
        report = self._generate_report(decisions, analysis_results)
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"report_{timestamp}.{self._get_file_extension()}"
        report_path = self.output_dir / report_filename
        
        self._save_report(report, report_path)
        
        results = {
            'report': report,
            'report_file': str(report_path),
            'timestamp': datetime.now().isoformat(),
            'summary': self._generate_executive_summary(decisions, analysis_results)
        }
        
        # Handle alerts if present
        alerts = decisions.get('alerts', [])
        if alerts:
            alerts_filename = f"alerts_{timestamp}.json"
            alerts_path = self.output_dir / alerts_filename
            self._save_alerts(alerts, alerts_path)
            results['alerts_file'] = str(alerts_path)
            results['alert_count'] = len(alerts)
            
            self.logger.warning(f"Generated {len(alerts)} alert(s)")
        
        self.logger.info(f"Report generated successfully: {report_path}")
        
        return results
    
    def _generate_report(
        self,
        decisions: Dict[str, Any],
        analysis_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive report from decisions and analysis.
        
        Args:
            decisions: Decision results
            analysis_results: Analysis results
        
        Returns:
            Report dictionary
        """
        report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'report_type': 'Enterprise Analysis Report',
                'version': '1.0'
            },
            'executive_summary': self._generate_executive_summary(decisions, analysis_results),
            'priority': decisions.get('priority', 'medium'),
            'decisions': {
                'summary': decisions.get('summary', ''),
                'detailed_decisions': decisions.get('decisions', {}),
                'recommended_actions': decisions.get('actions', []),
                'alerts': decisions.get('alerts', [])
            },
            'analysis': {
                'sentiment': analysis_results.get('sentiment', {}),
                'keywords': analysis_results.get('keywords', {}),
                'statistics': analysis_results.get('statistics', {}),
                'insights': analysis_results.get('insights', []),
                'enhanced_insights': analysis_results.get('enhanced_insights', '')
            },
            'strategic_advisory': decisions.get('strategic_advisory', '')
        }
        
        return report
    
    def _generate_executive_summary(
        self,
        decisions: Dict[str, Any],
        analysis_results: Dict[str, Any]
    ) -> str:
        """
        Generate executive summary of the analysis and decisions.
        
        Args:
            decisions: Decision results
            analysis_results: Analysis results
        
        Returns:
            Summary string
        """
        lines = []
        
        # Priority and decision summary
        priority = decisions.get('priority', 'medium').upper()
        lines.append(f"PRIORITY LEVEL: {priority}")
        lines.append("")
        lines.append(decisions.get('summary', 'No summary available'))
        lines.append("")
        
        # Strategic Advisory (LLM)
        advisory = decisions.get('strategic_advisory')
        if advisory:
            lines.append("────────────────────────────────────────────────────────────────")
            lines.append("✨ STRATEGIC AI ADVISORY")
            lines.append("────────────────────────────────────────────────────────────────")
            lines.append(advisory)
            lines.append("────────────────────────────────────────────────────────────────")
            lines.append("")
        
        # Sentiment summary
        sentiment = analysis_results.get('sentiment', {}).get('news', {})
        if sentiment:
            sentiment_label = sentiment.get('sentiment_label', 'neutral').upper()
            sentiment_score = sentiment.get('overall_sentiment', 0)
            article_count = sentiment.get('total_articles', 0)
            lines.append(f"Sentiment Analysis: {sentiment_label} (score: {sentiment_score:.2f})")
            lines.append(f"Analyzed {article_count} news article(s)")
            lines.append("")
        
        # Key insights
        insights = analysis_results.get('insights', [])
        if insights:
            lines.append("Key Insights:")
            for insight in insights[:5]:  # Top 5 insights
                lines.append(f"  • {insight}")
            lines.append("")
            
        # Enhanced Analysis (LLM)
        enhanced = analysis_results.get('enhanced_insights')
        if enhanced:
            lines.append("Market Analysis (Deep Insights):")
            lines.append(f"  {enhanced}")
            lines.append("")
        
        # Alerts
        alerts = decisions.get('alerts', [])
        if alerts:
            lines.append(f"⚠️  {len(alerts)} ALERT(S) TRIGGERED:")
            for alert in alerts:
                severity = alert.get('severity', 'info').upper()
                message = alert.get('message', '')
                lines.append(f"  [{severity}] {message}")
            lines.append("")
        
        # Actions
        actions = decisions.get('actions', [])
        if actions:
            lines.append("Recommended Actions:")
            for i, action in enumerate(actions[:7], 1):  # Top 7 actions
                lines.append(f"  {i}. {action}")
        
        return '\n'.join(lines)
    
    def _get_file_extension(self) -> str:
        """Get file extension based on output format."""
        format_extensions = {
            'json': 'json',
            'text': 'txt',
            'html': 'html'
        }
        return format_extensions.get(self.output_format, 'json')
    
    def _save_report(self, report: Dict[str, Any], path: Path):
        """
        Save report to file in the specified format.
        
        Args:
            report: Report dictionary
            path: File path  to save to
        """
        if self.output_format == 'json':
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        
        elif self.output_format == 'text':
            text_content = self._format_as_text(report)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text_content)
        
        elif self.output_format == 'html':
            html_content = self._format_as_html(report)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        else:
            # Default to JSON
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
    
    def _save_alerts(self, alerts: List[Dict[str, Any]], path: Path):
        """Save alerts to a separate JSON file."""
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'alert_count': len(alerts),
            'alerts': alerts
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(alert_data, f, indent=2, ensure_ascii=False)
    
    def _format_as_text(self, report: Dict[str, Any]) -> str:
        """Format report as plain text."""
        lines = []
        lines.append("=" * 80)
        lines.append("ENTERPRISE ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Generated: {report['metadata']['generated_at']}")
        lines.append("")
        lines.append("-" * 80)
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        lines.append(report.get('executive_summary', ''))
        lines.append("")
        lines.append("-" * 80)
        lines.append("DETAILED ANALYSIS")
        lines.append("-" * 80)
        lines.append(json.dumps(report.get('analysis', {}), indent=2))
        lines.append("")
        lines.append("=" * 80)
        
        return '\n'.join(lines)
    
    def _format_as_html(self, report: Dict[str, Any]) -> str:
        """Format report as HTML."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Enterprise Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
        .container {{ background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ background-color: #f8f9fa; padding: 20px; border-left: 4px solid #007bff; margin: 20px 0; }}
        .priority {{ font-size: 24px; font-weight: bold; color: #dc3545; }}
        .alert {{ background-color: #fff3cd; border: 1px solid #ffc107; padding: 10px; margin: 10px 0; border-radius: 4px; }}
        .metadata {{ color: #666; font-size: 14px; }}
        ul {{ line-height: 1.8; }}
        pre {{ background-color: #f8f9fa; padding: 15px; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Enterprise Analysis Report</h1>
        <p class="metadata">Generated: {report['metadata']['generated_at']}</p>
        
        <div class="summary">
            <h2>Executive Summary</h2>
            <pre>{report.get('executive_summary', '')}</pre>
        </div>
        
        <h2>Priority Level</h2>
        <p class="priority">{report.get('priority', 'medium').upper()}</p>
        
        <h2>Recommended Actions</h2>
        <ul>
        {''.join(f'<li>{action}</li>' for action in report.get('decisions', {}).get('recommended_actions', []))}
        </ul>
        
        <h2>Analysis Details</h2>
        <pre>{json.dumps(report.get('analysis', {}), indent=2)}</pre>
    </div>
</body>
</html>"""
        
        return html
    
    def validate_input(self, inputs: Dict[str, Any]) -> None:
        """Validate notifier inputs."""
        super().validate_input(inputs)
        
        if 'decisions' not in inputs:
            raise ValidationError(self.name, "Missing required input 'decisions'")
