import urllib.request
import json

API_URL = "http://localhost:8000/api/v1"

def test_dashboard():
    print("Testing /reports/dashboard ...")
    try:
        with urllib.request.urlopen(f"{API_URL}/reports/dashboard") as response:
            data = json.loads(response.read().decode("utf-8"))
            print(json.dumps(data, indent=2))
            
            # Basic validation
            if "daily_stats" not in data:
                print("❌ Missing daily_stats")
                return False
            if "wait_times" not in data:
                print("❌ Missing wait_times")
                return False
                print("Missing operator_stats")
                return False
            
            print("Report Structure Valid")
            return True
    except Exception as e:
        print(f"Failed: {e}")
        return False

if __name__ == "__main__":
    test_dashboard()
