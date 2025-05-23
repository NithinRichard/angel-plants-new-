from supabase import create_client, Client
from django.conf import settings
import os

def get_supabase_client() -> Client:
    """
    Initialize and return a Supabase client.
    Make sure to set SUPABASE_URL and SUPABASE_KEY in your environment variables.
    """
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    
    return create_client(supabase_url, supabase_key)

def upload_file_to_storage(bucket_name: str, file_path: str, file_content) -> str:
    """
    Upload a file to Supabase Storage.
    
    Args:
        bucket_name: Name of the storage bucket
        file_path: Path where the file will be stored in the bucket
        file_content: File content (bytes or file-like object)
    
    Returns:
        str: Public URL of the uploaded file
    """
    try:
        supabase = get_supabase_client()
        
        # Upload the file
        res = supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": "image/jpeg"}  # Adjust content type as needed
        )
        
        # Get public URL
        return supabase.storage.from_(bucket_name).get_public_url(file_path)
    except Exception as e:
        print(f"Error uploading file to Supabase Storage: {str(e)}")
        raise
