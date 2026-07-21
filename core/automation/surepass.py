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

LAST_ERROR = None

def call_surepass_api(endpoint, payload):
    """
    Generic helper to execute POST requests to Surepass API.
    Returns data or None.
    """
    global LAST_ERROR
    LAST_ERROR = None

    token = getattr(settings, 'SUREPASS_API_TOKEN', '').strip()
    if not token:
        LAST_ERROR = "SUREPASS_API_TOKEN is not configured in settings.py / .env"
        return None
        
    base_url = get_surepass_base_url()
    url = f"{base_url}/{endpoint}"
    try:
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
            err_msg = res_data.get('message') or "Surepass API query returned unsuccessful response."
            LAST_ERROR = err_msg
            print(f"Surepass API error response: {res_data}")
            return None
    except urllib.error.HTTPError as e:
        err_msg = f"HTTP Error {e.code}"
        try:
            err_body = e.read().decode('utf-8')
            err_json = json.loads(err_body)
            msg_code = err_json.get('message_code', '')
            api_msg = err_json.get('message', '')
            if msg_code == 'ip_not_whitelisted':
                err_msg = "Server IP not whitelisted on Surepass Dashboard."
            elif msg_code == 'invalid_token':
                err_msg = "Invalid Surepass Token in .env."
            elif api_msg:
                err_msg = api_msg
            else:
                err_msg = err_body
        except Exception:
            pass
        LAST_ERROR = err_msg
        return None
    except Exception as e:
        LAST_ERROR = f"API Connection Error: {str(e)}"
        return None

def verify_voter_card(epic_number, full_name=None, dob=None):
    """
    Fetch Voter details from Surepass using the new Voter ID API.
    """
    clean_epic = str(epic_number).strip().upper().replace(' ', '')
    payload = {"id_number": clean_epic}
    
    if full_name or dob:
        add_details = {}
        if full_name:
            add_details["full_name"] = str(full_name).strip()
        if dob:
            add_details["dob"] = str(dob).strip()
        payload["additional_details"] = add_details

    data = call_surepass_api("api/v1/voter-id/voter-id", payload)
    if not data and "additional_details" in payload:
        # Fallback to simple query if additional details query failed
        data = call_surepass_api("api/v1/voter-id/voter-id", {"id_number": clean_epic})

    if data:
        return {
            'epic_no': data.get('epic_no') or clean_epic,
            'name': data.get('name', 'Not Available'),
            'father_name': data.get('relation_name', 'Not Available'),
            'relation_type': data.get('relation_type', 'F'),
            'gender': "Male" if data.get('gender') in ['M', 'Male'] else ("Female" if data.get('gender') in ['F', 'Female'] else 'Not Available'),
            'age': data.get('age', 'Not Available'),
            'dob': data.get('dob', 'Not Available'),
            'house_no': data.get('house_no', 'Not Available'),
            'district': data.get('area', 'Not Available'),
            'state': data.get('state', 'Not Available'),
            'assembly': 'Not Available',
            'polling_station': 'Not Available',
            'source': "Live Election Commission Database (via Surepass API)"
        }
    return None

def verify_driving_license(dl_number, dob):
    """
    Fetch DL details from Surepass using the new Driving License API.
    """
    # Normalize DOB to YYYY-MM-DD
    clean_dob = str(dob).strip().replace('/', '-')
    parts = [p.strip() for p in clean_dob.split('-') if p.strip()]
    if len(parts) == 3:
        if len(parts[0]) == 2 and len(parts[2]) == 4:
            # DD-MM-YYYY -> YYYY-MM-DD
            clean_dob = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        elif len(parts[0]) == 4:
            # YYYY-MM-DD
            clean_dob = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"

    clean_dl = str(dl_number).strip().replace(' ', '')
    payload = {"id_number": clean_dl, "dob": clean_dob}
    data = call_surepass_api("api/v1/driving-license/driving-license", payload)
    if not data:
        # Fallback with space in DL number if unspaced failed
        payload_space = {"id_number": str(dl_number).strip(), "dob": clean_dob}
        data = call_surepass_api("api/v1/driving-license/driving-license", payload_space)

    if data:
        vehicle_classes = data.get('vehicle_classes') or data.get('cov')
        if isinstance(vehicle_classes, list):
            cov_str = ", ".join(vehicle_classes)
        else:
            cov_str = str(vehicle_classes or 'Not Available')

        return {
            'dl_number': data.get('license_number') or dl_number,
            'name': data.get('name', 'Not Available'),
            'father_name': data.get('father_or_husband_name', 'Not Available'),
            'gender': "Male" if data.get('gender') == 'M' else ("Female" if data.get('gender') == 'F' else data.get('gender', 'Not Available')),
            'status': data.get('current_status') or 'Active',
            'dob': data.get('dob', dob),
            'address': data.get('permanent_address') or data.get('temporary_address') or 'Not Available',
            'cov': cov_str,
            'valid_from': data.get('doi') or data.get('initial_doi', 'Not Available'),
            'valid_till': data.get('doe', 'Not Available'),
            'blood_group': data.get('blood_group') or 'UNKNOWN',
            'profile_image': data.get('profile_image') or '',
            'state': data.get('state', 'Not Available'),
            'ola_name': data.get('ola_name', 'Not Available'),
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


