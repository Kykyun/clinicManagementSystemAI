from django.db import models
from django.conf import settings


class XrayStudy(models.Model):
    BODY_REGION_CHOICES = [
        ('chest', 'Chest'),
        ('abdomen', 'Abdomen'),
        ('spine_cervical', 'Cervical Spine'),
        ('spine_thoracic', 'Thoracic Spine'),
        ('spine_lumbar', 'Lumbar Spine'),
        ('skull', 'Skull'),
        ('shoulder', 'Shoulder'),
        ('elbow', 'Elbow'),
        ('wrist', 'Wrist/Hand'),
        ('hip', 'Hip/Pelvis'),
        ('knee', 'Knee'),
        ('ankle', 'Ankle/Foot'),
        ('other', 'Other'),
    ]
    
    VIEW_CHOICES = [
        ('pa', 'PA (Posterior-Anterior)'),
        ('ap', 'AP (Anterior-Posterior)'),
        ('lateral', 'Lateral'),
        ('oblique', 'Oblique'),
        ('lordotic', 'Lordotic'),
        ('decubitus', 'Decubitus'),
        ('multiple', 'Multiple Views'),
    ]
    
    SIDE_CHOICES = [
        ('left', 'Left'),
        ('right', 'Right'),
        ('bilateral', 'Bilateral'),
        ('na', 'Not Applicable'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('in_progress', 'In Progress'),
        ('ai_analyzed', 'AI Analyzed'),
        ('reported', 'Reported'),
        ('verified', 'Verified'),
    ]
    
    PRIORITY_CHOICES = [
        ('routine', 'Routine'),
        ('urgent', 'Urgent'),
        ('stat', 'STAT'),
    ]
    
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='xray_studies')
    visit = models.ForeignKey('patients.Visit', on_delete=models.SET_NULL, null=True, blank=True, related_name='xray_studies')
    
    study_date = models.DateTimeField(auto_now_add=True)
    body_region = models.CharField(max_length=20, choices=BODY_REGION_CHOICES)
    view_type = models.CharField(max_length=20, choices=VIEW_CHOICES, default='ap')
    side = models.CharField(max_length=15, choices=SIDE_CHOICES, default='na')
    
    clinical_indication = models.TextField(help_text="Clinical question or reason for X-ray")
    clinical_history = models.TextField(blank=True, help_text="Relevant patient history")
    
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='routine')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    requesting_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='requested_xrays'
    )
    radiographer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='performed_xrays'
    )
    reporting_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reported_xrays'
    )
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-study_date']
        verbose_name = 'X-ray Study'
        verbose_name_plural = 'X-ray Studies'
    
    def __str__(self):
        return f"{self.patient.name} - {self.get_body_region_display()} ({self.study_date.strftime('%Y-%m-%d')})"


class XrayImage(models.Model):
    study = models.ForeignKey(XrayStudy, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='xray_images/%Y/%m/')
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f"Image for {self.study} - {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"


class XrayDocument(models.Model):
    DOC_TYPE_CHOICES = [
        ('referral', 'Referral Letter'),
        ('previous_report', 'Previous Report'),
        ('clinical_notes', 'Clinical Notes'),
        ('other', 'Other'),
    ]
    
    study = models.ForeignKey(XrayStudy, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='xray_documents/%Y/%m/')
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, default='other')
    title = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f"{self.title} - {self.study}"


class XrayAIAnalysis(models.Model):
    study = models.OneToOneField(XrayStudy, on_delete=models.CASCADE, related_name='ai_analysis')
    
    case_summary = models.TextField(blank=True)
    technical_assessment = models.TextField(blank=True)
    findings = models.TextField(blank=True)
    impression = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    
    red_flags = models.JSONField(default=list, blank=True)
    confidence_level = models.CharField(max_length=20, blank=True)
    
    raw_response = models.TextField(blank=True)
    
    analyzed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'X-ray AI Analysis'
        verbose_name_plural = 'X-ray AI Analyses'
    
    def __str__(self):
        return f"AI Analysis for {self.study}"


class XrayReport(models.Model):
    study = models.OneToOneField(XrayStudy, on_delete=models.CASCADE, related_name='report')
    
    technique = models.TextField(blank=True, help_text="Imaging technique used")
    findings = models.TextField(help_text="Detailed radiological findings")
    impression = models.TextField(help_text="Summary impression/diagnosis")
    recommendations = models.TextField(blank=True, help_text="Follow-up recommendations")
    
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='xray_reports'
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_xray_reports'
    )
    
    reported_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-reported_at']
    
    def __str__(self):
        return f"Report for {self.study}"
