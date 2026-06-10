#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import re
import urllib.request

# Security Rule Definitions
CLOUD_LIBS_PY = [
    r"(import|from)\s+(openai|anthropic|google\.generativeai|assemblyai|google\.cloud\.speech|azure\.cognitiveservices\.speech)",
    r"boto3\.client\(['\"]transcribe['\"]\)",
]

CLOUD_ENDPOINTS = [
    r"api\.openai\.com",
    r"api\.anthropic\.com",
    r"generativelanguage\.googleapis\.com",
    r"api\.assemblyai\.com",
    r"speech\.googleapis\.com",
    r"cognitiveservices\.azure\.com",
]

AUDIO_EXTENSIONS = [r"\.wav", r"\.raw", r"\.pcm", r"\.mp3", r"\.ogg", r"\.flac", r"\.aac", r"\.m4a"]

# Combine audio extensions into regex
AUDIO_EXT_REGEX = "|".join(AUDIO_EXTENSIONS)

# Python file writing pattern for audio files
PY_AUDIO_WRITE_PATTERNS = [
    rf"open\(.*({AUDIO_EXT_REGEX}).*['\"][w|a]b?['\"]\)",
    r"soundfile\.write\(",
    r"scipy\.io\.wavfile\.write\(",
    rf"wave\.open\(.*({AUDIO_EXT_REGEX}).*['\"][w|a]b?['\"]\)",
    r"librosa\.output\.write_wav\(",
]

# C++ file writing pattern for audio files
CPP_AUDIO_WRITE_PATTERNS = [
    rf"std::(ofstream|fstream).*({AUDIO_EXT_REGEX})",
    rf"fopen\(.*({AUDIO_EXT_REGEX}).*['\"][w|a]b?['\"]\)",
]

def get_diff():
    base_ref = os.environ.get("GITHUB_BASE_REF")
    if base_ref:
        print(f"Detected PR context. Base ref: {base_ref}")
        subprocess.run(["git", "fetch", "origin", base_ref], check=True)
        result = subprocess.run(
            ["git", "diff", f"origin/{base_ref}...HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    else:
        print("Detected non-PR/push context.")
        res = subprocess.run(["git", "rev-parse", "HEAD~1"], capture_output=True)
        if res.returncode == 0:
            result = subprocess.run(
                ["git", "diff", "HEAD~1...HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        else:
            result = subprocess.run(
                ["git", "diff", "4b825dc642cb6eb9a0ff3e482d4c5f14e2f0d041...HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout

def parse_diff(diff_text):
    file_changes = {}
    current_file = None
    
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            file_changes[current_file] = []
        elif line.startswith("+") and not line.startswith("+++"):
            if current_file:
                file_changes[current_file].append(line[1:])
    return file_changes

def scan_changes(file_changes):
    violations = []
    
    for filepath, lines in file_changes.items():
        ext = os.path.splitext(filepath)[1].lower()
        is_python = ext == ".py"
        is_cpp = ext in [".cpp", ".h", ".hpp", ".cc", ".cxx"]
        
        if not (is_python or is_cpp):
            continue
            
        if filepath == "scripts/ai_reviewer.py":
            continue
            
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith("#") or line_stripped.startswith("//"):
                continue
                
            # Rule 1: Zero Cloud Processing Checks
            if is_python:
                for pattern in CLOUD_LIBS_PY:
                    if re.search(pattern, line_stripped):
                        violations.append({
                            "file": filepath,
                            "line": line_stripped,
                            "rule": "Zero Cloud Processing Violation (Cloud Library Import)",
                            "desc": f"Found forbidden import/library usage: `{line_stripped}`"
                        })
            
            for pattern in CLOUD_ENDPOINTS:
                if re.search(pattern, line_stripped, re.IGNORECASE):
                    violations.append({
                        "file": filepath,
                        "line": line_stripped,
                        "rule": "Zero Cloud Processing Violation (Cloud API Endpoint)",
                        "desc": f"Found reference to cloud service endpoint: `{line_stripped}`"
                    })
            
            # Rule 2: In-Memory Only Checks
            if is_python:
                for pattern in PY_AUDIO_WRITE_PATTERNS:
                    if re.search(pattern, line_stripped):
                        violations.append({
                            "file": filepath,
                            "line": line_stripped,
                            "rule": "In-Memory Only Storage Violation (Audio File Save)",
                            "desc": f"Found file write pattern to physical disk: `{line_stripped}`. All audio capture and transcription must execute exclusively in RAM."
                        })
            
            if is_cpp:
                for pattern in CPP_AUDIO_WRITE_PATTERNS:
                    if re.search(pattern, line_stripped):
                        violations.append({
                            "file": filepath,
                            "line": line_stripped,
                            "rule": "In-Memory Only Storage Violation (Audio File Save)",
                            "desc": f"Found file write pattern to physical disk: `{line_stripped}`. All audio capture and transcription must execute exclusively in RAM."
                        })
                        
    return violations

def post_pr_comment(repo_name, pr_number, token, violations):
    url = f"https://api.github.com/repos/{repo_name}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "TrueVoice-AI-Reviewer-Action"
    }
    
    body = "## ⚠️ TrueVoice Security Scan: Vulnerabilities Detected\n\n"
    body += "Our continuous compliance scanner has identified security policy violations in this Pull Request. "
    body += "Please resolve them to satisfy the project's Zero-Trust and In-Memory rules before merging.\n\n"
    body += "| File | Line | Rule | Description |\n"
    body += "| --- | --- | --- | --- |\n"
    
    for v in violations:
        escaped_line = v["line"].replace("|", "\\|")
        body += f"| `{v['file']}` | `{escaped_line}` | **{v['rule']}** | {v['desc']} |\n"
        
    data = json.dumps({"body": body}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Comment posted successfully to PR #{pr_number}. Response code: {response.getcode()}")
    except Exception as e:
        print(f"Failed to post comment to PR #{pr_number}: {e}")

def post_pr_comment_text(repo_name, pr_number, token, body):
    url = f"https://api.github.com/repos/{repo_name}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "TrueVoice-AI-Reviewer-Action"
    }
    data = json.dumps({"body": body}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Comment posted successfully to PR #{pr_number}. Response code: {response.getcode()}")
    except Exception as e:
        print(f"Failed to post comment to PR #{pr_number}: {e}")

def run_gemini_review(diff_text, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt = (
        "You are a professional security reviewer. Your task is to audit the following git diff of a codebase "
        "for security vulnerabilities. Specifically, look for:\n"
        "1. Hardcoded secrets, API keys, passwords, or credentials.\n"
        "2. Bypass or deletion of security validation, input sanitization, or Filter-Verify checks.\n"
        "3. Any other critical security vulnerabilities.\n\n"
        "IMPORTANT CONTEXT:\n"
        "This is an academic / prototype project. It is expected to use mock classes, mock services, and mock test interfaces. "
        "Do NOT report mock files, simulation scripts, or test frameworks as security violations. Focus strictly on real "
        "production code changes in services/ or apps/.\n\n"
        "INSTRUCTIONS FOR YOUR RESPONSE:\n"
        "1. Start your response with a summary report of your findings in Markdown format.\n"
        "2. If you find any actual critical vulnerability that violates the rules (e.g. real hardcoded credentials, bypass of verification in services), "
        "you MUST include the exact string 'VULNERABILITY_FOUND' in your response.\n"
        "3. If everything is secure or only mock/simulation vulnerabilities are present, do NOT include 'VULNERABILITY_FOUND'.\n\n"
        f"Git Diff:\n{diff_text}"
    )
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            review_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            return review_text
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None

def main():
    try:
        diff_text = get_diff()
    except subprocess.CalledProcessError as e:
        print(f"Error getting git diff: {e}")
        sys.exit(1)
        
    file_changes = parse_diff(diff_text)
    violations = scan_changes(file_changes)
    
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    gemini_report = ""
    gemini_vulnerability_found = False
    
    if gemini_api_key:
        print("GEMINI_API_KEY detected. Initiating Gemini AI Security review...")
        review_text = run_gemini_review(diff_text, gemini_api_key)
        if review_text:
            gemini_report = review_text
            if "VULNERABILITY_FOUND" in review_text:
                gemini_vulnerability_found = True
        else:
            print("Gemini AI Security review failed or returned empty result.")
    else:
        print("GEMINI_API_KEY not found in environment. Skipping Gemini AI Security review.")
        
    # Combine results
    has_violations = bool(violations) or gemini_vulnerability_found
    
    # Compile the final report body
    report_body = ""
    if violations:
        report_body += "## ⚠️ TrueVoice Static Security Scan: Violations Detected\n\n"
        report_body += "| File | Line | Rule | Description |\n"
        report_body += "| --- | --- | --- | --- |\n"
        for v in violations:
            escaped_line = v["line"].replace("|", "\\|")
            report_body += f"| `{v['file']}` | `{escaped_line}` | **{v['rule']}** | {v['desc']} |\n"
        report_body += "\n"
        
    if gemini_report:
        report_body += "## 🤖 TrueVoice Gemini AI Security Report\n\n"
        report_body += gemini_report
        
    if not has_violations:
        report_body = "## ✅ TrueVoice Security Scan: Passed\n\nNo security vulnerabilities or compliance issues were detected in this revision."
        
    # Write report to review.md
    try:
        with open("review.md", "w") as f:
            f.write(report_body)
        print("Security audit report written to review.md")
    except Exception as e:
        print(f"Failed to write review.md: {e}")
        
    # Post PR comment if running in GitHub Actions PR context
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    
    pr_number = None
    if event_path:
        try:
            with open(event_path, "r") as f:
                event_data = json.load(f)
            pr_number = event_data.get("pull_request", {}).get("number")
        except Exception as e:
            print(f"Could not parse GITHUB_EVENT_PATH: {e}")
            
    if repo_name and pr_number and token:
        print(f"Posting security review comment to PR #{pr_number} on {repo_name}...")
        post_pr_comment_text(repo_name, pr_number, token, report_body)
    else:
        print("Not in GHA PR environment, skipping PR comment posting.")
        
    if has_violations:
        print("🚨 Security scan failed! Violations or vulnerabilities detected.")
        sys.exit(1)
    else:
        print("✅ Security scan passed.")
        sys.exit(0)

if __name__ == "__main__":
    main()
