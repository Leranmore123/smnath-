from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from decimal import Decimal
import random
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_REGULAR = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
try:
    import os
    nirmala_path = 'C:\\Windows\\Fonts\\Nirmala.ttf'
    nirmalab_path = 'C:\\Windows\\Fonts\\NirmalaB.ttf'
    if os.path.exists(nirmala_path) and os.path.exists(nirmalab_path):
        pdfmetrics.registerFont(TTFont('Nirmala', nirmala_path))
        pdfmetrics.registerFont(TTFont('Nirmala-Bold', nirmalab_path))
        FONT_REGULAR = 'Nirmala'
        FONT_BOLD = 'Nirmala-Bold'
except Exception:
    pass

from .models import UserProfile, Service, ServiceApplication, TopupRequest
from .automation.ration_card import download_ration_card_automated


# Service Fields Config for rendering forms dynamically
SERVICE_FIELDS = {
    'apply_senior': [
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter full name'},
        {'name': 'aadhaar_no', 'label': 'Aadhaar Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'mobile_no', 'label': 'Mobile Number', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'email_id', 'label': 'Email ID', 'type': 'text', 'placeholder': 'Enter Email ID'},
        {'name': 'gender', 'label': 'Gender', 'type': 'select', 'options': ['Male', 'Female', 'Other']},
        {'name': 'dob', 'label': 'Date of Birth', 'type': 'date', 'placeholder': ''},
        {'name': 'address', 'label': 'Address', 'type': 'text', 'placeholder': 'Enter full address'},
        {'name': 'talluk', 'label': 'Talluk', 'type': 'text', 'placeholder': 'Enter Talluk'},
        {'name': 'district', 'label': 'District', 'type': 'text', 'placeholder': 'Enter District'},
        {'name': 'pincode', 'label': 'Pincode', 'type': 'text', 'placeholder': 'Enter Pincode'},
        {'name': 'photo', 'label': 'Upload Candidate Photo', 'type': 'file', 'placeholder': ''},
        {'name': 'upload_aadhaar', 'label': 'Upload Aadhaar PDF/Image', 'type': 'file', 'placeholder': ''},
        {'name': 'blood_group_report', 'label': 'Upload Blood Group Report', 'type': 'file', 'placeholder': ''}
    ],
    'gl_sanction': [
        {'name': 'ration_card_no', 'label': 'Ration Card No.', 'type': 'text', 'placeholder': 'Enter Ration Card Number'},
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'}
    ],
    'gruhalaxmi': [
        {'name': 'ration_card_no', 'label': 'Ration Card No.', 'type': 'text', 'placeholder': 'Enter Ration Card Number'},
        {'name': 'aadhaar_number', 'label': 'Aadhaar Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'mobile_no', 'label': 'Mobile No.', 'type': 'text', 'placeholder': 'Enter Mobile Number'}
    ],
    'gruhalaxmi_sts': [
        {'name': 'ration_card_no', 'label': 'Ration Card No.', 'type': 'text', 'placeholder': 'Enter Ration Card Number'},
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'}
    ],
    'gruhalaxmikyc': [
        {'name': 'ration_card_no', 'label': 'Ration Card No.', 'type': 'text', 'placeholder': 'Enter Ration Card Number'},
        {'name': 'aadhaar_number', 'label': 'Aadhaar Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'mobile_no', 'label': 'Mobile No.', 'type': 'text', 'placeholder': 'Enter Mobile Number'}
    ],
    'gruhajyothi': [
        {'name': 'escom', 'label': 'Select ESCOM', 'type': 'select', 'options': ['BESCOM', 'CESC', 'GESCOM', 'HESCOM', 'MESCOM']},
        {'name': 'account_id', 'label': 'Account ID / Connection ID', 'type': 'text', 'placeholder': 'Enter Account ID'},
        {'name': 'account_holder_name', 'label': 'Account Holder Name', 'type': 'text', 'placeholder': 'Enter Holder Name'},
        {'name': 'account_holder_address', 'label': 'Account Holder Address', 'type': 'textarea', 'placeholder': 'Enter Address'},
        {'name': 'occupancy_type', 'label': 'Type of Occupancy', 'type': 'select', 'options': ['Owner', 'Tenant', 'Shared']},
        {'name': 'aadhaar_no', 'label': 'Aadhaar Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'mobile_no', 'label': 'Mobile No.', 'type': 'text', 'placeholder': 'Enter Mobile Number'}
    ],
    'gruhajyothi_dlink': [
        {'name': 'aadhaar_no', 'label': 'Aadhaar Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'mobile_no', 'label': 'Mobile No. for OTP', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'district', 'label': 'District', 'type': 'text', 'placeholder': 'Enter District'}
    ],
    'bhoomi_pahani_link': [
        {'name': 'aadhaar_no', 'label': 'Aadhaar Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'mobile_no', 'label': 'Mobile No. for OTP', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'district', 'label': 'Select District', 'type': 'select', 'options': ['Bengaluru Urban', 'Bengaluru Rural', 'Belagavi', 'Ballari', 'Bidar', 'Chamarajanagar', 'Chikkaballapur', 'Chikkamagaluru', 'Chitradurga', 'Dakshina Kannada', 'Davanagere', 'Dharwad', 'Gadag', 'Hassan', 'Haveri', 'Kalaburagi', 'Kodagu', 'Kolar', 'Koppal', 'Mandya', 'Mysuru', 'Raichur', 'Ramanagara', 'Shivamogga', 'Tumakuru', 'Udupi', 'Uttara Kannada', 'Vijayapura', 'Yadgir']},
        {'name': 'talluk', 'label': 'Select Talluk', 'type': 'text', 'placeholder': 'Enter Talluk'},
        {'name': 'hobli', 'label': 'Enter Hobli', 'type': 'text', 'placeholder': 'Enter Hobli'},
        {'name': 'village', 'label': 'Enter Village', 'type': 'text', 'placeholder': 'Enter Village'},
        {'name': 'survey_no', 'label': 'Enter Survey No.', 'type': 'text', 'placeholder': 'Enter Survey Number'},
        {'name': 'hissa_no', 'label': 'Hissa No. (Optional)', 'type': 'text', 'placeholder': 'Enter Hissa Number'}
    ],
    'rtc_download': [
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'district', 'label': 'Select District', 'type': 'select', 'options': ['Bengaluru Urban', 'Bengaluru Rural', 'Belagavi', 'Ballari', 'Bidar', 'Chamarajanagar', 'Chikkaballapur', 'Chikkamagaluru', 'Chitradurga', 'Dakshina Kannada', 'Davanagere', 'Dharwad', 'Gadag', 'Hassan', 'Haveri', 'Kalaburagi', 'Kodagu', 'Kolar', 'Koppal', 'Mandya', 'Mysuru', 'Raichur', 'Ramanagara', 'Shivamogga', 'Tumakuru', 'Udupi', 'Uttara Kannada', 'Vijayapura', 'Yadgir']},
        {'name': 'talluk', 'label': 'Select Talluk', 'type': 'text', 'placeholder': 'Enter Talluk'},
        {'name': 'hobli', 'label': 'Enter Hobli', 'type': 'text', 'placeholder': 'Enter Hobli'},
        {'name': 'village', 'label': 'Enter Village', 'type': 'text', 'placeholder': 'Enter Village'},
        {'name': 'survey_no', 'label': 'Enter Survey No.', 'type': 'text', 'placeholder': 'Enter Survey Number'}
    ],
    'abha_card': [
        {'name': 'aadhaar_no', 'label': 'Aadhaar Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'mobile_no', 'label': 'Mobile Number', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'state', 'label': 'Select State', 'type': 'select', 'options': ['Karnataka', 'Maharashtra', 'Gujarat', 'Goa', 'Tamil Nadu', 'Kerala', 'Andhra Pradesh', 'Telangana']}
    ],
    'ayush_card': [
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'aadhaar_no', 'label': 'Aadhaar Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'mobile_no', 'label': 'Mobile Number', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'relationship', 'label': 'Relationship with Family Head', 'type': 'select', 'options': ['Self', 'Wife', 'Husband', 'Son', 'Daughter', 'Father', 'Mother', 'Brother', 'Sister']},
        {'name': 'dob', 'label': 'Date of Birth', 'type': 'date', 'placeholder': ''},
        {'name': 'photo', 'label': 'Upload Live Photo', 'type': 'file', 'placeholder': ''},
        {'name': 'state', 'label': 'Select State', 'type': 'select', 'options': ['Karnataka', 'Maharashtra', 'Gujarat', 'Goa', 'Tamil Nadu', 'Kerala', 'Andhra Pradesh', 'Telangana']},
        {'name': 'district', 'label': 'Select District', 'type': 'text', 'placeholder': 'Enter District'},
        {'name': 'sub_division', 'label': 'Sub Division', 'type': 'text', 'placeholder': 'Enter Sub Division'}
    ],
    'ayush_dwnld': [
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'aadhaar_no', 'label': 'Aadhaar Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'mobile_no', 'label': 'Mobile Number', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'dob', 'label': 'Date of Birth', 'type': 'date', 'placeholder': ''},
        {'name': 'state', 'label': 'Select State', 'type': 'select', 'options': ['Karnataka', 'Maharashtra', 'Gujarat', 'Goa', 'Tamil Nadu', 'Kerala', 'Andhra Pradesh', 'Telangana']},
        {'name': 'district', 'label': 'Select District', 'type': 'text', 'placeholder': 'Enter District'}
    ],
    'eshram': [
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'aadhaar_no', 'label': 'Aadhaar Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'mobile_no', 'label': 'Mobile Number', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'marital_status', 'label': 'Marital Status', 'type': 'select', 'options': ['Never Married', 'Married', 'Widowed', 'Divorced']},
        {'name': 'relationship', 'label': 'Relationship', 'type': 'select', 'options': ['Father', 'Husband', 'Mother', 'Guardian']},
        {'name': 'relative_name', 'label': 'Relative Name', 'type': 'text', 'placeholder': 'Enter Name'},
        {'name': 'social_category', 'label': 'Social Category', 'type': 'select', 'options': ['General', 'OBC', 'SC', 'ST']},
        {'name': 'differently_abled', 'label': 'Differently Abled', 'type': 'select', 'options': ['No', 'Yes']},
        {'name': 'state', 'label': 'Select State', 'type': 'select', 'options': ['Karnataka', 'Maharashtra', 'Gujarat', 'Goa', 'Tamil Nadu', 'Kerala', 'Andhra Pradesh', 'Telangana']},
        {'name': 'district', 'label': 'Select District', 'type': 'text', 'placeholder': 'Enter District'},
        {'name': 'sub_division', 'label': 'Sub Division', 'type': 'text', 'placeholder': 'Enter Sub Division'},
        {'name': 'address_1', 'label': 'Address Line 1', 'type': 'text', 'placeholder': 'House/Flat No.'},
        {'name': 'address_2', 'label': 'Address Line 2', 'type': 'text', 'placeholder': 'Street/Locality'},
        {'name': 'pincode', 'label': 'Pincode', 'type': 'text', 'placeholder': 'Enter Pincode'},
        {'name': 'staying_years', 'label': 'Staying From (Years)', 'type': 'select', 'options': ['1 Year', '2-5 Years', '5-10 Years', '10+ Years']},
        {'name': 'education', 'label': 'Education Qualification', 'type': 'select', 'options': ['Literate', 'Primary', 'Middle', 'Secondary', 'Higher Secondary', 'Graduate', 'Post Graduate']},
        {'name': 'monthly_income', 'label': 'Monthly Income', 'type': 'select', 'options': ['Below 10000', '10000-15000', '15000-24000', '25000+']},
        {'name': 'gig_worker', 'label': 'Working in Platforms like Ola/Uber/Zomato etc', 'type': 'select', 'options': ['No', 'Yes']},
        {'name': 'occupation', 'label': 'Primary Occupation', 'type': 'text', 'placeholder': 'e.g. Driver, Tailor, Construction'},
        {'name': 'experience', 'label': 'Work Exp. (Years)', 'type': 'select', 'options': ['1 Year', '2 Years', '3 Years', '4 Years', '5+ Years']},
        {'name': 'bank_account', 'label': 'Bank Account Number', 'type': 'text', 'placeholder': 'Enter Account Number'},
        {'name': 'ifsc_code', 'label': 'IFSC Code', 'type': 'text', 'placeholder': 'Enter IFSC'}
    ],
    'eshram_dwnld': [
        {'name': 'aadhaar_no', 'label': 'Aadhaar Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'mobile_no', 'label': 'Mobile Number', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'state', 'label': 'Select State', 'type': 'select', 'options': ['Karnataka', 'Maharashtra', 'Gujarat', 'Goa', 'Tamil Nadu', 'Kerala', 'Andhra Pradesh', 'Telangana']}
    ],
    'pmkisan': [
        {'name': 'app_type', 'label': 'Application Type', 'type': 'select', 'options': ['e-KYC', 'Know Your Status', 'Update Mobile No.']},
        {'name': 'aadhaar_no', 'label': 'Aadhaar Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'mobile_no', 'label': 'Mobile No. for OTP', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'state', 'label': 'Select State', 'type': 'select', 'options': ['Karnataka', 'Maharashtra', 'Gujarat', 'Goa', 'Tamil Nadu', 'Kerala', 'Andhra Pradesh', 'Telangana']}
    ],
    'rc_dwnld': [
        {'name': 'ration_card_no', 'label': 'Ration Card Number', 'type': 'text', 'placeholder': 'Enter Ration Card Number'}
    ],
    'slct_offlinedist': [
        {'name': 'agent_rc_no', 'label': "Agent's Ration Card No", 'type': 'text', 'placeholder': 'Enter Agent Card Number'},
        {'name': 'customer_rc_no', 'label': 'Customer Ration Card No', 'type': 'text', 'placeholder': 'Enter Customer Card Number'}
    ],
    'shop_select': [
        {'name': 'ration_card_no', 'label': 'Enter Ration Card No.', 'type': 'text', 'placeholder': 'Enter Ration Card Number'}
    ],
    'annabhagya_view': [
        {'name': 'year', 'label': 'Select Year', 'type': 'select', 'options': ['2026', '2025', '2024', '2023']},
        {'name': 'month', 'label': 'Select Month', 'type': 'select', 'options': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']},
        {'name': 'ration_card_no', 'label': 'Enter RC Number', 'type': 'text', 'placeholder': 'Enter Ration Card Number'}
    ],
    'corr_select': [
        {'name': 'ration_card_no', 'label': 'Enter Ration Card No.', 'type': 'text', 'placeholder': 'Enter Ration Card Number'}
    ],
    'ration_to_aadhaar': [
        {'name': 'customer_name', 'label': 'Customer Name', 'type': 'text', 'placeholder': 'Enter Customer Name'},
        {'name': 'ration_card_no', 'label': 'Enter Ration Card No', 'type': 'text', 'placeholder': 'Enter Ration Card Number'}
    ],
    'aadhaar_to_ration': [
        {'name': 'customer_name', 'label': 'Enter Customer Name', 'type': 'text', 'placeholder': 'Enter Customer Name'},
        {'name': 'uid_no', 'label': 'Enter UID Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'}
    ],
    'epic_corrections_name': [
        {'name': 'epic_number', 'label': 'EPIC Number', 'type': 'text', 'placeholder': 'Enter EPIC Number'},
        {'name': 'first_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'First Name'},
        {'name': 'middle_name', 'label': 'Middle Name', 'type': 'text', 'placeholder': 'Middle Name'},
        {'name': 'surname', 'label': 'Surname', 'type': 'text', 'placeholder': 'Surname'},
        {'name': 'doc_proof', 'label': 'Document Upload - Name Proof', 'type': 'file', 'placeholder': ''}
    ],
    'offline_mobile': [
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'epic_number', 'label': 'EPIC No.', 'type': 'text', 'placeholder': 'Enter EPIC Number'},
        {'name': 'mobile_no', 'label': 'Mobile No. (Aadhaar Linked)', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'aadhaar_no', 'label': 'Applicant - Aadhaar No.', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'state', 'label': 'Select State', 'type': 'select', 'options': ['Karnataka', 'Maharashtra', 'Gujarat', 'Goa', 'Tamil Nadu', 'Kerala', 'Andhra Pradesh', 'Telangana']}
    ],
    'epic_corrections_photo': [
        {'name': 'epic_number', 'label': 'EPIC Number', 'type': 'text', 'placeholder': 'Enter EPIC Number'},
        {'name': 'full_name', 'label': 'Full Name', 'type': 'text', 'placeholder': 'Enter Full Name'},
        {'name': 'address', 'label': 'Address', 'type': 'text', 'placeholder': 'Enter Address'},
        {'name': 'photo', 'label': 'Photo Upload (JPG)', 'type': 'file', 'placeholder': ''}
    ],
    'epic_corrections_address': [
        {'name': 'epic_number', 'label': 'EPIC Number', 'type': 'text', 'placeholder': 'Enter EPIC Number'},
        {'name': 'name', 'label': 'Name', 'type': 'text', 'placeholder': 'Enter Name'},
        {'name': 'house_no', 'label': 'House Number', 'type': 'text', 'placeholder': 'Enter House Number'},
        {'name': 'street', 'label': 'Street/Locality/Road', 'type': 'text', 'placeholder': 'Enter Street'},
        {'name': 'village', 'label': 'Village', 'type': 'text', 'placeholder': 'Enter Village'},
        {'name': 'post_office', 'label': 'Post Office', 'type': 'text', 'placeholder': 'Enter Post Office'},
        {'name': 'pincode', 'label': 'PIN Code', 'type': 'text', 'placeholder': 'Enter PIN Code'},
        {'name': 'taluk', 'label': 'Taluqa/Tehsil', 'type': 'text', 'placeholder': 'Enter Taluk'},
        {'name': 'district', 'label': 'District', 'type': 'text', 'placeholder': 'Enter District'},
        {'name': 'state', 'label': 'State', 'type': 'text', 'placeholder': 'Enter State'},
        {'name': 'aadhaar_pdf', 'label': 'Upload Aadhaar Original PDF', 'type': 'file', 'placeholder': ''}
    ],
    'epic_corrections_gender': [
        {'name': 'epic_number', 'label': 'EPIC Number', 'type': 'text', 'placeholder': 'Enter EPIC Number'},
        {'name': 'first_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'First Name'},
        {'name': 'middle_name', 'label': 'Middle Name', 'type': 'text', 'placeholder': 'Middle Name'},
        {'name': 'surname', 'label': 'Surname', 'type': 'text', 'placeholder': 'Surname'},
        {'name': 'gender', 'label': 'Gender', 'type': 'select', 'options': ['Male', 'Female', 'Other']},
        {'name': 'doc_proof', 'label': 'Document Upload - Correction Proof', 'type': 'file', 'placeholder': ''}
    ],
    'epic_corrections_dob': [
        {'name': 'epic_number', 'label': 'EPIC Number', 'type': 'text', 'placeholder': 'Enter EPIC Number'},
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'dob', 'label': 'Date of Birth (DOB)', 'type': 'date', 'placeholder': ''},
        {'name': 'gender', 'label': 'Gender', 'type': 'select', 'options': ['Male', 'Female', 'Other']},
        {'name': 'doc_proof', 'label': 'Document Upload - DOB Proof', 'type': 'file', 'placeholder': ''}
    ],
    'original_voter_pdf': [
        {'name': 'epic_number', 'label': 'EPIC Number', 'type': 'text', 'placeholder': 'Enter EPIC Number'},
        {'name': 'state', 'label': 'Select State', 'type': 'select', 'options': ['Karnataka', 'Maharashtra', 'Gujarat', 'Goa', 'Tamil Nadu', 'Kerala', 'Andhra Pradesh', 'Telangana']}
    ],
    'voter_mobile_instant': [
        {'name': 'aadhaar_name', 'label': 'Aadhaar Name', 'type': 'text', 'placeholder': 'Enter Name as in Aadhaar'},
        {'name': 'epic_number', 'label': 'EPIC No.', 'type': 'text', 'placeholder': 'Enter EPIC Number'},
        {'name': 'mobile_no', 'label': 'New Link Mobile', 'type': 'text', 'placeholder': 'Enter New Mobile'},
        {'name': 'aadhaar_no', 'label': 'Aadhaar No.', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'}
    ],
    'voter_pdf_instant': [
        {'name': 'epic_number', 'label': 'EPIC Number', 'type': 'text', 'placeholder': 'Enter EPIC Number'}
    ],
    'dlallindia': [
        {'name': 'dl_number', 'label': 'DL Number', 'type': 'text', 'placeholder': 'Enter DL Number (e.g. KA012020XXXXXXX)'},
        {'name': 'dob', 'label': 'Date of Birth', 'type': 'text', 'placeholder': 'DD-MM-YYYY'}
    ],
    'dl_karnataka': [
        {'name': 'dl_number', 'label': 'Enter DL Number', 'type': 'text', 'placeholder': 'Enter Karnataka DL Number'},
        {'name': 'dob', 'label': 'Enter DOB', 'type': 'text', 'placeholder': 'DD-MM-YYYY'}
    ],
    'find_dlno': [
        {'name': 'name', 'label': 'DL Holder Name', 'type': 'text', 'placeholder': 'Enter Holder Name'},
        {'name': 'dob', 'label': 'DOB', 'type': 'date', 'placeholder': ''},
        {'name': 'mobile_no', 'label': 'Mobile Number', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'rto_name', 'label': 'RTO Name', 'type': 'text', 'placeholder': 'Enter RTO Station Name'}
    ],
    'link_dltomobile': [
        {'name': 'applicant_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Applicant Name'},
        {'name': 'dl_number', 'label': 'DL No.', 'type': 'text', 'placeholder': 'Enter Driving Licence Number'},
        {'name': 'aadhaar_no', 'label': 'Aadhaar Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'mobile_no', 'label': 'Mobile No. for OTP', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'state', 'label': 'Select State', 'type': 'select', 'options': ['Karnataka', 'Maharashtra', 'Gujarat', 'Goa', 'Tamil Nadu', 'Kerala', 'Andhra Pradesh', 'Telangana']}
    ],
    'rc_advance': [
        {'name': 'vehicle_no', 'label': 'Enter Vehicle No.', 'type': 'text', 'placeholder': 'e.g. KA01XX1234'}
    ],
    'allind_adv': [
        {'name': 'vehicle_no', 'label': 'Enter Vehicle No.', 'type': 'text', 'placeholder': 'e.g. KA01XX1234'},
        {'name': 'bg_type', 'label': 'Card Background', 'type': 'select', 'options': ['All India Standard', 'State Specific Background']},
        {'name': 'chip_type', 'label': 'Chip Type', 'type': 'select', 'options': ['Golden Smart Chip', 'QR/Barcode Format']}
    ],
    'rckar_pvc': [
        {'name': 'vehicle_no', 'label': 'Enter Vehicle No.', 'type': 'text', 'placeholder': 'e.g. KA01XX1234'}
    ],
    'vrc_mobile': [
        {'name': 'aadhaar_name', 'label': 'Applicant Name', 'type': 'text', 'placeholder': 'Enter Name as in Aadhaar'},
        {'name': 'vehicle_no', 'label': 'Vehicle Reg. No.', 'type': 'text', 'placeholder': 'e.g. KA01XX1234'},
        {'name': 'aadhaar_no', 'label': 'Aadhaar Number', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'},
        {'name': 'mobile_no', 'label': 'Mobile No. for OTP', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'state', 'label': 'Select State', 'type': 'select', 'options': ['Karnataka', 'Maharashtra', 'Gujarat', 'Goa', 'Tamil Nadu', 'Kerala', 'Andhra Pradesh', 'Telangana']}
    ],
    'll_exam': [
        {'name': 'app_no', 'label': 'App No', 'type': 'text', 'placeholder': 'Enter LL Application Number'},
        {'name': 'dob', 'label': 'DOB', 'type': 'date', 'placeholder': ''},
        {'name': 'password', 'label': 'Password', 'type': 'text', 'placeholder': 'Enter Exam Password'}
    ],
    'pan_card_print': [
        {'name': 'pan_number', 'label': 'PAN Number', 'type': 'text', 'placeholder': 'Enter 10-digit PAN'},
        {'name': 'full_name', 'label': 'Full Name (Auto-fetched or enter manually)', 'type': 'text', 'placeholder': 'Enter Full Name'},
        {'name': 'father_name', 'label': "Father's Name", 'type': 'text', 'placeholder': "Enter Father's Name"},
        {'name': 'dob', 'label': 'Date of Birth', 'type': 'date', 'placeholder': ''},
        {'name': 'gender', 'label': 'Gender', 'type': 'select', 'options': ['Male', 'Female', 'Other']},
        {'name': 'signature', 'label': 'Upload Signature', 'type': 'file', 'placeholder': ''},
        {'name': 'photo', 'label': 'Upload Photo', 'type': 'file', 'placeholder': ''}
    ],
    'aadhaar_panstatus': [
        {'name': 'aadhaar_no', 'label': 'Enter Aadhaar No.', 'type': 'text', 'placeholder': 'Enter 12-digit Aadhaar'}
    ],
    'pan_to_aadhaar': [
        {'name': 'pan_number', 'label': 'Enter PAN No.', 'type': 'text', 'placeholder': 'Enter 10-digit PAN'}
    ],
    'pan_mobile_find': [
        {'name': 'mobile_no', 'label': 'Mobile Number', 'type': 'text', 'placeholder': 'Enter Mobile Number'}
    ],
    'tailoring_certificate': [
        {'name': 'full_name', 'label': 'Full Name of the Candidate', 'type': 'text', 'placeholder': 'Enter Full Name'},
        {'name': 'mobile_no', 'label': 'Mobile Number', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'email', 'label': 'Email ID', 'type': 'text', 'placeholder': 'Enter Email ID'},
        {'name': 'confirm_email', 'label': 'Confirm Email ID', 'type': 'text', 'placeholder': 'Confirm Email ID'},
        {'name': 'gender', 'label': 'Gender', 'type': 'select', 'options': ['Male', 'Female', 'Other']},
        {'name': 'dob', 'label': 'Date of Birth', 'type': 'date', 'placeholder': ''},
        {'name': 'father_husband_name', 'label': 'Father/Husband Name', 'type': 'text', 'placeholder': 'Enter Relative Name'},
        {'name': 'state', 'label': 'Select State', 'type': 'select', 'options': ['Karnataka', 'Maharashtra', 'Gujarat', 'Goa', 'Tamil Nadu', 'Kerala', 'Andhra Pradesh', 'Telangana']},
        {'name': 'district', 'label': 'District', 'type': 'text', 'placeholder': 'Enter District'},
        {'name': 'taluk', 'label': 'Taluk', 'type': 'text', 'placeholder': 'Enter Taluk'},
        {'name': 'village', 'label': 'Village', 'type': 'text', 'placeholder': 'Enter Village'},
        {'name': 'pincode', 'label': 'Pin Code', 'type': 'text', 'placeholder': 'Enter Pin Code'},
        {'name': 'handicapped', 'label': 'Physical Handicap', 'type': 'select', 'options': ['No', 'Yes']},
        {'name': 'address', 'label': 'Address', 'type': 'textarea', 'placeholder': 'Enter Address'},
        {'name': 'education', 'label': 'Highest Education', 'type': 'select', 'options': ['Non-Matric', 'Matriculation', 'Intermediate', 'Graduate', 'Post-Graduate']},
        {'name': 'photo', 'label': 'Candidate Photo', 'type': 'file', 'placeholder': ''},
        {'name': 'id_proof', 'label': 'ID Proof (Aadhaar/PAN)', 'type': 'file', 'placeholder': ''},
        {'name': 'education_cert', 'label': 'Education Certificate', 'type': 'file', 'placeholder': ''}
    ],
    'basic_computer_certificate': [
        {'name': 'student_name', 'label': 'Student Name', 'type': 'text', 'placeholder': 'Enter Student Name'},
        {'name': 'father_name', 'label': 'Father Name', 'type': 'text', 'placeholder': 'Enter Father Name'},
        {'name': 'mother_name', 'label': 'Mother Name', 'type': 'text', 'placeholder': 'Enter Mother Name'},
        {'name': 'dob', 'label': 'Date of Birth', 'type': 'date', 'placeholder': ''},
        {'name': 'gender', 'label': 'Gender', 'type': 'select', 'options': ['Male', 'Female', 'Other']},
        {'name': 'qualification', 'label': 'Qualification', 'type': 'text', 'placeholder': 'e.g. 10th Standard'},
        {'name': 'cast_category', 'label': 'Cast Category', 'type': 'select', 'options': ['General', 'OBC', 'SC', 'ST']},
        {'name': 'state', 'label': 'State', 'type': 'text', 'placeholder': 'Enter State'},
        {'name': 'district', 'label': 'District', 'type': 'text', 'placeholder': 'Enter District'},
        {'name': 'full_address', 'label': 'Full Address', 'type': 'textarea', 'placeholder': 'Enter Address'},
        {'name': 'pincode', 'label': 'Pin Code', 'type': 'text', 'placeholder': 'Enter Pin Code'},
        {'name': 'mobile_no', 'label': 'Mobile Number', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'email', 'label': 'Email ID', 'type': 'text', 'placeholder': 'Enter Email'},
        {'name': 'photo', 'label': 'Upload Photo', 'type': 'file', 'placeholder': ''}
    ],
    'udyam_registration': [
        {'name': 'aadhaar_no', 'label': 'Enterprise Owner Aadhaar', 'type': 'text', 'placeholder': 'Enter Aadhaar Number'},
        {'name': 'mobile_no', 'label': 'Mobile Linked to Aadhaar', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'enterprise_name', 'label': 'Enterprise Name', 'type': 'text', 'placeholder': 'Enter Business Name'}
    ],
    'pvcmaker': [
        {'name': 'document_name', 'label': 'Document Type', 'type': 'text', 'placeholder': 'e.g. Identity Card'},
        {'name': 'front_image', 'label': 'Upload Front Side (Image/PDF)', 'type': 'file', 'placeholder': ''},
        {'name': 'back_image', 'label': 'Upload Back Side (Image/PDF)', 'type': 'file', 'placeholder': ''}
    ],
    'cibil_score': [
        {'name': 'full_name', 'label': 'Full Name', 'type': 'text', 'placeholder': 'Enter Full Name'},
        {'name': 'pan_no', 'label': 'PAN Number', 'type': 'text', 'placeholder': 'Enter PAN Number'},
        {'name': 'mobile_no', 'label': 'Mobile Number', 'type': 'text', 'placeholder': 'Enter Mobile Number'},
        {'name': 'email', 'label': 'Email Address', 'type': 'text', 'placeholder': 'Enter Email'}
    ]
}


def convert_text_to_pdf_bytes(text_content):
    from reportlab.pdfgen import canvas
    from io import BytesIO
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    y = 800
    p.setFont("Courier", 9)
    for line in text_content.split('\n'):
        p.drawString(50, y, line)
        y -= 15
        if y < 40:
            p.showPage()
            p.setFont("Courier", 9)
            y = 800
    p.save()
    buffer.seek(0)
    return buffer.getvalue()


def generate_mock_pdf(service_name, form_data):
    content = f"""--------------------------------------------------
                 SM SEVAONE PORTAL
         AUTOMATED DOCUMENT RETRIEVAL SYSTEM
--------------------------------------------------
Service Requested: {service_name}
Transaction ID: TXN{random.randint(10000000, 99999999)}
Status: VERIFIED & COMPLETED
Date Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

DETAILS RETRIEVED:
"""
    for key, value in form_data.items():
        content += f"{key.replace('_', ' ').upper()}: {value}\n"
    content += "\n--------------------------------------------------\n"
    content += "This is a computer generated document print copy.\n"
    content += "Verify details before printing onto PVC cards.\n"
    
    file_name = f"{service_name.lower().replace(' ', '_')}_{random.randint(1000, 9999)}.pdf"
    pdf_bytes = convert_text_to_pdf_bytes(content)
    return ContentFile(pdf_bytes, name=file_name)


def generate_completed_govt_document_pdf(app, form_fields):
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from io import BytesIO
    import random
    
    buffer = BytesIO()
    
    # We will generate a standard A4 size certificate for sanction orders,
    # or a card layout for ID card applications!
    if app.service.slug == 'apply_senior':
        # Generate double-sided Senior Citizen ID Card
        p = canvas.Canvas(buffer, pagesize=(350, 220))
        
        # FRONT SIDE
        p.setFillColor(HexColor("#eef2f3"))
        p.rect(10, 10, 330, 200, fill=True, stroke=True)
        p.setFillColor(HexColor("#b30000")) # Maroon header band
        p.rect(10, 180, 330, 30, fill=True, stroke=False)
        p.setFillColor(HexColor("#ffffff"))
        p.setFont("Helvetica-Bold", 8)
        p.drawCentredString(175, 198, "SENIOR CITIZEN IDENTITY CARD")
        p.setFont("Helvetica", 6)
        p.drawCentredString(175, 188, "GOVERNMENT OF KARNATAKA / ಕರ್ನಾಟಕ ಸರ್ಕಾರ")
        
        # Details
        name = form_fields.get('applicant_name', 'Not Available')
        aadhaar = form_fields.get('aadhaar_no', 'Not Available')
        dob = form_fields.get('dob', 'Not Available')
        bg = form_fields.get('blood_group_report', 'O +ve') # Default blood group
        if bg and bg.startswith('/media/'):
            bg = 'O +ve' # Clean dummy text
        mobile = form_fields.get('mobile_no', 'Not Available')
        
        p.setFillColor(HexColor("#000000"))
        p.setFont("Helvetica-Bold", 7)
        p.drawString(20, 150, f"Name: {name.upper()}")
        p.drawString(20, 130, f"DOB: {dob}")
        p.drawString(20, 110, f"Aadhaar: {aadhaar}")
        p.drawString(20, 90, f"Blood Group: {bg}")
        p.drawString(20, 70, f"Mobile: {mobile}")
        
        # Photo placeholder
        p.setFillColor(HexColor("#cccccc"))
        p.rect(250, 60, 70, 90, fill=True, stroke=True)
        p.setFillColor(HexColor("#333333"))
        p.setFont("Helvetica", 6)
        p.drawCentredString(285, 105, "PHOTO")
        
        # Bottom text
        p.setFillColor(HexColor("#444444"))
        p.setFont("Helvetica-Oblique", 6)
        p.drawString(20, 25, "Issued under the authority of Welfare of Senior Citizens Department.")
        
        p.showPage()
        
        # BACK SIDE
        p.setFillColor(HexColor("#eef2f3"))
        p.rect(10, 10, 330, 200, fill=True, stroke=True)
        p.setFillColor(HexColor("#333333")) # Dark header
        p.rect(10, 180, 330, 30, fill=True, stroke=False)
        p.setFillColor(HexColor("#ffffff"))
        p.setFont("Helvetica-Bold", 8)
        p.drawCentredString(175, 192, "EMERGENCY CONTACTS & ADDRESS")
        
        # Details
        address = form_fields.get('address', 'Not Available')
        talluk = form_fields.get('talluk', 'Not Available')
        district = form_fields.get('district', 'Not Available')
        pincode = form_fields.get('pincode', 'Not Available')
        
        p.setFillColor(HexColor("#000000"))
        p.setFont("Helvetica-Bold", 7)
        p.drawString(20, 140, "Address:")
        p.setFont("Helvetica", 7)
        # Handle long address wrap line
        p.drawString(20, 125, address[:45])
        p.drawString(20, 112, address[45:90])
        p.drawString(20, 99, f"Taluk: {talluk}, Dist: {district}")
        p.drawString(20, 86, f"Pin Code: {pincode}")
        
        # Terms / Barcode
        p.rect(200, 30, 120, 25, fill=False, stroke=True)
        p.setFont("Helvetica", 5)
        p.drawCentredString(260, 20, "* This card is non-transferable. If found, please return to ERO office.")
        
        # Draw barcode lines inside rect
        p.setStrokeColor(HexColor("#000000"))
        p.setLineWidth(1)
        for i in range(205, 315, 4):
            if random.choice([True, False]):
                p.line(i, 30, i, 55)
        
        p.save()
    else:
        # Standard A4 size sanction/certificate layout
        p = canvas.Canvas(buffer, pagesize=(595, 842)) # A4
        
        # Border
        p.setLineWidth(2)
        p.rect(20, 20, 555, 802)
        
        # Header
        p.setFillColor(HexColor("#0f172a"))
        p.rect(20, 750, 555, 72, fill=True, stroke=False)
        p.setFillColor(HexColor("#ffffff"))
        p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(297, 792, "GOVERNMENT OF KARNATAKA")
        p.setFont("Helvetica", 10)
        p.drawCentredString(297, 772, f"DEPARTMENT OF E-GOVERNANCE / {app.service.category.upper()}")
        p.setFont("Helvetica-Bold", 11)
        p.drawCentredString(297, 758, f"SANCTION ORDER / REGISTRATION CERTIFICATE")
        
        # Certificate body
        p.setFillColor(HexColor("#000000"))
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, 700, f"Order ID: {app.order_id}")
        p.drawRightString(545, 700, f"Date: {app.created_at.strftime('%d/%m/%Y') if app.created_at else '05/07/2026'}")
        
        p.drawString(50, 670, f"Service Name: {app.service.name.upper()}")
        p.drawString(50, 650, f"Status: COMPLETED (APPROVED)")
        
        # Render details dynamically
        p.line(50, 630, 545, 630)
        p.drawString(50, 610, "APPLICANT SUBMITTED DETAILS:")
        
        y = 580
        p.setFont("Helvetica", 9)
        for key, val in form_fields.items():
            if not isinstance(val, str) or not val.startswith('/media/'):
                p.drawString(60, y, f"• {key.replace('_', ' ').title()}: {val}")
                y -= 20
                if y < 150:
                    break
        
        # Congratulation message
        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y - 30, "DECLARATION & SANCTION APPROVAL:")
        p.setFont("Helvetica-Oblique", 9)
        p.drawString(50, y - 50, f"This is to certify that the request for {app.service.name} has been verified and approved by the competent")
        p.drawString(50, y - 65, "authority. The benefits/certificates associated with this scheme are hereby active and linked.")
        
        # QR Code placeholder
        p.rect(430, 60, 90, 90, fill=False, stroke=True)
        p.setFont("Helvetica", 6)
        p.drawCentredString(475, 105, "[ QR CODE SEAL ]")
        
        # Signature
        p.setFont("Helvetica-Bold", 9)
        p.drawString(50, 85, "Signed Digitally By:")
        p.setFont("Helvetica-Oblique", 9)
        p.drawString(50, 70, "Director of Electronic Services Delivery")
        p.drawString(50, 55, "Government of Karnataka")
        
        p.save()
        
    buffer.seek(0)
    from django.core.files.base import ContentFile
    filename = f"completed_{app.service.slug}_{app.order_id}.pdf"
    return ContentFile(buffer.getvalue(), name=filename)

def draw_front_card(p, pan_number, name, father_name, dob, abs_photo_path, abs_signature_path):
    from reportlab.lib.colors import HexColor
    
    # Save state for card clipping
    p.saveState()
    clip_path = p.beginPath()
    clip_path.rect(0, 0, 330, 200)
    p.clipPath(clip_path, stroke=False, fill=False)
    
    # Background color (Light blue-green gradient/fill)
    p.setFillColor(HexColor("#eef9ff"))
    p.rect(0, 0, 330, 200, fill=True, stroke=False)
    
    # Security Diagonal Lines Pattern
    p.setStrokeColor(HexColor("#dcedf7"))
    p.setLineWidth(0.5)
    for i in range(-110, 340, 15):
        p.line(i, 0, i + 100, 200)
        
    # Faint central security circle watermark
    p.setFillColor(HexColor("#e1f2fc"))
    p.circle(165, 90, 35, fill=True, stroke=False)
    
    # Top Header Band
    p.setFillColor(HexColor("#0f5b78"))
    p.rect(0, 175, 330, 25, fill=True, stroke=False)
    
    # Restore clipping state so border can be drawn normally
    p.restoreState()
    
    # Card outer border
    p.setStrokeColor(HexColor("#999999"))
    p.setLineWidth(0.5)
    p.rect(0, 0, 330, 200, fill=False, stroke=True)
    
    # Header Text
    p.setFillColor(HexColor("#ffffff"))
    p.setFont(FONT_BOLD, 6)
    p.drawString(8, 190, "आयकर विभाग")
    p.drawString(8, 182, "INCOME TAX DEPARTMENT")
    
    p.drawRightString(322, 190, "भारत सरकार")
    p.drawRightString(322, 182, "GOVT. OF INDIA")
    
    # Gold emblem in header center
    p.setFillColor(HexColor("#d4af37"))
    p.circle(165, 187, 7, fill=True, stroke=False)
    p.setFillColor(HexColor("#ffffff"))
    p.setFont(FONT_BOLD, 4)
    p.drawCentredString(165, 185, "GOI")
    
    # Photo (Left Side)
    if abs_photo_path:
        try:
            p.drawImage(abs_photo_path, 10, 85, width=60, height=70)
        except Exception:
            p.setFillColor(HexColor("#dddddd"))
            p.rect(10, 85, 60, 70, fill=True, stroke=True)
            p.setFillColor(HexColor("#777777"))
            p.setFont(FONT_REGULAR, 6)
            p.drawCentredString(40, 117, "PHOTO")
    else:
        p.setFillColor(HexColor("#dddddd"))
        p.rect(10, 85, 60, 70, fill=True, stroke=True)
        p.setFillColor(HexColor("#777777"))
        p.setFont(FONT_REGULAR, 6)
        p.drawCentredString(40, 117, "PHOTO")
        
    # Signature Label
    p.setFillColor(HexColor("#333333"))
    p.setFont(FONT_REGULAR, 4.5)
    p.drawString(10, 33, "हस्ताक्षर / Signature")
    
    # Signature (Bottom-Left)
    if abs_signature_path:
        try:
            p.setFillColor(HexColor("#ffffff"))
            p.rect(10, 10, 60, 20, fill=True, stroke=True)
            p.drawImage(abs_signature_path, 10, 10, width=60, height=20)
        except Exception:
            p.setFillColor(HexColor("#ffffff"))
            p.rect(10, 10, 60, 20, fill=True, stroke=True)
            p.setFillColor(HexColor("#777777"))
            p.setFont(FONT_REGULAR, 5)
            p.drawCentredString(40, 18, "SIGNATURE")
    else:
        p.setFillColor(HexColor("#ffffff"))
        p.rect(10, 10, 60, 20, fill=True, stroke=True)
        p.setFillColor(HexColor("#777777"))
        p.setFont(FONT_REGULAR, 5)
        p.drawCentredString(40, 18, "SIGNATURE")
        
    # PAN Number
    p.setFillColor(HexColor("#0f5b78"))
    p.setFont(FONT_BOLD, 6)
    p.drawString(80, 140, "स्थायी लेखा संख्या / Permanent Account Number")
    p.setFillColor(HexColor("#111111"))
    p.setFont(FONT_BOLD, 13)
    p.drawString(80, 122, pan_number.upper())
    
    # Name
    p.setFillColor(HexColor("#333333"))
    p.setFont(FONT_REGULAR, 5)
    p.drawString(80, 100, "नाम / Name")
    p.setFillColor(HexColor("#000000"))
    p.setFont(FONT_BOLD, 7)
    p.drawString(80, 90, name.upper())
    
    # Father's Name
    p.setFillColor(HexColor("#333333"))
    p.setFont(FONT_REGULAR, 5)
    p.drawString(80, 68, "पिता का नाम / Father's Name")
    p.setFillColor(HexColor("#000000"))
    p.setFont(FONT_BOLD, 7)
    p.drawString(80, 58, father_name.upper())
    
    # Date of Birth
    p.setFillColor(HexColor("#333333"))
    p.setFont(FONT_REGULAR, 5)
    p.drawString(80, 38, "जन्म तिथि / Date of Birth")
    p.setFillColor(HexColor("#000000"))
    p.setFont(FONT_BOLD, 7)
    p.drawString(80, 28, dob)
    
    # QR Code (Right Side)
    try:
        from reportlab.graphics.barcode import createBarcodeDrawing
        qr_val = f"PAN: {pan_number}\nName: {name}\nFather: {father_name}\nDOB: {dob}"
        qr_drawing = createBarcodeDrawing('QR', value=qr_val, width=75, height=75)
        qr_drawing.drawOn(p, 245, 25)
    except Exception:
        p.setFillColor(HexColor("#ffffff"))
        p.rect(245, 25, 75, 75, fill=True, stroke=True)
        p.setFillColor(HexColor("#777777"))
        p.setFont(FONT_REGULAR, 6)
        p.drawCentredString(282, 62, "[ QR CODE ]")

def draw_back_card(p, pan_number):
    from reportlab.lib.colors import HexColor
    
    # Save state for card clipping
    p.saveState()
    clip_path = p.beginPath()
    clip_path.rect(0, 0, 330, 200)
    p.clipPath(clip_path, stroke=False, fill=False)
    
    # Background color
    p.setFillColor(HexColor("#eef9ff"))
    p.rect(0, 0, 330, 200, fill=True, stroke=False)
    
    # Security Diagonal Lines Pattern
    p.setStrokeColor(HexColor("#dcedf7"))
    p.setLineWidth(0.5)
    for i in range(-110, 340, 15):
        p.line(i, 0, i + 100, 200)
        
    p.restoreState()
    
    # Card outer border
    p.setStrokeColor(HexColor("#999999"))
    p.setLineWidth(0.5)
    p.rect(0, 0, 330, 200, fill=False, stroke=True)
    
    p.setFillColor(HexColor("#333333"))
    p.setFont(FONT_REGULAR, 5)
    
    lines = [
        "1. This card is the property of the Income Tax Department.",
        "2. If found, please return to: Income Tax Service Unit,",
        "   NSDL, 5th Floor, Mantri Sterling, Plot No. 341,",
        "   Survey No. 997/8, Model Colony, Pune - 411016.",
        "3. Any unauthorized use or alteration of this card is",
        "   punishable under the Income Tax Act, 1961."
    ]
    
    y = 165
    for line in lines:
        p.drawString(10, y, line)
        y -= 10
        
    # Draw Silver Hologram box on the right side
    p.setFillColor(HexColor("#c0c0c0"))
    p.rect(260, 80, 55, 55, fill=True, stroke=True)
    p.setFillColor(HexColor("#888888"))
    p.setFont(FONT_BOLD, 6)
    p.drawCentredString(287, 112, "HOLO")
    p.drawCentredString(287, 102, "GRAM")
    
    # Draw barcode strip
    p.setFillColor(HexColor("#333333"))
    p.rect(10, 50, 310, 15, fill=True, stroke=False)
    p.setFillColor(HexColor("#ffffff"))
    p.setFont("Courier-Bold", 6)
    p.drawCentredString(165, 54, "* " + pan_number + " *")
    
    # Footer info
    p.setFillColor(HexColor("#0f5b78"))
    p.setFont(FONT_BOLD, 6)
    p.drawCentredString(165, 20, "Helpline: 1800-180-1961 | nsdl.co.in")

def generate_pan_card_pdf(pan_number, name, father_name, dob, photo_path=None, signature_path=None, gender="Male"):
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from io import BytesIO
    from django.core.files.storage import default_storage
    import os
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4) # A4 page size
    
    # Resolve absolute paths for photo and signature
    abs_photo_path = None
    if photo_path and photo_path != "Not uploaded":
        try:
            abs_photo_path = default_storage.path(photo_path)
            if not os.path.exists(abs_photo_path):
                abs_photo_path = None
        except Exception:
            abs_photo_path = None
            
    abs_signature_path = None
    if signature_path and signature_path != "Not uploaded":
        try:
            abs_signature_path = default_storage.path(signature_path)
            if not os.path.exists(abs_signature_path):
                abs_signature_path = None
        except Exception:
            abs_signature_path = None

    # ------------------ e-PAN A4 DOCUMENT HEADER ------------------
    # Header Bilingual Labels
    p.setFillColor(HexColor("#a00000")) # Dark red
    p.setFont(FONT_BOLD, 16)
    p.drawString(45, 800, "आयकर विभाग")
    p.setFillColor(HexColor("#000000"))
    p.setFont(FONT_BOLD, 12)
    p.drawString(45, 785, "INCOME TAX DEPARTMENT")
    
    p.setFillColor(HexColor("#000000"))
    p.setFont(FONT_BOLD, 12)
    p.drawRightString(550, 800, "भारत सरकार")
    p.drawRightString(550, 785, "GOVT. OF INDIA")
    
    # Gold emblem in header center
    p.setFillColor(HexColor("#d4af37"))
    p.circle(297, 795, 11, fill=True, stroke=False)
    p.setFillColor(HexColor("#ffffff"))
    p.setFont(FONT_BOLD, 6)
    p.drawCentredString(297, 792, "GOI")
    
    # e-PAN Blue Banner
    p.setFillColor(HexColor("#0f5b78"))
    p.rect(45, 745, 505, 22, fill=True, stroke=False)
    p.setFillColor(HexColor("#ffffff"))
    p.setFont(FONT_BOLD, 9)
    p.drawCentredString(297, 752, "ई - स्थायी लेखा संख्या  /  e - Permanent Account Number (e-PAN) Card")
    
    # ------------------ e-PAN DETAILS TABLE ------------------
    p.setStrokeColor(HexColor("#999999"))
    p.setLineWidth(0.5)
    p.rect(45, 520, 505, 210, fill=False, stroke=True)
    # Horizontal grid lines
    for y_line in [555, 590, 625, 660, 695]:
        p.line(45, y_line, 550, y_line)
    # Vertical grid line (width 195 points for label, 310 points for value)
    p.line(240, 520, 240, 730)
    
    p.setFillColor(HexColor("#000000"))
    p.setFont(FONT_BOLD, 8)
    
    # Row 1: Acknowledgement Number
    p.drawString(50, 710, "पावती संख्या / Acknowledgement Number")
    ack_number = f"88{random.randint(100000, 999999)}{random.randint(1000, 9999)}"
    p.drawString(245, 710, ack_number)
    try:
        from reportlab.graphics.barcode import createBarcodeDrawing
        barcode = createBarcodeDrawing('Code128', value=ack_number, width=120, height=20)
        barcode.drawOn(p, 420, 705)
    except Exception:
        pass
        
    # Row 2: Name
    p.drawString(50, 675, "नाम / Name")
    p.drawString(245, 675, name.upper())
    
    # Row 3: Father's Name
    p.drawString(50, 640, "पिता का नाम / Father's name")
    p.drawString(245, 640, father_name.upper())
    
    # Row 4: Date of Birth
    p.drawString(50, 605, "जन्म की तारीख / Date of Birth")
    p.drawString(245, 605, dob)
    
    # Row 5: Gender
    p.drawString(50, 570, "लिंग / Gender")
    p.drawString(245, 570, gender.upper())
    
    # Row 6: Communication Address
    p.drawString(50, 535, "संचार का पता / Comm. Address")
    p.drawString(245, 535, "Not Disclosed for Privacy (Electronic Copy)")
    
    # ------------------ VERIFICATION BLOCK ------------------
    # Photo box
    p.rect(45, 435, 60, 70, fill=False, stroke=True)
    if abs_photo_path:
        try:
            p.drawImage(abs_photo_path, 45, 435, width=60, height=70)
        except Exception:
            p.setFont(FONT_REGULAR, 6)
            p.drawCentredString(75, 467, "PHOTO")
    else:
        p.setFont(FONT_REGULAR, 6)
        p.drawCentredString(75, 467, "PHOTO")
        
    # Signature Box
    p.rect(125, 435, 120, 30, fill=False, stroke=True)
    p.setFont(FONT_REGULAR, 5)
    p.drawString(125, 468, "हस्ताक्षर / Signature")
    if abs_signature_path:
        try:
            p.drawImage(abs_signature_path, 125, 435, width=120, height=30)
        except Exception:
            p.drawCentredString(185, 447, "SIGNATURE")
    else:
        p.drawCentredString(185, 447, "SIGNATURE")
        
    # Digital Seal (Signature Not Verified yellow question mark)
    p.setFillColor(HexColor("#fffdf0"))
    p.rect(265, 435, 285, 70, fill=True, stroke=True)
    
    p.setFillColor(HexColor("#e67e22")) # Orange/yellow
    p.setFont(FONT_BOLD, 32)
    p.drawString(278, 452, "?")
    
    p.setFillColor(HexColor("#333333"))
    p.setFont(FONT_BOLD, 7)
    p.drawString(305, 488, "Signature Not Verified")
    p.setFont(FONT_REGULAR, 5.5)
    p.drawString(305, 478, "Digitally signed by Income Tax PAN Services Unit, NSDL.")
    p.drawString(305, 470, "Date: 2026.07.18 10:18:30 IST")
    p.drawString(305, 462, "Reason: NSDL e-PAN Sign")
    p.drawString(305, 454, "Location: Mumbai")
    
    # ------------------ INSTRUCTIONS BLOCK ------------------
    p.setFillColor(HexColor("#000000"))
    p.setFont(FONT_REGULAR, 6)
    
    instructions = [
        "1. Permanent Account Number (PAN) facilitates Income Tax Department linking of various documents, including payment of taxes,",
        "   tax demand, tax arrears, matching of information and easy retrieval of electronic information etc. relating to a taxpayer.",
        "   स्थायी लेखा संख्या (पैन) करदाता से संबंधित विभिन्न दस्तावेजों को जोड़ने में आयकर विभाग को सहायक होता है, जिसमें करों के भुगतान, आकलन,",
        "   कर मांग, टैक्स बकाया, सूचना के मिलान और इलेक्ट्रॉनिक जानकारी का आसान रखरखाव व बहाली आदि भी शामिल है।",
        "2. Quoting of PAN is now mandatory for several transactions specified under Income Tax Act, 1961 (Refer Rule 114B).",
        "   आयकर अधिनियम, 1961 के तहत निर्दिष्ट कई लेनदेन के लिए स्थायी लेखा संख्या (पैन) का उल्लेख अब अनिवार्य है (नियम 114B का संदर्भ लें)।",
        "3. Possessing or using more than one PAN is against the law & may attract penalty of up to Rs. 10,000.",
        "   एक से अधिक स्थायी लेखा संख्या (पैन) का रखना या उपयोग करना, कानून के विरुद्ध है और इसके लिए 10,000 रुपये तक का दंड लगाया जा सकता है।"
    ]
    
    y_inst = 410
    for line in instructions:
        p.drawString(45, y_inst, line)
        y_inst -= 10
        
    # Scissors and Dotted Cut Line
    p.setStrokeColor(HexColor("#999999"))
    p.setDash(2, 2)
    p.line(45, 260, 550, 260)
    p.setFont(FONT_BOLD, 6)
    p.drawCentredString(297, 263, "- - - - - - - - - - - - - - - - - - - - - - - - - - - CUT HERE - - - - - - - - - - - - - - - - - - - - - - - - - - -")
    p.setDash() # Reset dash
    
    # ------------------ BOTTOM CARDS (FRONT & BACK) ------------------
    # Draw Front Card (Left side at the bottom)
    p.saveState()
    p.translate(45, 75)
    p.scale(240/330, 150/200)
    draw_front_card(p, pan_number, name, father_name, dob, abs_photo_path, abs_signature_path)
    p.restoreState()
    
    # Draw Back Card (Right side at the bottom)
    p.saveState()
    p.translate(310, 75)
    p.scale(240/330, 150/200)
    draw_back_card(p, pan_number)
    p.restoreState()
    
    p.save()
    buffer.seek(0)
    file_name = f"pan_card_{pan_number}_{random.randint(1000, 9999)}.pdf"
    return ContentFile(buffer.getvalue(), name=file_name)


def generate_voter_card_pdf(epic_no, name, father_name, gender, age, state, district, assembly, polling_station):
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from io import BytesIO
    import random
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=(350, 220))
    
    # FRONT SIDE
    p.setFillColor(HexColor("#f4f4f4"))
    p.rect(10, 10, 330, 200, fill=True, stroke=True)
    
    p.setFillColor(HexColor("#2c3e50"))
    p.rect(10, 185, 330, 25, fill=True, stroke=False)
    
    p.setFillColor(HexColor("#ffffff"))
    p.setFont("Helvetica-Bold", 6)
    p.drawString(18, 200, "भारत निर्वाचन आयोग")
    p.drawString(18, 192, "ELECTION COMMISSION OF INDIA")
    
    p.setFillColor(HexColor("#000000"))
    p.setFont("Helvetica-Bold", 7)
    p.drawCentredString(175, 175, "मतदाता फोटो पहचान पत्र / ELECTOR PHOTO IDENTITY CARD")
    
    # EPIC Number
    p.setFont("Helvetica-Bold", 9)
    p.drawString(20, 155, epic_no.upper())
    
    # Details
    p.setFont("Helvetica-Bold", 6)
    p.drawString(20, 135, "नाम / Name:")
    p.setFont("Helvetica-Bold", 8)
    p.drawString(20, 125, name.upper())
    
    p.setFont("Helvetica-Bold", 6)
    p.drawString(20, 110, "सम्बन्धी का नाम / Relation Name:")
    p.setFont("Helvetica-Bold", 8)
    p.drawString(20, 100, father_name.upper())
    
    p.setFont("Helvetica-Bold", 6)
    p.drawString(20, 85, "लिंग / Gender:")
    p.setFont("Helvetica-Bold", 8)
    p.drawString(20, 75, gender.upper())
    
    p.setFont("Helvetica-Bold", 6)
    p.drawString(120, 85, "आयु / Age:")
    p.setFont("Helvetica-Bold", 8)
    p.drawString(120, 75, str(age))
    
    # Photo Placeholder
    p.setFillColor(HexColor("#dddddd"))
    p.rect(260, 80, 65, 75, fill=True, stroke=True)
    p.setFillColor(HexColor("#777777"))
    p.setFont("Helvetica", 6)
    p.drawCentredString(292, 115, "PHOTO")
    
    # BACK SIDE
    p.showPage()
    
    p.setFillColor(HexColor("#f4f4f4"))
    p.rect(10, 10, 330, 200, fill=True, stroke=True)
    
    # Details on back
    p.setFillColor(HexColor("#000000"))
    p.setFont("Helvetica-Bold", 6)
    p.drawString(20, 175, "विधानसभा क्षेत्र / Assembly Constituency:")
    p.setFont("Helvetica", 7)
    p.drawString(20, 165, assembly.upper())
    
    p.setFont("Helvetica-Bold", 6)
    p.drawString(20, 145, "भाग संख्या और नाम / Part No. & Name:")
    p.setFont("Helvetica", 7)
    p.drawString(20, 135, polling_station.upper())
    
    p.setFont("Helvetica-Bold", 6)
    p.drawString(20, 115, "राज्य / State:")
    p.setFont("Helvetica", 7)
    p.drawString(20, 105, state.upper())
    
    p.setFont("Helvetica-Bold", 6)
    p.drawString(150, 115, "जिला / District:")
    p.setFont("Helvetica", 7)
    p.drawString(150, 105, district.upper())
    
    # Signature of ERO
    p.rect(250, 45, 75, 25, fill=False, stroke=True)
    p.setFont("Helvetica", 5)
    p.drawCentredString(287, 35, "निर्वाचक रजिस्ट्रीकरण अधिकारी")
    p.drawCentredString(287, 28, "Electoral Registration Officer")
    
    # Barcode
    p.setFillColor(HexColor("#333333"))
    p.rect(20, 45, 180, 15, fill=True, stroke=False)
    p.setFillColor(HexColor("#ffffff"))
    p.setFont("Courier-Bold", 6)
    p.drawCentredString(110, 49, epic_no)
    
    p.save()
    buffer.seek(0)
    file_name = f"voter_card_{epic_no}_{random.randint(1000, 9999)}.pdf"
    return ContentFile(buffer.getvalue(), name=file_name)


def generate_dl_card_pdf(dl_no, name, dob, validity, status, address, cov):
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from io import BytesIO
    import random
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=(350, 220))
    
    # FRONT SIDE
    p.setFillColor(HexColor("#fffdf0")) # Light gold/yellow background
    p.rect(10, 10, 330, 200, fill=True, stroke=True)
    
    p.setFillColor(HexColor("#2980b9"))
    p.rect(10, 185, 330, 25, fill=True, stroke=False)
    
    p.setFillColor(HexColor("#ffffff"))
    p.setFont("Helvetica-Bold", 6)
    p.drawString(18, 200, "भारतीय संघ / UNION OF INDIA")
    p.drawString(18, 192, "चालन अनुज्ञप्ति / DRIVING LICENCE")
    
    p.setFillColor(HexColor("#000000"))
    # Licence No
    p.setFont("Helvetica-Bold", 8)
    p.drawString(20, 165, f"Licence No: {dl_no.upper()}")
    
    # Smart Chip Placeholder
    p.setFillColor(HexColor("#f39c12"))
    p.rect(20, 125, 25, 20, fill=True, stroke=True)
    p.setFillColor(HexColor("#000000"))
    p.setFont("Helvetica", 5)
    p.drawCentredString(32, 132, "CHIP")
    
    # Details
    p.setFont("Helvetica-Bold", 6)
    p.drawString(60, 145, "Name:")
    p.setFont("Helvetica", 7)
    p.drawString(60, 135, name.upper())
    
    p.setFont("Helvetica-Bold", 6)
    p.drawString(60, 120, "D.O.B:")
    p.setFont("Helvetica", 7)
    p.drawString(60, 110, dob)
    
    p.setFont("Helvetica-Bold", 6)
    p.drawString(150, 120, "COV (Vehicles):")
    p.setFont("Helvetica", 7)
    p.drawString(150, 110, cov.upper())
    
    # Address
    p.setFont("Helvetica-Bold", 6)
    p.drawString(20, 95, "Address:")
    p.setFont("Helvetica", 7)
    p.drawString(20, 85, address[:50].upper())
    if len(address) > 50:
        p.drawString(20, 75, address[50:100].upper())
        
    # Validity
    p.setFont("Helvetica-Bold", 6)
    p.drawString(20, 55, "Validity (NT):")
    p.setFont("Helvetica", 7)
    p.drawString(20, 45, validity)
    
    p.drawString(150, 55, "Status:")
    p.drawString(150, 45, status.upper())
    
    # Photo Placeholder
    p.setFillColor(HexColor("#dddddd"))
    p.rect(260, 95, 65, 75, fill=True, stroke=True)
    p.setFillColor(HexColor("#777777"))
    p.setFont("Helvetica", 6)
    p.drawCentredString(292, 130, "PHOTO")
    
    # Signature Placeholder
    p.setFillColor(HexColor("#ffffff"))
    p.rect(260, 60, 65, 20, fill=True, stroke=True)
    p.setFillColor(HexColor("#777777"))
    p.drawCentredString(292, 67, "SIGNATURE")
    
    # BACK SIDE
    p.showPage()
    
    p.setFillColor(HexColor("#fffdf0"))
    p.rect(10, 10, 330, 200, fill=True, stroke=True)
    
    # Terms / Disclaimer
    p.setFillColor(HexColor("#333333"))
    p.setFont("Helvetica", 5)
    
    lines = [
        "1. This licence is valid throughout India.",
        "2. If found, please return to the issuing authority / RTO.",
        "3. Any alteration or unauthorized possession is an offence.",
        "4. Helpline: 1800-180-0120 | transport.gov.in"
    ]
    
    y = 160
    for line in lines:
        p.drawString(20, y, line)
        y -= 12
        
    # Barcode
    p.setFillColor(HexColor("#333333"))
    p.rect(20, 60, 310, 15, fill=True, stroke=False)
    p.setFillColor(HexColor("#ffffff"))
    p.setFont("Courier-Bold", 6)
    p.drawCentredString(175, 64, "* " + dl_no + " *")
    
    p.save()
    buffer.seek(0)
    file_name = f"dl_card_{dl_no}_{random.randint(1000, 9999)}.pdf"
    return ContentFile(buffer.getvalue(), name=file_name)


def generate_vehicle_rc_pdf(reg_no, owner, model, fuel, reg_date, chassis, engine, insurance):
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from io import BytesIO
    import random
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=(350, 220))
    
    # FRONT SIDE
    p.setFillColor(HexColor("#eef4f8")) # Light blue background
    p.rect(10, 10, 330, 200, fill=True, stroke=True)
    
    p.setFillColor(HexColor("#2c3e50"))
    p.rect(10, 185, 330, 25, fill=True, stroke=False)
    
    p.setFillColor(HexColor("#ffffff"))
    p.setFont("Helvetica-Bold", 6)
    p.drawString(18, 200, "सड़क परिवहन और राजमार्ग मंत्रालय / MINISTRY OF ROAD TRANSPORT")
    p.drawString(18, 192, "पंजीकरण प्रमाण पत्र / REGISTRATION CERTIFICATE")
    
    p.setFillColor(HexColor("#000000"))
    # Registration No
    p.setFont("Helvetica-Bold", 8)
    p.drawString(20, 165, f"Reg No: {reg_no.upper()}")
    
    # Smart Chip Placeholder
    p.setFillColor(HexColor("#f39c12"))
    p.rect(20, 125, 25, 20, fill=True, stroke=True)
    p.setFillColor(HexColor("#000000"))
    p.setFont("Helvetica", 5)
    p.drawCentredString(32, 132, "CHIP")
    
    # Details
    p.setFont("Helvetica-Bold", 6)
    p.drawString(60, 145, "Owner Name:")
    p.setFont("Helvetica", 7)
    p.drawString(60, 135, owner.upper())
    
    p.setFont("Helvetica-Bold", 6)
    p.drawString(60, 120, "Model:")
    p.setFont("Helvetica", 7)
    p.drawString(60, 110, model.upper())
    
    p.setFont("Helvetica-Bold", 6)
    p.drawString(180, 120, "Fuel Type:")
    p.setFont("Helvetica", 7)
    p.drawString(180, 110, fuel.upper())
    
    p.setFont("Helvetica-Bold", 6)
    p.drawString(20, 95, "Registration Date:")
    p.setFont("Helvetica", 7)
    p.drawString(20, 85, reg_date)
    
    p.drawString(150, 95, "Insurance Valid Upto:")
    p.setFont("Helvetica", 7)
    p.drawString(150, 85, insurance)
    
    # State RTO seal placeholder
    p.setFillColor(HexColor("#ffffff"))
    p.circle(280, 60, 25, fill=True, stroke=True)
    p.setFillColor(HexColor("#1b5e20"))
    p.setFont("Helvetica-Bold", 4)
    p.drawCentredString(280, 65, "STATE RTO")
    p.drawCentredString(280, 58, "OFFICIAL SEAL")
    
    # BACK SIDE
    p.showPage()
    
    p.setFillColor(HexColor("#eef4f8"))
    p.rect(10, 10, 330, 200, fill=True, stroke=True)
    
    p.setFillColor(HexColor("#000000"))
    p.setFont("Helvetica-Bold", 6)
    p.drawString(20, 170, "Chassis Number:")
    p.setFont("Helvetica", 7)
    p.drawString(20, 160, chassis.upper())
    
    p.drawString(20, 140, "Engine Number:")
    p.setFont("Helvetica", 7)
    p.drawString(20, 130, engine.upper())
    
    p.drawString(20, 110, "Tax Paid Details:")
    p.setFont("Helvetica", 7)
    p.drawString(20, 100, "One-Time Tax Paid (LTT)")
    
    # Disclaimer
    p.setFillColor(HexColor("#333333"))
    p.setFont("Helvetica", 5)
    p.drawString(20, 40, "Helpline: 1800-180-0120 | parivahan.gov.in")
    
    # Barcode
    p.setFillColor(HexColor("#333333"))
    p.rect(20, 60, 310, 15, fill=True, stroke=False)
    p.setFillColor(HexColor("#ffffff"))
    p.setFont("Courier-Bold", 6)
    p.drawCentredString(175, 64, "* " + reg_no + " *")
    
    p.save()
    buffer.seek(0)
    file_name = f"rc_card_{reg_no}_{random.randint(1000, 9999)}.pdf"
    return ContentFile(buffer.getvalue(), name=file_name)


# Authentication Views
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        # Django authenticates on username, we resolve email to username
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            username = email # Fallback to entering username directly
            
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if hasattr(user, 'profile') and user.profile.status != 'Active':
                messages.error(request, "Your account has been deactivated. Please contact support.")
            else:
                login(request, user)
                return redirect('dashboard')
        else:
            messages.error(request, "Invalid email or password.")
            
    return render(request, 'core/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        state = request.POST.get('state', '').strip()
        address = request.POST.get('address', '').strip()
        password = request.POST.get('password', '')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, 'core/register.html')
            
        # Create user
        # Standard username will be email address
        username = email.split('@')[0] + str(random.randint(100, 999))
        while User.objects.filter(username=username).exists():
            username = email.split('@')[0] + str(random.randint(100, 999))
            
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=full_name
        )
        
        # Profile is created via post_save signal. Retrieve it and update other fields
        profile = user.profile
        profile.mobile_number = phone
        profile.state = state
        profile.address = address
        profile.save()
        
        # Auto log in user
        login(request, user)
        messages.success(request, "Account created successfully!")
        return redirect('dashboard')
        
    return render(request, 'core/register.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# Dashboard
@login_required
def dashboard(request):
    profile = request.user.profile
    
    # Calculate stats
    total_spent = ServiceApplication.objects.filter(
        user=request.user, 
        status='COMPLETED'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    pending_apps = ServiceApplication.objects.filter(
        user=request.user, 
        status='PENDING'
    ).count()
    
    completed_apps = ServiceApplication.objects.filter(
        user=request.user, 
        status='COMPLETED'
    ).count()
    
    # Recent requests
    recent_applications = ServiceApplication.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    recent_topups = TopupRequest.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    context = {
        'profile': profile,
        'total_spent': total_spent,
        'pending_apps': pending_apps,
        'completed_apps': completed_apps,
        'recent_applications': recent_applications,
        'recent_topups': recent_topups,
    }
    return render(request, 'core/dashboard.html', context)


# Wallet Page
@login_required
def wallet(request):
    if request.method == 'POST':
        amount_str = request.POST.get('amount', '0')
        utr = request.POST.get('utr', '').strip()
        demo_mode = request.POST.get('demo_mode', 'false') == 'true'
        
        try:
            amount = Decimal(amount_str)
        except ValueError:
            messages.error(request, "Invalid amount entered.")
            return redirect('wallet')
            
        if amount < Decimal('200.00'):
            messages.error(request, "Minimum recharge amount is ₹200.")
            return redirect('wallet')
            
        profile = request.user.profile
        
        if demo_mode:
            # Auto-approve instantly
            topup = TopupRequest.objects.create(
                user=request.user,
                amount=amount,
                balance_before=profile.wallet_balance,
                balance_after=profile.wallet_balance + amount,
                payment_method='Demo Instant Credit',
                transaction_id_utr=f"DEMO{random.randint(100000, 999999)}",
                status='APPROVED'
            )
            profile.wallet_balance += amount
            profile.save()
            messages.success(request, f"Wallet instantly charged with ₹{amount} (Demo Mode).")
        else:
            if not utr:
                messages.error(request, "UTR / UPI Reference transaction ID is required.")
                return redirect('wallet')
                
            # Put in pending
            TopupRequest.objects.create(
                user=request.user,
                amount=amount,
                balance_before=profile.wallet_balance,
                payment_method='UPI QR Code',
                transaction_id_utr=utr,
                status='PENDING'
            )
            messages.success(request, "Recharge request submitted. It will be credited after admin verification (normally 5-10 minutes).")
            
        return redirect('wallet_history')
        
    return render(request, 'core/wallet.html')


@login_required
def wallet_history(request):
    requests = TopupRequest.objects.filter(user=request.user).order_by('-created_at')
    
    # Simple search filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        requests = requests.filter(status=status_filter)
        
    context = {
        'requests': requests,
        'status_filter': status_filter
    }
    return render(request, 'core/wallet_history.html', context)


# Service List Views
@login_required
def services_list(request, category_slug):
    # Mapping slugs to actual category names
    cat_map = {
        'govt-services': 'Govt Services',
        'print-services': 'Print Services',
        'other-services': 'Other Services'
    }
    
    category_name = cat_map.get(category_slug, 'Govt Services')
    services = Service.objects.filter(category=category_name, is_active=True).order_by('name')
    
    # Subcategory grouping for Print Services
    subcategories = {}
    if category_slug == 'print-services':
        subcategories['ration_card'] = services.filter(subcategory='Ration Card')
        subcategories['voter_services'] = services.filter(subcategory='Voter Services')
        subcategories['dl_services'] = services.filter(subcategory='DL Services')
        subcategories['vehicle_services'] = services.filter(subcategory='Vehicle Services')
        subcategories['pan_services'] = services.filter(subcategory='PAN Services')
            
    context = {
        'category_slug': category_slug,
        'category_title': dict(Service.CATEGORY_CHOICES).get(category_name),
        'services': services,
        'subcategories': subcategories
    }
    return render(request, 'core/services_list.html', context)


# Apply for a specific service
@login_required
def apply_service(request, service_slug):
    service = get_object_or_404(Service, slug=service_slug, is_active=True)
    fields = SERVICE_FIELDS.get(service_slug, [])
    profile = request.user.profile
    
    if request.method == 'POST':
        # Wallet Balance Validation
        if profile.wallet_balance < service.cost:
            messages.error(request, f"Insufficient wallet balance. This service costs ₹{service.cost}. Your balance is ₹{profile.wallet_balance}.")
            return redirect('apply_service', service_slug=service_slug)
            
        # Parse Form Fields
        form_data = {}
        for field in fields:
            if field['type'] == 'file':
                # Handle file upload mock storing
                uploaded_file = request.FILES.get(field['name'])
                if uploaded_file:
                    path = default_storage.save(f"uploads/{request.user.username}/{uploaded_file.name}", uploaded_file)
                    form_data[field['name']] = path
                else:
                    form_data[field['name']] = "Not uploaded"
            else:
                form_data[field['name']] = request.POST.get(field['name'], '').strip()
                
        # Deduct Balance
        balance_before = profile.wallet_balance
        profile.wallet_balance -= service.cost
        profile.save()
        balance_after = profile.wallet_balance
        
        # Create Service Application
        app = ServiceApplication.objects.create(
            user=request.user,
            service=service,
            amount=service.cost,
            balance_before=balance_before,
            balance_after=balance_after,
            form_data=form_data,
            status='PENDING'
        )
        
        # If Automated, process it immediately!
        # If Automated, process it immediately!
        if service.service_type == 'Automated':
            if service.slug == 'voter_pdf_instant':
                from .automation import surepass
                epic_no = form_data.get('epic_number', '')
                client_id = surepass.generate_surepass_otp(epic_no)
                if not client_id:
                    profile.wallet_balance += service.cost
                    profile.save()
                    app.balance_after = profile.wallet_balance
                    app.status = 'REJECTED'
                    app.admin_notes = "Failed to trigger OTP via Surepass API. Cost refunded."
                    app.save()
                    messages.error(request, "Failed to trigger OTP verification code. Please check details and try again. Wallet balance refunded.")
                    return redirect('transaction_history')
                form_data['otp_client_id'] = client_id
                app.form_data = form_data
                app.status = 'PENDING_OTP'
                app.save()
                messages.success(request, "OTP has been successfully triggered to your registered mobile number.")
                return redirect('verify_otp', app_id=app.id)
            elif service.slug == 'rc_dwnld':
                rc_no = form_data.get('ration_card_no', '')
                result_file = download_ration_card_automated(rc_no)
                if not result_file:
                    profile.wallet_balance += service.cost
                    profile.save()
                    app.balance_after = profile.wallet_balance
                    app.status = 'REJECTED'
                    app.admin_notes = "Automated Selenium scraping failed."
                    app.save()
                    messages.error(request, "Failed to retrieve Ration Card details from government portal. Wallet balance refunded.")
                    return redirect('transaction_history')
                app.result_file.save(result_file.name, result_file)
                app.admin_notes = "Retrieved via Automated Selenium Web Scraper."
            elif service.slug == 'slct_offlinedist':
                rc_no = form_data.get('customer_rc_no', '')
                result_file = download_ration_card_automated(rc_no)
                if not result_file:
                    profile.wallet_balance += service.cost
                    profile.save()
                    app.balance_after = profile.wallet_balance
                    app.status = 'REJECTED'
                    app.admin_notes = "Automated Offline Bypass Scraper failed."
                    app.save()
                    messages.error(request, "Failed to retrieve Ration Card details from offline bypass portal. Wallet balance refunded.")
                    return redirect('transaction_history')
                app.result_file.save(result_file.name, result_file)
                app.admin_notes = "Retrieved via Automated Offline Bypass Scraper."
            else:
                # Dispatch other automated services to Surepass APIs
                from .automation import surepass
                api_data = None
                
                # Voter services
                if service.slug == 'original_voter_pdf':
                    epic_number = form_data.get('epic_number', '')
                    api_data = surepass.verify_voter_card(epic_number)
                    
                # Driving Licence services
                elif service.slug in ['dlallindia', 'dl_karnataka']:
                    dl_no = form_data.get('dl_number', '')
                    dob = form_data.get('dob', '2000-01-01')
                    try:
                        if '-' in dob:
                            parts = dob.split('-')
                            if len(parts) == 3:
                                dob = f"{parts[2]}-{parts[1]}-{parts[0]}"
                    except Exception:
                        pass
                    api_data = surepass.verify_driving_license(dl_no, dob)
                    
                # Vehicle RC services
                elif service.slug in ['allind_adv', 'rckar_pvc']:
                    vehicle_no = form_data.get('vehicle_no', '')
                    api_data = surepass.verify_vehicle_rc(vehicle_no)
                    
                # PAN services
                elif service.slug == 'pan_card_print':
                    pan_no = form_data.get('pan_number', '')
                    api_data = surepass.verify_pan_card(pan_no)
                    
                # Aadhaar PAN Link status / PAN Find
                elif service.slug == 'aadhaar_panstatus':
                    aadhaar_no = form_data.get('aadhaar_no', '')
                    api_data = surepass.check_pan_aadhaar_status(aadhaar_no)
                    
                # CIBIL services
                elif service.slug == 'cibil_score':
                    pan_no = form_data.get('pan_no', '')
                    name = form_data.get('full_name', '')
                    mobile = form_data.get('mobile_no', '')
                    dob = '1990-01-01'
                    api_data = surepass.verify_cibil(pan_no, name, mobile, dob)
                
                # If API returned real data, compile it into a real PDF card layout
                if api_data:
                    # Check if API returned an official base64 PDF directly (e.g. real PAN/Voter/Aadhaar)
                    pdf_base64 = api_data.get('pdf') or api_data.get('file') or api_data.get('pdf_base64')
                    if pdf_base64:
                        import base64
                        from django.core.files.base import ContentFile
                        try:
                            pdf_bytes = base64.b64decode(pdf_base64)
                            filename = f"official_{service.slug}_{app.order_id}.pdf"
                            result_file = ContentFile(pdf_bytes, name=filename)
                            app.result_file.save(result_file.name, result_file)
                            app.admin_notes = "Retrieved official government PDF document directly via Surepass API."
                            app.status = 'COMPLETED'
                            app.save()
                            messages.success(request, f"Official {service.name} downloaded successfully.")
                            return redirect('transaction_history')
                        except Exception:
                            pass

                    if service.slug == 'pan_card_print':
                        pan_no = api_data.get('pan_number') or form_data.get('pan_number') or ''
                        name = api_data.get('name') or form_data.get('full_name') or 'Not Available'
                        father = api_data.get('father_name') or form_data.get('father_name') or 'Not Available'
                        
                        dob_val = api_data.get('dob') or form_data.get('dob') or '1990-01-01'
                        # Format YYYY-MM-DD from HTML date picker to Indian standard DD/MM/YYYY
                        try:
                            if '-' in dob_val:
                                parts = dob_val.split('-')
                                if len(parts) == 3:
                                    dob_val = f"{parts[2]}/{parts[1]}/{parts[0]}"
                        except Exception:
                            pass
                        
                        # Pass uploaded photo and signature paths to card generator
                        photo_path = form_data.get('photo')
                        signature_path = form_data.get('signature')
                        gender = form_data.get('gender') or api_data.get('gender') or 'Male'
                        result_file = generate_pan_card_pdf(pan_no, name, father, dob_val, photo_path, signature_path, gender)
                    elif service.slug in ['voter_pdf_instant', 'original_voter_pdf']:
                        epic_no = api_data.get('epic_no', 'TEST1234567')
                        name = api_data.get('name', 'Not Available')
                        father = api_data.get('father_name', 'Not Available')
                        gender = api_data.get('gender', 'Male')
                        age = api_data.get('age', '35')
                        state = api_data.get('state', 'Karnataka')
                        district = api_data.get('district', 'Bengaluru')
                        assembly = api_data.get('assembly', 'Assembly Const 10')
                        station = api_data.get('polling_station', 'Polling Station 5')
                        result_file = generate_voter_card_pdf(epic_no, name, father, gender, age, state, district, assembly, station)
                    elif service.slug in ['dlallindia', 'dl_karnataka']:
                        dl_no = api_data.get('dl_number', 'KA01123456789')
                        name = api_data.get('name', 'Not Available')
                        dob = api_data.get('dob', '01/01/1990')
                        val = api_data.get('valid_till', '01/01/2040')
                        status = api_data.get('status', 'Active')
                        addr = api_data.get('address', 'Bengaluru, Karnataka')
                        cov = api_data.get('cov', 'MCWG, LMV')
                        result_file = generate_dl_card_pdf(dl_no, name, dob, val, status, addr, cov)
                    elif service.slug in ['allind_adv', 'rckar_pvc']:
                        reg_no = api_data.get('registration_no', 'KA01AB1234')
                        owner = api_data.get('owner_name', 'Not Available')
                        model = api_data.get('model', 'Not Available')
                        fuel = api_data.get('fuel_type', 'Petrol')
                        reg_date = api_data.get('registration_date', '01/01/2020')
                        chassis = api_data.get('chassis_no', 'TESTCHASSIS123')
                        engine = api_data.get('engine_no', 'TESTENGINE123')
                        ins = api_data.get('insurance_validity', '01/01/2027')
                        result_file = generate_vehicle_rc_pdf(reg_no, owner, model, fuel, reg_date, chassis, engine, ins)
                    else:
                        result_file = generate_mock_pdf(service.name, api_data)
                    app.result_file.save(result_file.name, result_file)
                    app.admin_notes = "Retrieved via Live Surepass.io Verification API."
                else:
                    profile.wallet_balance += service.cost
                    profile.save()
                    app.balance_after = profile.wallet_balance
                    app.status = 'REJECTED'
                    app.admin_notes = "Surepass API query failed."
                    app.save()
                    messages.error(request, f"Failed to retrieve/verify details from government database for '{service.name}'. Your wallet balance has been refunded.")
                    return redirect('transaction_history')
            
            app.status = 'COMPLETED'
            app.save()
            messages.success(request, f"Service '{service.name}' applied and processed instantly! Balance deducted: ₹{service.cost}.")
        else:
            # Trigger government submission webhook for automation bot/agent
            from .automation import webhooks
            webhooks.trigger_service_webhook(app)
            messages.success(request, f"Application for '{service.name}' submitted successfully. Balance deducted: ₹{service.cost}. Normally completed in 12-24 hours.")
            
        return redirect('transaction_history')
        
    context = {
        'service': service,
        'fields': fields,
        'wallet_balance': profile.wallet_balance,
        'remaining_needed': max(Decimal('0.00'), service.cost - profile.wallet_balance)
    }
    return render(request, 'core/apply_service.html', context)


@login_required
def transaction_history(request):
    apps = ServiceApplication.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by search query or status
    status_filter = request.GET.get('status', '')
    if status_filter:
        apps = apps.filter(status=status_filter)
        
    context = {
        'apps': apps,
        'status_filter': status_filter
    }
    return render(request, 'core/transaction_history.html', context)


# Profile & Settings
@login_required
def profile_view(request):
    profile = request.user.profile
    
    if request.method == 'POST':
        # Update profile settings
        full_name = request.POST.get('full_name', '').strip()
        mobile = request.POST.get('mobile_number', '').strip()
        state = request.POST.get('state', '').strip()
        address = request.POST.get('address', '').strip()
        
        # Update user
        request.user.first_name = full_name
        request.user.save()
        
        # Update profile
        profile.mobile_number = mobile
        profile.state = state
        profile.address = address
        profile.save()
        
        messages.success(request, "Profile updated successfully.")
        return redirect('profile')
        
    return render(request, 'core/profile.html')


@login_required
def change_password(request):
    if request.method == 'POST':
        old_pw = request.POST.get('old_password', '')
        new_pw = request.POST.get('new_password', '')
        confirm_pw = request.POST.get('confirm_password', '')
        
        if not request.user.check_password(old_pw):
            messages.error(request, "Incorrect current password.")
            return redirect('profile')
            
        if new_pw != confirm_pw:
            messages.error(request, "New passwords do not match.")
            return redirect('profile')
            
        request.user.set_password(new_pw)
        request.user.save()
        # Keep user logged in after password change
        login(request, request.user)
        messages.success(request, "Password changed successfully!")
        return redirect('profile')
        
    return redirect('profile')


# Static pricing and FAQ views
@login_required
def pricing(request):
    services = Service.objects.filter(is_active=True).order_by('category', 'name')
    context = {
        'services': services
    }
    return render(request, 'core/pricing.html', context)


@login_required
def faq(request):
    return render(request, 'core/faq.html')


# Staff/Superuser Panel
@staff_member_required
def admin_panel(request):
    pending_topups = TopupRequest.objects.filter(status='PENDING').order_by('-created_at')
    pending_applications = ServiceApplication.objects.filter(status='PENDING').order_by('-created_at')
    
    context = {
        'pending_topups': pending_topups,
        'pending_applications': pending_applications
    }
    return render(request, 'core/admin_panel.html', context)


@staff_member_required
def admin_approve_topup(request, topup_id):
    topup = get_object_or_404(TopupRequest, id=topup_id, status='PENDING')
    profile = topup.user.profile
    
    # Record balance logs
    topup.balance_before = profile.wallet_balance
    profile.wallet_balance += topup.amount
    profile.save()
    topup.balance_after = profile.wallet_balance
    topup.status = 'APPROVED'
    topup.admin_notes = f"Approved by admin {request.user.username} on {timezone.now().strftime('%Y-%m-%d')}"
    topup.save()
    
    messages.success(request, f"Topup request for user {topup.user.username} (₹{topup.amount}) APPROVED.")
    return redirect('admin_panel')


@staff_member_required
def admin_reject_topup(request, topup_id):
    topup = get_object_or_404(TopupRequest, id=topup_id, status='PENDING')
    topup.status = 'REJECTED'
    topup.admin_notes = request.POST.get('admin_notes', 'Rejected by admin.')
    topup.save()
    
    messages.success(request, f"Topup request for user {topup.user.username} (₹{topup.amount}) REJECTED.")
    return redirect('admin_panel')


@staff_member_required
def admin_complete_application(request, app_id):
    app = get_object_or_404(ServiceApplication, id=app_id, status='PENDING')
    
    if request.method == 'POST':
        result_file = request.FILES.get('result_file')
        admin_notes = request.POST.get('admin_notes', '').strip()
        
        if result_file:
            app.result_file = result_file
            app.status = 'COMPLETED'
            app.admin_notes = admin_notes
            app.save()
            messages.success(request, f"Application {app.order_id} marked as COMPLETED and file uploaded.")
        else:
            messages.error(request, "Please upload the result document file (PDF).")
            
    return redirect('admin_panel')


@staff_member_required
def admin_reject_application(request, app_id):
    app = get_object_or_404(ServiceApplication, id=app_id, status='PENDING')
    
    # Refund user wallet!
    profile = app.user.profile
    refund_amount = app.amount
    
    app.status = 'REJECTED'
    app.admin_notes = request.POST.get('admin_notes', 'Rejected and refunded. Details invalid or document not found.')
    app.save()
    
    # Process Refund
    profile.wallet_balance += refund_amount
    profile.save()
    
    messages.success(request, f"Application {app.order_id} REJECTED. Refund of ₹{refund_amount} credited back to user's wallet.")
    return redirect('admin_panel')


@login_required
def rc_wotp_short_rc(request):
    app_id = request.GET.get('no', '')
    
    # Try to fetch the application by ID
    app = None
    card_number = "540400321829"  # Default fallback card number
    
    if app_id.isdigit():
        try:
            app = ServiceApplication.objects.get(id=int(app_id))
            card_number = app.form_data.get('ration_card_no', app.form_data.get('customer_rc_no', card_number))
        except ServiceApplication.DoesNotExist:
            pass
            
    # If the card number matches our special real card 540400321829:
    if card_number == "540400321829":
        card_details = {
            'card_number': "540400321829",
            'card_type': "RC-PHH (Priority Household)",
            'ack_no': "179000294",
            'owner_en': "VIDYA PATIL",
            'owner_kn': "ವಿದ್ಯಾ ಪಾಟೀಲ (42)",
            'address_kn': "ಭಾಟನಾಗನೂರು",
            'address_en': "BHATNAGNUR ಆರ್. ಆರ್. ಸಂಖ್ಯೆ RR No : 56",
            'taluk': "ನಿಪ್ಪಾಣಿ",
            'district': "ಬೆಳಗಾವಿ",
            'panchayat': "ಕುರ್ಲಿ",
            'village': "ಭಾಟನಾಗನೂರ",
            'fps_name': "19-ಬಿ.ಟಿ.ಪಾಟೀಲ ಭಾಟನಾಗನೂರ / 19-B.T.PATIL BHATNAGANUR",
            'members': [
                {'name_kn': 'ರಾજારಾಮ ಪಾಟೀಲ', 'name_en': 'RAJARAM PATIL', 'relation': 'ಪತಿ (45)', 'photo': 'https://randomuser.me/api/portraits/men/32.jpg'},
                {'name_kn': 'ಪಲ್ಲವಿ ರಾಜಾರಾಮ ಪಾಟೀಲ', 'name_en': 'PALLAVI RAJARAM PATIL', 'relation': 'ಮಗಳು (21)', 'photo': 'https://randomuser.me/api/portraits/women/44.jpg'},
                {'name_kn': 'ನಮ್ರತಾ ಪಾಟೀಲ', 'name_en': 'NAMRATA PATIL', 'relation': 'ಮಗಳು (19)', 'photo': 'https://randomuser.me/api/portraits/women/65.jpg'},
                {'name_kn': 'ಗೌರಿ ರಾಜಾರಾಮ ಪಾಟೀಲ', 'name_en': 'GOURI RAJARAM PATIL', 'relation': 'ಮಗಳು (15)', 'photo': 'https://randomuser.me/api/portraits/women/12.jpg'},
                {'name_kn': 'ಸೋಹಮ ರಾಜಾರಾಮ ಪಾಟೀಲ', 'name_en': 'SOHAM RAJARAM PATIL', 'relation': 'ಮಗ (12)', 'photo': 'https://randomuser.me/api/portraits/men/5.jpg'},
            ]
        }
    else:
        # Generate mock details for other numbers
        card_details = {
            'card_number': card_number,
            'card_type': "RC-PHH (Priority Household)",
            'ack_no': str(random.randint(100000000, 999999999)),
            'owner_en': app.form_data.get('applicant_name', 'TEST USER') if (app and app.form_data) else 'TEST USER',
            'owner_kn': "ಟೆಸ್ಟ್ ಯುಜರ್ (38)",
            'address_kn': "ಬೆಂಗಳೂರು",
            'address_en': "BENGALURU RR No : 12",
            'taluk': "Bengaluru North",
            'district': "Bengaluru",
            'panchayat': "Ward 10",
            'village': "Hebbal",
            'fps_name': "55-RAMESH SHED / 55-RAMESH SHED",
            'members': [
                {'name_kn': 'ಟೆಸ್ಟ್ ಯುಜರ್', 'name_en': 'TEST USER', 'relation': 'HOF (38)', 'photo': 'https://randomuser.me/api/portraits/men/10.jpg'},
                {'name_kn': 'ಟೆಸ್ಟ್ વાઈફ', 'name_en': 'TEST WIFE', 'relation': 'પત્ની (32)', 'photo': 'https://randomuser.me/api/portraits/women/10.jpg'}
            ]
        }
        
    context = {
        'card': card_details,
        'app_id': app_id
    }
    return render(request, 'core/rc_wotp_short_rc.html', context)


@login_required
def pan_card_print(request):
    from datetime import datetime
    app_id = request.GET.get('no', '')
    
    app_data = None
    if app_id.isdigit():
        try:
            app = ServiceApplication.objects.get(id=int(app_id))
            form_data = app.form_data or {}
            
            full_name = form_data.get('full_name') or 'Not Available'
            father_name = form_data.get('father_name') or 'Not Available'
            pan_number = form_data.get('pan_number') or 'Not Available'
            gender = form_data.get('gender') or 'Male'
            
            dob_val = form_data.get('dob')
            dob_obj = None
            if dob_val:
                try:
                    dob_obj = datetime.strptime(dob_val, "%Y-%m-%d").date()
                except Exception:
                    try:
                        dob_obj = datetime.strptime(dob_val, "%d/%m/%Y").date()
                    except Exception:
                        dob_obj = dob_val
            
            photo_path = form_data.get('photo')
            photo_url = f"/media/{photo_path}" if photo_path and not photo_path.startswith('/media/') and photo_path != "Not uploaded" else ""
            
            sig_path = form_data.get('signature')
            sig_url = f"/media/{sig_path}" if sig_path and not sig_path.startswith('/media/') and sig_path != "Not uploaded" else ""
            
            class FileWrapper:
                def __init__(self, url):
                    self.url = url
            
            class AppWrapper:
                def __init__(self, full_name, dob, father_name, gender, photo_url, pan_number, signature_url):
                    self.full_name = full_name
                    self.dob = dob
                    self.father_name = father_name
                    self.gender = gender
                    self.photo = FileWrapper(photo_url) if photo_url else None
                    self.pan_number = pan_number
                    self.signature = FileWrapper(signature_url) if signature_url else None
            
            app_data = AppWrapper(full_name, dob_obj, father_name, gender, photo_url, pan_number, sig_url)
        except ServiceApplication.DoesNotExist:
            pass
            
    if not app_data:
        class FileWrapper:
            def __init__(self, url):
                self.url = url
        class AppWrapper:
            def __init__(self):
                self.full_name = "PARSHARAM SHINGADI BORGUNDE"
                self.dob = datetime.strptime("1995-05-15", "%Y-%m-%d").date()
                self.father_name = "SHINGADI BORGUNDE"
                self.gender = "MALE"
                self.photo = FileWrapper("https://www.pksevaone.com/retailer/dlcard/pan.png")
                self.pan_number = "ABCDE1234F"
                self.signature = FileWrapper("")
        app_data = AppWrapper()
        
    context = {
        'app': app_data,
        'app_id': app_id
    }
    return render(request, 'core/pan_card_print.html', context)


@login_required
def verify_otp_view(request, app_id):
    app = get_object_or_404(ServiceApplication, id=app_id, user=request.user, status='PENDING_OTP')
    
    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        if len(otp) < 4:
            messages.error(request, "Please enter a valid OTP.")
            return redirect('verify_otp', app_id=app_id)
            
        client_id = app.form_data.get('otp_client_id', '')
        
        # Step 2: Submit OTP to Surepass API
        from .automation import surepass
        api_data = surepass.submit_surepass_otp(client_id, otp)
        
        if api_data:
            # Check if API returned an official base64 PDF directly (e.g. real Voter card PDF)
            pdf_base64 = api_data.get('pdf') or api_data.get('file') or api_data.get('pdf_base64')
            if pdf_base64:
                import base64
                from django.core.files.base import ContentFile
                try:
                    pdf_bytes = base64.b64decode(pdf_base64)
                    filename = f"official_voter_{app.order_id}.pdf"
                    result_file = ContentFile(pdf_bytes, name=filename)
                    app.result_file.save(result_file.name, result_file)
                    app.admin_notes = "Retrieved official government Voter ID PDF directly via Surepass API."
                    app.status = 'COMPLETED'
                    app.save()
                    messages.success(request, "Official Voter Card PDF downloaded successfully.")
                    return redirect('transaction_history')
                except Exception:
                    pass

            # Generate the beautiful visual card PDF!
            epic_no = api_data.get('epic_no', 'TEST1234567')
            name = api_data.get('name', 'Not Available')
            father = api_data.get('father_name', 'Not Available')
            gender = api_data.get('gender', 'Male')
            age = api_data.get('age', '35')
            state = api_data.get('state', 'Karnataka')
            district = api_data.get('district', 'Bengaluru')
            assembly = api_data.get('assembly', 'Assembly Const 10')
            station = api_data.get('polling_station', 'Polling Station 5')
            
            result_file = generate_voter_card_pdf(epic_no, name, father, gender, age, state, district, assembly, station)
            app.result_file.save(result_file.name, result_file)
            app.admin_notes = "Retrieved and verified via Live Surepass.io OTP API."
            app.status = 'COMPLETED'
            app.save()
            
            messages.success(request, f"OTP Verified! Voter Card generated and processed successfully.")
            return redirect('transaction_history')
        else:
            messages.error(request, "Failed to verify OTP or OTP is incorrect. Please try again.")
            
    context = {
        'app': app,
        'service': app.service
    }
    return render(request, 'core/otp_verify.html', context)


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import base64
from django.core.files.base import ContentFile

@csrf_exempt
def govt_submission_bot_api(request):
    if request.method == 'POST':
        try:
            import json
            payload = json.loads(request.body.decode('utf-8'))
            order_id = payload.get('order_id')
            pdf_base64 = payload.get('pdf_base64') or payload.get('pdf')
            
            # Retrieve application from DB
            from core.models import ServiceApplication
            app = ServiceApplication.objects.get(order_id=order_id)
            
            if not pdf_base64:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'No PDF file returned by the government submission bot. Order remains PENDING.'
                }, status=400)
            
            # Decode the real PDF bytes directly!
            pdf_bytes = base64.b64decode(pdf_base64)
            filename = f"real_govt_doc_{app.service.slug}_{app.order_id}.pdf"
            result_file = ContentFile(pdf_bytes, name=filename)
            
            app.result_file.save(result_file.name, result_file)
            app.admin_notes = "Official government document uploaded autonomously by RPA Submission Bot."
            app.status = 'COMPLETED'
            app.save()
            
            return JsonResponse({'status': 'success', 'message': f'Order {order_id} processed with real PDF successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed.'}, status=405)


@login_required
def fetch_pan_details(request):
    """
    AJAX view to fetch details (Full Name) of a PAN number from Surepass
    before submitting the application form.
    """
    pan_number = request.GET.get('pan_number', '').strip().upper()
    if len(pan_number) != 10:
        return JsonResponse({'success': False, 'message': 'Please enter a valid 10-digit PAN number.'}, status=400)
    
    from .automation import surepass
    api_data = surepass.verify_pan_card(pan_number)
    if api_data and api_data.get('name'):
        return JsonResponse({
            'success': True,
            'name': api_data.get('name')
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'Surepass API Authorization Failed (HTTP 401 / IP Not Whitelisted). Please ensure server IP 13.62.54.247 is whitelisted on Surepass Dashboard.'
        }, status=400)



