import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Any
import hashlib
import time
import uuid

class SessionManager:
    """Enhanced session state management with rate limiting"""
    
    @staticmethod
    def init_session():
        """Initialize comprehensive session state"""
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())[:8]
        
        if 'user_preferences' not in st.session_state:
            st.session_state.user_preferences = {
                "risk_tolerance": 0.5,
                "trusted_sources": [],
                "feedback_history": [],
                "analysis_speed": "balanced"  # fast, balanced, thorough
            }
        
        if 'analysis_history' not in st.session_state:
            st.session_state.analysis_history = []
        
        if 'rate_limit_data' not in st.session_state:
            st.session_state.rate_limit_data = {
                "last_analysis_time": 0,
                "analyses_count": 0,
                "daily_reset": datetime.now().date()
            }
        
        if 'app_state' not in st.session_state:
            st.session_state.app_state = {
                "current_analysis": None,
                "processing": False,
                "last_error": None,
                "maintenance_mode": False
            }
    
    @staticmethod
    def check_rate_limit() -> tuple[bool, str]:
        """Enhanced rate limiting with multiple tiers"""
        rate_data = st.session_state.rate_limit_data
        current_time = time.time()
        
        # Reset daily counter
        if rate_data["daily_reset"] != datetime.now().date():
            rate_data["analyses_count"] = 0
            rate_data["daily_reset"] = datetime.now().date()
        
        # Check daily limit (50 analyses per day)
        if rate_data["analyses_count"] >= 50:
            return False, "Daily analysis limit reached (50). Please try again tomorrow."
        
        # Check cooldown period (10 seconds between analyses)
        time_since_last = current_time - rate_data["last_analysis_time"]
        if time_since_last < 10:
            remaining = int(10 - time_since_last)
            return False, f"Please wait {remaining} seconds before next analysis."
        
        # Check burst protection (max 5 analyses in 5 minutes)
        recent_analyses = [t for t in getattr(st.session_state, 'recent_analysis_times', []) 
                          if current_time - t < 300]  # 5 minutes
        
        if len(recent_analyses) >= 5:
            return False, "Too many analyses in a short period. Please wait 5 minutes."
        
        return True, ""
    
    @staticmethod
    def record_analysis():
        """Record successful analysis for rate limiting"""
        current_time = time.time()
        st.session_state.rate_limit_data["last_analysis_time"] = current_time
        st.session_state.rate_limit_data["analyses_count"] += 1
        
        # Track recent analyses for burst protection
        if 'recent_analysis_times' not in st.session_state:
            st.session_state.recent_analysis_times = []
        
        st.session_state.recent_analysis_times.append(current_time)
        
        # Keep only last hour of data
        st.session_state.recent_analysis_times = [
            t for t in st.session_state.recent_analysis_times 
            if current_time - t < 3600
        ]
    
    @staticmethod
    def safe_reset_session():
        """Safely reset session with confirmation"""
        essential_keys = ['session_id', 'user_preferences']
        
        # Store essential data
        backup = {key: st.session_state.get(key) for key in essential_keys}
        
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Restore essential data
        for key, value in backup.items():
            if value is not None:
                st.session_state[key] = value
        
        # Re-initialize
        SessionManager.init_session()
    
    @staticmethod
    def save_analysis_result(result: Dict[str, Any]):
        """Enhanced analysis result saving with metadata"""
        analysis_record = {
            "id": hashlib.md5(f"{datetime.now().isoformat()}{result.get('text', '')[:100]}".encode()).hexdigest()[:8],
            "timestamp": datetime.now().isoformat(),
            "text": result.get("text", "")[:200] + "..." if len(result.get("text", "")) > 200 else result.get("text", ""),
            "risk_level": result.get("risk_level", "unknown"),
            "confidence": result.get("confidence_score", 0),
            "processing_time": result.get("processing_time", 0),
            "api_calls_made": result.get("api_calls_count", 0),
            "human_reviewed": result.get("human_approval", "auto_approved") != "auto_approved"
        }
        
        # Manage history size
        if len(st.session_state.analysis_history) >= 20:
            st.session_state.analysis_history = st.session_state.analysis_history[-19:]
        
        st.session_state.analysis_history.append(analysis_record)
    
    @staticmethod
    def get_usage_stats() -> Dict[str, Any]:
        """Get comprehensive usage statistics"""
        rate_data = st.session_state.rate_limit_data
        
        return {
            "analyses_today": rate_data["analyses_count"],
            "daily_limit": 50,
            "remaining_today": 50 - rate_data["analyses_count"],
            "total_session_analyses": len(st.session_state.analysis_history),
            "session_duration": str(datetime.now() - datetime.fromisoformat(
                st.session_state.debug_info.get("session_start", datetime.now().isoformat())
            )).split('.')[0] if 'debug_info' in st.session_state else "Unknown"
        }

def calculate_risk_score(flags: List[str], confidence: float, user_tolerance: float = 0.5) -> tuple[str, float]:
    """Enhanced risk calculation with user tolerance adjustment"""
    base_risk = len(flags) * 0.2
    adjusted_risk = base_risk * (2 - user_tolerance)  # User tolerance affects sensitivity
    risk_score = min(adjusted_risk * (1 - confidence * 0.3), 1.0)
    
    if risk_score >= 0.8:
        return "critical", risk_score
    elif risk_score >= 0.6:
        return "high", risk_score
    elif risk_score >= 0.3:
        return "medium", risk_score
    else:
        return "low", risk_score
