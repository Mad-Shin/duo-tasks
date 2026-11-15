# duo-tasks — Matrix Factory Governed Workspace

## 🏭 Matrix Factory Engine Hooks
- **Factory Column**: `COL-09` (`duo-tasks`)
- **Central Matrix & Memory**: `c:/Users/gvale/.gemini/IA_Brain_Agents/company/state.json`
- **Learning Engine**: `python c:/Users/gvale/.gemini/IA_Brain_Agents/brain_cli.py learn "<keyword>"`
- **Guardrails Validation**: `python c:/Users/gvale/.gemini/IA_Brain_Agents/company/guardrails.py`

## 🐝 Multi-Agent Write Scopes (Shared / Branch Isolation)
- `architect` (`Workspace: "inherit"`): Read-only auditing, ADRs, planning & `/grill`.
- `builder` (`Workspace: "share"`): Source code edits inside mutually exclusive modules.
- `verifier` (`Workspace: "branch"` or `"inherit"`): Automated tests & deterministic QA.
