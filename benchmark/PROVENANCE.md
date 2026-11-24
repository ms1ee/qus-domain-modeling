# Benchmark provenance

출처: [PRDBench](https://github.com/AGI-Eval-Official/PRDBench) (MIT), commit `050bbcbd1332d94f031d67ca4427af0e48c58c91`

- `<id>/vanilla_PRD.md` = `PRDBench/<id>/src/PRD.md` (수정 없음)
- `<id>/evaluation/` = `PRDBench/<id>/evaluation/` (`__pycache__` 제외). 수정 원칙: PRD를 기준으로 테스트를 고친다.
  PRD/계약에 정의된 문자열 비교는 공백 제거 + 대소문자 무시(`norm`)로 비교한다.

## 37 Company Team Building Event Smart Lottery System

| 항목 | 파일 | 원래 테스트 | 수정 | 근거 |
|---|---|---|---|---|
| 2.2.1 | test_comprehensive_lottery_system.py | `"Third Prize-Movie Ticket"`, `"Second Prize-Shopping Card"`, `"First Prize-1 Day Annual Leave"` 정확 일치 | PRD 원문 `"Third Prize - Movie Tickets"`, `"Second Prize - Shopping Cards"`, `"First Prize - 1 Day Annual Leave"`, `norm` 비교 | PRD 2.2 |
| 2.4.4 | test_chenru_group_guarantee.py | 부서명 `"Chengru Group"` | `"Cheng Ru group"`, 결과 비교는 `norm` | PRD 2.4 |
| 2.5.2b | test_comprehensive_lottery_system.py | 헤더 `"Name,Department,Prize Name,Win Time"` | `"Name,Department,Prize Name,Winning Time"`, `norm` 비교 | PRD 2.5 |
| 2.1.4b | test_comprehensive_lottery_system.py | `"Format Error"`, `"Line 1"` 부분 문자열 | `norm` 비교 | 계약 문자열 |
| 2.5.2a | test_comprehensive_lottery_system.py | `"successfully exported"` 부분 문자열 | `norm` 비교 | 계약 문자열 |

| 2.5.2b | test_comprehensive_lottery_system.py | `os.path.abspath`를 patch해 임시 파일로 바꿔치기 (구현이 abspath를 써야만 통과) | 임시 폴더로 chdir 후 `awards_result_YYYYMMDD.txt`를 읽어 검사 | PRD 2.5 |
| 2.5.2b | test_comprehensive_lottery_system.py | `utf-8`로 읽음 (BOM이 있으면 헤더 불일치) | `utf-8-sig`로 읽음 (BOM 유무 모두 허용) | PRD 2.5 (CSV) |

plan 밖 테스트(`test_chenru_group_guarantee_not_triggered`)도 부서명만 같이 바꿨다.

단위 테스트 채점 제외:
- 2.3.2 Pause/Resume, 2.3.3 Terminate: 대화형 제어를 pytest(stdin 차단)로 검사할 수 없다. 실제 테스트도 `hasattr`와 일반 `draw()`만 확인한다. 셸 테스트 단계에서 다룬다.

항상 통과하는 테스트 (채점에 포함, 해석 시 참고):
- 2.1.4c Manual Handling: if/else 양쪽 모두 통과
