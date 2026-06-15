import csv
import hashlib
import io
import json
import os
import re
import uuid
from typing import List, Literal, Dict, Any, Optional
from pydantic import BaseModel, Field
from ..models import Ticket, TestCase
from ..integrations.llm_client import LLMClient
from ..integrations.supabase_client import SupabaseClient
from ..integrations.sheets_client import SheetsClient

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_CORE_DIR = os.path.dirname(__file__)
_REQUIREMENTS_TO_TCS_DIR = os.path.abspath(os.path.join(_CORE_DIR, '..', '..', 'requirements_to_TCs'))
_SKILL_PATH = os.path.join(_REQUIREMENTS_TO_TCS_DIR, 'skill.md')
_MANIFEST_PATH = os.path.join(_REQUIREMENTS_TO_TCS_DIR, '.manifest.json')


def _load_skill_prompt() -> str:
    """Read the prompt template from requirements_to_TCs/skill.md.

    The file must contain a line '## PROMPT' followed by the prompt body
    (which ends at the next '## ' heading or EOF). The {content} placeholder
    is filled in by the caller.
    """
    if not os.path.exists(_SKILL_PATH):
        raise FileNotFoundError(
            f"skill.md not found at {_SKILL_PATH}. "
            "Run from the project root or restore requirements_to_TCs/skill.md."
        )
    text = open(_SKILL_PATH, encoding='utf-8').read()
    # Extract everything after '## PROMPT'
    match = re.search(r'^##\s+PROMPT\s*\n(.*)', text, re.DOTALL | re.MULTILINE)
    if not match:
        raise ValueError("skill.md must contain a '## PROMPT' section.")
    return match.group(1).strip()


# ---------------------------------------------------------------------------
# Manifest helpers (deduplication)
# ---------------------------------------------------------------------------

def _load_manifest() -> dict:
    try:
        with open(_MANIFEST_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_manifest(manifest: dict):
    with open(_MANIFEST_PATH, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)


def _file_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------------------
# Structured output schemas — ticket flow
# ---------------------------------------------------------------------------

class _GeneratedTestCase(BaseModel):
    name: str = Field(description="Descriptive name of the test")
    type: Literal["frontend", "backend"]
    priority: Literal["critical", "high", "medium", "low"] = "medium"
    steps: List[str] = Field(default_factory=list)
    assertions: List[str] = Field(default_factory=list)
    test_data: Dict[str, Any] = Field(default_factory=dict)


class _GeneratedTestSuite(BaseModel):
    test_cases: List[_GeneratedTestCase] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Structured output schemas — requirements flow
# ---------------------------------------------------------------------------

class _RequirementsTestCase(BaseModel):
    title: str = Field(description="Starts with 'Verify that'")
    rfc_section: str = Field(description="RFC/requirements section this maps to")
    test_type: Literal["UI", "API", "Backend", "Integration", "Security"] = "Backend"
    priority: Literal["Critical", "High", "Medium"] = "Medium"
    preconditions: str = ""
    steps: List[str] = Field(default_factory=list)
    expected_result: str = ""
    test_data: Dict[str, str] = Field(default_factory=dict)


class _RequirementsTestSuite(BaseModel):
    test_cases: List[_RequirementsTestCase] = Field(default_factory=list)
    coverage_gaps: List[str] = Field(default_factory=list)
    regression_tests: List[str] = Field(default_factory=list)
    automation_candidates: List[str] = Field(default_factory=list)

class _TestPlanTestCase(BaseModel):
    test_id: str = Field(default="", description="The exact Test ID from the sheet, e.g. VIT-001")
    name: str = ""
    test_category: str = ""
    priority: str = "medium"
    type: str = "frontend"
    automation_status: str = ""
    steps: List[str] = Field(default_factory=list)
    expected_result: str = ""
    rfc_section: str = ""

class _TestPlanSuite(BaseModel):
    test_cases: List[_TestPlanTestCase] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Execution-type routing: map requirements test_type → frontend / backend
# ---------------------------------------------------------------------------
_REQ_TYPE_TO_EXEC = {
    "UI": "frontend",
    "API": "backend",
    "Backend": "backend",
    "Integration": "backend",
    "Security": "backend",
}


class TestCaseGenerator:
    def __init__(self):
        self.llm_client = LLMClient()
        self.supabase = SupabaseClient()
        self.sheets = SheetsClient()

    # ------------------------------------------------------------------
    # Ticket-based generation (existing flow, unchanged behaviour)
    # ------------------------------------------------------------------

    def generate_from_ticket(self, ticket: Ticket) -> List[TestCase]:
        print(f"Generating test cases for ticket: {ticket.title}")
        llm = self.llm_client.get_sonnet()
        if not llm:
            print("Claude client not initialized. Cannot generate tests.")
            return []

        prompt = f"""
        You are an expert QA engineer. Given the following ticket description,
        generate a list of test cases to thoroughly verify the requirements.

        Ticket Title: {ticket.title}
        Description: {ticket.description}
        Target App: https://qa-assignment-steel.vercel.app/

        Generate test cases that thoroughly verify the requirements. Treat any
        values inside test_data (dates, IDs, etc.) as plain strings.
        """

        try:
            cases_data = self._invoke_llm(llm, prompt)

            test_cases = []
            for item in cases_data:
                tc = TestCase(
                    id=str(uuid.uuid4()),
                    ticket_id=ticket.id,
                    name=item.get('name', 'Untitled Test'),
                    type=item.get('type', 'frontend'),
                    priority=item.get('priority', 'medium'),
                    steps=item.get('steps', []),
                    assertions=item.get('assertions', []),
                    test_data=item.get('test_data', {}),
                    ai_generated=True
                )
                test_cases.append(tc)

            self._save_to_db(test_cases)
            return test_cases

        except Exception as e:
            print(f"Error generating test cases: {e}")
            return []

    def _invoke_llm(self, llm, prompt: str) -> List[dict]:
        try:
            structured = llm.with_structured_output(_GeneratedTestSuite)
            suite = structured.invoke(prompt)
            return [tc.model_dump() for tc in suite.test_cases]
        except Exception as e:
            print(f"Structured output failed ({e}); falling back to text parsing.")
            response = llm.invoke(prompt)
            return self._parse_json_response(response.content)

    def _parse_json_response(self, content: str) -> List[dict]:
        content = content.strip()
        fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", content, re.DOTALL)
        if fence:
            content = fence.group(1).strip()
        start, end = content.find('['), content.rfind(']')
        if start != -1 and end != -1 and end > start:
            content = content[start:end + 1]
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            ctx = content[max(0, e.pos - 80):e.pos + 80]
            print(f"JSON parse error at char {e.pos}: ...{ctx}...")
            raise

    # ------------------------------------------------------------------
    # Requirements / PRD-based generation (new flow)
    # ------------------------------------------------------------------

    def generate_from_requirements(self, content: str, source_id: str) -> tuple[List[TestCase], dict]:
        """Generate a full test suite from a requirements / PRD document.

        Deduplication: if TCs have already been generated for this exact file
        content (same SHA-256 hash), the existing cases are returned from
        Supabase and no new LLM call is made.

        Returns (test_cases, metadata) where metadata holds coverage_gaps,
        regression_tests, and automation_candidates.
        """
        content_hash = _file_hash(content)
        manifest = _load_manifest()
        entry = manifest.get(source_id, {})

        # Deterministic UUID for this requirements file — satisfies the FK on test_cases.ticket_id
        ticket_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, source_id))

        # --- Dedup check ---
        if entry.get('hash') == content_hash:
            existing = self.supabase.get_test_cases_by_ticket_id(ticket_uuid)
            if existing:
                print(
                    f"⏭️  Skipping generation — {len(existing)} TCs already exist for "
                    f"'{source_id}' (hash unchanged). Delete or modify the requirements "
                    "file to force regeneration."
                )
                return existing, {
                    "coverage_gaps": entry.get("coverage_gaps", []),
                    "regression_tests": entry.get("regression_tests", []),
                    "automation_candidates": entry.get("automation_candidates", []),
                }
            # Hash matched but Supabase has no rows → fall through and regenerate
            print(f"ℹ️  Hash matched for '{source_id}' but no TCs found in DB — regenerating.")

        print(f"📋 Generating requirements test suite for: {source_id}")
        llm = self.llm_client.get_sonnet()
        if not llm:
            print("Claude client not initialized. Cannot generate tests.")
            return [], {}

        # Load prompt template from skill.md
        try:
            skill_prompt = _load_skill_prompt()
        except (FileNotFoundError, ValueError) as e:
            print(f"Error loading skill.md: {e}")
            return [], {}

        prompt = skill_prompt.replace('{content}', content)

        try:
            suite = self._invoke_requirements_llm(llm, prompt)
        except Exception as e:
            print(f"Error generating requirements test cases: {e}")
            return [], {}

        # Ensure a ticket row exists for this requirements file (FK requirement)
        from ..models import Ticket as TicketModel
        self.supabase.upsert_ticket(TicketModel(
            id=ticket_uuid,
            title=source_id,
            description=f"Requirements file: {source_id}",
            source='requirements',
            source_id=source_id,
        ))

        test_cases = []
        for item in suite.test_cases:
            exec_type = _REQ_TYPE_TO_EXEC.get(item.test_type, "backend")
            tc = TestCase(
                id=str(uuid.uuid4()),
                ticket_id=ticket_uuid,
                name=item.title,
                type=exec_type,
                priority=item.priority.lower(),
                steps=item.steps,
                assertions=[item.expected_result] if item.expected_result else [],
                test_data=item.test_data,
                ai_generated=True,
                preconditions=item.preconditions or None,
                expected_result=item.expected_result or None,
                rfc_section=item.rfc_section or None,
                test_category=item.test_type,
            )
            test_cases.append(tc)

        self._save_to_db(test_cases)

        metadata = {
            "coverage_gaps": suite.coverage_gaps,
            "regression_tests": suite.regression_tests,
            "automation_candidates": suite.automation_candidates,
        }

        if not test_cases:
            print("⚠️  Generation returned 0 test cases — manifest NOT updated so next run will retry.")
            return [], metadata

        # Update manifest only when TCs were actually generated
        manifest[source_id] = {
            "hash": content_hash,
            "tc_count": len(test_cases),
            "coverage_gaps": suite.coverage_gaps,
            "regression_tests": suite.regression_tests,
            "automation_candidates": suite.automation_candidates,
        }
        _save_manifest(manifest)
        print(f"✅ Generated {len(test_cases)} test cases. Manifest updated for '{source_id}'.")

        return test_cases, metadata

    def _invoke_requirements_llm(self, llm, prompt: str) -> _RequirementsTestSuite:
        """Structured output for requirements suite. Falls back to raw JSON parsing."""
        try:
            structured = llm.with_structured_output(_RequirementsTestSuite)
            suite = structured.invoke(prompt)
            if suite.test_cases:
                return suite
            print("⚠️  Structured output returned 0 test cases — falling back to JSON parsing.")
        except Exception as e:
            print(f"⚠️  Structured output failed ({e}) — falling back to JSON parsing.")

        # Fallback: ask for raw JSON with an explicit, tightly-scoped prompt so the
        # model doesn't add prose or fences that break parsing.
        fallback_prompt = (
            prompt
            + "\n\nRespond with ONLY a valid JSON object matching this exact schema "
            "(no markdown, no explanation):\n"
            '{"test_cases": [{"title": "...", "rfc_section": "...", '
            '"test_type": "UI|API|Backend|Integration|Security", '
            '"priority": "Critical|High|Medium", "preconditions": "...", '
            '"steps": ["..."], "expected_result": "...", "test_data": {"key": "value"}}], '
            '"coverage_gaps": ["..."], "regression_tests": ["..."], "automation_candidates": ["..."]}'
        )
        response = llm.invoke(fallback_prompt)
        raw = response.content.strip()
        print(f"Fallback raw response length: {len(raw)} chars")
        return self._parse_json_to_requirements_suite(raw)

    def _parse_json_to_requirements_suite(self, content: str) -> _RequirementsTestSuite:
        """Parse a raw JSON object response into a _RequirementsTestSuite."""
        # Strip fences if present
        fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", content, re.DOTALL)
        if fence:
            content = fence.group(1).strip()
        try:
            data = json.loads(content)
            return _RequirementsTestSuite(**data)
        except Exception as e:
            print(f"JSON suite parse failed ({e}), attempting CSV fallback.")
            return self._parse_csv_to_requirements_suite(content)

    def _parse_csv_to_requirements_suite(self, content: str) -> _RequirementsTestSuite:
        """Parse a CSV-formatted LLM response into a _RequirementsTestSuite."""
        fence = re.match(r"^```(?:csv)?\s*(.*?)\s*```$", content, re.DOTALL)
        if fence:
            content = fence.group(1).strip()

        test_cases: List[_RequirementsTestCase] = []
        coverage_gaps: List[str] = []
        regression_tests: List[str] = []
        automation_candidates: List[str] = []

        sections = re.split(r'\n(?=Coverage Gaps|Regression Tests|Automation Candidates)', content, flags=re.IGNORECASE)
        csv_block = sections[0]

        for section in sections[1:]:
            lines = [l.strip() for l in section.splitlines() if l.strip()]
            if not lines:
                continue
            header = lines[0].lower()
            items = [re.sub(r'^[\-\d\.]+\s*', '', l) for l in lines[1:]]
            if 'coverage gap' in header:
                coverage_gaps = items
            elif 'regression' in header:
                regression_tests = items
            elif 'automation' in header:
                automation_candidates = items

        reader = csv.DictReader(io.StringIO(csv_block))
        for row in reader:
            try:
                steps_raw = row.get('steps', '')
                steps = [s.strip() for s in re.split(r'\||;|\n', steps_raw) if s.strip()]
                test_cases.append(_RequirementsTestCase(
                    title=row.get('title', row.get('Title', 'Verify that...')),
                    rfc_section=row.get('rfc_section', row.get('RFC Section', '')),
                    test_type=row.get('test_type', row.get('Type', 'Backend')),
                    priority=row.get('priority', row.get('Priority', 'Medium')),
                    preconditions=row.get('preconditions', row.get('Preconditions', '')),
                    steps=steps,
                    expected_result=row.get('expected_result', row.get('Expected Result', '')),
                    test_data={},
                ))
            except Exception:
                continue

        return _RequirementsTestSuite(
            test_cases=test_cases,
            coverage_gaps=coverage_gaps,
            regression_tests=regression_tests,
            automation_candidates=automation_candidates,
        )

    # ------------------------------------------------------------------
    # Test Plan Spreadsheet Extraction
    # ------------------------------------------------------------------

    def generate_from_testplan(self, content: str, source_id: str, re_run: bool = False) -> List[TestCase]:
        print(f"📋 Extracting test cases from test plan sheet: {source_id}")
        
        ticket_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, source_id))
        
        # Check cache unless forced to re-run
        if not re_run:
            existing = self.supabase.get_test_cases_by_ticket_id(ticket_uuid)
            if existing and len(existing) > 0:
                print(f"⚡ Found {len(existing)} cached test cases in Database. Skipping AI extraction.")
                return existing
        else:
            print("🔄 Force re-run requested. Regenerating test cases from spreadsheet...")
            # We don't delete from DB here because upsert_ticket handles it or we just add them.
            # Actually, to avoid duplicates on re_run, we should ideally delete existing ones, 
            # but currently supabase_client doesn't have a direct delete_test_cases method.
            # We'll rely on the existing workflow.

        llm = self.llm_client.get_sonnet()
        if not llm:
            print("Claude client not initialized. Cannot extract tests.")
            return []

        skill_path = os.path.join(_CORE_DIR, '..', '..', 'regression-test-plan-extract', 'skill.md')
        try:
            text = open(skill_path, encoding='utf-8').read()
            match = re.search(r'^##\s+PROMPT\s*\n(.*)', text, re.DOTALL | re.MULTILINE)
            skill_prompt = match.group(1).strip()
        except Exception as e:
            print(f"Error loading regression-test-plan-extract skill: {e}")
            return []

        prompt = skill_prompt.replace('{content}', content)

        from ..models import Ticket as TicketModel
        self.supabase.upsert_ticket(TicketModel(
            id=ticket_uuid,
            title=source_id,
            description=f"Test Plan Spreadsheet: {source_id}",
            source='testplan',
            source_id=source_id,
        ))
        # Split content into sheets to process them one by one (avoids LLM output truncation)
        sheets_data = content.split('\n\n--- SHEET: ')
        summary_text = ""
        test_sheets = []
        
        for s in sheets_data:
            if not s.strip(): continue
            if s.startswith('Summary '):
                summary_text = '--- SHEET: ' + s
            else:
                test_sheets.append('--- SHEET: ' + s)
                
        all_test_cases = []
        
        for sheet_content in test_sheets:
            print(f"🔄 Processing {sheet_content.split('---')[1].strip()}...")
            chunk_content = summary_text + "\n\n" + sheet_content
            
            prompt = skill_prompt.replace('{content}', chunk_content)
            try:
                structured = llm.with_structured_output(_TestPlanSuite)
                suite = structured.invoke(prompt)
                
                for item in suite.test_cases:
                    tc = TestCase(
                        id=str(uuid.uuid4()),
                        ticket_id=ticket_uuid,
                        name=item.name,
                        type=item.type,
                        priority=item.priority,
                        automation_status=item.automation_status,
                        steps=item.steps,
                        assertions=[item.expected_result] if item.expected_result else [],
                        expected_result=item.expected_result or None,
                        rfc_section=item.rfc_section or None,
                        test_category=item.test_category or None,
                        ai_generated=False
                    )
                    all_test_cases.append(tc)
            except Exception as e:
                print(f"Error processing sheet chunk: {e}")

        self._save_to_db(all_test_cases)
        print(f"✅ Extracted {len(all_test_cases)} test cases from {source_id}.")
        return all_test_cases

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------

    def export_to_sheets(self, test_cases: List[TestCase], sheets_id: str):
        if sheets_id:
            print(f"Exporting {len(test_cases)} test cases to Google Sheets...")
            self.sheets.write_test_cases_to_sheet(sheets_id, test_cases)

    def export_requirements_suite_to_sheets(self, test_cases: List[TestCase], metadata: dict, sheets_id: str):
        if sheets_id:
            print(f"Exporting {len(test_cases)} requirements test cases to Google Sheets...")
            self.sheets.write_requirements_test_cases_to_sheet(sheets_id, test_cases, metadata)

    def export_to_csv(self, test_cases: List[TestCase], filepath: str, metadata: dict = None):
        """Write requirements test suite to a local CSV file in TestRail format."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        fieldnames = [
            "ID", "RFC Section", "Title", "Type", "Priority",
            "Preconditions", "Steps", "Expected Result", "Test Data"
        ]
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for i, tc in enumerate(test_cases, 1):
                writer.writerow({
                    "ID": f"TC-{i:04d}",
                    "RFC Section": tc.rfc_section or "",
                    "Title": tc.name,
                    "Type": tc.test_category or tc.type,
                    "Priority": tc.priority.title(),
                    "Preconditions": tc.preconditions or "",
                    "Steps": " | ".join(tc.steps),
                    "Expected Result": tc.expected_result or (tc.assertions[0] if tc.assertions else ""),
                    "Test Data": "; ".join(f"{k}={v}" for k, v in tc.test_data.items()),
                })

            if metadata:
                f.write("\n\nCoverage Gaps / Clarifications Needed\n")
                for gap in metadata.get("coverage_gaps", []):
                    f.write(f"- {gap}\n")
                f.write("\nTop 20 Regression Tests\n")
                for t in metadata.get("regression_tests", []):
                    f.write(f"- {t}\n")
                f.write("\nTop 10 Automation Candidates\n")
                for t in metadata.get("automation_candidates", []):
                    f.write(f"- {t}\n")

        print(f"CSV exported to: {filepath}")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_to_db(self, test_cases: List[TestCase]):
        for tc in test_cases:
            try:
                self.supabase.insert_test_case(tc)
            except Exception as e:
                print(f"Error saving test case {tc.id} to Supabase: {e}")
