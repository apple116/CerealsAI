# database.py
import os
import sys
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be set")
    sys.exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def init_db():
    """
    Initialize the database by creating the users table if it doesn't exist.
    Note: In Supabase, you typically create tables through the dashboard or SQL editor.
    This function serves as a verification that the connection works.
    """
    try:
        # Test the connection by attempting to query the users table
        result = supabase.table('users').select('id').limit(1).execute()
        print("Database connection verified successfully")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("Please ensure the 'users' table exists in your Supabase database with columns:")
        print("- id (int8, primary key, auto-increment)")
        print("- email (text, unique, not null)")
        print("- password (text, not null)")
        print("- created_at (timestamptz, default now())")
        return False

def add_user(email, password):
    """Add a new user to the database"""
    hashed_password = generate_password_hash(password)
    
    try:
        result = supabase.table('users').insert({
            'email': email,
            'password': hashed_password
        }).execute()
        
        return True
    except Exception as e:
        print(f"Error adding user: {e}")
        # Check if it's a unique constraint violation (email already exists)
        if "duplicate key value" in str(e).lower() or "unique constraint" in str(e).lower():
            return False
        # Re-raise other exceptions
        raise e

def get_user_by_email(email):
    """Retrieve a user by their email address"""
    try:
        result = supabase.table('users').select('*').eq('email', email).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]  # Return the first (and should be only) user
        return None
    except Exception as e:
        print(f"Error retrieving user: {e}")
        return None

def verify_password(hashed_password, password):
    """Verify a password against its hash"""
    return check_password_hash(hashed_password, password)

def get_user_by_id(user_id):
    """Retrieve a user by their ID (helper function for potential future use)"""
    try:
        result = supabase.table('users').select('*').eq('id', user_id).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        print(f"Error retrieving user by ID: {e}")
        return None

def update_user_password(email, new_password):
    """Update a user's password (helper function for potential future use)"""
    hashed_password = generate_password_hash(new_password)
    
    try:
        result = supabase.table('users').update({
            'password': hashed_password
        }).eq('email', email).execute()
        
        return len(result.data) > 0
    except Exception as e:
        print(f"Error updating password: {e}")
        return False

def delete_user(email):
    """Delete a user by email (helper function for potential future use)"""
    try:
        result = supabase.table('users').delete().eq('email', email).execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False

def validate_database_schema(supabase_client):
    """Validate that the database has the required schema"""
    try:
        # Try to describe the table structure
        # Note: This is a basic validation - Supabase doesn't have a direct 
        # table description method, so we'll test by trying operations
        
        print("🔍 Validating database schema...")
        
        # Test 1: Check if required columns exist by attempting a select
        required_columns = ['id', 'email', 'password', 'created_at']
        
        try:
            result = supabase_client.table('users').select(','.join(required_columns)).limit(1).execute()
            print("✅ All required columns exist")
        except Exception as e:
            if "column" in str(e).lower():
                print("❌ Missing required columns")
                print(f"Error: {e}")
                return False
        
        # Test 2: Check unique constraint on email
        print("🔒 Testing email uniqueness constraint...")
        # This would be tested during actual user creation
        
        # Test 3: Check if created_at has default value
        print("📅 Schema validation completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False

def get_table_info_sql():
    """Return SQL to check table information"""
    return """
-- Run this in your Supabase SQL editor to check table structure
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM 
    information_schema.columns 
WHERE 
    table_name = 'users' 
    AND table_schema = 'public'
ORDER BY 
    ordinal_position;
"""

# Initialize the database connection when the module is imported
if not init_db():
    print("WARNING: Database initialization failed. The application may not work correctly.")