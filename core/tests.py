from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from core.models import UserProfile, Service, ServiceApplication, TopupRequest
from decimal import Decimal
import io

# Patch Django's template context copy method for Python 3.14 compatibility
import django.template.context
def custom_context_copy(self):
    obj = self.__class__.__new__(self.__class__)
    if hasattr(self, 'dicts'):
        obj.dicts = self.dicts[:]
    if hasattr(self, 'render_context'):
        rc_src = self.render_context
        rc_obj = rc_src.__class__.__new__(rc_src.__class__)
        if hasattr(rc_src, 'dicts'):
            rc_obj.dicts = rc_src.dicts[:]
        obj.render_context = rc_obj
    for k, v in self.__dict__.items():
        if k not in ('dicts', 'render_context'):
            setattr(obj, k, v)
    return obj
django.template.context.BaseContext.__copy__ = custom_context_copy
django.template.context.Context.__copy__ = custom_context_copy
django.template.context.RequestContext.__copy__ = custom_context_copy



class SMSevaTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create standard test user
        self.user = User.objects.create_user(
            username='testcustomer',
            email='testcustomer@example.com',
            password='testpassword123',
            first_name='Test Customer'
        )
        self.profile = self.user.profile
        self.profile.wallet_balance = Decimal('100.00')
        self.profile.save()
        
        # Create staff user
        self.staff_user = User.objects.create_user(
            username='teststaff',
            email='teststaff@example.com',
            password='staffpassword123',
            is_staff=True,
            first_name='Test Staff'
        )
        
        # Fetch already seeded services
        self.manual_service = Service.objects.get(slug="apply_senior")
        self.auto_service = Service.objects.get(slug="rc_dwnld")

    def test_user_profile_creation(self):
        """Verify that profile and custom member_id are created for new users."""
        user = User.objects.create_user(
            username='newuser',
            email='newuser@example.com',
            password='newpassword123',
            first_name='New User'
        )
        self.assertTrue(hasattr(user, 'profile'))
        self.assertTrue(user.profile.member_id.startswith('SMSEVA'))
        self.assertEqual(user.profile.wallet_balance, Decimal('0.00'))

    def test_login_flow(self):
        """Verify user login and redirection to dashboard."""
        response = self.client.post(reverse('login'), {
            'email': 'testcustomer@example.com',
            'password': 'testpassword123'
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_wallet_recharge_and_staff_approval(self):
        """Test the wallet topup request and staff approval flow."""
        self.client.login(username='testcustomer', password='testpassword123')
        
        # Submit a recharge request
        response = self.client.post(reverse('wallet'), {
            'amount': '500.00',
            'utr': 'UTR999999999',
            'demo_mode': 'false'
        })
        self.assertRedirects(response, reverse('wallet_history'))
        
        # Verify pending topup request exists
        topup = TopupRequest.objects.get(transaction_id_utr='UTR999999999')
        self.assertEqual(topup.status, 'PENDING')
        self.assertEqual(topup.amount, Decimal('500.00'))
        
        # Log in as staff to approve it
        self.client.login(username='teststaff', password='staffpassword123')
        approve_response = self.client.post(reverse('admin_approve_topup', args=[topup.id]))
        self.assertRedirects(approve_response, reverse('admin_panel'))
        
        # Verify balance updated
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.wallet_balance, Decimal('600.00'))
        
        topup.refresh_from_db()
        self.assertEqual(topup.status, 'APPROVED')

    def test_apply_automated_service(self):
        """Test applying for an automated service which completes instantly."""
        self.client.login(username='testcustomer', password='testpassword123')
        
        # Apply for automated service
        response = self.client.post(reverse('apply_service', args=[self.auto_service.slug]), {
            'ration_card_no': 'RC123456789'
        })
        self.assertRedirects(response, reverse('transaction_history'))
        
        # Verify application created and completed
        app = ServiceApplication.objects.get(service=self.auto_service, user=self.user)
        self.assertEqual(app.status, 'COMPLETED')
        self.assertEqual(app.amount, Decimal('5.00'))
        self.assertTrue(app.result_file.name.endswith('.pdf'))
        
        # Check wallet deduction
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.wallet_balance, Decimal('95.00'))

    def test_apply_manual_service_and_staff_complete(self):
        """Test applying for manual service and approval/completion by staff."""
        self.client.login(username='testcustomer', password='testpassword123')
        
        # Apply for manual service with dummy file uploads
        photo_file = io.BytesIO(b"dummy_photo_data")
        photo_file.name = "myphoto.jpg"
        aadhaar_file = io.BytesIO(b"dummy_aadhaar_data")
        aadhaar_file.name = "myaadhaar.pdf"
        blood_file = io.BytesIO(b"dummy_blood_data")
        blood_file.name = "myblood.png"
        
        with self.settings(GOVT_SUBMISSION_WEBHOOK_URL=''):
            response = self.client.post(reverse('apply_service', args=[self.manual_service.slug]), {
                'applicant_name': 'Balu Ravate',
                'aadhaar_no': '123412341234',
                'mobile_no': '9876543210',
                'email_id': 'balu@example.com',
                'gender': 'Male',
                'dob': '2009-01-01',
                'address': 'Karnatak State',
                'talluk': 'Taluk A',
                'district': 'District B',
                'pincode': '560001',
                'photo': photo_file,
                'upload_aadhaar': aadhaar_file,
                'blood_group_report': blood_file
            })
            self.assertRedirects(response, reverse('transaction_history'))
        
        # Verify application is pending
        app = ServiceApplication.objects.get(service=self.manual_service, user=self.user)
        self.assertEqual(app.status, 'PENDING')
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.wallet_balance, Decimal('50.00')) # 100 - 50 = 50
        
        # Log in as staff
        self.client.login(username='teststaff', password='staffpassword123')
        
        # Upload result file to complete the application
        result_file = io.BytesIO(b"dummy_result_pdf_content")
        result_file.name = "senior_citizen_card_result.pdf"
        
        complete_response = self.client.post(reverse('admin_complete_application', args=[app.id]), {
            'result_file': result_file,
            'admin_notes': 'Processed by staff successfully.'
        })
        self.assertRedirects(complete_response, reverse('admin_panel'))
        
        # Verify application is completed
        app.refresh_from_db()
        self.assertEqual(app.status, 'COMPLETED')
        self.assertEqual(app.admin_notes, 'Processed by staff successfully.')
        self.assertTrue(app.result_file.name.endswith('.pdf'))

    def test_selenium_ration_card_download_automation(self):
        """Verify that the automated Selenium Ration Card downloader executes correctly."""
        from core.automation.ration_card import download_ration_card_automated
        # Running with a demo card number will invoke the fast simulation path to verify output logic
        result = download_ration_card_automated("RC998877665")
        self.assertIsNotNone(result)
        self.assertTrue(result.name.startswith("ration_card_RC998877665_"))
        pdf_bytes = result.read()
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertTrue(len(pdf_bytes) > 200)

    from unittest.mock import patch

    @patch('core.automation.surepass.generate_surepass_otp')
    @patch('core.automation.surepass.submit_surepass_otp')
    def test_otp_verification_flow(self, mock_submit, mock_generate):
        """Verify the 2-step OTP verification flow for automated services."""
        mock_generate.return_value = 'mocked_client_id_12345'
        mock_submit.return_value = {
            'epic_no': 'EPIC9876543',
            'name': 'Balu Ravate',
            'father_name': 'Sambhaji Ravate',
            'gender': 'Male',
            'age': '29',
            'state': 'Karnataka',
            'district': 'Belagavi',
            'assembly': 'Nippani Assembly',
            'polling_station': 'Government School Kurli',
            'source': 'Mocked API'
        }
        
        # Retrieve seeded Voter OTP service
        voter_otp_service = Service.objects.get(slug="voter_pdf_instant")
        
        self.client.login(username='testcustomer', password='testpassword123')
        
        # Step 1: Submit details -> expect redirection to OTP page and PENDING_OTP status
        apply_response = self.client.post(reverse('apply_service', args=[voter_otp_service.slug]), {
            'epic_number': 'EPIC9876543'
        })
        
        app = ServiceApplication.objects.get(service=voter_otp_service, user=self.user)
        self.assertEqual(app.status, 'PENDING_OTP')
        self.assertEqual(app.form_data.get('otp_client_id'), 'mocked_client_id_12345')
        
        # Should redirect to verification URL
        self.assertRedirects(apply_response, reverse('verify_otp', args=[app.id]))
        
        # Step 2: Submit OTP on verification URL -> expect status transition to COMPLETED and PDF generation
        otp_submit_response = self.client.post(reverse('verify_otp', args=[app.id]), {
            'otp': '123456'
        })
        
        self.assertRedirects(otp_submit_response, reverse('transaction_history'))
        app.refresh_from_db()
        self.assertEqual(app.status, 'COMPLETED')
        self.assertTrue(app.result_file.name.endswith('.pdf'))
        self.assertTrue(app.result_file.read().startswith(b"%PDF-"))

    def test_local_govt_bot_submission_flow(self):
        """Verify that applying for a manual service triggers the local bot to generate the official document PDF."""
        self.client.login(username='testcustomer', password='testpassword123')
        
        # Override setting in tests to point to our local bot url
        with self.settings(GOVT_SUBMISSION_WEBHOOK_URL='http://testserver' + reverse('govt_submission_bot')):
            response = self.client.post(reverse('apply_service', args=[self.manual_service.slug]), {
                'applicant_name': 'Test Senior User',
                'aadhaar_no': '123412341234',
                'mobile_no': '9876543210',
                'email_id': 'senior@example.com',
                'gender': 'Male',
                'dob': '1950-01-01',
                'address': 'Kanakpura Road, Bengaluru',
                'talluk': 'Bengaluru South',
                'district': 'Bengaluru',
                'pincode': '560062'
            })
            
            self.assertRedirects(response, reverse('transaction_history'))
            
            # Fetch the application and verify it was processed and completed by the local bot
            app = ServiceApplication.objects.get(service=self.manual_service, user=self.user)
            self.assertEqual(app.status, 'COMPLETED')
            self.assertEqual(app.admin_notes, "Official government document uploaded autonomously by RPA Submission Bot.")
            self.assertTrue(app.result_file.name.endswith('.pdf'))
            self.assertTrue(app.result_file.read().startswith(b"%PDF-"))



