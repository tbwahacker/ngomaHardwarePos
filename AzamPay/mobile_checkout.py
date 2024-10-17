import os
from azampay import Azampay
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# in production use
# azampay = Azampay(app_name='<app_name>', client_id='<client_id>', client_secret='<client_secret>', sandbox=False)


# Initialize AzamPay
gateway = Azampay(
    app_name=os.getenv("APP_NAME"),
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    x_api_key=os.getenv("X_API_KEY"),
)

print(gateway.supported_mnos())

checkout_response = gateway.mobile_checkout(amount=100, mobile='255685750593', external_id='123456789', provider='Airtel')

print(checkout_response)