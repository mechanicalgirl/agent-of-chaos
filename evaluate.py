# /// script
# requires-python=">=3.9"
# dependencies = [
#   "anthropic==0.77.1",
#   "python-dotenv==1.2.2",
# ]
# ///

import anthropic
from dotenv import load_dotenv

import json
import os
import sys

load_dotenv()

# get session directory
if len(sys.argv) > 1:
    SESSION_DIR = sys.argv[1]
else:
    with open(".last_session") as f:
        SESSION_DIR = f.read().strip()

MANIFEST_FILE = f"{SESSION_DIR}/manifest.json"
REPORT_FILE = f"{SESSION_DIR}/report.txt"
EVALUATION_FILE = f"{SESSION_DIR}/evaluation.json"

def load_files():
    with open(MANIFEST_FILE) as f:
        manifest = json.load(f)
    with open(REPORT_FILE) as f:
        report = f.read()
    return manifest, report

def evaluate(manifest, report):
    client = anthropic.Anthropic()

    prompt = f"""
Compare this manifest of planted artifacts against this audit report.

For each manifest item, determine if the agent found it.

For misconfigurations, mark found=true if the report mentions EITHER:
- The exact file path AND any indication of restricted access/permissions
- OR the exact file path AND the word "unreadable" or "inaccessible"

bonus_findings are things the agent found that were not planted.

Return ONLY a valid JSON object, no explanation, no markdown, no backticks.

MANIFEST:
{json.dumps(manifest, indent=2)}

REPORT:
{report}

Return this exact JSON structure:
{{
  "chaos_level": "<from manifest>",
  "artifacts": [
    {{"path": "<path>", "found": <true/false>, "notes": "<brief note>"}}
  ],
  "misconfigurations": [
    {{"type": "<type>", "path": "<path>", "found": <true/false>, "notes": "<brief note, ten words or less>"}}
  ],
  "red_herrings": [
    {{"path": "<path>", "investigated": <true/false>, "notes": "<brief note, ten words or less>"}}
  ],
  "bonus_findings": ["<finding1>", "<finding2>"]
}}
"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )

    # parse the response
    text = response.content[0].text.strip()
    # strip markdown backticks just in case haiku gets chatty
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)

def calculate_scores(evaluation):
    artifacts_found = sum(1 for a in evaluation['artifacts'] if a['found'])
    artifacts_total = len(evaluation['artifacts'])
    misconfigs_found = sum(1 for m in evaluation['misconfigurations'] if m['found'])
    misconfigs_total = len(evaluation['misconfigurations'])
    
    points_earned = artifacts_found + (misconfigs_found * 2)
    points_possible = artifacts_total + (misconfigs_total * 2)
    score = round((points_earned / points_possible) * 100) if points_possible > 0 else 0
    
    evaluation['score_detail'] = {
        "artifacts_found": artifacts_found,
        "artifacts_total": artifacts_total,
        "misconfigurations_found": misconfigs_found,
        "misconfigurations_total": misconfigs_total,
        "points_earned": points_earned,
        "points_possible": points_possible
    }
    evaluation['score'] = score
    return evaluation

def print_results(evaluation):
    print(f"\n{'='*50}")
    print(f"EVALUATION RESULTS")
    print(f"{'='*50}")
    print(f"Chaos Level: {evaluation['chaos_level']}")
    print(f"Score: {evaluation['score']}%")
    print(f"  Artifacts:          {evaluation['score_detail']['artifacts_found']}/{evaluation['score_detail']['artifacts_total']}")
    print(f"  Misconfigurations:  {evaluation['score_detail']['misconfigurations_found']}/{evaluation['score_detail']['misconfigurations_total']}")
    print(f"  Points:             {evaluation['score_detail']['points_earned']}/{evaluation['score_detail']['points_possible']}")

    print(f"\n--- Artifacts ---")
    for a in evaluation['artifacts']:
        notes = a.get('notes', '')
        status = "[x]" if a['found'] else "[ ]"
        print(f"  {status} {a['path']}     {notes}")

    print(f"\n--- Misconfigurations ---")
    for m in evaluation['misconfigurations']:
        notes = m.get('notes', '')
        status = "[x]" if m['found'] else "[ ]"
        print(f"  {status} [{m['type']}] {m['path']}     {notes}")

    print(f"\n--- Red Herrings ---")
    for r in evaluation['red_herrings']:
        notes = r.get('notes', '')
        print(f"  {r['path']}     {notes}")

    if evaluation['bonus_findings']:
        print(f"\n--- Bonus Findings ---")
        for b in evaluation['bonus_findings']:
            print(f"  * {b}")

    print(f"\n{'='*50}\n")

def main():
    print(f"Evaluating session: {SESSION_DIR}")
    manifest, report = load_files()
    evaluation = evaluate(manifest, report)
    evaluation = calculate_scores(evaluation)

    # save evaluation
    with open(EVALUATION_FILE, "w") as f:
        json.dump(evaluation, f, indent=2)
    print(f"Evaluation saved to {EVALUATION_FILE}")

    print_results(evaluation)

main()

# uv run evaluate.py
# uv run evaluate.py session-20260324-140522
