from qus import r3llm_diagnose as D


class FakeMatcher:
    classes = {"timetable", "class"}
    synonyms = {"roster": "timetable"}

    def map_term(self, t):
        t = t.lower()
        return self.synonyms.get(t, t)


def _node(order, name, stories, key=None):
    return {"order": order, "name": name, "key": key if key is not None else name.lower(),
            "edges": [{"story": s, "match": "exact"} for s in stories]}


def test_duplicates_follow_scorer_order():
    dups = D.duplicates(["Timetable", "timetable", "Roster", "Class", "Grade"], FakeMatcher())
    assert dups == [{"gold": "timetable", "first": "Timetable", "dup": "Roster"}]  # 표기 반복(timetable)은 중복이 아니다


def test_exclusion_reasons_in_candidate_order():
    nodes = [_node(0, "Timetable", [1, 2]), _node(1, "Roster", [3]), _node(2, "Student", [1, 3]),
             _node(3, "Teacher", [4]), _node(4, "Lonely", []), _node(5, "Admin", [5]), _node(6, "timetable", [6])]
    assert D.exclusion_reason("Timetable", "Roster", nodes, {}) is None  # Student가 공통 이웃
    assert D.exclusion_reason("Timetable", "Student", nodes, {}).startswith("같은 스토리에 함께 나옴 (스토리 1)")
    assert D.exclusion_reason("Teacher", "Roster", nodes, {}) == "공통 이웃 없음"
    assert D.exclusion_reason("Lonely", "Roster", nodes, {}) == "공통 이웃 없음 (완전 일치 스토리 없음: Lonely)"
    assert D.exclusion_reason("Admin", "Roster", nodes, {5: "R1_actor"}) == "Admin: R1_actor에서 먼저 제거"
    assert D.exclusion_reason("timetable", "Roster", nodes, {}) == "timetable: 정규화 키가 같은 앞 이름 'Timetable'이 대표"
    assert D.exclusion_reason("Nope", "Roster", nodes, {}) == "Nope: 출처 그래프 노드 없음"
