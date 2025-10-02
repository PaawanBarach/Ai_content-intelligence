from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Literal, Any
import streamlit as st
from src.nodes import (
    content_analysis_node,
    verification_node,
    risk_assessment_node,
    human_review_node,
    report_generation_node
)
from src.error_handler import ErrorHandler

class ContentState(TypedDict):
    # Input
    text: str
    source_url: str
    force_human_review: bool
    include_external_verification: bool
    
    # Analysis Results
    content_type: str
    language: str
    topics: List[str]
    entities: List[Dict[str, Any]]
    sentiment: Dict[str, float]
    summary: str
    key_claims: List[str]
    writing_style: str
    
    # Verification
    fact_check_results: List[Dict[str, Any]]
    similar_articles: List[Dict[str, Any]]
    verification_score: float
    
    # Risk Assessment
    misinformation_flags: List[str]
    risk_level: Literal["low", "medium", "high", "critical"]
    confidence_score: float
    risk_score: float
    flags_detected: int
    
    # Human Review
    human_approval: str
    review_status: str
    reviewer_notes: str
    
    # Final Output
    recommendations: List[str]
    final_report: str
    processing_complete: bool
    report_timestamp: str
    processing_time: float

def route_by_content_complexity(state: ContentState) -> str:
    """Route based on content complexity and user preferences"""
    
    # Check if forced human review
    if state.get("force_human_review", False):
        return "verification"
    
    # Route based on content length and type
    text_length = len(state.get("text", ""))
    content_type = state.get("content_type", "unknown")
    
    # Long content or research papers get full verification
    if text_length > 1000 or content_type == "research":
        return "verification"
    
    # Social media content always gets verification due to viral potential
    if content_type == "social_media":
        return "verification"
    
    # All other content gets verification (for this demo)
    return "verification"

def route_by_risk_level(state: ContentState) -> str:
    """Enhanced routing based on risk level and user preferences"""
    
    risk_level = state.get("risk_level", "low")
    force_review = state.get("force_human_review", False)
    
    # Critical and high risk always require human review
    if risk_level in ["critical", "high"] or force_review:
        return "human_review"
    
    # Medium risk with thorough analysis mode requires review
    # ✅ FIXED: Add safety check for session_state
    try:
        analysis_speed = st.session_state.user_preferences.get("analysis_speed", "balanced")
    except (AttributeError, KeyError):
        analysis_speed = "balanced"  # Default fallback
    
    if risk_level == "medium" and analysis_speed == "thorough":
        return "human_review"
    
    # Otherwise proceed to report generation
    return "generate_report"


def should_include_verification(state: ContentState) -> str:
    """Determine if external verification should be included"""
    
    # Check user preference
    if not state.get("include_external_verification", True):
        return "risk_assessment"
    
    # Always verify high-risk indicators
    text_lower = state.get("text", "").lower()
    high_risk_keywords = ["breaking", "exclusive", "leaked", "secret", "shocking"]
    
    if any(keyword in text_lower for keyword in high_risk_keywords):
        return "verification"
    
    # Check if we have entities to verify
    if state.get("entities", []):
        return "verification"
    
    # Skip verification for obvious low-risk content
    return "risk_assessment"

def create_workflow():
    """Create enhanced workflow with comprehensive error handling"""
    
    try:
        workflow = StateGraph(ContentState)
        
        # Add all processing nodes
        workflow.add_node("content_analysis", content_analysis_node)
        workflow.add_node("verification", verification_node)
        workflow.add_node("risk_assessment", risk_assessment_node)
        workflow.add_node("human_review", human_review_node)
        workflow.add_node("generate_report", report_generation_node)
        
        # Set entry point
        workflow.set_entry_point("content_analysis")
        
        # Content analysis always goes to verification check
        workflow.add_conditional_edges(
            "content_analysis",
            should_include_verification,
            {
                "verification": "verification",
                "risk_assessment": "risk_assessment"
            }
        )
        
        # Verification goes to risk assessment
        workflow.add_edge("verification", "risk_assessment")
        
        # Risk assessment routes based on risk level
        workflow.add_conditional_edges(
            "risk_assessment",
            route_by_risk_level,
            {
                "human_review": "human_review",
                "generate_report": "generate_report"
            }
        )
        
        # Human review goes to report generation
        workflow.add_edge("human_review", "generate_report")
        
        # Report generation is the end
        workflow.add_edge("generate_report", END)
        
        compiled_workflow = workflow.compile()
        
        # Debug: Confirm what we're returning
        print(f"🐛 create_workflow returning: {type(compiled_workflow)}")
        
        return compiled_workflow
        
    except Exception as e:
        # Manual error handling instead of decorator
        print(f"❌ Error creating workflow: {e}")
        ErrorHandler.log_error(e, {"component": "workflow_creation"})
        return None

