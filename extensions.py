import stripe
from google import genai
from supabase import create_client

import config

supabase = (
    create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)
    if config.SUPABASE_URL and config.SUPABASE_ANON_KEY
    else None
)

stripe.api_key = config.STRIPE_SECRET_KEY

genai_client = (
    genai.Client(api_key=config.GEMINI_API_KEY)
    if config.GEMINI_API_KEY
    else None
)
