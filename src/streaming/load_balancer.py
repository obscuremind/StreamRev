"""
Load balancer for streaming servers
"""

import logging
from typing import Optional, List, Dict, Any
import random

logger = logging.getLogger(__name__)


class LoadBalancer:
    """Load balancer for distributing streams across servers"""
    
    def __init__(self, db):
        """
        Initialize load balancer
        
        Args:
            db: Database instance
        """
        self.db = db
        self.servers = []
        self._load_servers()
    
    def _load_servers(self):
        """Load server nodes from database"""
        try:
            query = """
                SELECT * FROM server_nodes 
                WHERE status = 1 
                ORDER BY load ASC
            """
            self.servers = self.db.fetch_all(query)
            logger.info(f"Loaded {len(self.servers)} active servers")
        except Exception as e:
            logger.error(f"Failed to load servers: {str(e)}")
            self.servers = []
    
    def get_best_server(self, stream_type: str = 'streaming') -> Optional[Dict[str, Any]]:
        """
        Get best available server based on load
        
        Args:
            stream_type: Type of server (streaming, transcoding, etc.)
            
        Returns:
            Server information or None
        """
        # Reload servers to get latest status
        self._load_servers()
        
        # Filter by type
        available = [s for s in self.servers if s['type'] == stream_type]
        
        if not available:
            logger.warning(f"No available servers of type: {stream_type}")
            return None
        
        # Filter servers under capacity
        under_capacity = [
            s for s in available 
            if s['current_clients'] < s['max_clients']
        ]
        
        if not under_capacity:
            logger.warning("All servers at capacity")
            return None
        
        # Return server with lowest load
        best_server = min(under_capacity, key=lambda x: x['load'])
        
        logger.info(f"Selected server: {best_server['name']} (load: {best_server['load']})")
        return best_server
    
    def round_robin(self, stream_type: str = 'streaming') -> Optional[Dict[str, Any]]:
        """
        Round-robin server selection
        
        Args:
            stream_type: Type of server
            
        Returns:
            Server information or None
        """
        self._load_servers()
        
        available = [
            s for s in self.servers 
            if s['type'] == stream_type and s['current_clients'] < s['max_clients']
        ]
        
        if not available:
            return None
        
        # Simple round-robin using random selection
        return random.choice(available)
    
    def update_server_load(self, server_id: int, clients_delta: int = 1) -> bool:
        """
        Update server load and client count
        
        Args:
            server_id: Server ID
            clients_delta: Change in client count (positive or negative)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = """
                UPDATE server_nodes 
                SET current_clients = current_clients + %s,
                    load = (current_clients + %s) * 100 / max_clients
                WHERE id = %s
            """
            return self.db.execute(query, (clients_delta, clients_delta, server_id))
        except Exception as e:
            logger.error(f"Failed to update server load: {str(e)}")
            return False
    
    def get_server_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all servers
        
        Returns:
            List of server statistics
        """
        self._load_servers()
        
        stats = []
        for server in self.servers:
            stats.append({
                'id': server['id'],
                'name': server['name'],
                'hostname': server['hostname'],
                'type': server['type'],
                'status': server['status'],
                'load': server['load'],
                'current_clients': server['current_clients'],
                'max_clients': server['max_clients'],
                'capacity_percent': (server['current_clients'] / server['max_clients'] * 100) 
                                   if server['max_clients'] > 0 else 0
            })
        
        return stats
    
    def build_stream_url(self, server: Dict[str, Any], stream_path: str) -> str:
        """
        Build full stream URL for a server
        
        Args:
            server: Server information
            stream_path: Stream path
            
        Returns:
            Full stream URL
        """
        protocol = 'https' if server.get('port') == 443 else 'http'
        port = f":{server['port']}" if server['port'] not in [80, 443] else ''
        
        url = f"{protocol}://{server['hostname']}{port}/{stream_path}"
        return url
