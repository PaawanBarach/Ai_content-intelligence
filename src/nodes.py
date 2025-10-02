import streamlit as st
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from src.config import get_llm_client, cached_news_search, cached_fact_check, config
from src.error_handler import ErrorHandler, error_boundary
from src.debug_tools import performance_monitor
import json
import re
import time
import random
from typing import Dict, Any, List

def call_llm_with_retry(llm, message, max_retries: int = 4) -> str:
    """Invoke LLM with exponential backoff on rate limits."""
    for attempt in range(max_retries):
        try:
            rsp = llm.invoke([message]).content.strip()
            if rsp:
                return rsp
            raise ValueError("Empty LLM response")
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                wait = min((2 ** attempt) * 2 + random.uniform(0, 1), 60)
                if attempt < max_retries - 1:
                    st.warning(f"⚠️ Rate-limited – retrying in {wait:.1f}s…")
                    time.sleep(wait)
                else:
                    raise e
            else:
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    raise e
    raise RuntimeError("LLM failed after retries")

def extract_json(text: str) -> str:
    """Return substring between first '{' and last '}'."""
    i, j = text.find("{"), text.rfind("}")
    return text[i:j + 1] if i != -1 < j else text

# ---------- Node ----------------------------------------------------
@error_boundary
@performance_monitor("content_analysis")
def content_analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    p = st.empty()
    with p: st.info("🔍 Analysing content…")

    llm = get_llm_client()
    if not llm:
        p.empty()
        return ErrorHandler.handle_api_error(Exception("LLM unavailable"),
                                             "openrouter")

    # ---- Prompt: ask explicitly for JSON-only ----------------------
    prompt = f"""Return valid JSON only – no markdown or prose.

{{
  "content_type": "news|blog|social_media|research|opinion",
  "language": "en",
  "topics": ["t1","t2"],
  "entities": [{{"name":"n","type":"ORG","confidence":0.95}}],
  "sentiment": {{"positive":0,"negative":0,"neutral":1,"confidence":0.9}},
  "summary": "…",
  "key_claims": [],
  "writing_style": "formal|informal"
}}

Analyse: {state['text']}

JSON:"""

    try:
        raw = call_llm_with_retry(llm, HumanMessage(content=prompt))
        cleaned = extract_json(raw)
        data = json.loads(cleaned)

        p.success("✅ Analysis complete")
        time.sleep(0.3); p.empty()

        return {
            "content_type":  data.get("content_type", "unknown"),
            "language":      data.get("language", "en"),
            "topics":        data.get("topics", []),
            "entities":      data.get("entities", []),
            "sentiment":     data.get("sentiment",
                                      {"neutral": 1.0, "confidence": 0.5}),
            "summary":       data.get("summary", ""),
            "key_claims":    data.get("key_claims", []),
            "writing_style": data.get("writing_style", "unknown"),
        }

    except json.JSONDecodeError as e:
        p.empty()
        ErrorHandler.log_error(e, {"component": "content_analysis", "raw_response": raw[:200]})
        # Return minimal valid structure
        return {
            "content_type": "unknown",
            "language": "en",
            "topics": [],
            "entities": [],
            "sentiment": {"neutral": 1.0, "confidence": 0.1},
            "summary": "Analysis failed - JSON parse error",
            "key_claims": [],
            "writing_style": "unknown"
        }
    except Exception as e:
        p.empty()
        if "429" in str(e) or "rate" in str(e).lower():
            st.error("⚠️ Rate limit reached. Please wait before retrying.")
            # Return minimal structure
            return {
                "content_type": "unknown",
                "language": "en",
                "topics": [],
                "entities": [],
                "sentiment": {"neutral": 1.0, "confidence": 0.1},
                "summary": "Analysis paused due to rate limiting",
                "key_claims": [],
                "writing_style": "unknown"
            }
        raise e

@error_boundary
@performance_monitor("verification")
def verification_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced verification with progress tracking"""
    
    progress_placeholder = st.empty()
    with progress_placeholder:
        st.info("🔍 Verifying information with external sources...")
    
    entities = state.get("entities", [])
    topics = state.get("topics", [])
    
    search_query = ""
    if entities and len(entities) > 0:
        # Handle list of entities properly
        if isinstance(entities[0], dict):
            search_query = entities[0].get("name", "")
        else:
            search_query = str(entities[0])
    elif topics and len(topics) > 0:
        search_query = " ".join(topics[:2])  # Use first 2 topics
    else:
        search_query = state.get("text", "")[:50]
    
    if not search_query.strip():
        progress_placeholder.warning("⚠️ No search terms found for verification")
        time.sleep(1)
        progress_placeholder.empty()
        return {
            "fact_check_results": [],
            "similar_articles": [],
            "verification_score": 0.5
        }
    
    verification_progress = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("📰 Searching for related articles...")
        verification_progress.progress(33)
        similar_articles = cached_news_search(search_query)
        
        status_text.text("✅ Checking fact-checkers...")
        verification_progress.progress(66)
        fact_check_results = cached_fact_check(search_query)
        
        status_text.text("📊 Calculating verification score...")
        verification_progress.progress(100)
        
        verification_score = 0.5
        
        if similar_articles:
            verification_score += 0.1
        
        if fact_check_results:
            ratings = [fc.get("rating", "").lower() for fc in fact_check_results]
            if any("true" in rating or "correct" in rating for rating in ratings):
                verification_score += 0.2
            elif any("false" in rating or "incorrect" in rating for rating in ratings):
                verification_score -= 0.3
        
        verification_score = max(0.0, min(1.0, verification_score))
        
        verification_progress.empty()
        status_text.empty()
        progress_placeholder.success("✅ Verification completed!")
        time.sleep(0.5)
        progress_placeholder.empty()
        
        return {
            "fact_check_results": fact_check_results[:3],
            "similar_articles": similar_articles[:3],
            "verification_score": verification_score
        }
        
    except Exception as e:
        verification_progress.empty()
        status_text.empty()
        progress_placeholder.empty()
        ErrorHandler.log_error(e, {"component": "verification"})
        return {
            "fact_check_results": [],
            "similar_articles": [],
            "verification_score": 0.5
        }

@error_boundary
@performance_monitor("risk_assessment")
def risk_assessment_node(state: Dict[str, Any]) -> Dict[str, Any]:
    p = st.empty()
    with p:
        st.info("⚠️  Assessing risk…")

    llm = get_llm_client()
    if not llm:
        p.empty()
        return ErrorHandler.handle_api_error(
            Exception("LLM unavailable"), "openrouter")

    # Prompt: ask ONLY for the JSON object you need
    prompt = (
        "Analyse the following content and return ONLY a JSON object with "
        'exactly these keys: "risk_level" (low|medium|high|critical), '
        '"confidence" (0-1 float), "reason" (short string).\n\n'
        f"Content:\n{state['text']}\n\nJSON:"
    )

    try:
        # No cleaning necessary – model is already in JSON mode
        raw_json = llm.invoke([HumanMessage(content=prompt)]).content
        data     = json.loads(raw_json)     # Guaranteed to parse unless provider fails

        p.success(f"✅ Risk: {data['risk_level'].upper()}")
        time.sleep(0.3); p.empty()

        return {
            "risk_level":        data["risk_level"],
            "risk_score":        1 - data["confidence"],     # keep legacy field
            "confidence_score":  data["confidence"],
            "risk_reason":       data["reason"],
            "misinformation_flags": [],
            "flags_detected":    0,
        }

    except Exception as e:                 # provider error or JSON failure
        p.empty()
        return ErrorHandler.handle_api_error(e, "openrouter")

@error_boundary
def human_review_node(state: Dict[str, Any]) -> Dict[str, Any]:
    if "review_decision" in st.session_state:
        decision = st.session_state.pop("review_decision")
        notes = st.session_state.get("reviewer_notes", "")
        return {
            "human_approval": decision,
            "review_status": "reviewed", 
            "reviewer_notes": notes
        }
    
    risk_level = state.get("risk_level", "low")
    if risk_level == "low":
        return {"human_approval": "auto_approved", "review_status": "no_review_needed", "reviewer_notes": ""}
    
    st.warning(f"Human Review Required - Risk: {risk_level.upper()}")
    st.write(f"**Summary:** {state.get('summary', 'N/A')}")
    
    col1, col2, col3, col4 = st.columns(4)
    if col1.button("✅ Approve", key="app_btn"): st.session_state.review_decision = "approved"; st.rerun()
    if col2.button("❌ Reject", key="rej_btn"): st.session_state.review_decision = "rejected"; st.rerun()  
    if col3.button("📝 Edit", key="edit_btn"): st.session_state.review_decision = "needs_editing"; st.rerun()
    if col4.button("⏭️ Skip", key="skip_btn"): st.session_state.review_decision = "skipped"; st.rerun()
    
    st.text_area("Notes:", key="reviewer_notes", height=80)
    st.stop()

@error_boundary
@performance_monitor("report_generation")
def report_generation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced report generation with comprehensive recommendations"""
    
    progress_placeholder = st.empty()
    with progress_placeholder:
        st.info("📊 Generating comprehensive analysis report...")
    
    risk_level = state.get("risk_level", "unknown")
    approval_status = state.get("human_approval", "auto_approved")
    confidence = state.get("confidence_score", 0)
    
    recommendations = []
    
    if risk_level == "critical":
        recommendations.extend([
            "🚨 **URGENT**: Do not publish without thorough fact-checking",
            "🔍 **VERIFY**: All claims with primary sources",
            "⚠️ **LABEL**: Consider adding content warning if published",
            "📊 **MONITOR**: Track engagement and feedback closely"
        ])
    elif risk_level == "high":
        recommendations.extend([
            "⚠️ **CAUTION**: Additional fact-checking strongly recommended",
            "📋 **REVIEW**: Have second opinion before publication",
            "📊 **TRACK**: Monitor audience response if published"
        ])
    elif risk_level == "medium":
        recommendations.extend([
            "📋 **STANDARD**: Follow normal editorial review process",
            "✅ **MONITOR**: Regular content performance tracking"
        ])
    else:
        recommendations.append("✅ **CLEAR**: Content appears safe for standard publication")
    
    if approval_status == "rejected":
        recommendations.insert(0, "❌ **DO NOT PUBLISH**: Human reviewer has rejected this content")
    elif approval_status == "needs_editing":
        recommendations.insert(0, "📝 **EDIT REQUIRED**: Content flagged for revision before publication")
    elif approval_status == "approved":
        recommendations.insert(0, "✅ **HUMAN APPROVED**: Content has been reviewed and approved")
    
    content_type = state.get("content_type", "unknown")
    if content_type == "news":
        recommendations.append("📰 **NEWS**: Verify publication date and source credibility")
    elif content_type == "research":
        recommendations.append("🔬 **RESEARCH**: Check for peer review and methodology")
    elif content_type == "social_media":
        recommendations.append("📱 **SOCIAL**: Higher scrutiny for viral potential")
    
    entities_list = [e.get("name", "") for e in state.get("entities", [])][:5]
    topics_list = state.get("topics", [])[:3]
    flags_list = state.get("misinformation_flags", [])
    
    report_sections = [
        f"## 📊 **Content Analysis Report**",
        f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Analysis ID:** {st.session_state.get('session_id', 'N/A')}-{int(time.time())}",
        "",
        f"### 🎯 **Risk Assessment**",
        f"- **Risk Level:** {risk_level.upper()} ({'🔴' if risk_level == 'critical' else '🟡' if risk_level == 'high' else '🟢' if risk_level == 'low' else '🟠'})",
        f"- **Confidence Score:** {confidence:.1%}",
        f"- **Verification Score:** {state.get('verification_score', 0):.1%}",
        f"- **Flags Detected:** {len(flags_list)}",
        "",
        f"### 📝 **Content Overview**",
        f"- **Type:** {content_type.title()}",
        f"- **Language:** {state.get('language', 'Unknown')}",
        f"- **Writing Style:** {state.get('writing_style', 'Unknown').title()}",
        f"- **Summary:** {state.get('summary', 'No summary available')}",
        "",
    ]
    
    if entities_list:
        report_sections.extend([
            f"### 🎯 **Key Entities**",
            f"- {', '.join(entities_list)}",
            ""
        ])
    
    if topics_list:
        report_sections.extend([
            f"### 🏷️ **Topics**",
            f"- {', '.join(topics_list)}",
            ""
        ])
    
    if flags_list:
        report_sections.extend([
            f"### ⚠️ **Risk Flags**",
            *[f"- {flag.replace('_', ' ').title()}" for flag in flags_list],
            ""
        ])
    
    similar_articles = state.get("similar_articles", [])
    fact_checks = state.get("fact_check_results", [])
    
    if similar_articles or fact_checks:
        report_sections.extend([
            f"### 🔍 **External Verification**",
            f"- **Related Articles Found:** {len(similar_articles)}",
            f"- **Fact-Check Results:** {len(fact_checks)}",
            ""
        ])
    
    if approval_status != "auto_approved":
        reviewer_notes = state.get("reviewer_notes", "") or st.session_state.get("temp_reviewer_notes", "")
        report_sections.extend([
            f"### 👤 **Human Review**",
            f"- **Status:** {approval_status.replace('_', ' ').title()}",
            f"- **Reviewer Notes:** {reviewer_notes or 'No additional notes'}",
            ""
        ])
    
    final_report = "\n".join(report_sections)
    
    progress_placeholder.success("✅ Report generation completed!")
    time.sleep(0.5)
    progress_placeholder.empty()
    
    return {
        "recommendations": recommendations,
        "final_report": final_report,
        "processing_complete": True,
        "report_timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "processing_time": time.time() - st.session_state.get('analysis_start_time', time.time())
    }
