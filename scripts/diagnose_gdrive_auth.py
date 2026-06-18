#!/usr/bin/env python3
"""
Google Drive Upload Diagnostics & Fix Script
Tests MCP connection and provides authentication troubleshooting
"""

import json
import sys
from pathlib import Path

def check_mcp_config():
    """Verify .mcp.json configuration."""
    mcp_path = Path.home() / '.claude' / 'mcp.json'
    project_mcp = Path.cwd() / '.mcp.json'
    
    print("=== MCP Configuration Check ===")
    
    for path in [mcp_path, project_mcp]:
        if path.exists():
            try:
                with open(path) as f:
                    config = json.load(f)
                print(f"✓ Found MCP config at {path}")
                
                if 'mcpServers' in config and 'google-docs' in config['mcpServers']:
                    gd = config['mcpServers']['google-docs']
                    print(f"  - Command: {gd.get('command')}")
                    print(f"  - Args: {gd.get('args')}")
                    
                    # Check if the python path exists
                    cmd_path = Path(gd.get('command', ''))
                    if cmd_path.exists():
                        print(f"  - Python executable: ✓ EXISTS")
                    else:
                        print(f"  - Python executable: ✗ NOT FOUND")
                else:
                    print(f"  - ✗ google-docs server not configured")
            except Exception as e:
                print(f"✗ Error reading {path}: {e}")
        else:
            print(f"  - {path}: not found")
    print()

def check_token():
    """Verify token.json exists and is valid."""
    token_path = Path.home() / '.claude' / 'mcp-servers' / 'google-docs-mcp-server' / 'token.json'
    
    print("=== Token Status ===")
    
    if not token_path.exists():
        print(f"✗ Token not found at {token_path}")
        print("  → Run: mcp__google-docs__authorize_google_docs()")
        return False
    
    try:
        with open(token_path) as f:
            token = json.load(f)
        
        print(f"✓ Token found at {token_path}")
        
        # Check required fields
        required = ['token', 'refresh_token', 'client_id', 'client_secret']
        missing = [f for f in required if f not in token]
        
        if missing:
            print(f"✗ Missing fields: {', '.join(missing)}")
            return False
        
        # Check scopes
        scopes = token.get('scopes', [])
        required_scopes = [
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive.file'
        ]
        
        print(f"  - Scopes: {len(scopes)} configured")
        for scope in required_scopes:
            if scope in scopes:
                print(f"    ✓ {scope}")
            else:
                print(f"    ✗ {scope} MISSING")
        
        # Check expiry
        if 'expiry' in token:
            from datetime import datetime
            expiry = datetime.fromisoformat(token['expiry'].replace('Z', '+00:00'))
            now = datetime.now(expiry.tzinfo)
            
            if expiry < now:
                print(f"  - ✗ Token EXPIRED at {token['expiry']}")
                print(f"  → Will auto-refresh on next use")
            else:
                print(f"  - ✓ Token valid until {token['expiry']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error reading token: {e}")
        return False
    
    print()

def check_credentials():
    """Verify credentials.json exists."""
    creds_path = Path.home() / '.claude' / 'mcp-servers' / 'google-docs-mcp-server' / 'credentials.json'
    
    print("=== Credentials Check ===")
    
    if not creds_path.exists():
        print(f"✗ credentials.json not found at {creds_path}")
        print("  → You need OAuth2 credentials from Google Cloud Console")
        return False
    
    try:
        with open(creds_path) as f:
            creds = json.load(f)
        
        print(f"✓ Credentials found")
        
        if 'installed' in creds:
            client = creds['installed']
            print(f"  - Client ID: {client.get('client_id', 'missing')[:40]}...")
            print(f"  - Project ID: {client.get('project_id', 'missing')}")
        elif 'web' in creds:
            client = creds['web']
            print(f"  - Client ID: {client.get('client_id', 'missing')[:40]}...")
            print(f"  - Project ID: {client.get('project_id', 'missing')}")
        else:
            print(f"  - ✗ Unknown credentials format")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error reading credentials: {e}")
        return False
    
    print()

def main():
    print("\n" + "="*60)
    print("Google Drive Upload - Authentication Diagnostics")
    print("="*60 + "\n")
    
    config_ok = check_mcp_config()
    creds_ok = check_credentials()
    token_ok = check_token()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if config_ok and creds_ok and token_ok:
        print("✓ All checks passed - authentication should work")
        print("\nIf you still get 'Authentication Needed' errors:")
        print("  1. Restart Claude Code to reload MCP servers")
        print("  2. Test with: mcp__google-docs__read_document(document_id='test')")
        print("  3. If that fails, re-authorize: mcp__google-docs__authorize_google_docs()")
    else:
        print("✗ Authentication issues detected")
        print("\nTO FIX:")
        if not creds_ok:
            print("  1. Ensure credentials.json exists with valid OAuth2 client")
        if not token_ok:
            print("  2. Run: mcp__google-docs__authorize_google_docs()")
            print("     This will open a browser for Google sign-in")
        if not config_ok:
            print("  3. Check .mcp.json points to the correct Python path")
    
    print()

if __name__ == '__main__':
    main()
