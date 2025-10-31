#!/usr/bin/env python3
"""
Comprehensive error handling and logging system for the Agentic Voice Assistant.
Provides graceful error handling for AWS service failures, fallback responses, and monitoring.
"""

import logging
import traceback
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import json


class ErrorType(Enum):
    """Types of errors that can occur in the system."""
    AWS_SERVICE_ERROR = "aws_service_error"
    VOICE_PROCESSING_ERROR = "voice_processing_error"
    AGENT_PROCESSING_ERROR = "agent_processing_error"
    DATABASE_ERROR = "database_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for an error."""
    error_type: ErrorType
    severity: ErrorSeverity
    component: str
    operation: str
    timestamp: datetime = field(default_factory=datetime.now)
    user_session_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""
    error_id: str
    context: ErrorContext
    exception: Optional[Exception]
    error_message: str
    stack_trace: Optional[str]
    recovery_attempted: bool = False
    recovery_successful: bool = False
    fallback_used: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


class ErrorHandler:
    """Comprehensive error handler with logging, recovery, and fallback mechanisms."""
    
    def __init__(self, log_level: int = logging.INFO):
        self.logger = logging.getLogger("VoiceAssistant.ErrorHandler")
        self.logger.setLevel(log_level)
        
        # Error tracking
        self.error_history: List[ErrorRecord] = []
        self.error_counts: Dict[ErrorType, int] = {}
        self.recovery_strategies: Dict[ErrorType, Callable] = {}
        self.fallback_responses: Dict[ErrorType, List[str]] = {}
        
        # Configure logging format
        self._setup_logging()
        
        # Initialize fallback responses
        self._initialize_fallback_responses()
        
        # Initialize recovery strategies
        self._initialize_recovery_strategies()
    
    def _setup_logging(self):
        """Set up comprehensive logging configuration."""
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for error logs
        try:
            file_handler = logging.FileHandler('voice_assistant_errors.log')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.WARNING)
            self.logger.addHandler(file_handler)
        except Exception as e:
            self.logger.warning(f"Could not create log file: {e}")
    
    def _initialize_fallback_responses(self):
        """Initialize fallback responses for different error types."""
        self.fallback_responses = {
            ErrorType.AWS_SERVICE_ERROR: [
                "I'm having trouble connecting to my services right now. Let me try a different approach.",
                "There seems to be a temporary service issue. Please try again in a moment.",
                "I'm experiencing some technical difficulties. Let me see what I can do locally."
            ],
            ErrorType.VOICE_PROCESSING_ERROR: [
                "I'm having trouble with audio processing. Could you try speaking again?",
                "There was an issue with voice recognition. Please repeat your request.",
                "I didn't catch that clearly. Could you rephrase your question?"
            ],
            ErrorType.AGENT_PROCESSING_ERROR: [
                "I'm having trouble processing your request. Let me try a different approach.",
                "There was an issue analyzing your query. Could you be more specific?",
                "I'm experiencing some processing difficulties. Let me escalate this to a human agent."
            ],
            ErrorType.DATABASE_ERROR: [
                "I'm having trouble accessing the information right now. Please try again shortly.",
                "There's a temporary issue with data retrieval. Let me see what I can find elsewhere.",
                "I can't access the database at the moment. Would you like me to escalate this?"
            ],
            ErrorType.NETWORK_ERROR: [
                "I'm having connectivity issues. Let me try to reconnect.",
                "There seems to be a network problem. Please wait while I attempt to reconnect.",
                "I'm experiencing connection difficulties. This might take a moment to resolve."
            ],
            ErrorType.AUTHENTICATION_ERROR: [
                "I'm having trouble with authentication. Let me try to reconnect to the services.",
                "There's an authentication issue. Please wait while I resolve this.",
                "I need to re-authenticate with the services. This should just take a moment."
            ],
            ErrorType.VALIDATION_ERROR: [
                "I didn't understand that request. Could you rephrase it?",
                "That doesn't seem like a valid request. Could you be more specific?",
                "I'm not sure how to handle that. Could you try asking differently?"
            ],
            ErrorType.TIMEOUT_ERROR: [
                "That's taking longer than expected. Let me try a faster approach.",
                "The request is timing out. Let me try a different method.",
                "This is taking too long. Would you like me to try something else?"
            ],
            ErrorType.UNKNOWN_ERROR: [
                "I encountered an unexpected issue. Let me try again.",
                "Something unexpected happened. Please try your request again.",
                "I'm not sure what went wrong there. Let me attempt a different approach."
            ]
        }
    
    def _initialize_recovery_strategies(self):
        """Initialize recovery strategies for different error types."""
        self.recovery_strategies = {
            ErrorType.AWS_SERVICE_ERROR: self._recover_aws_service,
            ErrorType.VOICE_PROCESSING_ERROR: self._recover_voice_processing,
            ErrorType.AGENT_PROCESSING_ERROR: self._recover_agent_processing,
            ErrorType.DATABASE_ERROR: self._recover_database,
            ErrorType.NETWORK_ERROR: self._recover_network,
            ErrorType.AUTHENTICATION_ERROR: self._recover_authentication,
            ErrorType.TIMEOUT_ERROR: self._recover_timeout,
        }
    
    async def handle_error(self, 
                          exception: Exception, 
                          context: ErrorContext,
                          attempt_recovery: bool = True) -> Dict[str, Any]:
        """
        Handle an error with comprehensive logging, recovery, and fallback.
        
        Returns:
            Dict containing error handling results and fallback response
        """
        # Generate unique error ID
        error_id = f"ERR_{int(time.time())}_{hash(str(exception)) % 10000:04d}"
        
        # Create error record
        error_record = ErrorRecord(
            error_id=error_id,
            context=context,
            exception=exception,
            error_message=str(exception),
            stack_trace=traceback.format_exc()
        )
        
        # Log the error
        self._log_error(error_record)
        
        # Update error counts
        self.error_counts[context.error_type] = self.error_counts.get(context.error_type, 0) + 1
        
        # Attempt recovery if enabled
        recovery_result = None
        if attempt_recovery and context.error_type in self.recovery_strategies:
            try:
                recovery_result = await self.recovery_strategies[context.error_type](exception, context)
                error_record.recovery_attempted = True
                error_record.recovery_successful = recovery_result.get('success', False)
            except Exception as recovery_error:
                self.logger.error(f"Recovery strategy failed for {error_id}: {recovery_error}")
        
        # Get fallback response
        fallback_response = self._get_fallback_response(context.error_type)
        error_record.fallback_used = True
        
        # Store error record
        self.error_history.append(error_record)
        
        # Trim error history if it gets too long
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-500:]
        
        return {
            'error_id': error_id,
            'handled': True,
            'recovery_attempted': error_record.recovery_attempted,
            'recovery_successful': error_record.recovery_successful,
            'fallback_response': fallback_response,
            'severity': context.severity.value,
            'should_escalate': context.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL],
            'recovery_result': recovery_result
        }
    
    def _log_error(self, error_record: ErrorRecord):
        """Log an error with appropriate level and detail."""
        context = error_record.context
        
        # Create log message
        log_message = f"Error {error_record.error_id}: {error_record.error_message}"
        
        # Create detailed log message with context
        detailed_message = f"[{context.component}:{context.operation}] {log_message} (Type: {context.error_type.value}, Severity: {context.severity.value})"
        if context.user_session_id:
            detailed_message += f" (Session: {context.user_session_id})"
        
        # Log at appropriate level
        if context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(detailed_message)
            if error_record.stack_trace:
                self.logger.critical(f"Stack trace for {error_record.error_id}:\n{error_record.stack_trace}")
        elif context.severity == ErrorSeverity.HIGH:
            self.logger.error(detailed_message)
            if error_record.stack_trace:
                self.logger.error(f"Stack trace for {error_record.error_id}:\n{error_record.stack_trace}")
        elif context.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(detailed_message)
        else:
            self.logger.info(detailed_message)
    
    def _get_fallback_response(self, error_type: ErrorType) -> str:
        """Get a fallback response for the given error type."""
        responses = self.fallback_responses.get(error_type, self.fallback_responses[ErrorType.UNKNOWN_ERROR])
        
        # Use error count to vary responses
        error_count = self.error_counts.get(error_type, 0)
        response_index = (error_count - 1) % len(responses)
        
        return responses[response_index]
    
    async def _recover_aws_service(self, exception: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Attempt to recover from AWS service errors."""
        self.logger.info(f"Attempting AWS service recovery for {context.component}")
        
        try:
            # Wait a moment for transient issues
            await asyncio.sleep(1)
            
            # Try to reinitialize the client (this would be component-specific)
            # For now, just return a recovery attempt result
            return {
                'success': False,
                'message': 'AWS service recovery attempted',
                'retry_recommended': True,
                'retry_delay': 5
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Recovery failed: {e}',
                'retry_recommended': False
            }
    
    async def _recover_voice_processing(self, exception: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Attempt to recover from voice processing errors."""
        self.logger.info(f"Attempting voice processing recovery for {context.component}")
        
        try:
            # For voice processing, we might try to reset audio devices
            await asyncio.sleep(0.5)
            
            return {
                'success': False,
                'message': 'Voice processing recovery attempted',
                'retry_recommended': True,
                'retry_delay': 2
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Voice recovery failed: {e}',
                'retry_recommended': False
            }
    
    async def _recover_agent_processing(self, exception: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Attempt to recover from agent processing errors."""
        self.logger.info(f"Attempting agent processing recovery for {context.component}")
        
        try:
            # For agent processing, we might try to reset the agent state
            await asyncio.sleep(0.5)
            
            return {
                'success': False,
                'message': 'Agent processing recovery attempted',
                'retry_recommended': True,
                'retry_delay': 1
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Agent recovery failed: {e}',
                'retry_recommended': False
            }
    
    async def _recover_database(self, exception: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Attempt to recover from database errors."""
        self.logger.info(f"Attempting database recovery for {context.component}")
        
        try:
            # For database errors, we might try to reconnect
            await asyncio.sleep(1)
            
            return {
                'success': False,
                'message': 'Database recovery attempted',
                'retry_recommended': True,
                'retry_delay': 3
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Database recovery failed: {e}',
                'retry_recommended': False
            }
    
    async def _recover_network(self, exception: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Attempt to recover from network errors."""
        self.logger.info(f"Attempting network recovery for {context.component}")
        
        try:
            # For network errors, we might try to reconnect
            await asyncio.sleep(2)
            
            return {
                'success': False,
                'message': 'Network recovery attempted',
                'retry_recommended': True,
                'retry_delay': 5
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Network recovery failed: {e}',
                'retry_recommended': False
            }
    
    async def _recover_authentication(self, exception: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Attempt to recover from authentication errors."""
        self.logger.info(f"Attempting authentication recovery for {context.component}")
        
        try:
            # For auth errors, we might try to refresh credentials
            await asyncio.sleep(1)
            
            return {
                'success': False,
                'message': 'Authentication recovery attempted',
                'retry_recommended': True,
                'retry_delay': 3
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Authentication recovery failed: {e}',
                'retry_recommended': False
            }
    
    async def _recover_timeout(self, exception: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Attempt to recover from timeout errors."""
        self.logger.info(f"Attempting timeout recovery for {context.component}")
        
        try:
            # For timeout errors, we might try with a shorter timeout
            return {
                'success': False,
                'message': 'Timeout recovery attempted',
                'retry_recommended': True,
                'retry_delay': 1,
                'suggested_timeout': 5  # Suggest shorter timeout
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Timeout recovery failed: {e}',
                'retry_recommended': False
            }
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        total_errors = len(self.error_history)
        
        if total_errors == 0:
            return {
                'total_errors': 0,
                'error_types': {},
                'severity_distribution': {},
                'recovery_success_rate': 0.0,
                'recent_errors': []
            }
        
        # Count by type
        type_counts = {}
        severity_counts = {}
        recovery_attempts = 0
        recovery_successes = 0
        
        for record in self.error_history:
            # Count by type
            error_type = record.context.error_type.value
            type_counts[error_type] = type_counts.get(error_type, 0) + 1
            
            # Count by severity
            severity = record.context.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Count recovery attempts
            if record.recovery_attempted:
                recovery_attempts += 1
                if record.recovery_successful:
                    recovery_successes += 1
        
        # Calculate recovery success rate
        recovery_success_rate = (recovery_successes / recovery_attempts * 100) if recovery_attempts > 0 else 0.0
        
        # Get recent errors (last 10)
        recent_errors = []
        for record in self.error_history[-10:]:
            recent_errors.append({
                'error_id': record.error_id,
                'type': record.context.error_type.value,
                'severity': record.context.severity.value,
                'component': record.context.component,
                'operation': record.context.operation,
                'message': record.error_message,
                'timestamp': record.timestamp.isoformat(),
                'recovery_attempted': record.recovery_attempted,
                'recovery_successful': record.recovery_successful
            })
        
        return {
            'total_errors': total_errors,
            'error_types': type_counts,
            'severity_distribution': severity_counts,
            'recovery_success_rate': recovery_success_rate,
            'recovery_attempts': recovery_attempts,
            'recovery_successes': recovery_successes,
            'recent_errors': recent_errors
        }
    
    def should_escalate_error(self, error_type: ErrorType, recent_count: int = 5) -> bool:
        """Determine if an error pattern should trigger escalation."""
        # Check recent error frequency
        recent_errors = self.error_history[-recent_count:] if len(self.error_history) >= recent_count else self.error_history
        
        # Count errors of this type in recent history
        recent_type_count = sum(1 for record in recent_errors if record.context.error_type == error_type)
        
        # Escalate if we have too many of the same error type recently
        if recent_type_count >= 3:
            return True
        
        # Escalate critical errors immediately
        if error_type in [ErrorType.AWS_SERVICE_ERROR, ErrorType.AUTHENTICATION_ERROR]:
            return recent_type_count >= 2
        
        return False
    
    async def cleanup_old_errors(self, max_age_hours: int = 24):
        """Clean up old error records to prevent memory issues."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        original_count = len(self.error_history)
        self.error_history = [record for record in self.error_history if record.timestamp > cutoff_time]
        
        cleaned_count = original_count - len(self.error_history)
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} old error records")


# Global error handler instance
error_handler = ErrorHandler()


# Convenience functions for common error handling patterns
async def handle_aws_error(exception: Exception, component: str, operation: str, 
                          session_id: Optional[str] = None) -> Dict[str, Any]:
    """Handle AWS service errors."""
    context = ErrorContext(
        error_type=ErrorType.AWS_SERVICE_ERROR,
        severity=ErrorSeverity.HIGH,
        component=component,
        operation=operation,
        user_session_id=session_id
    )
    return await error_handler.handle_error(exception, context)


async def handle_voice_error(exception: Exception, component: str, operation: str,
                            session_id: Optional[str] = None) -> Dict[str, Any]:
    """Handle voice processing errors."""
    context = ErrorContext(
        error_type=ErrorType.VOICE_PROCESSING_ERROR,
        severity=ErrorSeverity.MEDIUM,
        component=component,
        operation=operation,
        user_session_id=session_id
    )
    return await error_handler.handle_error(exception, context)


async def handle_agent_error(exception: Exception, component: str, operation: str,
                            session_id: Optional[str] = None) -> Dict[str, Any]:
    """Handle agent processing errors."""
    context = ErrorContext(
        error_type=ErrorType.AGENT_PROCESSING_ERROR,
        severity=ErrorSeverity.MEDIUM,
        component=component,
        operation=operation,
        user_session_id=session_id
    )
    return await error_handler.handle_error(exception, context)


async def handle_database_error(exception: Exception, component: str, operation: str,
                               session_id: Optional[str] = None) -> Dict[str, Any]:
    """Handle database errors."""
    context = ErrorContext(
        error_type=ErrorType.DATABASE_ERROR,
        severity=ErrorSeverity.HIGH,
        component=component,
        operation=operation,
        user_session_id=session_id
    )
    return await error_handler.handle_error(exception, context)


# Decorator for automatic error handling
def handle_errors(error_type: ErrorType = ErrorType.UNKNOWN_ERROR, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 component: str = "Unknown",
                 operation: str = "Unknown"):
    """Decorator for automatic error handling in async functions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    error_type=error_type,
                    severity=severity,
                    component=component,
                    operation=operation
                )
                error_result = await error_handler.handle_error(e, context)
                
                # Return a default result or re-raise based on severity
                if severity == ErrorSeverity.CRITICAL:
                    raise
                else:
                    return {
                        'success': False,
                        'error': error_result,
                        'fallback_response': error_result['fallback_response']
                    }
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test the error handler
    async def test_error_handler():
        print("Testing Error Handler...")
        
        # Test AWS error
        try:
            raise Exception("AWS service unavailable")
        except Exception as e:
            result = await handle_aws_error(e, "TestComponent", "test_operation")
            print(f"AWS Error Result: {result}")
        
        # Test voice error
        try:
            raise Exception("Microphone not accessible")
        except Exception as e:
            result = await handle_voice_error(e, "VoiceProcessor", "initialize_microphone")
            print(f"Voice Error Result: {result}")
        
        # Get statistics
        stats = error_handler.get_error_statistics()
        print(f"Error Statistics: {json.dumps(stats, indent=2)}")
    
    asyncio.run(test_error_handler())