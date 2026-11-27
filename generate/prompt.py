## Modeling step: sees the PRD only. Domain model (classes, attributes, associations) as JSON.
MODELING_PROMPT = """Read the Product Requirements Document (PRD) below and build a domain model of it. Include:
1. Classes: name, and attributes with types.
2. Associations between classes: name, the two classes, and the multiplicity at each end.

Answer with a single JSON object in the following format, and nothing else:
{
  "classes": [
    {"name": "ClassName", "attributes": [{"name": "attributeName", "type": "type"}]}
  ],
  "associations": [
    {"name": "associationName", "source": "ClassName", "target": "ClassName",
     "source_multiplicity": "1", "target_multiplicity": "0..*"}
  ]
}

<PRD>
%s
</PRD>
"""

## Code generation step: PRD (+ domain model) + interface. 2nd %s: "" (direct) or MODELING_SECTION (modeling)
CODEGEN_PROMPT = """Write the source code files of the Python program described in the Product Requirements Document (PRD) below.

Requirements:
- Python 3.10, standard library only.
- Put every file under src/.
- Implement every functional requirement in the PRD.
- Do not write test files.
- Follow the Interface section exactly for module paths, class and function names, signatures, and return values.
- Do not ask questions. Complete the whole program in this response.

Output each file in the following format, one block per file:
<file path="src/path/to/file.py">
file content
</file>

<PRD>
%s
</PRD>
%s
<Interface>
%s
</Interface>
"""

MODELING_SECTION = """
The following domain model was derived from the PRD. Use it as a reference for the structure of the project.
<DomainModel>
%s
</DomainModel>
"""

STATE_CODE_RULES = """Implement the Python 3.10 program specified by the PRD and Interface below using only the standard library.
No tools are available: do not emit tool/function calls or request file browsing or shell execution. All inputs are provided below.
Return source code in your final answer using the file blocks below; reasoning or a tool call is not an implementation.
Follow module paths, class/function names, signatures, and return values exactly. Implement all functional requirements.
The supplied tests, requirements, domain model and provided data are immutable. Do not write or weaken tests.
The CurrentCode section is the complete CURRENT generated source, not a suggestion or an old conversation.
RepairHistory records prior attempts in this trial. Use their changed files, scores and repeated revisions to avoid resubmitting unchanged failing code.
repeat_of_round identifies an earlier identical applied source; validation_round identifies the evaluation behind the score. Rejected or unchanged responses may retain an earlier score without a new test run. Null scores mean unmeasured.
Use the observed validation failures to diagnose the cause and repair the implementation. Do not claim success without executable code.
On the initial request, produce the complete program. On a repair request, return only changed/new files, with their COMPLETE contents.
Use <file path="src/path/to/file.py">file content</file> for each file.
To remove an existing generated file, use <delete path="src/path/to/file.py"/>. Do not delete provided files.
Preserve every file that is not explicitly updated or deleted. Never return a patch/diff as file content.
Do not ask questions; implement the requested changes in this response.
"""
