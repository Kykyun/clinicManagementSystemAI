import os
import time
import json
import logging
from typing import Optional, Dict, Any, Tuple
from google import genai
from google.genai import types
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
        api_key = os.environ.get('GEMINI_API_KEY')
        if api_key:
            self.client = genai.Client(api_key=api_key)
    
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
    
    def _clean_json_response(self, text: str) -> str:
        """Remove markdown code blocks from JSON responses."""
        import re
        text = text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return text.strip()
    
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
    
    def _call_gemini(self, messages: list, user=None, action: str = "assistant", 
                     max_tokens: int = None) -> Tuple[bool, str, Dict]:
        if not self.is_enabled():
            return False, "AI features are not enabled", {}
        
        start_time = time.time()
        system_instruction = None
        input_summary = ""
        
        try:
            contents = []
            for msg in messages:
                role = msg.get('role', '')
                content_text = msg.get('content', '')
                
                if role == 'system':
                    system_instruction = content_text
                elif role == 'user':
                    contents.append(types.Content(
                        role='user',
                        parts=[types.Part.from_text(text=content_text)]
                    ))
                    input_summary = content_text[:500]
                elif role == 'assistant':
                    contents.append(types.Content(
                        role='model',
                        parts=[types.Part.from_text(text=content_text)]
                    ))
            
            config = types.GenerateContentConfig(
                max_output_tokens=max_tokens or self.config.max_tokens,
                temperature=float(self.config.temperature),
                system_instruction=system_instruction if system_instruction else None,
            )
            
            response = self.client.models.generate_content(
                model=self.config.model_name,
                contents=contents,
                config=config
            )
            
            response_time = int((time.time() - start_time) * 1000)
            
            content = ""
            try:
                # Try response.text first (new SDK format)
                if hasattr(response, 'text') and response.text:
                    content = response.text
                # Fallback to candidates extraction
                elif hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            part = candidate.content.parts[0]
                            if hasattr(part, 'text'):
                                content = part.text or ""
                
                if not content:
                    # Log detailed response structure for debugging
                    logger.warning(f"Empty content from response. Response type: {type(response)}")
                    if hasattr(response, 'candidates'):
                        logger.warning(f"Candidates: {response.candidates}")
            except Exception as text_err:
                logger.error(f"Could not extract text from response: {text_err}")
                logger.error(f"Response object: {response}")
                content = ""
            
            tokens = 0
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                tokens = getattr(response.usage_metadata, 'total_token_count', 0) or 0
            
            self._log_request(
                user=user,
                action=action,
                input_text=input_summary,
                output_text=content[:500] if content else "",
                tokens=tokens,
                response_time=response_time
            )
            
            return True, content, {"tokens": tokens, "response_time": response_time}
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            status = "error"
            if "rate" in error_msg.lower() or "quota" in error_msg.lower():
                status = "rate_limited"
            elif "timeout" in error_msg.lower():
                status = "timeout"
            
            self._log_request(
                user=user,
                action=action,
                input_text=input_summary,
                status=status,
                response_time=response_time,
                error=error_msg[:500]
            )
            
            logger.error(f"Gemini API error: {e}")
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
    
    success, response, meta = service._call_gemini(messages, user, "triage", max_tokens=500)
    
    if not success:
        return {"success": False, "error": response, "disclaimer": AI_DISCLAIMER}
    
    try:
        result = json.loads(service._clean_json_response(response))
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
Also extract any vital signs mentioned in the notes.

Raw Notes:
{raw_notes}

Respond in JSON format:
{{
    "history": "Patient history and chief complaint",
    "examination": "Physical examination findings",
    "assessment": "Clinical assessment and possible diagnoses",
    "plan": "Treatment plan and follow-up",
    "vitals": {{
        "bp": "systolic/diastolic format like 120/80 if found, otherwise null",
        "pulse": numeric pulse rate if found (e.g., 72), otherwise null,
        "temp": numeric temperature in Celsius if found (e.g., 37.5), otherwise null,
        "weight": numeric weight in kg if found, otherwise null,
        "height": numeric height in cm if found, otherwise null
    }},
    "suggested_icd10_codes": [
        {{"code": "J06.9", "description": "Acute upper respiratory infection"}}
    ]
}}

Look for vital signs in keywords like: BP, Blood Pressure, PR, Pulse, HR, Heart Rate, Temp, Temperature, Weight, Height.
Common patterns: "BP 120/80", "PR 72 bpm", "Temp 37.5C", "Weight 70kg".
Only respond with valid JSON. The ICD-10 codes are suggestions only."""

    messages = [
        {"role": "system", "content": "You are a medical documentation assistant. Structure clinical notes into standard SOAP/consultation format. Extract vital signs from the notes carefully. Suggest relevant ICD-10 codes as hints only - final coding must be done by the clinician."},
        {"role": "user", "content": prompt}
    ]
    
    success, response, meta = service._call_gemini(messages, user, "consultation_notes")
    
    if not success:
        return {"success": False, "error": response, "disclaimer": AI_DISCLAIMER}
    
    try:
        result = json.loads(service._clean_json_response(response))
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
    
    success, response, meta = service._call_gemini(messages, user, "medical_summary")
    
    if not success:
        return {"success": False, "error": response, "disclaimer": AI_DISCLAIMER}
    
    try:
        result = json.loads(service._clean_json_response(response))
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
    
    success, response, meta = service._call_gemini(messages, user, "referral_letter")
    
    if not success:
        return {"success": False, "error": response, "disclaimer": AI_DISCLAIMER}
    
    try:
        result = json.loads(service._clean_json_response(response))
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
    
    success, response, meta = service._call_gemini(messages, user, "stock_suggestion")
    
    if not success:
        return {"success": False, "error": response}
    
    try:
        result = json.loads(service._clean_json_response(response))
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
    
    success, response, meta = service._call_gemini(messages, user, "dashboard_insight", max_tokens=800)
    
    if not success:
        return {"success": False, "error": response}
    
    if not response or not response.strip():
        return {"success": False, "error": "AI returned an empty response. Please try again."}
    
    try:
        cleaned = service._clean_json_response(response)
        result = json.loads(cleaned)
        result["success"] = True
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse dashboard insights response: {e}")
        logger.error(f"Raw response: {response[:500] if response else 'None'}")
        return {"success": False, "error": f"Failed to parse AI response: {str(e)}", "raw_response": response[:300] if response else ""}


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
    
    success, response, meta = service._call_gemini(messages, user, "assistant")
    
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
    
    success, response, meta = service._call_gemini(messages, user, "revenue_forecast")
    
    if not success:
        return {"success": False, "error": response}
    
    try:
        result = json.loads(service._clean_json_response(response))
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
    
    success, response, meta = service._call_gemini(messages, user, "anomaly_detection")
    
    if not success:
        return {"success": False, "error": response}
    
    try:
        result = json.loads(service._clean_json_response(response))
        result["success"] = True
        return result
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse AI response", "raw_response": response}


def ai_suggest_prescriptions(consultation_data: Dict, available_medicines: list, user=None) -> Dict[str, Any]:
    """Suggest prescriptions based on consultation diagnosis and available medicines."""
    service = AIService()
    if not service.is_enabled('assistant'):
        return {"success": False, "error": "AI prescription suggestions are not enabled"}
    
    if available_medicines:
        medicines_list = "\n".join([
            f"- {med['name']} ({med.get('generic_name', '')}) - {med.get('strength', '')} {med.get('form', '')}"
            for med in available_medicines[:100]
        ])
    else:
        medicines_list = "No medicines currently in the clinic inventory. You may suggest common medicines and set is_new_medicine to true for all."
    
    prompt = f"""Based on this consultation, suggest appropriate prescriptions.

Patient Details:
- Age: {consultation_data.get('patient_age', 'Unknown')}
- Gender: {consultation_data.get('patient_gender', 'Unknown')}
- Allergies: {consultation_data.get('allergies', 'None known')}

Consultation:
- Chief Complaint: {consultation_data.get('chief_complaint', '')}
- Diagnosis: {consultation_data.get('diagnosis', '')}
- Treatment Plan: {consultation_data.get('treatment_plan', '')}
- Vitals: BP {consultation_data.get('bp', '-')}, Pulse {consultation_data.get('pulse', '-')}

Available Medicines in Clinic:
{medicines_list}

Respond in JSON format:
{{
    "prescriptions": [
        {{
            "medicine_name": "Medicine name (must match available medicines if possible)",
            "generic_name": "Generic name",
            "dosage": "e.g., 500mg, 10ml",
            "frequency": "e.g., BD (twice daily), TDS (three times daily), OD (once daily)",
            "duration": "e.g., 3 days, 5 days, 1 week",
            "quantity": numeric quantity to dispense,
            "instructions": "Any special instructions",
            "is_new_medicine": true if medicine not in available list or false if it exists
        }}
    ],
    "clinical_notes": "Brief explanation of prescription choices",
    "warnings": ["Any drug interaction or allergy warnings"]
}}

Important:
1. Match medicine names to the available medicines list when possible
2. If a required medicine is not available, set is_new_medicine to true
3. Use standard medical abbreviations: OD (once daily), BD (twice daily), TDS (three times daily), QID (four times daily), PRN (as needed)
4. Consider patient allergies and contraindications

Only respond with valid JSON."""

    messages = [
        {"role": "system", "content": "You are a clinical pharmacology assistant. Suggest appropriate prescriptions based on the diagnosis. Match medicines to the clinic's available inventory when possible. Use standard medical dosing conventions and consider patient factors like age, allergies, and vital signs. Keep your response concise - suggest only 2-3 essential medications."},
        {"role": "user", "content": prompt}
    ]
    
    success, response, meta = service._call_gemini(messages, user, "prescription_suggestions", max_tokens=2000)
    
    if not success:
        return {"success": False, "error": response}
    
    if not response or not response.strip():
        return {"success": False, "error": "AI returned an empty response. Please try again."}
    
    try:
        cleaned_response = service._clean_json_response(response)
        result = json.loads(cleaned_response)
        result["success"] = True
        result["disclaimer"] = "AI-suggested prescriptions require clinician review. Verify dosages and check for contraindications."
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse prescription AI response: {e}")
        logger.error(f"Raw response: {response[:500] if response else 'None'}")
        return {"success": False, "error": f"Failed to parse AI response. The AI may have returned an invalid format.", "raw_response": response[:500] if response else ""}
