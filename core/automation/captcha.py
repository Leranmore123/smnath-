import time
import base64
import urllib.request
import urllib.parse
from django.conf import settings

def solve_captcha_2captcha(image_bytes):
    """
    Submits CAPTCHA image to 2Captcha API and polls for solution.
    If TWOCAPTCHA_API_KEY is not configured, logs it and returns None.
    """
    api_key = getattr(settings, 'TWOCAPTCHA_API_KEY', '')
    if not api_key:
        print("2Captcha API Key is not set in settings.py. Skipping live CAPTCHA solving.")
        return None
        
    try:
        # Base64 encode the image bytes
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Submit the CAPTCHA image
        post_data = urllib.parse.urlencode({
            'key': api_key,
            'method': 'base64',
            'body': image_base64,
            'json': 0  # We parse plain text response: OK|ID
        }).encode('utf-8')
        
        submit_url = "https://2captcha.com/in.php"
        req = urllib.request.Request(submit_url, data=post_data)
        with urllib.request.urlopen(req, timeout=15) as response:
            res_text = response.read().decode('utf-8')
            
        if not res_text.startswith("OK|"):
            print(f"2Captcha Submission Error: {res_text}")
            return None
            
        captcha_id = res_text.split("|")[1]
        print(f"2Captcha successfully submitted. CAPTCHA ID: {captcha_id}. Polling for result...")
        
        # Poll for completion (maximum 15 attempts, 3 seconds delay between polls)
        poll_url = f"https://2captcha.com/res.php?key={api_key}&action=get&id={captcha_id}"
        
        # Wait a few seconds before first poll
        time.sleep(5)
        
        for attempt in range(15):
            try:
                with urllib.request.urlopen(poll_url, timeout=10) as response:
                    poll_text = response.read().decode('utf-8')
                
                if poll_text == "CAPCHA_NOT_READY":
                    print(f"CAPTCHA not ready yet (attempt {attempt + 1}/15). Waiting...")
                    time.sleep(3)
                    continue
                elif poll_text.startswith("OK|"):
                    solved_text = poll_text.split("|")[1]
                    print(f"2Captcha Solver Success! Solved Text: {solved_text}")
                    return solved_text
                else:
                    print(f"2Captcha Polling Response Error: {poll_text}")
                    return None
            except Exception as e:
                print(f"Error during 2Captcha polling attempt: {str(e)}")
                time.sleep(3)
                
        print("2Captcha Solving Timeout: Exceeded maximum attempts.")
        return None
        
    except Exception as e:
        print(f"2Captcha Request Failed: {str(e)}")
        return None
