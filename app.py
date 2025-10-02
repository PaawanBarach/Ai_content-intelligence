import json
from typing import Dict, List, Any
import streamlit as st
import sys
import os
import time
from datetime import datetime
import hashlib

# Add src to Python path
sys.path.insert(0, os.path.dirname(__file__))

from src.workflow import create_workflow as create_workflow_func, ContentState
from src.utils import SessionManager
from src.config import Config, config
from src.error_handler import ErrorHandler
from src.debug_tools import DebugTools

@st.cache_resource
def get_compiled_workflow():
    """Get cached compiled workflow"""
    from src.workflow import create_workflow
    return create_workflow()

# Page configuration
st.set_page_config(
    page_title="AI Content Intelligence Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .risk-low { background: linear-gradient(90deg, #d4edda, #c3e6cb); color: #155724; padding: 1rem; border-radius: 0.5rem; }
    .risk-medium { background: linear-gradient(90deg, #fff3cd, #ffeaa7); color: #856404; padding: 1rem; border-radius: 0.5rem; }
    .risk-high { background: linear-gradient(90deg, #f8d7da, #fab1a0); color: #721c24; padding: 1rem; border-radius: 0.5rem; }
    .risk-critical { background: linear-gradient(90deg, #dc3545, #e17055); color: white; padding: 1rem; border-radius: 0.5rem; }
    .metric-card { background: #f8f9fa; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #007bff; }
    .status-good { color: #28a745; }
    .status-warning { color: #ffc107; }
    .status-error { color: #dc3545; }
</style>
""", unsafe_allow_html=True)

def initialize_app():
    """Initialize application with comprehensive setup"""
    try:
        # Initialize session management
        SessionManager.init_session()
        DebugTools.init_debug_session()
        
        # Validate configuration
        validation_results = Config.validate_config()
        
        # Store validation results for sidebar
        st.session_state.config_validation = validation_results
        
        return True
        
    except Exception as e:
        ErrorHandler.log_error(e, {"component": "app_initialization"})
        st.error(f"🚨 Application initialization failed: {str(e)}")
        return False

def render_enhanced_sidebar():
    """Render comprehensive sidebar with all tools"""
    with st.sidebar:
        st.header("🎛️ **Control Panel**")
        
        # Quick Actions
        st.subheader("⚡ Quick Actions")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Reset Session", help="Clear all session data"):
                if st.button("✅ Confirm Reset", key="confirm_reset"):
                    SessionManager.safe_reset_session()
                    st.success("Session reset!")
                    st.experimental_rerun()
        
        with col2:
            if st.button("🧹 Clear Cache", help="Clear API response cache"):
                st.cache_data.clear()
                st.success("Cache cleared!")
        
        # Configuration Status
        st.subheader("🔌 **API Status**")
        validation_results = st.session_state.get('config_validation', {})
        
        status_items = [
            ("OpenRouter API", validation_results.get('openrouter_key', False), validation_results.get('openrouter_api', False)),
            ("News API", validation_results.get('news_api_key', False), validation_results.get('news_api', False)),
            ("Google Fact Check", validation_results.get('google_api_key', False), validation_results.get('google_api', False))
        ]
        
        for name, has_key, api_working in status_items:
            if has_key and api_working:
                st.markdown(f'<span class="status-good">✅ {name}</span>', unsafe_allow_html=True)
            elif has_key:
                st.markdown(f'<span class="status-warning">⚠️ {name} (Key OK, API Issues)</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="status-error">❌ {name}</span>', unsafe_allow_html=True)
        
        # User Preferences
        st.subheader("⚙️ **Preferences**")
        
        # Risk tolerance
        risk_tolerance = st.slider(
            "Risk Tolerance",
            0.0, 1.0,
            st.session_state.user_preferences.get("risk_tolerance", 0.5),
            0.1,
            help="Higher = more tolerant of risky content"
        )
        st.session_state.user_preferences["risk_tolerance"] = risk_tolerance
        
        # Analysis speed
        analysis_speed = st.selectbox(
            "Analysis Depth",
            ["fast", "balanced", "thorough"],
            index=["fast", "balanced", "thorough"].index(
                st.session_state.user_preferences.get("analysis_speed", "balanced")
            ),
            help="Fast: Quick analysis, Thorough: Detailed analysis with human review"
        )
        st.session_state.user_preferences["analysis_speed"] = analysis_speed
        
        # Usage Statistics
        st.subheader("📊 **Usage Stats**")
        usage_stats = SessionManager.get_usage_stats()
        
        for key, value in usage_stats.items():
            display_key = key.replace('_', ' ').title()
            st.write(f"**{display_key}:** {value}")
        
        # Rate Limiting Status
        analyses_remaining = usage_stats.get('remaining_today', 0)
        if analyses_remaining <= 5:
            st.warning(f"⚠️ Only {analyses_remaining} analyses remaining today")
        
        # Debug Tools
        DebugTools.display_debug_panel()
        
        # Error Log
        ErrorHandler.display_error_summary()
        
        # Analysis History
        if st.session_state.analysis_history:
            with st.expander("📈 **Analysis History**", expanded=False):
                st.write(f"**Total Analyses:** {len(st.session_state.analysis_history)}")
                
                for i, analysis in enumerate(reversed(st.session_state.analysis_history[-5:])):
                    risk_color = {
                        'low': '🟢', 'medium': '🟡', 'high': '🟠', 'critical': '🔴'
                    }.get(analysis['risk_level'], '⚪')
                    
                    st.write(f"{risk_color} **Analysis {i+1}**")
                    st.write(f"  Risk: {analysis['risk_level']}")
                    st.write(f"  Time: {analysis['timestamp'][:16]}")
                    
                    if st.checkbox(f"Show details {i+1}", key=f"history_{i}"):
                        st.write(f"  Text: {analysis['text']}")
                        st.write(f"  Confidence: {analysis['confidence']:.1%}")

def main():
    """Enhanced main application with comprehensive error handling"""
    
    # Global error boundary
    try:
        # Initialize application
        if not initialize_app():
            st.stop()
        
        # Render sidebar
        render_enhanced_sidebar()
        
        # Main header
        st.markdown('<h1 class="main-header">🔍 AI Content Intelligence Platform</h1>', unsafe_allow_html=True)
        st.markdown("**Enterprise-grade content analysis with AI-powered risk assessment and fact-checking**")
        
        # Check for maintenance mode
        if st.session_state.app_state.get("maintenance_mode", False):
            st.error("🚧 **Maintenance Mode**: The platform is currently under maintenance. Please try again later.")
            st.stop()
        
        # Main application tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📝 Content Analysis", 
            "📊 Workflow", 
            "🎯 Demo Content", 
            "📚 Help & Documentation"
        ])
        
        with tab1:
            render_content_analysis_tab()
        
        with tab2:
            render_workflow()
        
        with tab3:
            render_demo_content_tab()
        
        with tab4:
            render_help_tab()
    
    except Exception as e:
        # Global error handler
        ErrorHandler.log_error(e, {"component": "main_application"})
        
        st.error("🚨 **Application Error Occurred**")
        st.write("The application encountered an unexpected error. Our team has been notified.")
        
        with st.expander("🔍 **Error Details** (for debugging)", expanded=False):
            st.write(f"**Error Type:** {type(e).__name__}")
            st.write(f"**Error Message:** {str(e)}")
            st.write(f"**Time:** {datetime.now().isoformat()}")
        
        # Recovery options
        st.write("### 🔧 **Recovery Options:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh Page"):
                st.experimental_rerun()
        
        with col2:
            if st.button("🧹 Reset Session"):
                SessionManager.safe_reset_session()
                st.experimental_rerun()
        
        with col3:
            if st.button("📞 Report Issue"):
                st.info("Please contact support with the error details above.")

def render_content_analysis_tab():
    """Enhanced content analysis tab with comprehensive features"""
    
    st.header("📝 **Single Content Analysis**")
    
    # Check rate limiting first
    can_analyze, rate_message = SessionManager.check_rate_limit()
    
    if not can_analyze:
        st.warning(f"⏱️ **Rate Limited**: {rate_message}")
        return
    
    # Input methods
    input_method = st.radio(
        "**Choose Input Method:**",
        ["✏️ Text Input", "🔗 URL Input", "📁 File Upload"],
        horizontal=True
    )
    
    content_text = ""
    source_url = ""
    
    if input_method == "✏️ Text Input":
        content_text = st.text_area(
            "**Enter content to analyze:**",
            value=st.session_state.get('selected_demo_content', ''),
            height=200,
            placeholder="Paste your content here...",
            help="Enter any text content for analysis (news articles, social media posts, blog content, etc.)"
        )
        source_url = st.text_input(
            "**Source URL (Optional):**",
            placeholder="https://example.com/article",
            help="Original URL of the content (if available)"
        )
    
    elif input_method == "🔗 URL Input":
        source_url = st.text_input(
            "**Enter Article URL:**",
            placeholder="https://example.com/article",
            help="URL will be processed to extract content"
        )
        if source_url:
            st.info("📝 **Note**: URL content extraction is not implemented in this demo. Please copy and paste the content manually.")
    
    else:  # File Upload
        uploaded_file = st.file_uploader(
            "**Upload Text File:**",
            type=['txt', 'md'],
            help="Upload a text file for analysis"
        )
        if uploaded_file:
            try:
                content_text = str(uploaded_file.read(), "utf-8")
                st.success(f"✅ File uploaded: {uploaded_file.name}")
                st.text_area("**File Content Preview:**", content_text[:500] + "..." if len(content_text) > 500 else content_text, height=100)
            except Exception as e:
                st.error(f"❌ Failed to read file: {str(e)}")
    
    # Analysis options
    with st.expander("🎛️ **Advanced Options**", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            force_human_review = st.checkbox(
                "Force Human Review",
                help="Require human review regardless of risk level"
            )
        
        with col2:
            include_external_verification = st.checkbox(
                "Include External Verification",
                value=True,
                help="Check external sources for verification (uses API calls)"
            )
    
    # Analysis button
    analyze_button = st.button(
        "🔍 **Start Analysis**",
        type="primary",
        disabled=not content_text or st.session_state.app_state.get("processing", False),
        help="Begin comprehensive content analysis"
    )
    
    if analyze_button:
        if not content_text.strip():
            st.error("❌ Please provide content to analyze")
            return
        
        if not config.OPENROUTER_API_KEY:
            st.error("❌ OpenRouter API key is required for analysis")
            return
        
        # Start analysis
        perform_content_analysis(content_text, source_url, force_human_review, include_external_verification)

def perform_content_analysis(content_text: str, source_url: str, force_human_review: bool, include_external_verification: bool):
    """Perform comprehensive content analysis with progress tracking"""
    
    # Set processing state
    st.session_state.app_state["processing"] = True
    st.session_state.analysis_start_time = time.time()
    
    try:
        # Create initial state
        initial_state = {
            "text": content_text,
            "source_url": source_url or "",
            "force_human_review": force_human_review,
            "include_external_verification": include_external_verification
        }
        
        # Main progress container
        progress_container = st.container()
        
        with progress_container:
            # Overall progress
            st.subheader("🚀 **Analysis in Progress**")
            overall_progress = st.progress(0)
            
            # Status updates
            status_placeholder = st.empty()
            
            # Initialize workflow
            status_placeholder.info("⚙️ Initializing analysis workflow...")
            overall_progress.progress(10)
            
            workflow_app = get_compiled_workflow()
            
            if not workflow_app:
                raise Exception("Failed to initialize workflow")
            
            # Execute workflow
            status_placeholder.info("🤖 Running AI analysis pipeline...")
            overall_progress.progress(30)
            
            result = workflow_app.invoke(initial_state)
            
            # Check for human review interruption
            if st.session_state.get('human_review_pending', False):
                status_placeholder.warning("⏳ Analysis paused for human review...")
                overall_progress.progress(80)
                return  # Exit to allow human review
            
            # Complete analysis
            overall_progress.progress(100)
            status_placeholder.success("✅ Analysis completed successfully!")
            
            # Record successful analysis
            SessionManager.record_analysis()
            
            # Add processing metadata
            result["processing_time"] = time.time() - st.session_state.analysis_start_time
            result["text"] = content_text  # Preserve original text
            result["api_calls_count"] = getattr(st.session_state, 'api_calls_count', 0)
            
            # Save results
            SessionManager.save_analysis_result(result)
            
            # Update debug info
            if 'debug_info' in st.session_state:
                st.session_state.debug_info["total_analyses"] += 1
            
            # Display results
            time.sleep(1)  # Brief pause for UX
            progress_container.empty()  # Clear progress indicators
            
            display_comprehensive_results(result)
    
    except Exception as e:
        ErrorHandler.log_error(e, {"component": "content_analysis", "content_length": len(content_text)})
        
        st.error(f"❌ **Analysis Failed**: {str(e)}")
        
        # Show recovery options
        st.write("### 🔧 **Recovery Options:**")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Retry Analysis"):
                st.experimental_rerun()
        
        with col2:
            if st.button("🎯 Focus on Essential Analysis"):
                # Retry with minimal features
                st.session_state.app_state["processing"] = False
                st.experimental_rerun()
    
    finally:
        # Reset processing state
        st.session_state.app_state["processing"] = False

def display_comprehensive_results(result: Dict[str, Any]):
    """Display comprehensive analysis results with enhanced UI"""
    
    st.success("🎉 **Analysis Complete!**")
    
    # Risk Level Header with enhanced styling
    risk_level = result.get('risk_level', 'unknown')
    confidence = result.get('confidence_score', 0)
    processing_time = result.get('processing_time', 0)
    
    risk_colors = {
        'low': 'risk-low',
        'medium': 'risk-medium',
        'high': 'risk-high', 
        'critical': 'risk-critical'
    }
    
    risk_emoji = {
        'low': '🟢',
        'medium': '🟡',
        'high': '🟠',
        'critical': '🔴'
    }
    
    st.markdown(f"""
    <div class="{risk_colors.get(risk_level, '')}">
        <h2>{risk_emoji.get(risk_level, '⚪')} Risk Level: {risk_level.upper()}</h2>
        <p><strong>Confidence:</strong> {confidence:.1%} | <strong>Processing Time:</strong> {processing_time:.1f}s</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Key Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Content Type", result.get('content_type', 'unknown').title())
    
    
    with col2:
        st.metric("Entities Found", len(result.get('entities', [])))
    with col3:
        st.metric("Verification Score", f"{result.get('verification_score', 0):.1%}")
    
    with col4:
        flags_count = len(result.get('misinformation_flags', []))
        st.metric("Warning Flags", flags_count, delta=f"-{flags_count}" if flags_count > 0 else "0")
    
    with col5:
        api_calls = result.get('api_calls_count', 0)
        st.metric("API Calls Made", api_calls)
    
    # Detailed Analysis Sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Analysis Details",
        "🚨 Risk Assessment", 
        "🔍 Verification Results",
        "📄 Full Report"
    ])
    
    with tab1:
        render_analysis_details_tab(result)
    
    with tab2:
        render_risk_assessment_tab(result)
    
    with tab3:
        render_verification_results_tab(result)
    
    with tab4:
        render_full_report_tab(result)
    
    # Action Buttons
    st.markdown("---")
    st.subheader("📤 **Export & Actions**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        export_data = {k: v for k, v in result.items() if k != 'text'}  # Exclude full text
        st.download_button(
            "📊 Export JSON",
            data=json.dumps(export_data, indent=2),
            file_name=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            key="download_json"
        )
    
    with col2:
        # Generate CSV data
        csv_lines = [
            "Field,Value",
            f"Risk Level,{result.get('risk_level', 'unknown')}",
            f"Confidence,{result.get('confidence_score', 0):.1%}",
            f"Verification Score,{result.get('verification_score', 0):.1%}",
            f"Content Type,{result.get('content_type', 'unknown')}",
            f"Processing Time,{result.get('processing_time', 0):.1f}s",
            f"Entities Found,{len(result.get('entities', []))}",
            f"Flags Detected,{len(result.get('misinformation_flags', []))}"
        ]
        csv_content = "\n".join(csv_lines)
        st.download_button(
            "📝 Export CSV",
            data=csv_content,
            file_name=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key="download_csv"
        )
    
    with col3:
        if st.button("🔄 **Analyze Similar**"):
            # Store current content for similar analysis
            st.session_state['similar_base_content'] = result.get('text', '')
            st.session_state['similar_base_entities'] = result.get('entities', [])
            st.success("✅ Content stored. Enter similar text in the analysis tab.")
    
    with col4:
        if st.button("📊 **View Trends**"):
            # Show analysis trends from history
            if st.session_state.analysis_history:
                render_trends_modal(st.session_state.analysis_history)
            else:
                st.info("No analysis history available for trends")
    
    # Feedback Section
    render_feedback_section(result)

def render_analysis_details_tab(result: Dict[str, Any]):
    """Render detailed analysis information"""
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("🎯 **Key Information**")
        
        # Content Summary
        summary = result.get('summary', 'No summary available')
        st.info(f"**Summary:** {summary}")
        
        # Entities
        entities = result.get('entities', [])
        if entities:
            st.write("**🎯 Key Entities:**")
            for entity in entities[:8]:  # Show up to 8 entities
                confidence_bar = "█" * int(entity.get('confidence', 0) * 10)
                st.write(f"-  **{entity.get('name')}** ({entity.get('type')}) {confidence_bar} {entity.get('confidence', 0):.1%}")
        else:
            st.write("**🎯 Key Entities:** None detected")
        
        # Topics
        topics = result.get('topics', [])
        if topics:
            st.write("**🏷️ Topics:**")
            topic_tags = " ".join([f"`{topic}`" for topic in topics])
            st.markdown(topic_tags)
        else:
            st.write("**🏷️ Topics:** None identified")
    
    with col_right:
        st.subheader("😊 **Sentiment Analysis**")
        
        sentiment = result.get('sentiment', {})
        if sentiment:
            # Create sentiment visualization
            sentiment_data = {k: v for k, v in sentiment.items() if k != 'confidence'}
            
            if sentiment_data:
                # Display sentiment scores
                for emotion, score in sentiment_data.items():
                    st.write(f"**{emotion.title()}:** {score:.1%}")
                    st.progress(score)
                
                st.write(f"**Confidence:** {sentiment.get('confidence', 0):.1%}")
            else:
                st.write("Sentiment analysis unavailable")
        else:
            st.write("No sentiment data available")
        
        # Additional metadata
        st.subheader("📋 **Metadata**")
        st.write(f"**Language:** {result.get('language', 'Unknown')}")
        st.write(f"**Writing Style:** {result.get('writing_style', 'Unknown').title()}")
        st.write(f"**Content Length:** {len(result.get('text', ''))} characters")

def render_risk_assessment_tab(result: Dict[str, Any]):
    """Render comprehensive risk assessment information"""
    
    st.subheader("⚠️ **Risk Analysis**")
    
    # Risk Overview
    risk_level = result.get('risk_level', 'unknown')
    confidence = result.get('confidence_score', 0)
    risk_score = result.get('risk_score', 0)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Risk Level", risk_level.upper())
    with col2:
        st.metric("Risk Score", f"{risk_score:.2f}")
    with col3:
        st.metric("Confidence", f"{confidence:.1%}")
    
    # Warning Flags
    flags = result.get('misinformation_flags', [])
    
    if flags:
        st.subheader("🚩 **Warning Flags Detected**")
        
        flag_descriptions = {
            "conspiracy_language": "Contains language typical of conspiracy theories",
            "sensational_language": "Uses sensational or exaggerated language",
            "anti_establishment": "Shows anti-establishment rhetoric",
            "media_distrust": "Expresses distrust of mainstream media",
            "urgency_manipulation": "Uses urgency to manipulate reader response",
            "miracle_claims": "Makes claims about miracle cures or solutions",
            "absolute_certainty": "Uses absolute certainty language inappropriately",
            "clickbait_indicators": "Contains clickbait-style language",
            "low_verification_score": "Could not be verified with external sources",
            "uncertain_sentiment_analysis": "Sentiment analysis showed low confidence",
            "no_external_corroboration": "No external sources found to support claims"
        }
        
        for flag in flags:
            flag_display = flag.replace('_', ' ').title()
            description = flag_descriptions.get(flag, "Potential risk indicator detected")
            
            st.warning(f"**{flag_display}**")
            st.write(f"  ↳ {description}")
    else:
        st.success("✅ **No Risk Flags Detected**")
        st.write("The content appears to be free of common misinformation indicators.")
    
    # Human Review Status
    human_approval = result.get('human_approval', 'auto_approved')
    reviewer_notes = result.get('reviewer_notes', '')
    
    if human_approval != 'auto_approved':
        st.subheader("👤 **Human Review Results**")
        
        approval_status = {
            'approved': ('✅', 'Content approved by human reviewer'),
            'rejected': ('❌', 'Content rejected by human reviewer'),
            'needs_editing': ('📝', 'Content flagged for editing'),
            'review_skipped': ('⏭️', 'Human review was skipped')
        }
        
        emoji, description = approval_status.get(human_approval, ('❓', 'Unknown review status'))
        
        st.write(f"{emoji} **Status:** {description}")
        
        if reviewer_notes:
            st.write(f"**Reviewer Notes:** {reviewer_notes}")

def render_verification_results_tab(result: Dict[str, Any]):
    """Render external verification results"""
    
    st.subheader("🔍 **External Verification**")
    
    verification_score = result.get('verification_score', 0)
    similar_articles = result.get('similar_articles', [])
    fact_checks = result.get('fact_check_results', [])
    
    # Verification Overview
    st.metric("Overall Verification Score", f"{verification_score:.1%}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📰 **Related Articles**")
        
        if similar_articles:
            for i, article in enumerate(similar_articles, 1):
                with st.expander(f"Article {i}: {article.get('title', 'Untitled')}", expanded=False):
                    if article.get('description'):
                        st.write(f"**Description:** {article['description']}")
                    if article.get('publishedAt'):
                        st.write(f"**Published:** {article['publishedAt'][:10]}")
                    if article.get('url'):
                        st.write(f"**Source:** {article['url']}")
        else:
            st.info("No related articles found")
    
    with col2:
        st.subheader("✅ **Fact-Check Results**")
        
        if fact_checks:
            for i, fact_check in enumerate(fact_checks, 1):
                with st.expander(f"Fact-Check {i}: {fact_check.get('text', 'No title')[:50]}...", expanded=False):
                    if fact_check.get('claimant'):
                        st.write(f"**Claimant:** {fact_check['claimant']}")
                    if fact_check.get('rating'):
                        rating = fact_check['rating']
                        if 'true' in rating.lower() or 'correct' in rating.lower():
                            st.success(f"**Rating:** {rating}")
                        elif 'false' in rating.lower() or 'incorrect' in rating.lower():
                            st.error(f"**Rating:** {rating}")
                        else:
                            st.warning(f"**Rating:** {rating}")
                    if fact_check.get('url'):
                        st.write(f"**Source:** {fact_check['url']}")
        else:
            st.info("No fact-check results found")

def render_full_report_tab(result: Dict[str, Any]):
    """Render the complete analysis report"""
    
    st.subheader("📄 **Complete Analysis Report**")
    
    report_text = result.get('final_report', 'No report available')
    
    # Display the full report
    st.markdown(report_text)
    
    # Recommendations
    recommendations = result.get('recommendations', [])
    
    if recommendations:
        st.subheader("🎯 **AI Recommendations**")
        
        for rec in recommendations:
            if rec.startswith('🚨') or rec.startswith('❌'):
                st.error(rec)
            elif rec.startswith('⚠️') or rec.startswith('📝'):
                st.warning(rec)
            elif rec.startswith('✅') or rec.startswith('🟢'):
                st.success(rec)
            else:
                st.info(rec)

def render_trends_modal(history: List[Dict[str, Any]]):
    """Display analysis trends from history"""
    with st.expander("📈 **Analysis Trends**", expanded=True):
        if len(history) > 1:
            # Risk level distribution
            risk_counts = {}
            for h in history:
                risk = h.get('risk_level', 'unknown')
                risk_counts[risk] = risk_counts.get(risk, 0) + 1
            
            st.subheader("🎯 Risk Level Distribution")
            for risk, count in sorted(risk_counts.items()):
                pct = (count / len(history)) * 100
                st.write(f"{risk.upper()}: {count} ({pct:.0f}%)")
                st.progress(pct / 100)
            
            # Average metrics
            avg_confidence = sum(h.get('confidence', 0) for h in history) / len(history)
            avg_time = sum(h.get('processing_time', 0) for h in history) / len(history)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Avg Confidence", f"{avg_confidence:.1%}")
            with col2:
                st.metric("Avg Processing Time", f"{avg_time:.1f}s")
            
            # Timeline
            st.subheader("📅 Recent Activity")
            for h in history[-5:]:
                st.write(f"- {h['timestamp'][:16]} | Risk: {h['risk_level']} | Confidence: {h['confidence']:.0%}")

def render_feedback_section(result: Dict[str, Any]):
    """Render user feedback collection section"""
    
    st.markdown("---")
    st.subheader("💬 **Help Us Improve**")
    st.write("Your feedback helps improve our AI analysis accuracy.")
    
    with st.expander("📝 **Provide Feedback**", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            accuracy_rating = st.select_slider(
                "How accurate was this analysis?",
                options=['Very Poor', 'Poor', 'Fair', 'Good', 'Excellent'],
                value='Good',
                key="accuracy_feedback"
            )
            
            usefulness_rating = st.select_slider(
                "How useful were the recommendations?",
                options=['Not Useful', 'Somewhat Useful', 'Very Useful'],
                value='Somewhat Useful',
                key="usefulness_feedback"
            )
        
        with col2:
            feedback_category = st.selectbox(
                "Feedback Category:",
                ["General", "False Positive", "False Negative", "Missing Information", "UI/UX", "Performance"],
                key="feedback_category"
            )
            
            would_recommend = st.radio(
                "Would you recommend this tool?",
                ["Yes", "No", "Maybe"],
                horizontal=True,
                key="recommend_feedback"
            )
        
        feedback_notes = st.text_area(
            "Additional Comments (Optional):",
            placeholder="Tell us what we can improve...",
            key="feedback_notes"
        )
        
        if st.button("📤 **Submit Feedback**", type="primary"):
            feedback_data = {
                "accuracy": accuracy_rating,
                "usefulness": usefulness_rating,
                "category": feedback_category,
                "would_recommend": would_recommend,
                "notes": feedback_notes,
                "analysis_id": result.get('report_timestamp', ''),
                "timestamp": datetime.now().isoformat()
            }
            
            # Store feedback in session state
            if 'user_feedback' not in st.session_state:
                st.session_state.user_feedback = []
            
            st.session_state.user_feedback.append(feedback_data)
            
            # Update user preferences feedback history
            st.session_state.user_preferences['feedback_history'].append(feedback_data)
            
            st.success("🎉 Thank you for your feedback! It helps us improve our AI models.")

def render_workflow():
    """Render workflow graph"""
    
    st.subheader("Processing Workflow")
    try:
        st.image("images/workflow.png", use_container_width=True)
    except Exception as e:
        st.error("Workflow chart unavailable")
        st.text("Content Input → AI Analysis → Risk Assessment → Verification → Human Review → Export")

    
    st.subheader("📁 **Upload Content**")
    
    upload_method = st.radio(
        "Choose upload method:",
        ["📄 CSV File", "🔗 RSS Feed", "📂 Multiple Files"],
        horizontal=True
    )
    
    if upload_method == "📄 CSV File":
        st.write("Upload a CSV file with columns: 'content', 'source_url', 'title'")
        uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
        
        if uploaded_file:
            st.warning("Batch processing not yet implemented")
    
    elif upload_method == "🔗 RSS Feed":
        rss_url = st.text_input("RSS Feed URL:", placeholder="https://example.com/feed.xml")
        max_articles = st.slider("Maximum Articles to Process:", 1, 50, 10)
        
        if rss_url and st.button("📥 Fetch RSS Feed"):
            st.warning("RSS processing not yet implemented")
    
    else:  # Multiple Files
        uploaded_files = st.file_uploader(
            "Upload Text Files",
            type=['txt', 'md'],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.write(f"📁 {len(uploaded_files)} files uploaded")
            st.warning("Multi-file processing not yet implemented")

def render_demo_content_tab():
    """Render demo content for testing"""
    
    st.header("🎯 **Demo Content**")
    st.write("Try the analysis with these carefully crafted sample contents:")
    
    demo_contents = {
        "📰 **Legitimate News**": {
            "content": """Scientists at Stanford University have published new research in the journal Nature showing that machine learning algorithms can predict protein folding with 90% accuracy. The breakthrough, led by Dr. Sarah Chen's team, could accelerate drug discovery processes by reducing the time needed to understand protein structures from months to days. The research was peer-reviewed and replicated by independent teams at MIT and Oxford.""",
            "risk": "low"
        },
        
        "🚨 **High-Risk Content**": {
            "content": """URGENT: Secret government documents LEAKED! Scientists don't want you to know this shocking truth about vaccines that big pharma is hiding. Mainstream media won't report this amazing discovery that will change everything. Doctors hate this one simple trick that can cure any disease instantly. Click here before they remove this exclusive revelation!""",
            "risk": "critical"
        },
        
        "📱 **Social Media Misinformation**": {
            "content": """OMG guys!!! Just heard from my friend who works at Apple that they're releasing iPhone 16 next week with holographic display and teleportation features! The government is trying to hide this technology but it's finally happening! Share before they delete this post! #iPhone16 #Conspiracy #Truth""",
            "risk": "high"
        },
        
        "📚 **Academic Research**": {
            "content": """This longitudinal study (n=1,247) examined the correlation between social media usage and academic performance among college students over 24 months. Using regression analysis, we found a statistically significant negative correlation (r=-0.34, p<0.001) between daily social media time and GPA. Limitations include self-reported data and potential confounding variables.""",
            "risk": "low"
        },
        
        "🤔 **Misleading But Subtle**": {
            "content": """New study reveals that drinking 8 glasses of water daily might be completely unnecessary for most people. Many health experts are now questioning this long-held belief, with some suggesting that forcing water consumption could actually be harmful. The beverage industry has been promoting excessive water intake for profit.""",
            "risk": "medium"
        }
    }
    
    for title, demo_data in demo_contents.items():
        with st.expander(title, expanded=False):
            st.write(f"**Expected Risk Level:** {demo_data['risk'].title()}")
            st.write("**Content:**")
            st.text_area("", demo_data['content'], height=100, key=f"demo_{title}", disabled=True)
            
            if st.button(f"🔍 Analyze This Content", key=f"analyze_{title}"):
                # Set the content for analysis
                st.session_state.selected_demo_content = demo_data['content']
                st.session_state.demo_source_url = f"demo://content/{title.replace(' ', '_').lower()}"
                st.success(f"✅ Demo content loaded! Switch to the 'Content Analysis' tab to process it.")

def render_help_tab():
    """Render help and documentation"""
    
    st.header("📚 **Help & Documentation**")
    
    help_tabs = st.tabs(["🚀 Getting Started", "🔧 Troubleshooting", "📊 Understanding Results", "🛡️ Privacy & Security"])
    
    with help_tabs[0]:
        st.subheader("🚀 **Getting Started**")
        
        st.markdown("""
        ### **How to Use This Platform**
        
        1. **📝 Input Content**: Enter text, URL, or upload a file
        2. **⚙️ Configure Settings**: Adjust risk tolerance and analysis depth in the sidebar
        3. **🔍 Run Analysis**: Click the analyze button to start processing
        4. **👤 Review Results**: For high-risk content, provide human review when prompted
        5. **📊 Interpret Results**: Review the comprehensive analysis and recommendations
        
        ### **Key Features**
        
        - **🤖 AI-Powered Analysis**: Advanced content classification and entity extraction
        - **🔍 Fact-Checking**: Cross-references with external sources and fact-checkers
        - **⚠️ Risk Assessment**: Identifies potential misinformation indicators
        - **👤 Human-in-the-Loop**: Requires human review for high-risk content
        - **📊 Comprehensive Reports**: Detailed analysis with actionable recommendations
        
        ### **Best Practices**
        
        - Provide source URLs when available for better verification
        - Use thorough analysis mode for important content
        - Always review AI recommendations critically
        - Consider context and intent when interpreting results
        """)
    
    with help_tabs[1]:
        st.subheader("🔧 **Troubleshooting**")
        
        st.markdown("""
        ### **Common Issues**
        
        **❌ "OpenRouter API key required"**
        - Ensure you have set the OPENROUTER_API_KEY in your environment
        - Check the API status in the sidebar
        
        **⏱️ Rate limit errors**
        - Wait for the cooldown period (shown in sidebar)
        - You have 50 analyses per day on the free tier
        
        **🐌 Slow processing**
        - DeepSeek-R1 can take 30-60 seconds for complex analysis
        - Try "fast" analysis mode for quicker results
        
        **❌ Analysis fails**
        - Check your internet connection
        - Try with shorter content (under 2000 characters)
        - Use the "Reset Session" button if issues persist
        
        ### **Performance Tips**
        
        - Use shorter content for faster processing
        - Disable external verification if APIs are slow
        - Clear cache regularly using the sidebar button
        """)
    
    with help_tabs[2]:
        st.subheader("📊 **Understanding Results**")
        
        st.markdown("""
        ### **Risk Levels**
        
        🟢 **Low Risk**: Content appears reliable and well-sourced
        🟡 **Medium Risk**: Some concerns detected, standard review recommended
        🟠 **High Risk**: Multiple risk indicators, human review required
        🔴 **Critical Risk**: High likelihood of misinformation, urgent review needed
        
        ### **Key Metrics**
        
        **Confidence Score**: How certain the AI is about its analysis (higher = more certain)
        **Verification Score**: How well the content can be verified with external sources
        **Warning Flags**: Specific indicators of potential misinformation
        
        ### **Common Warning Flags**
        
        - **Conspiracy Language**: "secret", "they don't want you to know"
        - **Sensational Language**: "shocking", "amazing", "unbelievable"
        - **Urgency Manipulation**: "urgent", "before they remove this"
        - **Miracle Claims**: "instant cure", "guaranteed results"
        - **Low Verification**: Cannot be confirmed with external sources
        """)
    
    with help_tabs[3]:
        st.subheader("🛡️ **Privacy & Security**")
        
        st.markdown("""
        ### **Data Handling**
        
        - **No Persistent Storage**: Your content is not permanently stored
        - **Session-Based**: Data is cleared when you close the browser
        - **API Calls**: Content is sent to OpenRouter and external APIs for analysis
        - **No User Tracking**: We don't track personal information
        
        ### **Security Measures**
        
        - All API communications use HTTPS encryption
        - No content is logged permanently
        - Session data is isolated per user
        - Error logs contain no personal information
        
        ### **Recommendations**
        
        - Don't analyze highly sensitive or confidential content
        - Use your own API keys for production use
        - Review and clear session data regularly
        - Be aware that content is processed by external AI services
        """)

# Add this to handle demo content selection
def handle_demo_content():
    """Handle demo content selection from other tabs"""
    if 'selected_demo_content' in st.session_state:
        return st.session_state.selected_demo_content, st.session_state.get('demo_source_url', '')
    return "", ""

if __name__ == "__main__":
    main()
