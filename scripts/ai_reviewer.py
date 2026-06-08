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

def main():
    try:
        diff_text = get_diff()
    except subprocess.CalledProcessError as e:
        print(f"Error getting git diff: {e}")
        sys.exit(1)
        
    file_changes = parse_diff(diff_text)
    violations = scan_changes(file_changes)
    
    if violations:
        print(f"🚨 Found {len(violations)} security violations!")
        for v in violations:
            print(f"[{v['rule']}] {v['file']}: {v['line']}")
            
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
            print(f"Posting comments to PR #{pr_number} on {repo_name}...")
            post_pr_comment(repo_name, pr_number, token, violations)
        else:
            print("Not in GHA PR environment, skipping PR comment posting.")
            
        sys.exit(1)
    else:
        print("✅ No security violations found. Review passed.")
        sys.exit(0)

if __name__ == "__main__":
    main()
