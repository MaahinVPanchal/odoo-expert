import logging
import sys
from pathlib import Path
from src.config.settings import settings

def setup_logger():
    """Configure and return a logger instance."""
    logger = logging.getLogger("odoo_expert")
    
    # Only add handlers if they haven't been added already
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        try:
            # Create logs directory if it doesn't exist
            settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Setup file handler
            file_handler = logging.FileHandler(settings.LOGS_DIR / "app.log")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not setup file logging: {e}")
    
    return logger

# Create a singleton logger instance
logger = setup_logger()