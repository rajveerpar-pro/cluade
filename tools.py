"""
Automation workflow tools for the Claude agent.
Each tool handles a specific aspect of workflow creation and error resolution.
"""

import json
import requests
from anthropic import beta_tool


@beta_tool
def analyze_error(error_message: str, error_code: str = "", service_name: str = "") -> str:
    """
    Analyze an automation workflow error and explain what went wrong.

    Args:
        error_message: The full error message from the automation workflow.
        error_code: HTTP status code or error code (e.g. '429', '403', 'ECONNREFUSED').
        service_name: Name of the service that threw the error (e.g. 'Google My Business', 'Slack').
    """
    analysis = {
        "error_message": error_message,
        "error_code": error_code,
        "service": service_name,
        "diagnosis": "",
        "severity": "",
        "is_retryable": False,
    }

    code = str(error_code).strip()

    if code == "429" or "rate limit" in error_message.lower():
        analysis["diagnosis"] = (
            "Rate limit exceeded. The API is rejecting requests because too many "
            "were sent in a short period. This is temporary."
        )
        analysis["severity"] = "low"
        analysis["is_retryable"] = True
        analysis["recommended_wait_seconds"] = 60

    elif code == "401" or "unauthorized" in error_message.lower():
        analysis["diagnosis"] = (
            "Authentication failed. The API key or OAuth token is missing, expired, "
            "or invalid. Refresh credentials and retry."
        )
        analysis["severity"] = "high"
        analysis["is_retryable"] = False

    elif code == "403" or "forbidden" in error_message.lower() or "permission" in error_message.lower():
        analysis["diagnosis"] = (
            "Permission denied. The authenticated account does not have access to "
            "this resource. Check API scopes and account permissions."
        )
        analysis["severity"] = "high"
        analysis["is_retryable"] = False

    elif code == "404" or "not found" in error_message.lower():
        analysis["diagnosis"] = (
            "Resource not found. The endpoint URL may be wrong, or the resource "
            "(account, location, etc.) may have been deleted or moved."
        )
        analysis["severity"] = "medium"
        analysis["is_retryable"] = False

    elif code in ("500", "502", "503", "529") or "server error" in error_message.lower():
        analysis["diagnosis"] = (
            "Server-side error from the external API. This is temporary â "
            "retry with exponential backoff."
        )
        analysis["severity"] = "low"
        analysis["is_retryable"] = True
        analysis["recommended_wait_seconds"] = 30

    elif "timeout" in error_message.lower() or "connection" in error_message.lower():
        analysis["diagnosis"] = (
            "Network connectivity issue. The service may be unreachable, "
            "or the request timed out. Check your internet connection and retry."
        )
        analysis["severity"] = "medium"
        analysis["is_retryable"] = True
        analysis["recommended_wait_seconds"] = 10

    elif "need sudo" in error_message.lower() or "administrator" in error_message.lower():
        analysis["diagnosis"] = (
            "Insufficient system permissions. The process requires elevated privileges. "
            "Run as administrator or use a package manager that doesn't need sudo."
        )
        analysis["severity"] = "medium"
        analysis["is_retryable"] = False

    else:
        analysis["diagnosis"] = (
            "Unrecognized error. Check the service documentation for error code details."
        )
        analysis["severity"] = "unknown"
        analysis["is_retryable"] = False

    return json.dumps(analysis, indent=2)


@beta_tool
def check_api_endpoint(url: str, method: str = "GET", headers: str = "{}") -> str:
    """
    Test connectivity to an API endpoint and report the result.

    Args:
        url: The full URL to test (e.g. 'https://api.example.com/v1/health').
        method: HTTP method to use: GET, POST, HEAD. Defaults to GET.
        headers: JSON string of HTTP headers to include (e.g. '{"Authorization": "Bearer TOKEN"}').
    """
    try:
        parsed_headers = json.loads(headers) if headers else {}
    except json.JSONDecodeError:
        return json.dumps({"success": False, "error": "Invalid headers JSON"})

    result = {
        "url": url,
        "method": method.upper(),
        "success": False,
        "status_code": None,
        "reachable": False,
        "latency_ms": None,
        "error": None,
    }

    try:
        import time
        start = time.monotonic()
        resp = requests.request(
            method.upper(),
            url,
            headers=parsed_headers,
            timeout=10,
            allow_redirects=True,
        )
        elapsed = round((time.monotonic() - start) * 1000)

        result["status_code"] = resp.status_code
        result["latency_ms"] = elapsed
        result["reachable"] = True
        result["success"] = resp.status_code < 400
        if not result["success"]:
            result["error"] = f"HTTP {resp.status_code}"

    except requests.exceptions.ConnectionError as e:
        result["error"] = f"Connection refused or DNS failure: {str(e)[:120]}"
    except requests.exceptions.Timeout:
        result["error"] = "Request timed out after 10 seconds"
    except Exception as e:
        result["error"] = str(e)[:200]

    return json.dumps(result, indent=2)


@beta_tool
def suggest_workflow_fix(
    error_type: str,
    service_name: str,
    workflow_step: str = "",
) -> str:
    """
    Suggest concrete fixes for a failing automation workflow step.

    Args:
        error_type: Type of error: 'auth', 'rate_limit', 'not_found', 'permission',
                    'server_error', 'network', 'config', 'sudo'.
        service_name: Name of the service (e.g. 'Google My Business', 'Zapier', 'Make').
        workflow_step: Description of the failing step (optional).
    """
    fixes = {
        "auth": {
            "title": "Authentication Fix",
            "steps": [
                "1. Delete the stored token file (e.g. token.json, .credentials/)",
                "2. Re-run the authentication flow to get fresh tokens",
                "3. Ensure your OAuth scopes include all required permissions",
                "4. For API keys: regenerate the key in the service's developer console",
                "5. Set the key as an environment variable â never hardcode it",
            ],
            "code_example": (
                "import os\n"
                "# Refresh token example\n"
                "token_path = 'token.json'\n"
                "if os.path.exists(token_path):\n"
                "    os.remove(token_path)\n"
                "# Re-run your auth flow"
            ),
        },
        "rate_limit": {
            "title": "Rate Limit Fix",
            "steps": [
                "1. Add exponential backoff: start at 1s, double on each retry (max 6 retries)",
                "2. Reduce request concurrency â process items sequentially",
                "3. Cache responses where possible to reduce repeat calls",
                "4. Check the service's rate limit headers (X-RateLimit-Remaining)",
                "5. Consider upgrading your API tier for higher limits",
            ],
            "code_example": (
                "import time\n\n"
                "def api_call_with_backoff(fn, max_retries=6):\n"
                "    for attempt in range(max_retries):\n"
                "        try:\n"
                "            return fn()\n"
                "        except RateLimitError:\n"
                "            wait = 2 ** attempt\n"
                "            print(f'Rate limited. Waiting {wait}s...')\n"
                "            time.sleep(wait)\n"
                "    raise Exception('Max retries exceeded')"
            ),
        },
        "not_found": {
            "title": "Resource Not Found Fix",
            "steps": [
                "1. Verify the resource ID or URL is correct",
                "2. Check if the resource still exists in the service's dashboard",
                "3. Confirm you are targeting the correct environment (prod vs staging)",
                "4. Review any recent API version changes in the service docs",
            ],
            "code_example": "",
        },
        "permission": {
            "title": "Permission Fix",
            "steps": [
                "1. Check which OAuth scopes your app has â compare to what the endpoint needs",
                "2. Re-authorize the app with the required scopes",
                f"3. For {service_name}: check the developer console for scope settings",
                "4. Ensure the account has the right role (e.g. Owner, Editor)",
            ],
            "code_example": "",
        },
        "server_error": {
            "title": "Server Error Fix",
            "steps": [
                "1. Wait 30â60 seconds and retry",
                f"2. Check {service_name}'s status page for ongoing incidents",
                "3. Implement retry logic with backoff for 5xx errors",
                "4. Log the request_id from the response header for support tickets",
            ],
            "code_example": "",
        },
        "network": {
            "title": "Network Fix",
            "steps": [
                "1. Verify your internet connection is active",
                "2. Test the endpoint directly: curl -I <url>",
                "3. Check if a firewall or proxy is blocking outbound requests",
                "4. Set a timeout on your HTTP requests (recommended: 30s)",
            ],
            "code_example": (
                "import requests\n"
                "response = requests.get(url, timeout=30)"
            ),
        },
        "sudo": {
            "title": "System Permission Fix (No sudo needed)",
            "steps": [
                "1. Use nvm to install Node.js without sudo:",
                "   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash",
                "   nvm install --lts",
                "   npm install -g @anthropic-ai/claude-code",
                "2. For Python packages: use a virtual environment (python3 -m venv .venv)",
                "3. For pip: use --user flag: pip install --user <package>",
            ],
            "code_example": (
                "# Create and activate a virtual environment\n"
                "python3 -m venv .venv\n"
                "source .venv/bin/activate\n"
                "pip install -r requirements.txt"
            ),
        },
        "config": {
            "title": "Configuration Fix",
            "steps": [
                "1. Validate your config file structure against the service docs",
                "2. Check for missing required fields",
                "3. Ensure API keys and URLs are set correctly",
                "4. Use environment variables for secrets â never hardcode them",
            ],
            "code_example": (
                "import os\n"
                "from dotenv import load_dotenv\n\n"
                "load_dotenv()  # loads .env file\n"
                "api_key = os.environ['API_KEY']  # raises if missing"
            ),
        },
    }

    fix = fixes.get(error_type.lower(), {
        "title": "General Workflow Fix",
        "steps": [
            "1. Check the service's API documentation for the failing step",
            "2. Enable verbose logging to capture the full request/response",
            "3. Test the endpoint manually with curl or Postman",
            "4. Search the service's community forums for similar errors",
        ],
        "code_example": "",
    })

    output = {
        "service": service_name,
        "workflow_step": workflow_step,
        "fix": fix,
    }
    return json.dumps(output, indent=2)


@beta_tool
def generate_workflow_template(
    source_service: str,
    target_service: str,
    trigger: str,
    action: str,
) -> str:
    """
    Generate a Python automation workflow template connecting two services.

    Args:
        source_service: The service that triggers the workflow (e.g. 'Google My Business').
        target_service: The service that receives the output (e.g. 'Slack', 'Google Sheets').
        trigger: What event starts the workflow (e.g. 'new review', 'form submission').
        action: What action to perform on the target (e.g. 'send message', 'append row').
    """
    template = f'''"""
Automation workflow: {source_service} â {target_service}
Trigger : {trigger}
Action  : {action}
"""

import os
import time
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ââ Configuration ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
SOURCE_API_KEY = os.environ["{source_service.upper().replace(" ", "_")}_API_KEY"]
TARGET_API_KEY = os.environ["{target_service.upper().replace(" ", "_")}_API_KEY"]
MAX_RETRIES    = 6


# ââ Helpers ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def api_get(url: str, headers: dict, retries: int = MAX_RETRIES):
    """GET with exponential backoff for rate-limit and server errors."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 429:
                wait = 2 ** attempt
                log.warning("Rate limited â waiting %ds (attempt %d/%d)", wait, attempt + 1, retries)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError as e:
            log.error("Connection error: %s", e)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"API call failed after {{retries}} retries: {{url}}")


def api_post(url: str, headers: dict, payload: dict, retries: int = MAX_RETRIES):
    """POST with exponential backoff."""
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 429:
                wait = 2 ** attempt
                log.warning("Rate limited â waiting %ds", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError as e:
            log.error("Connection error: %s", e)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"API call failed after {{retries}} retries: {{url}}")


# ââ Source: fetch data from {source_service} âââââââââââââââââââââââââââââââââââ
def fetch_from_source() -> list[dict]:
    """Fetch items triggered by: {trigger}"""
    url = "https://api.{source}.example.com/v1/items".format(
        source="{source_service.lower().replace(' ', '-')}"
    )
    headers = {{"Authorization": f"Bearer {{SOURCE_API_KEY}}"}}
    data = api_get(url, headers)
    items = data.get("items", [])
    log.info("Fetched %d items from {source_service}", len(items))
    return items


# ââ Target: send data to {target_service} âââââââââââââââââââââââââââââââââââââ
def send_to_target(item: dict) -> None:
    """Perform action: {action}"""
    url = "https://api.{target}.example.com/v1/action".format(
        target="{target_service.lower().replace(' ', '-')}"
    )
    headers = {{"Authorization": f"Bearer {{TARGET_API_KEY}}", "Content-Type": "application/json"}}
    payload = {{
        "text": f"New event from {source_service}: {{item.get('title', item)}}",
        "data": item,
    }}
    result = api_post(url, headers, payload)
    log.info("Sent to {target_service}: %s", result)


# ââ Main workflow ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def run():
    log.info("Starting workflow: {source_service} â {target_service}")
    try:
        items = fetch_from_source()
        for item in items:
            send_to_target(item)
        log.info("Workflow complete â processed %d items", len(items))
    except Exception as e:
        log.error("Workflow failed: %s", e)
        raise


if __name__ == "__main__":
    run()
'''
    return json.dumps({
        "source_service": source_service,
        "target_service": target_service,
        "trigger": trigger,
        "action": action,
        "template": template,
        "env_vars_needed": [
            f"{source_service.upper().replace(' ', '_')}_API_KEY",
            f"{target_service.upper().replace(' ', '_')}_API_KEY",
        ],
        "next_steps": [
            "1. Set the required environment variables in a .env file",
            "2. Replace placeholder API URLs with the real endpoints",
            "3. Install dependencies: pip install requests python-dotenv",
            "4. Run: python workflow.py",
        ],
    }, indent=2)


@beta_tool
def validate_workflow_config(config_json: str) -> str:
    """
    Validate a workflow configuration JSON and report missing or invalid fields.

    Args:
        config_json: JSON string representing the workflow configuration to validate.
    """
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError as e:
        return json.dumps({
            "valid": False,
            "errors": [f"Invalid JSON: {e}"],
            "warnings": [],
        })

    errors = []
    warnings = []

    required_fields = ["source", "target", "trigger", "action"]
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: '{field}'")

    if "api_key" in str(config).lower():
        value = str(config)
        if any(len(v) > 10 for k, v in config.items() if "key" in k.lower() and isinstance(v, str)):
            warnings.append(
                "Potential hardcoded API key detected. Use environment variables instead."
            )

    if "retry" not in config and "retries" not in config:
        warnings.append("No retry configuration found. Consider adding retry logic for resilience.")

    if "timeout" not in config:
        warnings.append("No timeout configured. Requests may hang indefinitely.")

    if "logging" not in config and "log_level" not in config:
        warnings.append("No logging configured. Add logging to help debug failures.")

    return json.dumps({
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "fields_found": list(config.keys()),
    }, indent=2)
