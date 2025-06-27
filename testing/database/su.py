from supabase import create_client
import os

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")

print("Connecting to Supabase...")
print("URL:", url)
print("Key:", key[:6] + "..." + key[-6:])

try:
    supabase = create_client(url, key)
    print("Connected to Supabase successfully.")
    test = supabase.table("users").select("*").limit(1).execute()
    print("Test query result:", test)
except Exception as e:
    print("Database connection failed:", e)
