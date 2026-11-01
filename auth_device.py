import sys
import os
import json
import time
import base64
import hashlib
import secrets
import threading
import urllib.request
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_FILE = os.path.join(BASE_DIR, "keys_pool.json")
SITE = "https://www.orcarouter.ai"
PROXY = "http://127.0.0.1:3067"

def get_opener():
    proxy_handler = urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY})
    return urllib.request.build_opener(proxy_handler)

def load_keys():
    if not os.path.exists(KEYS_FILE):
        return []
    with open(KEYS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return [k.strip() for k in data.get("keys", []) if k.strip() and not k.startswith("orca_live_demo")]

def save_key(api_key):
    keys = load_keys()
    if api_key not in keys:
        keys.append(api_key)
        data = {
            "keys": keys,
            "description": "OrcaRouter API Keys Pool"
        }
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[+] Key successfully saved! Total keys in pool: {len(keys)}")
    else:
        print("[*] Key already exists in pool.")

def test_key(key):
    opener = get_opener()
    url = f"{SITE}/api/v1/models"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {key}", "User-Agent": "curl/8.4.0"}
    )
    try:
        resp = opener.open(req, timeout=10)
        return True, "Active (200 OK)"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)

# --- Mode 1: PKCE Loopback Flow ---
auth_code_received = None

class PKCECallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code_received
        query = parse_qs(urlparse(self.path).query)
        code = query.get("code", [None])[0]
        if code:
            auth_code_received = code
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h1>Authorization Successful!</h1><p>You can close this tab and return to the terminal.</p>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Authorization failed: no code parameter.")

    def log_message(self, format, *args):
        return # Silence HTTP server logs

def run_pkce_flow():
    global auth_code_received
    auth_code_received = None
    
    # 1. Generate code_verifier and code_challenge
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")
    
    # 2. Start local server
    port = 28419
    server = HTTPServer(("127.0.0.1", port), PKCECallbackHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    callback_url = f"http://127.0.0.1:{port}/callback"
    auth_url = f"{SITE}/auth?callback_url={urllib.parse.quote(callback_url)}&code_challenge={code_challenge}&code_challenge_method=S256"
    
    print(f"\n👉 Opening PKCE Authorization in browser:\n    {auth_url}\n")
    try:
        webbrowser.open(auth_url)
    except:
        pass
        
    print("[*] Waiting for browser callback...")
    start = time.time()
    while time.time() - start < 180 and not auth_code_received:
        time.sleep(1)
        sys.stdout.write(".")
        sys.stdout.flush()
        
    server.shutdown()
    
    if not auth_code_received:
        print("\n[-] Timed out waiting for browser callback.")
        return None
        
    print(f"\n[+] Authorization code caught! Exchanging for API key...")
    opener = get_opener()
    exchange_payload = {
        "code": auth_code_received,
        "code_verifier": code_verifier
    }
    req = urllib.request.Request(
        f"{SITE}/api/v1/auth/keys",
        data=json.dumps(exchange_payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "curl/8.4.0"}
    )
    try:
        resp = opener.open(req, timeout=15)
        res_data = json.loads(resp.read().decode())
        key = res_data.get("key")
        if key:
            print(f"[+] API KEY ACQUIRED: {key[:14]}...{key[-6:]}")
            save_key(key)
            return key
        else:
            print(f"[-] Response did not contain key: {res_data}")
    except Exception as e:
        print(f"[-] Key exchange failed: {e}")
    return None

def main():
    print("=" * 60)
    print("  OrcaRouter API Key Manager & Auth Helper")
    print("=" * 60)
    
    keys = load_keys()
    print(f"[*] Keys in pool: {len(keys)}")
    for idx, k in enumerate(keys):
        ok, msg = test_key(k)
        status_icon = "🟢" if ok else "🔴"
        print(f"  [{idx+1}] {status_icon} {k[:14]}...{k[-6:]} -> {msg}")
        
    print("\n[1] 1-Click Browser PKCE Authorization (Recommended)")
    print("[2] Paste API Key manually")
    print("[3] Exit")
    
    choice = input("\nSelect action [1-3] (default 1): ").strip()
    if choice == "2":
        k = input("Enter OrcaRouter API Key: ").strip()
        if k:
            ok, msg = test_key(k)
            if ok:
                save_key(k)
            else:
                print(f"[-] Verification failed ({msg}), save anyway? [y/N]: ", end="")
                if input().lower().startswith("y"):
                    save_key(k)
    elif choice == "3":
        return
    else:
        run_pkce_flow()

if __name__ == "__main__":
    main()
