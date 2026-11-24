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
