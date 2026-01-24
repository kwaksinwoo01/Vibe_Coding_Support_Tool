#!/usr/bin/env python3
"""
Example client for vibeStation API.
Demonstrates how to interact with the vibeStation API programmatically.
"""
import requests
import time
import sys


class VibeStationClient:
    """Client for vibeStation API."""
    
    def __init__(self, base_url="http://127.0.0.1:8765", auth_key=None):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the vibeStation API
            auth_key: Authentication key (auto-fetched if not provided)
        """
        self.base_url = base_url
        self.auth_key = auth_key or self.get_auth_key()
        
    def get_auth_key(self):
        """Get authentication key from server."""
        try:
            response = requests.get(f"{self.base_url}/auth_key", timeout=5)
            response.raise_for_status()
            return response.json()['auth_key']
        except Exception as e:
            print(f"Error getting auth key: {e}")
            print("Make sure vibeStation is running!")
            sys.exit(1)
    
    def check_health(self):
        """Check server health."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def send_log(self, tier, message):
        """
        Send a tier log.
        
        Args:
            tier: Log tier (A-F)
            message: Log message
            
        Returns:
            Response data
        """
        response = requests.post(
            f"{self.base_url}/stream",
            headers={'Authorization': f'Bearer {self.auth_key}'},
            json={'tier': tier, 'message': message}
        )
        response.raise_for_status()
        return response.json()
    
    def get_logs(self, tier=None, limit=100):
        """
        Get logs from server.
        
        Args:
            tier: Optional tier filter (A-F)
            limit: Maximum number of logs to retrieve
            
        Returns:
            List of log entries
        """
        params = {'limit': limit}
        if tier:
            params['tier'] = tier
        
        response = requests.get(
            f"{self.base_url}/logs",
            headers={'Authorization': f'Bearer {self.auth_key}'},
            params=params
        )
        response.raise_for_status()
        return response.json()['logs']
    
    def send_vibe_log(self, destination, data):
        """
        Send vibe log with retry mechanism.
        
        Args:
            destination: Destination URL
            data: Data to send
            
        Returns:
            Response data
        """
        response = requests.post(
            f"{self.base_url}/vibe_log",
            headers={'Authorization': f'Bearer {self.auth_key}'},
            json={'destination': destination, 'data': data}
        )
        response.raise_for_status()
        return response.json()


def demo():
    """Demonstrate API usage."""
    print("vibeStation Client Demo")
    print("=" * 60)
    
    # Initialize client
    print("\n1. Initializing client...")
    client = VibeStationClient()
    print(f"   ✓ Connected to {client.base_url}")
    print(f"   ✓ Auth key: {client.auth_key[:20]}...")
    
    # Check health
    print("\n2. Checking server health...")
    health = client.check_health()
    print(f"   ✓ Status: {health['status']}")
    print(f"   ✓ Logs count: {health['logs_count']}")
    
    # Send logs for each tier
    print("\n3. Sending tier logs...")
    tiers = [
        ('A', 'Critical: System overload detected'),
        ('B', 'Error: Failed to connect to database'),
        ('C', 'Warning: Memory usage at 85%'),
        ('D', 'Info: User login successful'),
        ('E', 'Debug: Processing request #1234'),
        ('F', 'Trace: Function call: process_data()')
    ]
    
    for tier, message in tiers:
        result = client.send_log(tier, message)
        print(f"   ✓ Sent tier {tier}: {result['status']}")
        time.sleep(0.1)
    
    # Retrieve all logs
    print("\n4. Retrieving all logs...")
    all_logs = client.get_logs()
    print(f"   ✓ Retrieved {len(all_logs)} logs")
    for log in all_logs:
        print(f"     - [{log['tier']}] {log['message']}")
    
    # Retrieve filtered logs
    print("\n5. Retrieving critical logs (tier A)...")
    critical_logs = client.get_logs(tier='A')
    print(f"   ✓ Retrieved {len(critical_logs)} critical logs")
    for log in critical_logs:
        print(f"     - {log['message']}")
    
    print("\n" + "=" * 60)
    print("✓ Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        demo()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure vibeStation is running:")
        print("  python run_vibestation.py")
        sys.exit(1)
