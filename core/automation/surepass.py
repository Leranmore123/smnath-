import json
import random
import urllib.request
import urllib.error
import urllib.parse
from django.conf import settings

def get_surepass_base_url():
    """
    Dynamically determine whether to use the sandbox or production URL
    """
    mode = getattr(settings, 'SUREPASS_MODE', 'production').lower()
    if mode in ['production', 'prod', 'live']:
        return "https://kyc-api.surepass.app"
    elif mode == 'sandbox':
        return "https://sandbox.surepass.app"
    return "https://kyc-api.surepass.app"

def call_surepass_api(endpoint, payload):
    """
    Generic helper to execute POST requests to Surepass API.
    """
    token = getattr(settings, 'SUREPASS_API_TOKEN', '').strip()
    if not token:
        print("SUREPASS_API_TOKEN is not configured in settings.py / .env. Skipping API execution.")
        return None
        
    base_url = get_surepass_base_url()
    url = f"{base_url}/{endpoint}"
    try:
        # Standard Surepass API expects 'Bearer <token>' or raw token if already formatted
        auth_header = f"Bearer {token}" if not token.startswith("Bearer ") else token
        headers = {
            'Content-Type': 'application/json',
            'Authorization': auth_header
        }
        try:
            clean_token = token.replace('Bearer ', '').strip()
            parts = clean_token.split('.')
            if len(parts) >= 2:
                import base64
                payload_b64 = parts[1] + '=' * (4 - len(parts[1]) % 4)
                token_payload = json.loads(base64.b64decode(payload_b64).decode('utf-8'))
                client_id = token_payload.get('identity') or token_payload.get('email')
                if client_id:
                    headers['x-client-id'] = client_id
        except Exception:
            pass

        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            
        if res_data.get('success') or res_data.get('status_code') == 200:
            return res_data.get('data', {})
        else:
            print(f"Surepass API error response: {res_data}")
            return None
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode('utf-8')
            err_json = json.loads(err_body)
            msg_code = err_json.get('message_code', '')
            if msg_code == 'ip_not_whitelisted':
                print(f"[Surepass API Error] IP not whitelisted. Please add your server IP to Surepass Dashboard whitelist. ({err_body})")
            elif msg_code == 'invalid_token':
                print(f"[Surepass API Error] Invalid Token. Please verify SUREPASS_API_TOKEN in .env ({err_body})")
            else:
                print(f"Surepass HTTPError {e.code}: {err_body}")
        except Exception:
            print(f"Surepass HTTPError {e.code}: {str(e)}")
        return None
    except Exception as e:
        print(f"Surepass API execution failed: {str(e)}")
        return None

def verify_voter_card(epic_number):
    """
    Fetch Voter details from Surepass using the new Voter ID API.
    """
    payload = {"id_number": epic_number}
    data = call_surepass_api("api/v1/voter-id/voter-id", payload)
    if data:
        return {
            'epic_no': data.get('epic_no', epic_number),
            'name': data.get('name', 'Not Available'),
            'father_name': data.get('relation_name', 'Not Available'),
            'gender': "Male" if data.get('gender') == 'M' else ("Female" if data.get('gender') == 'F' else 'Not Available'),
            'age': data.get('age', 'Not Available'),
            'state': data.get('state', 'Not Available'),
            'district': data.get('area', 'Not Available'),
            'assembly': 'Not Available',
            'polling_station': 'Not Available',
            'source': "Live Election Commission Database (via Surepass API)"
        }
    return None

def verify_driving_license(dl_number, dob):
    """
    Fetch DL details from Surepass using the new Driving License API.
    """
    payload = {"id_number": dl_number, "dob": dob}
    data = call_surepass_api("api/v1/driving-license/driving-license", payload)
    if data:
        return {
            'dl_number': dl_number,
            'name': data.get('name', 'Not Available'),
            'status': 'Active',
            'dob': data.get('dob', dob),
            'address': data.get('permanent_address', 'Not Available'),
            'cov': ", ".join(data.get('cov', [])) if isinstance(data.get('cov'), list) else data.get('cov', 'Not Available'),
            'valid_from': data.get('doi', 'Not Available'),
            'valid_till': data.get('doe', 'Not Available'),
            'source': "Live Parivahan Sewa Database (via Surepass API)"
        }
    return None

def verify_vehicle_rc(vehicle_number):
    """
    Fetch Vehicle RC details from Surepass using the new RC V2 API (with enrich=True).
    """
    payload = {"id_number": vehicle_number, "enrich": True}
    data = call_surepass_api("api/v1/rc/rc-v2", payload)
    if data:
        return {
            'registration_no': vehicle_number,
            'owner_name': data.get('owner_name', 'Not Available'),
            'model': data.get('maker_model') or data.get('maker_description', 'Not Available'),
            'fuel_type': data.get('fuel_type', 'Not Available'),
            'registration_date': data.get('registration_date', 'Not Available'),
            'chassis_no': data.get('vehicle_chasi_number', 'Not Available'),
            'engine_no': data.get('vehicle_engine_number', 'Not Available'),
            'insurance_validity': data.get('insurance_upto', 'Not Available'),
            'fitness_validity': data.get('fit_up_to', 'Not Available'),
            'source': "Live Vahan Database (via Surepass API)"
        }
    return None

def verify_pan_card(pan_number):
    """
    Fetch PAN details from Surepass using the PAN / PAN Lite API.
    """
    payload = {"id_number": pan_number}
    data = call_surepass_api("api/v1/pan/pan", payload)
    if not data:
        data = call_surepass_api("api/v1/pan/pan-lite", payload)
        
    if data:
        return {
            'pan_number': pan_number,
            'name': data.get('full_name') or data.get('name') or data.get('pan_holder_name', 'Not Available'),
            'status': data.get('status', 'Active'),
            'category': data.get('category', 'person'),
            'source': "Live Income Tax Department Database (via Surepass API)"
        }
    return None

def verify_cibil(pan_number, full_name, mobile_number, dob):
    """
    Fetch CIBIL credit score report from Surepass.
    """
    payload = {
        "pan": pan_number,
        "full_name": full_name,
        "mobile_number": mobile_number,
        "dob": dob
    }
    data = call_surepass_api("api/v1/kyc/cibil", payload)
    if data:
        return {
            'pan': pan_number,
            'name': full_name,
            'score': data.get('credit_score', 750),
            'summary': data.get('report_summary', 'Excellent Credit History'),
            'active_accounts': data.get('active_accounts', 1),
            'source': "Live CIBIL Bureau Credit Report (via Surepass API)"
        }
    return None

def check_pan_aadhaar_status(aadhaar_number):
    """
    Check PAN to Aadhaar linking status from Surepass.
    """
    payload = {"aadhaar": aadhaar_number}
    data = call_surepass_api("api/v1/kyc/pan-aadhaar-link-status", payload)
    if data:
        return {
            'aadhaar_number': aadhaar_number,
            'pan_number': data.get('pan_number', 'Not Available'),
            'linked_status': data.get('linked_status', 'Linked'),
            'message': data.get('message', 'PAN retrieved successfully from Aadhaar database.'),
            'source': "Live Income Tax Department Database (via Surepass API)"
        }
    return None

def generate_surepass_otp(id_number):
    """
    Step 1: Request OTP from Surepass.
    """
    payload = {"id_number": id_number}
    data = call_surepass_api("api/v1/voter-id/voter-id-with-otp/generate-otp", payload)
    if data:
        return data.get('client_id')
    return None

def submit_surepass_otp(client_id, otp):
    """
    Step 2: Submit the OTP to complete verification.
    """
    if not client_id:
        return None
        
    payload = {"client_id": client_id, "otp": otp}
    data = call_surepass_api("api/v1/voter-id/voter-id-with-otp/submit-otp", payload)
    if data:
        return {
            'epic_no': data.get('epic_number', 'Not Available'),
            'name': data.get('full_name', 'Not Available'),
            'father_name': data.get('relation_name', 'Not Available'),
            'gender': data.get('gender', 'Not Available'),
            'age': data.get('age', 'Not Available'),
            'state': data.get('state', 'Not Available'),
            'district': data.get('district', 'Not Available'),
            'assembly': data.get('assembly_constituency', 'Not Available'),
            'polling_station': data.get('polling_station', 'Not Available'),
            'source': "Live Election Commission Database (via Surepass API + User OTP)"
        }
    return None


