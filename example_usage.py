"""
Example usage of the HR Knowledge Base Agent API.
This demonstrates how to interact with the server.
"""
import requests
import json


def test_server_health(base_url: str = "http://localhost:8000"):
    """Test server health check."""
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health Check: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("Server is not running or connection failed")
        return False


def test_query(base_url: str = "http://localhost:8000"):
    """Test query endpoint."""
    query_data = {
        "query": """
        请帮我为员工张三生成一份B1模板的警告文档，
        违规原因是多次迟到，职位是工程师，员工ID是666，部门是研发部，经理是李四，违规详情是经常上班迟到早退。
        """,
        "template_type": "B1"
    }
    
    try:
        response = requests.post(f"{base_url}/api/query", json=query_data)
        print(f"\nQuery Response: {response.status_code}")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("Server is not running or connection failed")
        return False


if __name__ == "__main__":
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print(f"Testing HR Agent API at {base_url}")
    print("=" * 50)
    
    if test_server_health(base_url):
        print("\n✓ Server is healthy")
        test_query(base_url)
    else:
        print("\n✗ Server health check failed")
        print("\nTo start the server, run:")
        print("  python -m main --mode server")
