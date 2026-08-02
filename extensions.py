import stripe
from groq import Groq
from supabase import create_client

import config

supabase = (
    create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)
    if config.SUPABASE_URL and config.SUPABASE_ANON_KEY
    else None
)

stripe.api_key = config.STRIPE_SECRET_KEY

groq_client = (
    Groq(api_key=config.GROQ_API_KEY)
    if config.GROQ_API_KEY
    else None
)
