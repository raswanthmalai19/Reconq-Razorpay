import requests
BASE_URL = "http://localhost:8000/api"
res = requests.post(f"{BASE_URL}/razorpay/sync")
print(res.json())
