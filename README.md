# 연구 보고서 AI 피드백 시스템

고등학교 학생들의 연구 보고서 작성을 돕는 AI 피드백 시스템입니다. 구글 문서에 자동으로 댓글 형태의 피드백을 제공합니다.

## 🚀 배포 방법

### 1. GitHub 저장소 생성
1. GitHub에서 새 저장소 생성
2. 다음 파일들을 업로드:
   - `main.py` (메인 Streamlit 앱)
   - `google_docs_integration.py` (Google API 연동)
   - `requirements.txt` (패키지 종속성)

### 2. Google Cloud 설정
1. [Google Cloud Console](https://console.cloud.google.com/)에서 새 프로젝트 생성
2. Google Docs API와 Google Drive API 활성화
3. 서비스 계정 생성 및 JSON 키 다운로드

### 3. Anthropic API 키 준비
1. [Anthropic Console](https://console.anthropic.com/)에서 API 키 생성

### 4. Streamlit Cloud 배포
1. [Streamlit Cloud](https://streamlit.io/cloud)에 가입
2. GitHub 저장소 연결
3. 배포 설정에서 다음 환경변수 추가:

#### Secrets 설정 (Settings > Secrets)
```toml
# Anthropic API 키
ANTHROPIC_API_KEY = "your-anthropic-api-key-here"

# Google Service Account 정보
[google_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nyour-private-key-here\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account-email@your-project-id.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account-email%40your-project-id.iam.gserviceaccount.com"
```

## 📝 사용 방법

### 학생용 가이드
1. **구글 문서 공유 설정**
   - 연구 보고서 구글 문서를 생성
   - 공유 버튼 클릭 → "링크가 있는 모든 사용자" → "댓글 작성자" 권한 설정
   - 문서 링크 복사

2. **AI 피드백 받기**
   - Streamlit 앱에 접속
   - 구글 문서 링크 입력
   - "피드백 분석 시작" 버튼 클릭
   - 분석 완료 후 구글 문서에서 댓글 확인

### 교사용 관리
- 학생들에게 앱 링크와 사용 방법 안내
- 필요시 피드백 내용 검토 및 추가 지도

## 🔧 기술 스택

- **Frontend**: Streamlit
- **AI Engine**: Anthropic Claude
- **Integration**: Google Docs API, Google Drive API
- **Deployment**: Streamlit Cloud + GitHub

## 📋 피드백 기준

AI는 다음 기준으로 피드백을 제공합니다:

1. **구조와 논리성**: 서론-본론-결론의 논리적 흐름
2. **내용의 충실성**: 주제 탐구의 깊이와 자료의 신뢰성
3. **학술적 글쓰기**: 객관적 서술과 적절한 인용
4. **창의성과 독창성**: 새로운 관점과 비판적 사고
5. **형식과 표현**: 맞춤법, 문법, 일관된 형식

## 🔒 보안 및 개인정보

- 학생 문서는 임시적으로만 접근하며 저장되지 않습니다
- API 키는 Streamlit Cloud의 보안 환경에서 관리됩니다
- 모든 통신은 HTTPS로 암호화됩니다

## 📞 지원

- 기술적 문제: GitHub Issues 활용
- 교육적 문의: 담당 교사 (공지훈) 연락

## 📄 라이선스

이 프로젝트는 교육 목적으로 개발되었으며, MIT 라이선스 하에 배포됩니다.

## 🛠️ 추가 개발 계획

### 단기 계획
- [ ] 더 정교한 피드백 알고리즘 개발
- [ ] 학생별 피드백 히스토리 관리
- [ ] 다양한 문서 형식 지원 (PDF, Word 등)

### 중기 계획
- [ ] 교사용 대시보드 개발
- [ ] 학급별 통계 및 분석 기능
- [ ] 피드백 품질 개선을 위한 기계학습 적용

### 장기 계획
- [ ] 다국어 지원
- [ ] 타 학교 확산을 위한 표준화
- [ ] 학습 분석학 기반 개인화 교육

## 🔍 문제 해결

### 자주 발생하는 문제

**Q: "문서에 접근할 수 없습니다" 오류**
A: 구글 문서의 공유 설정을 확인해주세요. "링크가 있는 모든 사용자 - 댓글 작성자" 권한이 필요합니다.

**Q: "AI 분석이 너무 오래 걸립니다"**
A: 문서 길이가 길거나 네트워크 상태에 따라 시간이 소요될 수 있습니다. 잠시 기다려주세요.

**Q: "피드백이 문서에 나타나지 않습니다"**
A: 브라우저를 새로고침하거나 구글 문서를 다시 열어보세요.

### 기술적 지원
- GitHub Issues: 버그 리포트 및 기능 요청
- 이메일: 기술적 문의사항
- 교사 네트워크: 교육적 활용 방안 공유

## 📊 성과 측정

### 교육적 효과 지표
- 학생 글쓰기 능력 향상도
- 연구 보고서 완성도 증가
- 학생 만족도 및 참여도
- 교사 업무 효율성 개선

### 기술적 성능 지표
- 시스템 응답 시간
- 피드백 정확도
- 사용자 접속률
- 오류 발생률

---

**개발자**: 완도고등학교 공지훈 교사  
**연락처**: [이메일 주소]  
**GitHub**: [저장소 링크]  
**배포 URL**: [Streamlit 앱 링크]

*이 시스템은 학생들의 학습을 돕고 교사의 업무를 지원하기 위해 개발되었습니다.*
