from qus.data import Story
from qus.extract import build_relationship_prompt, extract, parse_final_json
from qus.llm import LLMResponse

STORIES = [Story(1, "As a customer, I want to place an order, so that I get products.")]


class FakeClient:
    def __init__(self, *texts):
        self.texts = list(texts)
        self.prompts = []

    def complete(self, prompt):
        self.prompts.append(prompt)
        return LLMResponse(self.texts.pop(0), "fake", "end_turn", 1, 1, {})


def test_parse_takes_last_object_with_key():
    text = 'Step 1 {"classes": ["Draft"]} ... final:\n```json\n{"classes": ["Customer", "Order"]}\n```'
    assert parse_final_json(text, "classes") == ["Customer", "Order"]


def test_parse_ignores_objects_without_key():
    assert parse_final_json('{"note": 1}', "classes") is None
    assert parse_final_json("no json here", "classes") is None


def test_extract_passes_run_classes_to_relationship_prompt():
    client = FakeClient('reasoning {"classes": ["Customer", "Order"]}',
                        'reasoning {"associations": [["Customer", "Order"], ["bad"]]}')
    record = extract(client, STORIES)
    assert record["classes"] == ["Customer", "Order"]
    assert record["associations"] == [["Customer", "Order"]]
    assert "형식이 잘못된 항목 1개" in record["error"]
    assert client.prompts[1] == build_relationship_prompt(STORIES, ["Customer", "Order"])
    assert client.prompts[1].rstrip().endswith("Classes:\nCustomer\nOrder")


def test_extract_stops_when_classes_unparsable():
    client = FakeClient("no list")
    record = extract(client, STORIES)
    assert record["classes"] is None and "associations" not in record["calls"]
    assert record["error"].startswith("classes:")
