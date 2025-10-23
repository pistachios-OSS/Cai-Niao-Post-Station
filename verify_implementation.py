"""
Verification script to check the implementation without requiring all dependencies.
This verifies the structure and key features of the fix.
"""
import ast
import sys
from pathlib import Path


def check_file_syntax(filepath):
    """Check if a Python file has valid syntax."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read(), filename=str(filepath))
        return True, None
    except SyntaxError as e:
        return False, str(e)


def check_server_lifespan_implementation():
    """Check if server.py uses lifespan instead of on_event."""
    server_file = Path("server.py")
    if not server_file.exists():
        return False, "server.py not found"
    
    content = server_file.read_text()
    lines = content.split('\n')
    
    # Check for lifespan usage
    has_lifespan = "@asynccontextmanager" in content and "async def lifespan" in content
    
    # Check that on_event decorator is NOT actually used (not in comments)
    # Look for lines starting with @app.on_event (ignoring comments)
    has_on_event = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('@app.on_event'):
            has_on_event = True
            break
    
    # Check for FastAPI app creation with lifespan
    has_app_with_lifespan = "lifespan=lifespan" in content
    
    if has_on_event:
        return False, "Still uses deprecated @app.on_event decorator"
    
    if not has_lifespan:
        return False, "Does not use lifespan event handler"
    
    if not has_app_with_lifespan:
        return False, "FastAPI app not configured with lifespan"
    
    return True, "Uses modern lifespan event handlers"


def check_port_conflict_handling():
    """Check if port conflict is handled."""
    server_file = Path("server.py")
    if not server_file.exists():
        return False, "server.py not found"
    
    content = server_file.read_text()
    
    # Check for find_available_port function
    has_find_port = "def find_available_port" in content
    
    # Check for socket binding test
    has_socket_check = "socket.socket" in content and "s.bind" in content
    
    # Check for auto_port parameter
    has_auto_port = "auto_port" in content
    
    if not has_find_port:
        return False, "Missing find_available_port function"
    
    if not has_socket_check:
        return False, "Missing socket binding check"
    
    if not has_auto_port:
        return False, "Missing auto_port configuration"
    
    return True, "Port conflict handling implemented"


def check_main_modes():
    """Check if main.py supports both CLI and server modes."""
    main_file = Path("main.py")
    if not main_file.exists():
        return False, "main.py not found"
    
    content = main_file.read_text()
    
    # Check for argparse
    has_argparse = "import argparse" in content
    
    # Check for mode selection
    has_mode_choice = '"cli", "server"' in content or "'cli', 'server'" in content
    
    # Check for run_cli and run_server functions
    has_cli_function = "def run_cli" in content
    has_server_function = "def run_server" in content
    
    if not has_argparse:
        return False, "Missing argparse for mode selection"
    
    if not has_mode_choice:
        return False, "Missing CLI/server mode choice"
    
    if not has_cli_function or not has_server_function:
        return False, "Missing run_cli or run_server functions"
    
    return True, "Supports both CLI and server modes"


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Verification of FastAPI Implementation Fixes")
    print("=" * 60)
    
    checks = [
        ("Syntax check: main.py", lambda: check_file_syntax("main.py")),
        ("Syntax check: server.py", lambda: check_file_syntax("server.py")),
        ("Modern lifespan events", check_server_lifespan_implementation),
        ("Port conflict handling", check_port_conflict_handling),
        ("CLI and server modes", check_main_modes),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            passed, message = check_func()
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"\n{status}: {check_name}")
            if message:
                print(f"  → {message}")
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"\n✗ ERROR: {check_name}")
            print(f"  → {str(e)}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All checks passed!")
        print("\nKey features implemented:")
        print("  1. Modern lifespan event handlers (no deprecation warning)")
        print("  2. Automatic port conflict resolution")
        print("  3. Both CLI and server modes supported")
        print("\nTo run the server:")
        print("  python main.py --mode server")
        print("\nThe server will automatically find an available port")
        print("starting from 8000 if the default port is in use.")
    else:
        print("✗ Some checks failed")
        return 1
    
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
