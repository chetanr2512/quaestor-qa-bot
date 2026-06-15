# Requirements / PRD

Paste your RFC, PRD, or technical design document here.

The QA agent reads this file and generates a full test suite using the
Senior QA Architect prompt defined in `requirements_to_TCs/skill.md`.

Run:
```
python -m agent --source requirements
```

Add `--csv-out output/suite.csv` to export as a TestRail-format CSV.
Add `--sheets-id <ID>` to write directly to Google Sheets.

---

<!-- Replace everything below this line with your actual requirements -->
# Requirements Document: QA Assignment Todo Application

## 1. Overview
The application is a web-based "Todo List" designed as a target for a QA automation take-home assignment. It allows users to manage their daily tasks with features such as due dates, priorities, and filtering. The application features user authentication to keep tasks private.

## 2. Authentication & User Management
### 2.1 Sign In
- Users must be able to log in using their registered `Email` and `Password`.
- The system must provide a "Sign in" button to submit credentials.
- **Quick Login:** For testing and quick access, the system provides one-click "Quick login" buttons to bypass standard authentication for specific admin profiles:
  - `Login as admin1`
  - `Login as admin2`

### 2.2 Registration
- A link to the `Register` page is available on the login screen for new users to create an account.

## 3. Todo Management Features
### 3.1 Creating a Todo
- **Title:** Users can enter a task title in a text input with the placeholder "What needs doing?".
- **Due Date:** Users can optionally specify a due date for the task using a date picker input.
- **Submission:** Users can submit the new task by clicking the "Add" button.

### 3.2 Viewing Todos
- Todos are displayed in a list format.
- Each todo item displays the following information (if provided):
  - The task title.
  - The associated priority level.
  - The due date.

### 3.3 Modifying Todos
- **Completion Status:** Users can mark a todo as completed or active using a dedicated checkbox next to each task.
- **Priority Levels:** Users can assign and update the priority of a task. The available priority levels are:
  - `low`
  - `medium`
  - `high`

### 3.4 Deleting Todos
- Users can remove a task from their list by clicking the "Delete" button associated with that specific task.

## 4. Filtering and Organization
The application provides filter controls to help users view specific subsets of their tasks:
- **All:** Displays all tasks, regardless of their completion status.
- **Active:** Displays only incomplete tasks.
- **Completed:** Displays only tasks that have been marked as complete.

## 5. Technical Observations
- The application is a Single Page Application (SPA) built with React/Next.js.
- Elements have dedicated `data-testid` attributes (e.g., `data-testid="new-todo-title"`, `data-testid="login-submit"`, `data-testid="filter-active"`), confirming its design for QA automation and end-to-end testing.
