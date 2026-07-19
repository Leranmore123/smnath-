from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import random

class UserProfile(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    member_id = models.CharField(max_length=20, unique=True, blank=True)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    mobile_number = models.CharField(max_length=15, blank=True)
    state = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')

    def save(self, *args, **kwargs):
        if not self.member_id:
            # Generate ID in format SMSEVA0100 + serial/random
            while True:
                candidate_id = f"SMSEVA{random.randint(1000, 9999)}"
                if not UserProfile.objects.filter(member_id=candidate_id).exists():
                    self.member_id = candidate_id
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name or self.user.username} ({self.member_id})"

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # Avoid failure if profile doesn't exist for imported superusers
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            UserProfile.objects.create(user=instance)


class Service(models.Model):
    CATEGORY_CHOICES = [
        ('Govt Services', 'Karnataka Govt. Services'),
        ('Print Services', 'Print Services'),
        ('Other Services', 'Other Services'),
    ]
    
    SUBCATEGORY_CHOICES = [
        ('none', 'None'),
        ('Ration Card', 'Ration Card Services'),
        ('Voter Services', 'Voter Services'),
        ('DL Services', 'DL Services'),
        ('Vehicle Services', 'Vehicle Services'),
        ('PAN Services', 'PAN Services'),
    ]
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    subcategory = models.CharField(max_length=30, choices=SUBCATEGORY_CHOICES, default='none')
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    service_type = models.CharField(max_length=15, choices=[('Manual', 'Manual'), ('Automated', 'Automated')], default='Manual')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - ₹{self.cost} ({self.category})"


class ServiceApplication(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PENDING_OTP', 'Pending OTP Verification'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
    ]
    
    order_id = models.CharField(max_length=30, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='service_applications')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    
    form_data = models.JSONField(default=dict, blank=True)
    
    result_file = models.FileField(upload_to='service_results/', blank=True, null=True)
    admin_notes = models.TextField(blank=True)
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            while True:
                candidate_id = f"TXN{random.randint(10000000, 99999999)}"
                if not ServiceApplication.objects.filter(order_id=candidate_id).exists():
                    self.order_id = candidate_id
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_id} - {self.service.name} ({self.user.username})"


class TopupRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    order_id = models.CharField(max_length=30, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topup_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(max_length=20, default='Online')
    transaction_id_utr = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            while True:
                candidate_id = f"TOP{random.randint(10000000, 99999999)}"
                if not TopupRequest.objects.filter(order_id=candidate_id).exists():
                    self.order_id = candidate_id
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_id} - ₹{self.amount} ({self.user.username})"
