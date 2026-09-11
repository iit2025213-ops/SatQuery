# app/storage/supabase_client.py

from supabase import create_client, Client
import logging

logger = logging.getLogger("satquery")

class SupabaseClient:
    """Wrapper for Supabase client with connection pooling"""
    
    def __init__(self, url: str, key: str, service_role_key: str):
        """Initialize Supabase client"""
        self.url = url
        self.key = key
        self.service_role_key = service_role_key
        
        # Create client for user operations
        self.client: Client = create_client(url, key)
        
        # Create admin client for privileged operations
        self.admin_client: Client = create_client(url, service_role_key)
        
        logger.info("Supabase client initialized")
    
    async def health_check(self) -> bool:
        """Check if Supabase is accessible"""
        try:
            # Try to execute a simple query
            response = self.client.table("users").select("id").limit(1).execute()
            logger.info("Supabase health check passed")
            return True
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            raise
    
    def get_user_client(self) -> Client:
        """Get user-level client"""
        return self.client
    
    def get_admin_client(self) -> Client:
        """Get admin-level client (for privileged operations)"""
        return self.admin_client
