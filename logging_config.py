import logging
from logging.handlers import RotatingFileHandler
import os
from termcolor import colored

def setup_logger(name, log_file, level=logging.INFO, console_level=logging.INFO):
    """Function to setup as many loggers as you want"""
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(console_level)

    logger = logging.getLogger(name)
    logger.setLevel(min(level, console_level))
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def log_message(logger, message, level='info'):
    color_map = {
        'debug': 'blue',
        'info': 'green',
        'warning': 'yellow',
        'error': 'red',
        'critical': 'red'
    }
    color = color_map.get(level.lower(), 'white')
    log_func = getattr(logger, level.lower())
    log_func(colored(message, color))

# Setup main logger
main_logger = setup_logger('google_photos_loader', 'google_photos_loader.log')