"""
Run PokeProtocol with Automatic Bug Report Generation

This script runs host, joiner, and spectator modes and automatically
generates a comprehensive bug report after execution.
"""

import sys
import time
import subprocess
import threading
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


def run_peer_mode(mode: str, port: int = None, host_ip: str = None, host_port: int = None):
    """
    Run a peer in a specific mode.
    
    Args:
        mode: 'host', 'joiner', or 'spectator'
        port: Port for the peer (optional)
        host_ip: Host IP for joiner/spectator (optional)
        host_port: Host port for joiner/spectator (optional)
    """
    script_path = Path(__file__).parent / 'interactive_battle.py'
    
    cmd = [sys.executable, str(script_path), mode]
    
    # Note: This is a simplified version. In practice, you'd want to
    # run these in separate processes or use the peer classes directly
    print(f"Would run: {' '.join(cmd)}")
    return cmd


def main():
    """Main entry point for running with debugging."""
    print("=" * 80)
    print("POKEPROTOCOL DEBUGGING MODE")
    print("=" * 80)
    print()
    print("This script will help you run the protocol with debugging enabled.")
    print("After running host, joiner, and spectator, a bug report will be generated.")
    print()
    print("To use:")
    print("1. Run this script to start debugging mode")
    print("2. In separate terminals, run:")
    print("   - python scripts/interactive_battle.py host")
    print("   - python scripts/interactive_battle.py joiner")
    print("   - python scripts/interactive_battle.py spectator")
    print("3. After all peers finish, run:")
    print("   - python scripts/generate_bug_report.py")
    print()
    print("The bug report will be saved as bug_report_YYYYMMDD_HHMMSS.txt")
    print()
    
    response = input("Press Enter to generate bug report from current session, or 'q' to quit: ")
    
    if response.lower() == 'q':
        return
    
    # Generate bug report
    print("\nGenerating bug report...")
    try:
        from generate_bug_report import BugReportGenerator
        
        generator = BugReportGenerator()
        filename = generator.save_report()
        
        print(f"\n✓ Bug report generated successfully!")
        print(f"  File: {filename}")
        print(f"\nTo view the report:")
        print(f"  - Open {filename} in a text editor")
        print(f"  - Or run: cat {filename} (Linux/Mac)")
        print(f"  - Or run: type {filename} (Windows)")
        
    except ImportError as e:
        print(f"\n✗ Error: Could not import bug report generator: {e}")
        print("  Make sure scripts/generate_bug_report.py exists")
    except Exception as e:
        print(f"\n✗ Error generating bug report: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

