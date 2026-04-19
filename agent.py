"""
Automation Workflow Agent
--------------------------
An AI agent powered by Claude that helps you:
  • Create automation workflow connections between services
  • Diagnose and fix errors in automation workflows

Usage:
    python agent.py

Set your API key:
    export ANTHROPIC_API_KEY="sk-ant-..."
"""

import os
import anthropic

from tools import (
    analyze_error,
    check_api_endpoint,
    suggest_workflow_fix,
    generate_workflow_template,
    validate_workflow_config,
)

SYSTEM_PROMPT = """You are an expert automation workflow engineer. You help users:

1. CREATE automation workflow connections between services (Google My Business, Slack,
   Google Sheets, Zapier, Make, HubSpot, etc.)
2. DIAGNOSE and FIX errors that appear in automation workflows

When the user describes a problem or wants to build something, use your tools to:
- Analyze any error messages they share
- Check if API endpoints are reachable
- Suggest concrete fixes with code examples
- Generate ready-to-use workflow templates
- Validate their workflow configuration

Always be specific and practical. When you suggest a fix, show the exact steps
and code. When generating a workflow template, explain what environment variables
need to be set and how to run it."""

TOOLS = [
    analyze_error,
    check_api_endpoint,
    suggest_workflow_fix,
    generate_workflow_template,
    validate_workflow_config,
]


def run_agent():
    client = anthropic.Anthropic()
    conversation: list[dict] = []

    print("=" * 60)
    print("  Automation Workflow Agent")
    print("  Powered by Claude claude-opus-4-7")
    print("=" * 60)
    print("\nI can help you:")
    print("  • Build automation workflow connections between services")
    print("  • Diagnose and fix errors in your workflows")
    print("\nType 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        conversation.append({"role": "user", "content": user_input})

        runner = client.beta.messages.tool_runner(
            model="claude-opus-4-7",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=conversation,
        )

        final_message = None
        for message in runner:
            final_message = message

        if final_message is None:
            print("Agent: (no response)\n")
            continue

        assistant_text = ""
        for block in final_message.content:
            if block.type == "text":
                assistant_text += block.text

        print(f"\nAgent: {assistant_text}\n")

        conversation.append({
            "role": "assistant",
            "content": assistant_text or "(tool result)",
        })


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.")
        print("Set it with: export ANTHROPIC_API_KEY='sk-ant-...'")
        raise SystemExit(1)

    run_agent()
