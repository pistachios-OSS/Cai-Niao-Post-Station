"""
Main entry point for HR Knowledge Base Agent.
Supports both CLI and server modes.
"""
import argparse
import sys

from .hr_agent import HRKnowledgeBaseAgent


def run_cli():
    """Run in CLI mode for testing."""
    agent = HRKnowledgeBaseAgent()

    query = """
    请帮我为员工张三生成一份B1模板的警告文档，
    违规原因是多次迟到，职位是工程师，员工ID是666，部门是研发部，经理是李四，违规详情是经常上班迟到早退。
    """
    result = agent.generate_answer(query)
    print(result)


def run_server(host: str = "0.0.0.0", port: int = 8000, auto_port: bool = True):
    """Run in server mode."""
    from .server import run_server
    run_server(host=host, port=port, auto_port=auto_port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HR Knowledge Base Agent")
    parser.add_argument(
        "--mode",
        choices=["cli", "server"],
        default="cli",
        help="Run mode: cli for command-line interface, server for API server"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host address for server mode (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for server mode (default: 8000)"
    )
    parser.add_argument(
        "--no-auto-port",
        action="store_true",
        help="Disable automatic port selection if specified port is in use"
    )
    
    args = parser.parse_args()
    
    if args.mode == "cli":
        run_cli()
    else:
        run_server(host=args.host, port=args.port, auto_port=not args.no_auto_port)
