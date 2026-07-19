import json
import urllib.request
import urllib.parse
from django.conf import settings

def trigger_service_webhook(application):
    """
    Trigger a webhook POST call to automatically forward the manual form details
    to an external automation tool (like Selenium bot, Make.com, or Zapier).
    """
    webhook_url = getattr(settings, 'GOVT_SUBMISSION_WEBHOOK_URL', '')
    if not webhook_url:
        print(f"Govt Webhook URL not configured. Skipping webhook for order {application.order_id}.")
        return False

    # Extract all submitted text data
    text_data = {}
    for key, value in application.form_data.items():
        if isinstance(value, str) and not value.startswith('/media/'):
            text_data[key] = value

    # Extract file URLs
    file_urls = {}
    for key, value in application.form_data.items():
        if isinstance(value, str) and value.startswith('/media/'):
            file_urls[key] = value

    # Format the payload
    payload = {
        'order_id': application.order_id,
        'service_name': application.service.name,
        'service_slug': application.service.slug,
        'category': application.service.category,
        'cost': float(application.amount),
        'submitted_by': application.user.username,
        'member_id': application.user.profile.member_id,
        'form_fields': text_data,
        'uploaded_files': file_urls,
        'timestamp': application.created_at.isoformat() if application.created_at else ''
    }

    # If the URL points to our own server, we can process it locally
    # without making an external HTTP request, which prevents getaddrinfo/DNS errors!
    if '127.0.0.1' in webhook_url or 'localhost' in webhook_url or 'testserver' in webhook_url:
        try:
            from core.views import govt_submission_bot_api, generate_completed_govt_document_pdf
            from django.test import RequestFactory
            import base64
            
            # Generate test document for loopback simulation
            test_pdf_file = generate_completed_govt_document_pdf(application, text_data)
            pdf_base64_data = base64.b64encode(test_pdf_file.read()).decode('utf-8')
            payload['pdf_base64'] = pdf_base64_data
            
            factory = RequestFactory()
            body_data = json.dumps(payload)
            req = factory.post('/api/govt-submission-bot/', data=body_data, content_type='application/json')
            
            # Call view directly
            response = govt_submission_bot_api(req)
            if response.status_code == 200:
                print(f"Successfully triggered local government submission bot for order {application.order_id}.")
                return True
            else:
                print(f"Local bot returned status {response.status_code}: {response.content}")
                return False
        except Exception as e:
            print(f"Local bot execution error: {str(e)}")
            return False

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'SMSeva-Govt-Webhook-Agent'
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.getcode()
            if status_code in [200, 201, 202]:
                print(f"Successfully triggered government submission webhook for order {application.order_id}.")
                return True
    except Exception as e:
        print(f"Error triggering government submission webhook: {str(e)}")
        return False
