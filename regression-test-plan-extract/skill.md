# Skill: Extract Regression Test Plan from Sheets

## Purpose
This skill extracts structured test cases directly from a provided Test Plan Spreadsheet (like Excel or Google Sheets), respecting the defined Severities, Types, and Automation levels.

---

## PROMPT

Act as an expert QA Automation Lead.

You are provided with a complete Regression Test Plan exported from a spreadsheet. The first part contains the "Summary" or instructions, followed by several sheets with test case data.

Goal:
Extract EVERY test case into a structured JSON list, respecting the types, severities, and automation rules defined in the spreadsheet summary.

Instructions:
1. Parse the text representation of the spreadsheet carefully.
2. Read the Summary instructions to understand what the severities (Priority) and Automation types mean for this project.
3. For each row in the test case sheets, extract the test case into the following JSON schema:
    - `name` (string): The title/name of the test case (Test Case column).
    - `test_category` (string): The category or feature area of the test case.
    - `priority` (string): The exact severity/priority as defined in the sheet (e.g., P1, P2, Critical, High).
    - `type` (string): The type of test (e.g., Smoke, Regression, Integration).
    - `automation_status` (string): The automation level. Extract EXACTLY as provided (e.g., "Manual", "Playwright", "API"). If a test is "Manual", it will not be executed by the bot. "Playwright" and "API" indicate automated execution.
    - `steps` (array of strings): The individual steps required to execute the test. Split multi-line steps into an array.
    - `expected_result` (string): What should happen if the test passes.
    - `rfc_section` (string): Leave empty or map to category.
4. Filter out any empty rows or header rows.
5. Output ONLY valid JSON containing a list of these objects under the key "test_cases". No markdown fences or explanations outside the JSON block.

Format required:
{"test_cases": [{"name": "...", "test_category": "...", "priority": "...", "type": "...", "automation_status": "...", "steps": ["..."], "expected_result": "..."}]}

Spreadsheet Content:
{content}
