import streamlit as st
import traceback
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ErrorHandler:
    """Comprehensive error handling system"""
    
    @staticmethod
    def log_error(error: Exception, context: Dict[str, Any] = None):
        """Log errors with context"""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {},
            "session_id": st.session_state.get('session_id', 'unknown')
        }
        
        # Log to console
        logger.error(f"Application Error: {error_data}")
        
        # Store in session state for debugging
        if 'error_log' not in st.session_state:
            st.session_state.error_log = []
        
        st.session_state.error_log.append(error_data)
        
        # Keep only last 10 errors to manage memory
        if len(st.session_state.error_log) > 10:
            st.session_state.error_log = st.session_state.error_log[-10:]
    
    @staticmethod
    def handle_api_error(error: Exception, api_name: str) -> Dict[str, Any]:
        """Handle API-specific errors - no fallback"""
        ErrorHandler.log_error(error, {"api": api_name})
        st.error(f"❌ {api_name.title()} API error: {str(error)}")
        raise error
    
    @staticmethod
    def safe_execute(func, *args, error_context=None, **kwargs):
        """Safely execute functions with error handling"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ErrorHandler.log_error(e, error_context)
            raise e
    
    @staticmethod
    def display_error_summary():
        """Display error summary in sidebar"""
        if 'error_log' in st.session_state and st.session_state.error_log:
            with st.sidebar.expander("🐛 Error Log", expanded=False):
                st.write(f"**Total Errors:** {len(st.session_state.error_log)}")
                
                for i, error in enumerate(reversed(st.session_state.error_log[-3:])):
                    st.write(f"**Error {i+1}:** {error['error_type']}")
                    st.write(f"*Time:* {error['timestamp'][:19]}")
                    if st.checkbox(f"Show details {i+1}", key=f"error_detail_{i}"):
                        st.code(error['error_message'])

def error_boundary(func):
    """Decorator for error boundary functionality"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ErrorHandler.log_error(e, {"function": func.__name__})
            st.error(f"An error occurred in {func.__name__}: {str(e)}")
            return None
    return wrapper
