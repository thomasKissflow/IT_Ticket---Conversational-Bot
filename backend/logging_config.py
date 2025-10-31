"""
Logging configuration to suppress unwanted logs.
"""

import logging

def setup_clean_logging():
    """Set up clean logging with minimal noise."""
    
    # Set root logger to WARNING to suppress most logs
    logging.getLogger().setLevel(logging.WARNING)
    
    # Suppress specific noisy loggers
    noisy_loggers = [
        'voice_processor',
        'voice_input_handler', 
        'voice_output_handler',
        'interruption_detector',
        'utils.data_access',
        'botocore',
        'boto3',
        'urllib3',
        'uvicorn',
        'websocket_server',
        'llm_client',
        'performance_optimizer'
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.ERROR)
    
    # Only show our essential debug info
    logging.getLogger('main').setLevel(logging.WARNING)
    
    # Configure basic format
    logging.basicConfig(
        level=logging.WARNING,
        format='%(message)s'
    )