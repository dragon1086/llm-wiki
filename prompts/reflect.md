# Meta-Prompt: Reflect (자기개선 루프)

누적된 서비스 분석 결과(findings/)를 되돌아보고 **dimensions/ 개선안을 제안**하는 프롬프트.

## 언제 실행하는가

- 3개 이상 서비스를 분석한 뒤
- 주기적으로 (예: 격주 / 월간)
- 특정 서비스에서 "기존 dimension으로는 안 잡히는" 패턴을 여러 번 발견했을 때

## 실행 방법

### 지금 (수동)

1. Claude Code 세션에서 llm-wiki repo 열기
2. 아래 `### 프롬프트` 본문을 복사해 붙여넣기
3. Claude가 생성한 제안서를 `/tmp/reflect-<date>.md` 로 저장
4. 사람이 리뷰 → 채택할 부분만 `prompts/service-analysis/dimensions/` 에 반영 + 커밋

### 장래 (자동화 예정)

```bash
python scripts/wiki.py reflect
# → findings/ 전체 로드 → 현재 dimensions/ 스냅샷 → call_claude() → /tmp/reflect-<date>.md
```

스크립트 형태는 기존 `scripts/lint.py --deep` 패턴을 따른다:
- `utils.call_claude()` 경유
- 구조화 출력 (`===FILE: ...===` 블록) 파싱
- 사람 승인 전에는 파일에 쓰지 않고 제안만

---

### 프롬프트

```
당신은 llm-wiki의 마이크로서비스 분석 시스템을 관리하는 메타 에이전트다.
목표: 누적된 서비스 분석 결과(findings + summaries)를 검토해
      prompts/service-analysis/dimensions/ 개선안을 제안한다.

## 입력

### 현재 dimensions/ 스냅샷

<각 dimensions/*.md 의 Intent + What to look for 섹션 요약하여 붙여넣기>

### 최근 서비스 분석 (summaries/, 서비스 단위)

<최근 분석된 raw/services/ 또는 summaries/*.md 의 "❓ 의문점" 섹션들만 발췌>

## 분석 지시사항

1. **반복 패턴 탐지**
   - 3개 이상 서비스에서 공통으로 "의문점"에 등장하지만 현재 dimension이 포착하지 못한 주제?
   - 예: "Feature flag 사용", "멀티테넌시 처리", "감사 로그(audit trail)" 등
   - 각 반복 주제마다 → **신규 dimension 제안**

2. **기존 dimension 결함**
   - 특정 dimension이 특정 서비스에서 유독 빈약하게 채워져 있다면 → **checklist 보완 제안**
   - 어떤 forensic prompt가 3+ 서비스에서 답을 얻지 못했다면 → 질문을 더 구체화하거나 삭제 제안

3. **프로파일 후보**
   - 비슷한 성격의 서비스가 N개 이상이면 → 전용 프로파일 제안
   - 예: "analyzed 서비스 중 3개가 메시지 소비 전용 (Controller 없음) → consumer-only 프로파일 제안"

## 출력 형식 (엄수)

===PROPOSAL: new-dimension === 형식으로 신규 dimension draft
===PROPOSAL: edit-dimension | <name>=== 형식으로 기존 dimension 수정안
===PROPOSAL: new-profile | <name>=== 형식으로 프로파일 draft
===SUMMARY=== 로 전체 요약

각 PROPOSAL 블록에는:
- **근거**: 어떤 서비스의 어떤 의문점이 계기였는지 인용
- **제안 내용**: full markdown (신규면 전체, 수정이면 diff 형식)
- **예상 효과**: 다음 분석부터 무엇이 더 잘 드러날지

## 최상위 원칙

- **과잉 제안 금지**. 3+ 서비스에서 근거가 쌓인 것만 제안.
- 관찰되지 않은 이론적 개선은 제외.
- 기존 dimension과 중복되면 중복이라고 명시하고 병합 제안.
- 모든 제안은 **"이 서비스들을 분석하면서 드러난 것"** 으로 근거 필수.

지금 제안서를 생성하라.
```

## 출력 해석 가이드 (사람용)

각 PROPOSAL을 다음 3단계로 판단:

1. **근거 충분성**: 인용된 서비스 사례가 실제로 공통 패턴인가?
2. **dimension 적합성**: 별도 dimension으로 분리할 가치가 있는가, 기존 dimension의 checklist 추가로 충분한가?
3. **유지보수 비용**: 새 dimension이 모든 서비스 분석에 자동 적용되면 노이즈가 되지 않는가? (프로파일로 한정하는 게 나을 수도)

채택 결정 후:

- 신규 dimension → `prompts/service-analysis/dimensions/<name>.md` 생성 + `profiles/default.md` 순서 추가
- 수정안 → 해당 dimension 파일 직접 편집
- 프로파일 → `profiles/<name>.md` 생성 + SKILL.md 에 언급

커밋 메시지 예시: `feat(service-analysis): add audit-trail dimension (from reflect-2026-05-01)`

## 실제 운영 리듬 제안

```
월 1회:
  1. python scripts/wiki.py reflect  (구현 후)
  2. 제안서 리뷰
  3. 채택분 커밋
  4. 다음 달 분석부터 새 dimension 자동 반영
```
