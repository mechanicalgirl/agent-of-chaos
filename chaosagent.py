# /// script
# requires-python="==3.12"
# dependencies = [
#   "paramiko==4.0.0",
#   "python-dotenv==1.2.2",
#   "anthropic==0.77.1",
# ]
# ///

import anthropic
from dotenv import load_dotenv
import paramiko

from datetime import datetime
import os
import sys


load_dotenv()
ssh_host = os.getenv("SSH_HOST")
ssh_port = int(os.getenv("SSH_PORT"))
ssh_user = os.getenv("SSH_USER")
ssh_password = os.getenv("SSH_PASSWORD")

SESSION_ID = datetime.now().strftime("%Y%m%d-%H%M%S")
RESULTS_DIR = f"./session-{SESSION_ID}"
RETRIEVED_DIR = f"{RESULTS_DIR}/retrieved"
REPORT_FILE = f"{RESULTS_DIR}/report.txt"
os.makedirs(RETRIEVED_DIR, exist_ok=True)

def log(message):
    print(message)
    with open(f"{RESULTS_DIR}/agent.log", "a") as f:
        f.write(message + "\n")

client = anthropic.Anthropic()

tools = [
    {
        "name": "run_command",
        "description": "Run a read-only shell command on the remote server via SSH",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to run"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file on the remote server",
        "input_schema": {
            "type": "object", 
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the file"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "retrieve_file",
        "description": "Download a text file from the remote server to local storage for detailed review",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the file on the remote server"}
            },
            "required": ["path"]
        }
    }
]

def run_command(ssh, command):
    forbidden = ["rm", "mv", "chmod", "chown", "sudo"]
    if any(f in command for f in forbidden):
        return "ERROR: That command is not permitted"
    _, stdout, stderr = ssh.exec_command(command, timeout=10)
    try:
        return stdout.read().decode() or stderr.read().decode() or "(no output)"
    except Exception:
        return "ERROR: Command timed out"

def read_file(ssh, path):
    _, stdout, _ = ssh.exec_command(f"cat {path}")
    return stdout.read().decode() or "(no output)"

def retrieve_file(ssh, remote_path):
    try:
        sftp = ssh.open_sftp()
        local_path = f"{RETRIEVED_DIR}{remote_path}"
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        sftp.get(remote_path, local_path)
        sftp.close()
        return f"File retrieved to {local_path}"
    except PermissionError:
        return f"ERROR: Permission denied reading {remote_path}"
    except FileNotFoundError:
        return f"ERROR: File not found: {remote_path}"
    except Exception as e:
        return f"ERROR: Could not retrieve {remote_path}: {str(e)}"

def retrieve_manifests(ssh):
    _, stdout, _ = ssh.exec_command("cat /var/run/manifest_location.txt")
    manifest_dir = stdout.read().decode().strip()
    if not manifest_dir:
        log("WARNING: manifest_location.txt not found, skipping manifest retrieval")
        return
    sftp = ssh.open_sftp()
    for filename in ["manifest.json", "manifest.txt"]:
        local_path = f"{RESULTS_DIR}/{filename}"
        try:
            sftp.get(f"{manifest_dir}/{filename}", local_path)
            log(f"Retrieved {filename}")
        except FileNotFoundError:
            log(f"WARNING: {filename} not found on server")
    sftp.close()

def run_agent(ssh):
    retrieve_manifests(ssh)  # grab ground truth before agent starts

    messages = [
        {
            "role": "user",
            "content": """You are auditing a legacy email server to help plan a migration and rebuild.
            Your primary focus is mail infrastructure, but document the broader system as well.

            Explore and report on:

            PRIMARY (be thorough):
            - Mail software installed, versions, and configuration (Postfix, Dovecot, Sendmail, Exim, etc.)
            - Mail-related services, processes, and ports
            - SSL/TLS configuration and certificates
            - Authentication configuration
            - Any documentation files, notes, or text files you find anywhere on the system
            - Security concerns specific to the mail configuration

            SECONDARY (high level only):
            - Operating system version and general health
            - Disk usage and available space
            - Any running processes and services (include any non-email services, even if they seem benign)
            - Anything that looks concerning or outdated

            IMPORTANT: Only run non-interactive commands. Avoid commands that wait for 
            user input like bare 'sendmail', 'mail', 'telnet' without arguments, etc.
            Use flags that force non-interactive mode where possible (e.g. 'sendmail -V' 
            instead of 'sendmail').

            When you find standalone text files or documentation artifacts, use retrieve_file to 
            download them for detailed review.

            Be thorough but only use read-only commands."""
        }
    ]

    while True:
        log(f"--- Loop iteration, messages so far: {len(messages)} ---")
        response = client.messages.create(
            # model="claude-opus-4-5",
            model="claude-haiku-4-5-20251001",
            max_tokens=8192,  # bump from 4096
            tools=tools,
            messages=messages
        )

        # add assistant response to history
        messages.append({"role": "assistant", "content": response.content})

        # if claude is done, print the final report and exit
        if response.stop_reason == "end_turn":
            log("--- Agent finished, generating report ---")
            for block in response.content:
                if hasattr(block, "text"):
                    log(block.text)
                    with open(REPORT_FILE, "w") as f:
                        f.write(block.text)
            break

        # otherwise, execute whatever tools claude asked for
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                log(f">>> Calling tool: {block.name} with {block.input}")
                if block.name == "run_command":
                    result = run_command(ssh, block.input["command"])
                elif block.name == "read_file":
                    result = read_file(ssh, block.input["path"])
                elif block.name == "retrieve_file":
                    result = retrieve_file(ssh, block.input["path"])
                log(f"<<< Result: {result[:100]}...")  # just first 100 chars so it's not overwhelming
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })

        if tool_results:
            # feed results back to claude and loop again
            messages.append({"role": "user", "content": tool_results})
        else:
         if not tool_results:
            log(f"WARNING: No tool results, stop_reason={response.stop_reason}")
            for block in response.content:
                log(f"  block type: {block.type}")
                if hasattr(block, 'text') and block.text:
                    log(f"  text: {block.text[:200]}")
                    with open(REPORT_FILE, "w") as f:
                        f.write(block.text + "\n(NOTE: Report may be incomplete)")
            break

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # For local testing only
    # ssh.load_system_host_keys() # loads ~/.ssh/known_hosts automatically; SSH into the real server manually once first, accept the key
    ssh.connect(ssh_host, port=ssh_port, username=ssh_user, password=ssh_password)
    log("SSH connection successful")
except Exception as e:
    log(e)
    sys.exit()

run_agent(ssh) 
ssh.close()

# uv run chaosagent.py
