from django.db import models
from django.conf import settings
from setup_app.models import Medicine, LabTest, Allergy, Panel


class Patient(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    ID_TYPE_CHOICES = [
        ('nric', 'NRIC'),
        ('passport', 'Passport'),
    ]
    
    patient_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    id_type = models.CharField(max_length=10, choices=ID_TYPE_CHOICES, default='nric')
    id_number = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    allergies = models.ManyToManyField(Allergy, blank=True)
    chronic_illnesses = models.TextField(blank=True)
    blood_type = models.CharField(max_length=5, blank=True)
    panel = models.ForeignKey(Panel, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.patient_id} - {self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class Visit(models.Model):
    VISIT_TYPE_CHOICES = [
        ('medical', 'Medical Visit'),
        ('otc', 'Over The Counter'),
        ('followup', 'Follow-up'),
        ('emergency', 'Emergency'),
        ('vaccination', 'Vaccination'),
    ]
    
    STATUS_CHOICES = [
        ('waiting_triage', 'Waiting - Triage'),
        ('waiting_doctor', 'Waiting - Doctor'),
        ('in_consultation', 'In Consultation'),
        ('to_pharmacy', 'To Pharmacy'),
        ('to_lab', 'To Lab'),
        ('ready_for_payment', 'Ready for Payment'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYER_TYPE_CHOICES = [
        ('self_pay', 'Self Pay'),
        ('corporate', 'Corporate'),
        ('insurance', 'Insurance'),
    ]
    
    visit_number = models.CharField(max_length=20, unique=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='visits')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='patient_visits')
    visit_type = models.CharField(max_length=20, choices=VISIT_TYPE_CHOICES, default='medical')
    payer_type = models.CharField(max_length=20, choices=PAYER_TYPE_CHOICES, default='self_pay')
    visit_date = models.DateTimeField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='waiting_triage')
    queue_number = models.IntegerField(null=True, blank=True)
    room = models.CharField(max_length=50, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_visits')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-visit_date']

    def __str__(self):
        return f"{self.visit_number} - {self.patient.full_name}"
    
    @property
    def status_display_class(self):
        status_classes = {
            'waiting_triage': 'warning',
            'waiting_doctor': 'info',
            'in_consultation': 'primary',
            'to_pharmacy': 'secondary',
            'to_lab': 'secondary',
            'ready_for_payment': 'success',
            'completed': 'success',
            'cancelled': 'danger',
        }
        return status_classes.get(self.status, 'secondary')


class Triage(models.Model):
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='triage')
    bp_systolic = models.IntegerField(null=True, blank=True, verbose_name='BP Systolic')
    bp_diastolic = models.IntegerField(null=True, blank=True, verbose_name='BP Diastolic')
    heart_rate = models.IntegerField(null=True, blank=True, verbose_name='Heart Rate (bpm)')
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='Temperature (°C)')
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Weight (kg)')
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Height (cm)')
    spo2 = models.IntegerField(null=True, blank=True, verbose_name='SpO2 (%)')
    pain_score = models.IntegerField(null=True, blank=True, verbose_name='Pain Score (0-10)')
    notes = models.TextField(blank=True)
    allergy_flag = models.BooleanField(default=False, verbose_name='Allergy Alert')
    infection_risk = models.BooleanField(default=False, verbose_name='Infection Risk')
    fall_risk = models.BooleanField(default=False, verbose_name='Fall Risk')
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Triage for {self.visit}"
    
    @property
    def bp_display(self):
        if self.bp_systolic and self.bp_diastolic:
            return f"{self.bp_systolic}/{self.bp_diastolic}"
        return "-"
    
    @property
    def bmi(self):
        if self.weight and self.height and self.height > 0:
            height_m = float(self.height) / 100
            return round(float(self.weight) / (height_m * height_m), 1)
        return None


class Consultation(models.Model):
    MC_REASON_CHOICES = [
        ('unfit_work', 'Unfit for Work'),
        ('unfit_school', 'Unfit for School'),
        ('hospitalization', 'Hospitalization'),
        ('rest', 'Rest at Home'),
        ('other', 'Other'),
    ]
    
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='consultation')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    chief_complaint = models.TextField()
    history_of_illness = models.TextField(blank=True)
    examination_findings = models.TextField(blank=True)
    diagnosis = models.TextField()
    treatment_plan = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    vitals_bp = models.CharField(max_length=20, blank=True)
    vitals_pulse = models.IntegerField(null=True, blank=True)
    vitals_temp = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    vitals_weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    vitals_height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    mc_issued = models.BooleanField(default=False)
    mc_start_date = models.DateField(null=True, blank=True)
    mc_end_date = models.DateField(null=True, blank=True)
    mc_days = models.IntegerField(null=True, blank=True)
    mc_reason = models.CharField(max_length=20, choices=MC_REASON_CHOICES, blank=True)
    mc_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Consultation for {self.visit}"


class Prescription(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='prescriptions')
    medicine = models.ForeignKey(Medicine, on_delete=models.SET_NULL, null=True)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=50)
    quantity = models.IntegerField(default=1)
    instructions = models.TextField(blank=True)
    is_dispensed = models.BooleanField(default=False)
    dispensed_at = models.DateTimeField(null=True, blank=True)
    dispensed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.medicine.name} for {self.consultation.visit.patient.full_name}"

    @property
    def total_price(self):
        if self.medicine:
            return self.medicine.selling_price * self.quantity
        return 0


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_appointments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['appointment_date', 'appointment_time']

    def __str__(self):
        return f"{self.patient.full_name} - {self.appointment_date} {self.appointment_time}"


class LabResult(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('reviewed', 'Reviewed'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='lab_results')
    visit = models.ForeignKey(Visit, on_delete=models.SET_NULL, null=True, blank=True)
    lab_test = models.ForeignKey(LabTest, on_delete=models.SET_NULL, null=True)
    result_value = models.CharField(max_length=200)
    result_unit = models.CharField(max_length=50, blank=True)
    normal_range = models.CharField(max_length=100, blank=True)
    is_abnormal = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    result_file = models.FileField(upload_to='lab_results/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='performed_lab_tests')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_lab_tests')
    test_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lab_test.name} - {self.patient.full_name}"


class Immunization(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='immunizations')
    vaccine_name = models.CharField(max_length=200)
    batch_number = models.CharField(max_length=50, blank=True)
    dose_number = models.IntegerField(default=1)
    date_given = models.DateField()
    next_due_date = models.DateField(null=True, blank=True)
    administered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vaccine_name} - {self.patient.full_name}"
