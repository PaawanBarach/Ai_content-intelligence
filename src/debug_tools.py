import streamlit as st
import psutil
import time
from datetime import datetime
from typing import Dict, Any
import json

class DebugTools:
    """Debugging and monitoring tools"""
    
    @staticmethod
    def init_debug_session():
        """Initialize debug session tracking"""
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = {
                "session_start": datetime.now().isoformat(),
                "total_analyses": 0,
                "api_calls": 0,
                "errors": 0,
                "performance_metrics": []
            }
    
    @staticmethod
    def track_performance(operation_name: str, start_time: float, end_time: float):
        """Track operation performance"""
        if 'debug_info' not in st.session_state:
            DebugTools.init_debug_session()
        
        duration = end_time - start_time
        metric = {
            "operation": operation_name,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
        
        st.session_state.debug_info["performance_metrics"].append(metric)
        
        # Keep only last 20 metrics
        if len(st.session_state.debug_info["performance_metrics"]) > 20:
            st.session_state.debug_info["performance_metrics"] = \
                st.session_state.debug_info["performance_metrics"][-20:]
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get current system information"""
        try:
            return {
                "memory_usage": f"{psutil.virtual_memory().percent}%",
                "memory_available": f"{psutil.virtual_memory().available / (1024**3):.2f} GB",
                "cpu_usage": f"{psutil.cpu_percent()}%",
                "session_uptime": str(datetime.now() - datetime.fromisoformat(
                    st.session_state.debug_info.get("session_start", datetime.now().isoformat())
                )).split('.')[0]
            }
        except:
            return {"status": "System info unavailable"}
    
    @staticmethod
    def display_debug_panel():
        """Display comprehensive debug panel in sidebar"""
        with st.sidebar.expander("🔍 Debug Panel", expanded=False):
            # System Information
            st.subheader("System Status")
            system_info = DebugTools.get_system_info()
            for key, value in system_info.items():
                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
            
            # Session Statistics
            if 'debug_info' in st.session_state:
                st.subheader("Session Stats")
                debug_info = st.session_state.debug_info
                st.write(f"**Total Analyses:** {debug_info.get('total_analyses', 0)}")
                st.write(f"**API Calls:** {debug_info.get('api_calls', 0)}")
                st.write(f"**Errors:** {debug_info.get('errors', 0)}")
            
            # Performance Metrics
            if 'debug_info' in st.session_state and st.session_state.debug_info.get('performance_metrics'):
                st.subheader("Performance")
                metrics = st.session_state.debug_info['performance_metrics'][-5:]  # Last 5
                for metric in metrics:
                    st.write(f"**{metric['operation']}:** {metric['duration']:.2f}s")
            
            # Export Debug Data
            if st.button("📊 Export Debug Data"):
                debug_export = {
                    "session_info": st.session_state.get('debug_info', {}),
                    "error_log": st.session_state.get('error_log', []),
                    "system_info": system_info,
                    "export_timestamp": datetime.now().isoformat()
                }
                
                st.download_button(
                    "⬇️ Download Debug Report",
                    data=json.dumps(debug_export, indent=2),
                    file_name=f"debug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

def performance_monitor(operation_name: str):
    """Decorator to monitor function performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                DebugTools.track_performance(operation_name, start_time, end_time)
                return result
            except Exception as e:
                end_time = time.time()
                DebugTools.track_performance(f"{operation_name}_ERROR", start_time, end_time)
                raise e
        return wrapper
    return decorator
