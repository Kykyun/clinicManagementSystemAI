import os
import time
import json
import logging
from typing import Optional, Dict, Any, Tuple
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)

AI_DISCLAIMER = "This is an AI-generated suggestion for clinician support only and must be reviewed by a qualified healthcare professional."


class AIService:
    def __init__(self):
        self.client = None
        self.config = None
        self._initialize()
    
    def _initialize(self):
        from .models import AIConfig
        self.config = AIConfig.get_config()
        api_key = os.environ.get('OPENAI_API_KEY')
        if api_key:
            self.client = OpenAI(api_key=api_key)
    
    def is_enabled(self, feature: str = None) -> bool:
        if not self.client:
            return False
        if not self.config.is_enabled:
            return False
        if feature:
            feature_field = f"{feature}_enabled"
            return getattr(self.config, feature_field, True)
        return True
    
    def _truncate_text(self, text: str, max_length: int = 500) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
    
    def _log_request(self, user, action: str, input_text: str, output_text: str = "", 
                     status: str = "success", tokens: int = 0, response_time: int = 0, 
                     error: str = ""):
        from .models import AILog
        try:
            AILog.objects.create(
                user=user,
                action=action,
                status=status,
                input_summary=self._truncate_text(input_text),
                output_summary=self._truncate_text(output_text),
                tokens_used=tokens,
                response_time_ms=response_time,
                error_message=error
            )
        except Exception as e:
            logger.error(f"Failed to log AI request: {e}")
    
    def _call_openai(self, messages: list, user=None, action: str = "assistant", 
                     max_tokens: int = None) -> Tuple[bool, str, Dict]:
        if not self.is_enabled():
            return False, "AI features are not enabled", {}
        
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                max_tokens=max_tokens or self.config.max_tokens,
                temperature=float(self.config.temperature)
            )
            
            response_time = int((time.time() - start_time) * 1000)
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            
            self._log_request(
                user=user,
                action=action,
                input_text=str(messages[-1].get('content', ''))[:500],
                output_text=content[:500] if content else "",
                tokens=tokens,
                response_time=response_time
            )
            
            return True, content, {"tokens": tokens, "response_time": response_time}
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            status = "error"
            if "rate" in error_msg.lower():
                status = "rate_limited"
            elif "timeout" in error_msg.lower():
                status = "timeout"
            
            self._log_request(
                user=user,
                action=action,
                input_text=str(messages[-1].get('content', ''))[:500] if messages else "",
                status=status,
                response_time=response_time,
                error=error_msg[:500]
            )
            
            logger.error(f"OpenAI API error: {e}")
            return False, f"AI service error: {error_msg}", {}


def ai_suggest_triage(complaint_text: str, user=None) -> Dict[str, Any]:
    service = AIService()
    if not service.is_enabled('triage'):
        return {"success": False, "error": "Triage AI is not enabled"}
    
    prompt = f"""Analyze this patient complaint and provide triage classification.

Complaint: {complaint_text}

Respond in JSON format:
{{
    "urgency": "low|medium|high|emergency",
    "urgency_reason": "brief explanation",
    "suggested_department": "General Practice|Pediatrics|Obstetrics|Emergency|etc",
    "estimated_duration_minutes": 10|20|30|45|60,
    "key_symptoms": ["symptom1", "symptom2"]
}}

Only respond with valid JSON, no additional text."""

    messages = [
        {"role": "system", "content": "You are a medical triage assistant. Classify patient complaints by urgency and suggest appropriate department routing. Be conservative - when in doubt, classify as higher urgency."},
        {"role": "user", "content": prompt}
    ]
    
    success, response, meta = service._call_openai(messages, user, "triage", max_tokens=500)
    
    if not success:
        return {"success": False, "error": response, "disclaimer": AI_DISCLAIMER}
    
    try:
        result = json.loads(response)
        result["success"] = True
        result["disclaimer"] = AI_DISCLAIMER
        return result
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse AI response", "raw_response": response, "disclaimer": AI_DISCLAIMER}


def ai_structure_consultation_notes(raw_notes: str, user=None) -> Dict[str, Any]:
    service = AIService()
    if not service.is_enabled('consultation_notes'):
        return {"success": False, "error": "Consultation notes AI is not enabled"}
    
    prompt = f"""Structure these clinical notes into a proper medical consultation format.

Raw Notes:
{raw_notes}

Respond in JSON format:
{{
    "history": "Patient history and chief complaint",
    "examination": "Physical examination findings",
    "assessment": "Clinical assessment and possible diagnoses",
    "plan": "Treatment plan and follow-up",
    "suggested_icd10_codes": [
        {{"code": "J06.9", "description": "Acute upper respiratory infection"}}
    ]
}}

Only respond with valid JSON. The ICD-10 codes are suggestions only."""

    messages = [
        {"role": "system", "content": "You are a medical documentation assistant. Structure clinical notes into standard SOAP/consultation format. Suggest relevant ICD-10 codes as hints only - final coding must be done by the clinician."},
        {"role": "user", "content": prompt}
    ]
    
    success, response, meta = service._call_openai(messages, user, "consultation_notes")
    
    if not success:
        return {"success": False, "error": response, "disclaimer": AI_DISCLAIMER}
    
    try:
        result = json.loads(response)
        result["success"] = True
        result["disclaimer"] = AI_DISCLAIMER
        return result
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse AI response", "raw_response": response, "disclaimer": AI_DISCLAIMER}


def ai_summarize_medical_history(patient_data: Dict, user=None) -> Dict[str, Any]:
    service = AIService()
    if not service.is_enabled('medical_summary'):
        return {"success": False, "error": "Medical summary AI is not enabled"}
    
    prompt = f"""Summarize this patient's medical history concisely for quick clinical reference.

Patient Data:
- Name: {patient_data.get('name', 'Unknown')}
- Age: {patient_data.get('age', 'Unknown')}
- Gender: {patient_data.get('gender', 'Unknown')}
- Allergies: {patient_data.get('allergies', 'None recorded')}
- Chronic Illnesses: {patient_data.get('chronic_illnesses', 'None recorded')}
- Recent Visits: {patient_data.get('recent_visits', 'None')}
- Current Medications: {patient_data.get('medications', 'None recorded')}
- Lab Results: {patient_data.get('lab_results', 'None')}

Respond in JSON format:
{{
    "key_chronic_conditions": ["condition1", "condition2"],
    "recent_acute_issues": ["issue1", "issue2"],
    "important_allergies": ["allergy1"],
    "current_medications_summary": "Brief medication summary",
    "clinical_alerts": ["Any important alerts for the clinician"],
    "summary_paragraph": "A brief 2-3 sentence clinical summary"
}}

Only respond with valid JSON."""

    messages = [
        {"role": "system", "content": "You are a medical summarization assistant. Create concise, clinically relevant summaries of patient medical histories. Highlight important information that a clinician needs to know quickly."},
        {"role": "user", "content": prompt}
    ]
    
    success, response, meta = service._call_openai(messages, user, "medical_summary")
    
    if not success:
        return {"success": False, "error": response, "disclaimer": AI_DISCLAIMER}
    
    try:
        result = json.loads(response)
        result["success"] = True
        result["disclaimer"] = AI_DISCLAIMER
        return result
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse AI response", "raw_response": response, "disclaimer": AI_DISCLAIMER}


def ai_draft_referral_letter(patient_data: Dict, referral_data: Dict, user=None) -> Dict[str, Any]:
    service = AIService()
    if not service.is_enabled('referral_letter'):
        return {"success": False, "error": "Referral letter AI is not enabled"}
    
    prompt = f"""Draft a professional medical referral letter.

Patient Information:
- Name: {patient_data.get('name')}
- Age: {patient_data.get('age')}
- ID: {patient_data.get('id_number')}

Referral Details:
- Referring Doctor: {referral_data.get('referring_doctor')}
- Referred To: {referral_data.get('referred_to')}
- Specialty: {referral_data.get('specialty')}
- Reason: {referral_data.get('reason')}
- Clinical Notes: {referral_data.get('clinical_notes')}
- Diagnosis: {referral_data.get('diagnosis')}
- Treatment Given: {referral_data.get('treatment')}

Respond in JSON format:
{{
    "salutation": "Dear Dr. [Name] / Dear Colleague",
    "body": "The main body of the referral letter - professional, concise, and clinically relevant",
    "closing": "Thank you for seeing this patient. Please do not hesitate to contact us if you require further information."
}}

Only respond with valid JSON."""

    messages = [
        {"role": "system", "content": "You are a medical letter writing assistant. Draft professional, concise referral letters that effectively communicate patient information between healthcare providers."},
        {"role": "user", "content": prompt}
    ]
    
    success, response, meta = service._call_openai(messages, user, "referral_letter")
    
    if not success:
        return {"success": False, "error": response, "disclaimer": AI_DISCLAIMER}
    
    try:
        result = json.loads(response)
        result["success"] = True
        result["disclaimer"] = AI_DISCLAIMER
        return result
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse AI response", "raw_response": response, "disclaimer": AI_DISCLAIMER}


def ai_suggest_stock_order(stock_data: list, user=None) -> Dict[str, Any]:
    service = AIService()
    if not service.is_enabled('stock_suggestion'):
        return {"success": False, "error": "Stock suggestion AI is not enabled"}
    
    stock_summary = "\n".join([
        f"- {item['name']}: Current={item['current']}, Min={item['min_level']}, Avg Daily Use={item.get('avg_daily', 'N/A')}"
        for item in stock_data[:20]
    ])
    
    prompt = f"""Analyze stock levels and suggest reorder quantities.

Current Stock Status:
{stock_summary}

Respond in JSON format:
{{
    "suggestions": [
        {{
            "item_name": "Item Name",
            "current_stock": 50,
            "suggested_order": 200,
            "reasoning": "Brief explanation of why this quantity",
            "priority": "high|medium|low"
        }}
    ],
    "summary": "Overall stock status summary"
}}

Only respond with valid JSON. Focus on items below minimum level first."""

    messages = [
        {"role": "system", "content": "You are an inventory management assistant. Analyze stock levels and suggest optimal reorder quantities based on current stock, minimum levels, and usage patterns."},
        {"role": "user", "content": prompt}
    ]
    
    success, response, meta = service._call_openai(messages, user, "stock_suggestion")
    
    if not success:
        return {"success": False, "error": response}
    
    try:
        result = json.loads(response)
        result["success"] = True
        return result
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse AI response", "raw_response": response}


def ai_generate_dashboard_insights(clinic_data: Dict, user=None) -> Dict[str, Any]:
    service = AIService()
    if not service.is_enabled('dashboard_insights'):
        return {"success": False, "error": "Dashboard insights AI is not enabled"}
    
    prompt = f"""Generate brief, actionable insights from this clinic data.

Clinic Statistics:
- Today's Visits: {clinic_data.get('today_visits', 0)}
- 7-Day Average Visits: {clinic_data.get('avg_7day_visits', 0)}
- Today's Revenue: {clinic_data.get('today_revenue', 0)}
- 7-Day Average Revenue: {clinic_data.get('avg_7day_revenue', 0)}
- Top Conditions This Week: {clinic_data.get('top_conditions', [])}
- Top Medicines This Week: {clinic_data.get('top_medicines', [])}
- Pending Appointments: {clinic_data.get('pending_appointments', 0)}
- Low Stock Items: {clinic_data.get('low_stock_count', 0)}

Respond in JSON format:
{{
    "insights": [
        {{
            "type": "trend|alert|info",
            "icon": "chart-line|exclamation-triangle|info-circle",
            "title": "Brief title",
            "message": "Insight message (1-2 sentences max)"
        }}
    ]
}}

Provide 3-5 most relevant insights. Only respond with valid JSON."""

    messages = [
        {"role": "system", "content": "You are a clinic management analytics assistant. Generate brief, actionable insights that help clinic managers understand trends and take action."},
        {"role": "user", "content": prompt}
    ]
    
    success, response, meta = service._call_openai(messages, user, "dashboard_insight", max_tokens=800)
    
    if not success:
        return {"success": False, "error": response}
    
    try:
        result = json.loads(response)
        result["success"] = True
        return result
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse AI response", "raw_response": response}


def ai_chat_assistant(message: str, context: str = "", user=None) -> Dict[str, Any]:
    service = AIService()
    if not service.is_enabled('assistant'):
        return {"success": False, "error": "AI Assistant is not enabled"}
    
    system_prompt = """You are a helpful AI assistant for a clinic management system. You can:
1. Answer questions about how to use the system
2. Explain features and workflows
3. Provide general guidance on clinic operations
4. Help interpret data summaries (but never provide medical advice)

Important rules:
- Never provide medical diagnoses or treatment recommendations
- Never access or modify patient data directly
- Always encourage users to consult qualified healthcare professionals for clinical decisions
- Be concise and helpful"""

    if context:
        system_prompt += f"\n\nCurrent context:\n{context}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]
    
    success, response, meta = service._call_openai(messages, user, "assistant")
    
    if not success:
        return {"success": False, "error": response}
    
    return {"success": True, "response": response}


def ai_forecast_revenue(historical_data: list, days: int = 7, user=None) -> Dict[str, Any]:
    service = AIService()
    if not service.is_enabled('revenue_forecast'):
        return {"success": False, "error": "Revenue forecast AI is not enabled"}
    
    data_summary = "\n".join([
        f"- {item['date']}: Visits={item['visits']}, Revenue={item['revenue']}"
        for item in historical_data[-30:]
    ])
    
    prompt = f"""Analyze historical clinic data and forecast the next {days} days.

Historical Data (last 30 days):
{data_summary}

Respond in JSON format:
{{
    "forecast": [
        {{"date": "YYYY-MM-DD", "predicted_visits": 25, "predicted_revenue": 1500}}
    ],
    "trend": "increasing|stable|decreasing",
    "confidence": "high|medium|low",
    "factors": ["Key factors influencing the forecast"]
}}

Only respond with valid JSON."""

    messages = [
        {"role": "system", "content": "You are a business analytics assistant. Analyze historical clinic data to forecast future visits and revenue. Consider day-of-week patterns, trends, and seasonality."},
        {"role": "user", "content": prompt}
    ]
    
    success, response, meta = service._call_openai(messages, user, "revenue_forecast")
    
    if not success:
        return {"success": False, "error": response}
    
    try:
        result = json.loads(response)
        result["success"] = True
        return result
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse AI response", "raw_response": response}


def ai_detect_anomalies(transaction_data: list, user=None) -> Dict[str, Any]:
    service = AIService()
    if not service.is_enabled('anomaly_detection'):
        return {"success": False, "error": "Anomaly detection AI is not enabled"}
    
    data_summary = "\n".join([
        f"- {item['date']} {item['type']}: {item['amount']} by {item.get('user', 'Unknown')}"
        for item in transaction_data[-50:]
    ])
    
    prompt = f"""Analyze these financial transactions for potential anomalies.

Recent Transactions:
{data_summary}

Respond in JSON format:
{{
    "anomalies": [
        {{
            "severity": "high|medium|low",
            "description": "What was detected",
            "recommendation": "Suggested action"
        }}
    ],
    "summary": "Overall assessment of transaction patterns"
}}

Only flag genuinely unusual patterns. Respond with valid JSON only."""

    messages = [
        {"role": "system", "content": "You are a financial auditing assistant. Analyze transaction patterns to identify potential anomalies like unusual amounts, frequency patterns, or suspicious activities. Be balanced - flag genuine concerns without excessive false positives."},
        {"role": "user", "content": prompt}
    ]
    
    success, response, meta = service._call_openai(messages, user, "anomaly_detection")
    
    if not success:
        return {"success": False, "error": response}
    
    try:
        result = json.loads(response)
        result["success"] = True
        return result
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse AI response", "raw_response": response}
