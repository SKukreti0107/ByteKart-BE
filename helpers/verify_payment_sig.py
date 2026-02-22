import razorpay
from pydantic import BaseModel
from typing import Dict
from dotenv import load_dotenv
load_dotenv()
import os
key_id = os.getenv("RAZOR_PAY_KEY_ID")
key_secret = os.getenv("RAZOR_PAY_API_KEY")


def get_razorpay_client():
    client = razorpay.Client(auth=(key_id, key_secret))
    return client

def verify_payment(razorpay_order_id:str,razorpay_payment_id:str,razorpay_signature:str,client=None):
    if client is None:
        client = get_razorpay_client()
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False