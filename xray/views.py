from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
import json
import os
import base64

from .models import XrayStudy, XrayImage, XrayDocument, XrayAIAnalysis, XrayReport
from .forms import XrayStudyForm, XrayImageForm, XrayDocumentForm, XrayReportForm
from patients.models import Patient


@login_required
def xray_dashboard(request):
    studies = XrayStudy.objects.select_related('patient', 'requesting_doctor').all()
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        studies = studies.filter(status=status_filter)
    
    priority_filter = request.GET.get('priority', '')
    if priority_filter:
        studies = studies.filter(priority=priority_filter)
    
    search = request.GET.get('search', '')
    if search:
        studies = studies.filter(
            Q(patient__name__icontains=search) |
            Q(patient__ic_number__icontains=search) |
            Q(clinical_indication__icontains=search)
        )
    
    pending_count = XrayStudy.objects.filter(status='pending').count()
    ai_analyzed_count = XrayStudy.objects.filter(status='ai_analyzed').count()
    urgent_count = XrayStudy.objects.filter(priority__in=['urgent', 'stat'], status='pending').count()
    
    context = {
        'studies': studies[:50],
        'pending_count': pending_count,
        'ai_analyzed_count': ai_analyzed_count,
        'urgent_count': urgent_count,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'search': search,
    }
    return render(request, 'xray/dashboard.html', context)


@login_required
def xray_new(request):
    patients = Patient.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        form = XrayStudyForm(request.POST)
        if form.is_valid():
            study = form.save(commit=False)
            study.requesting_doctor = request.user
            study.save()
            messages.success(request, 'X-ray study created successfully. You can now upload images.')
            return redirect('xray:detail', pk=study.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = XrayStudyForm()
    
    context = {
        'form': form,
        'patients': patients,
    }
    return render(request, 'xray/new_study.html', context)


@login_required
def xray_detail(request, pk):
    study = get_object_or_404(XrayStudy.objects.select_related('patient', 'requesting_doctor', 'radiographer', 'reporting_doctor'), pk=pk)
    images = study.images.all()
    documents = study.documents.all()
    
    ai_analysis = getattr(study, 'ai_analysis', None)
    report = getattr(study, 'report', None)
    
    image_form = XrayImageForm()
    document_form = XrayDocumentForm()
    
    if report:
        report_form = XrayReportForm(instance=report)
    elif ai_analysis:
        report_form = XrayReportForm(initial={
            'findings': ai_analysis.findings,
            'impression': ai_analysis.impression,
            'recommendations': ai_analysis.recommendations,
        })
    else:
        report_form = XrayReportForm()
    
    context = {
        'study': study,
        'images': images,
        'documents': documents,
        'ai_analysis': ai_analysis,
        'report': report,
        'image_form': image_form,
        'document_form': document_form,
        'report_form': report_form,
    }
    return render(request, 'xray/study_detail.html', context)


@login_required
def upload_image(request, pk):
    study = get_object_or_404(XrayStudy, pk=pk)
    
    if request.method == 'POST':
        form = XrayImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.study = study
            image.save()
            messages.success(request, 'X-ray image uploaded successfully.')
        else:
            messages.error(request, 'Failed to upload image. Please try again.')
    
    return redirect('xray:detail', pk=pk)


@login_required
def upload_document(request, pk):
    study = get_object_or_404(XrayStudy, pk=pk)
    
    if request.method == 'POST':
        form = XrayDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.study = study
            doc.save()
            messages.success(request, 'Document uploaded successfully.')
        else:
            messages.error(request, 'Failed to upload document. Please try again.')
    
    return redirect('xray:detail', pk=pk)


@login_required
def ai_analyze(request, pk):
    study = get_object_or_404(XrayStudy, pk=pk)
    images = study.images.all()
    
    if not images.exists():
        messages.error(request, 'Please upload at least one X-ray image before requesting AI analysis.')
        return redirect('xray:detail', pk=pk)
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
        
        system_prompt = """You are an AI radiology assistant integrated into a clinic information system.
Your purpose is to support doctors and radiographers in reviewing and interpreting X-ray studies.

IMPORTANT: You do NOT replace a radiologist or doctor. You provide decision support only, never a final diagnosis.
Always remind the user that your output is preliminary and must be confirmed by a qualified healthcare professional.

For each X-ray case, provide analysis in this exact JSON format:
{
    "case_summary": "Brief case summary with patient info and study type",
    "technical_assessment": "Evaluate image quality - positioning, exposure, coverage, artifacts",
    "findings": "Detailed systematic review by anatomical region with normal and abnormal findings",
    "impression": "1-3 most likely diagnoses or main concerns",
    "recommendations": "Non-prescriptive follow-up suggestions",
    "red_flags": ["List of any urgent/red-flag findings"],
    "confidence_level": "high/medium/low"
}

Be systematic, thorough, and always err on the side of caution."""
        
        patient = study.patient
        case_info = f"""
Patient Information:
- Age: {patient.age if hasattr(patient, 'age') else 'Unknown'}
- Sex: {patient.gender if hasattr(patient, 'gender') else 'Unknown'}

Study Information:
- Body Region: {study.get_body_region_display()}
- View Type: {study.get_view_type_display()}
- Side: {study.get_side_display()}
- Priority: {study.get_priority_display()}

Clinical Indication: {study.clinical_indication}
Clinical History: {study.clinical_history or 'Not provided'}

Please analyze the attached X-ray image(s) and provide your assessment.
"""
        
        contents = [case_info]
        
        for img in images:
            try:
                with open(img.image.path, 'rb') as f:
                    image_data = f.read()
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                    
                    ext = img.image.name.split('.')[-1].lower()
                    mime_type = 'image/jpeg'
                    if ext == 'png':
                        mime_type = 'image/png'
                    elif ext == 'gif':
                        mime_type = 'image/gif'
                    
                    contents.append(types.Part.from_bytes(data=image_data, mime_type=mime_type))
            except Exception as e:
                print(f"Error loading image: {e}")
                continue
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
                max_output_tokens=2000,
            )
        )
        
        response_text = response.text
        
        try:
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            analysis_data = json.loads(response_text)
        except json.JSONDecodeError:
            analysis_data = {
                'case_summary': '',
                'technical_assessment': '',
                'findings': response_text,
                'impression': '',
                'recommendations': '',
                'red_flags': [],
                'confidence_level': 'medium'
            }
        
        ai_analysis, created = XrayAIAnalysis.objects.update_or_create(
            study=study,
            defaults={
                'case_summary': analysis_data.get('case_summary', ''),
                'technical_assessment': analysis_data.get('technical_assessment', ''),
                'findings': analysis_data.get('findings', ''),
                'impression': analysis_data.get('impression', ''),
                'recommendations': analysis_data.get('recommendations', ''),
                'red_flags': analysis_data.get('red_flags', []),
                'confidence_level': analysis_data.get('confidence_level', 'medium'),
                'raw_response': response.text,
            }
        )
        
        study.status = 'ai_analyzed'
        study.save()
        
        messages.success(request, 'AI analysis completed successfully.')
        
    except Exception as e:
        messages.error(request, f'AI analysis failed: {str(e)}')
    
    return redirect('xray:detail', pk=pk)


@login_required
def create_report(request, pk):
    study = get_object_or_404(XrayStudy, pk=pk)
    
    if request.method == 'POST':
        report = getattr(study, 'report', None)
        form = XrayReportForm(request.POST, instance=report)
        
        if form.is_valid():
            report = form.save(commit=False)
            report.study = study
            report.reported_by = request.user
            report.save()
            
            study.status = 'reported'
            study.reporting_doctor = request.user
            study.save()
            
            messages.success(request, 'Report saved successfully.')
        else:
            messages.error(request, 'Failed to save report. Please check the form.')
    
    return redirect('xray:detail', pk=pk)


@login_required
def verify_report(request, pk):
    study = get_object_or_404(XrayStudy, pk=pk)
    report = getattr(study, 'report', None)
    
    if not report:
        messages.error(request, 'No report to verify.')
        return redirect('xray:detail', pk=pk)
    
    report.verified_by = request.user
    report.verified_at = timezone.now()
    report.save()
    
    study.status = 'verified'
    study.save()
    
    messages.success(request, 'Report verified successfully.')
    return redirect('xray:detail', pk=pk)
