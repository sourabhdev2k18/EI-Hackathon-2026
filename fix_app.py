"""
fix_app.py - Run this once: python fix_app.py
Patches app.py to guard against None fault_type causing AttributeError.
"""
with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

old_line = "{'\U0001f916 AI Anomaly: ' + anomaly.fault_type.upper() if anomaly.is_anomaly else '\u2705 All parameters normal'}"
new_line = "{('\U0001f916 AI Anomaly: ' + anomaly.fault_type.upper()) if (anomaly.is_anomaly and anomaly.fault_type) else '\u2705 All parameters normal'}"

if old_line in content:
    content = content.replace(old_line, new_line)
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: app.py has been patched.")
else:
    print("WARNING: Could not find the exact old line to replace.")
    print("Searching for a looser match...")
    import re
    pattern = re.compile(
        r"\{'[^']*AI Anomaly: '\s*\+\s*anomaly\.fault_type\.upper\(\)\s*if\s*anomaly\.is_anomaly\s*else\s*'[^']*All parameters normal'\}"
    )
    matches = pattern.findall(content)
    if matches:
        new_content = pattern.sub(
            "{('\U0001f916 AI Anomaly: ' + anomaly.fault_type.upper()) if (anomaly.is_anomaly and anomaly.fault_type) else '\u2705 All parameters normal'}",
            content
        )
        with open("app.py", "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"SUCCESS: Patched {len(matches)} occurrence(s) using pattern match.")
    else:
        print("ERROR: No match found at all. The file content may differ from expected.")
        print("Please paste the exact contents of line 277 back to Claude.")
