import os
import urllib.request
import urllib.parse
import urllib.error
import json
import time

API_URL = "http://localhost:8000/api/v1"
MONITOR_URL = "http://localhost:8000/api/v1/tickets/monitor"

def make_request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    
    if data:
        data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            try:
                return json.loads(res_body), response.status
            except json.JSONDecodeError:
                return res_body, response.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return body, e.code
    except Exception as e:
        print(f"Request failed: {e}")
        return None, 0

def make_form_request(url, data):
    data = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            return json.loads(res_body), response.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return body, e.code

def test_kiosk_flow():
    print("\n--- Testing Kiosk Flow ---")
    # 1. Get Queues
    queues, status = make_request(f"{API_URL}/queues/")
    if status != 200:
        print(f"❌ Failed to get queues: {queues}")
        return None
    
    if not queues:
        print("❌ No queues found.")
        return None
        
    queue = next((q for q in queues if q["is_active"]), None)
    if not queue:
        print("❌ No active queues found.")
        return None
    
    print(f"Found active queue: {queue['name']} ({queue['id']})")
    
    # 2. Create Ticket
    print(f"Requesting ticket for queue ID {queue['id']}...")
    ticket, status = make_request(f"{API_URL}/tickets/", method="POST", data={"queue_id": queue['id']})
    if status != 200:
        print(f"Failed to create ticket: {ticket}")
        return None
    
    number = ticket.get("number", "UNKNOWN")
    t_id = ticket.get("id", "UNKNOWN")
    print(f"Ticket Created: {number} (ID: {t_id})")
    return ticket, queue

def test_manual_clerk_flow(ticket_id, queue_id):
    print("\n--- Testing Clerk Flow ---")
    
    # 1. Login
    username = "operador"
    password = os.getenv("DEFAULT_OPERATOR_PASSWORD", "1234")
    print(f"Logging in as {username}...")
    
    auth_data, status = make_form_request(f"{API_URL}/login/access-token", {"username": username, "password": password})
    if status != 200:
        print("Operator login failed. Trying admin...")
        username = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@gestiondeturnos.cl")
        password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin")
        auth_data, status = make_form_request(f"{API_URL}/login/access-token", {"username": username, "password": password})
        if status != 200:
            print(f"Login failed: {auth_data}")
            return False

    token = auth_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful.")
    
    # Get Operator ID. Since login doesn't return ID directly in all cases (depends on implementation),
    # let's fetch /operators/
    ops, status = make_request(f"{API_URL}/operators/", headers=headers)
    my_op = next((op for op in ops if op["username"] == "operador"), None)
    
    if my_op:
        operator_id = my_op["id"]
        print(f"Identified Operator ID: {operator_id}")
    else:
        print("'operador' not found in list, using ID 1 as fallback.")
        operator_id = 1

    # 2. Call Next
    print(f"Calling next ticket...")
    call_payload = {
        "operator_id": operator_id,
        "module_id": 1,
        "queue_ids": [queue_id]
    }
    
    ticket, status = make_request(f"{API_URL}/tickets/call-next", method="POST", data=call_payload, headers=headers)
    if status != 200:
        print(f"Failed to call next: {ticket}")
        return False
    
    print(f"Called Ticket: {ticket['number']} (ID: {ticket['id']})")
    
    # 3. Complete
    print(f"Completing Ticket {ticket['number']}...")
    comp, status = make_request(f"{API_URL}/tickets/{ticket['id']}/complete", method="POST", headers=headers)
    if status != 200:
        print(f"Failed to complete: {comp}")
        return False
        
    print(f"Ticket {comp['number']} marked as {comp['status']}.")
    return True

def test_monitor():
    print("\n--- Testing Monitor State ---")
    data, status = make_request(MONITOR_URL)
    if status != 200:
        print(f"Failed monitor check: {data}")
        return
    
    w = len(data.get("waiting", []))
    s = len(data.get("serving", []))
    h = len(data.get("history", []))
    print(f"Monitor: Waiting={w}, Serving={s}, History={h}")

if __name__ == "__main__":
    try:
        urllib.request.urlopen(API_URL).read() # Health check path actually needs /health usually or ensure root returns something
        # Let's assume root is not API_URL but localhost:8000
    except:
        pass # Ignore root check, specific endpoints matter
        
    res = test_kiosk_flow()
    if res:
        ticket, queue = res
        test_monitor()
        success = test_manual_clerk_flow(ticket['id'], queue['id'])
        if success:
            test_monitor()
            print("\nVERIFICATION SUCCESS!")
        else:
            print("\nVERIFICATION FAILED (Clerk)")
    else:
        print("\nVERIFICATION FAILED (Kiosk)")
