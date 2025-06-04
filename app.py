import streamlit as st
import anthropic
import re
import time
import os
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import json

# 기존 코드에 추가할 Google Docs 연동 클래스
class SimpleGoogleDocsCommenter:
    def __init__(self):
        """간단한 Google Docs 댓글 추가 클래스"""
        self.credentials = self._get_credentials()
        if self.credentials:
            self.docs_service = build('docs', 'v1', credentials=self.credentials)
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
        else:
            self.docs_service = None
            self.drive_service = None
    
    def _get_credentials(self):
        """서비스 계정 인증 정보 가져오기"""
        try:
            service_account_info = st.secrets["google_service_account"]
            scopes = [
                'https://www.googleapis.com/auth/documents.readonly',
                'https://www.googleapis.com/auth/drive.file',
                'https://www.googleapis.com/auth/drive.comments'
            ]
            return Credentials.from_service_account_info(
                service_account_info, scopes=scopes
            )
        except Exception as e:
            st.warning(f"Google 인증 설정이 없습니다: {str(e)}")
            return None
    
    def is_available(self):
        """Google API 사용 가능 여부 확인"""
        return self.credentials is not None and self.docs_service is not None
    
    def get_document_content(self, doc_id):
        """문서 내용 읽기"""
        if not self.is_available():
            return None
            
        try:
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            
            content = ""
            for element in document.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    paragraph = element['paragraph']
                    for text_run in paragraph.get('elements', []):
                        if 'textRun' in text_run:
                            content += text_run['textRun']['content']
            
            return {
                'title': document.get('title', '제목 없음'),
                'content': content.strip(),
                'doc_id': doc_id
            }
        except Exception as e:
            st.error(f"문서 읽기 실패: {str(e)}")
            st.info("💡 문서 공유 설정을 확인해주세요. '링크가 있는 모든 사용자 - 댓글 작성자' 권한이 필요합니다.")
            return None
    
    def add_comment(self, doc_id, comment_text):
        """문서에 댓글 추가 (Drive API 사용)"""
        if not self.is_available():
            return False
            
        try:
            # Drive API를 사용해서 댓글 추가
            comment_body = {
                'content': comment_text
            }
            
            result = self.drive_service.comments().create(
                fileId=doc_id,
                body=comment_body
            ).execute()
            
            return True
            
        except Exception as e:
            st.error(f"댓글 추가 실패: {str(e)}")
            return False
    
    def add_structured_feedback(self, doc_id, feedback_sections):
        """구조화된 피드백을 여러 댓글로 추가"""
        if not self.is_available():
            return False
            
        success_count = 0
        total_sections = len([f for f in feedback_sections.values() if f.strip()])
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, (section_name, feedback_content) in enumerate(feedback_sections.items()):
            if feedback_content.strip():
                status_text.text(f"댓글 추가 중: {section_name}")
                
                # 댓글 내용 포맷팅
                comment_text = f"""🤖 AI 피드백 - {section_name}

{feedback_content}

---
📌 이 피드백은 AI에 의해 생성되었습니다.
💡 참고용으로 활용하시고, 궁금한 점은 교사에게 문의하세요."""
                
                if self.add_comment(doc_id, comment_text):
                    success_count += 1
                
                # 진행 상황 업데이트
                progress_bar.progress((i + 1) / total_sections)
                time.sleep(2)  # API 호출 간격 조절 (중요!)
        
        status_text.empty()
        progress_bar.empty()
        
        return success_count > 0

# 기존 main.py에 추가할 함수들
def process_document_with_real_comments(doc_url):
    """실제 구글 문서에 댓글을 추가하는 프로세스"""
    
    # 1. 문서 ID 추출
    doc_id = extract_doc_id(doc_url)
    if not doc_id:
        st.error("❌ 유효하지 않은 문서 링크입니다.")
        return False
    
    # 2. Google Docs 연동 초기화
    commenter = SimpleGoogleDocsCommenter()
    
    if not commenter.is_available():
        st.warning("⚠️ Google API 설정이 없어 데모 모드로 실행됩니다.")
        return process_document_demo_mode(doc_url)
    
    # 3. 문서 내용 읽기
    with st.spinner("📖 구글 문서 내용을 읽는 중..."):
        doc_data = commenter.get_document_content(doc_id)
    
    if not doc_data:
        st.error("❌ 문서를 읽을 수 없습니다.")
        st.info("""
        **다음 사항을 확인해주세요:**
        1. 문서 공유 설정: "링크가 있는 모든 사용자 - 댓글 작성자"
        2. 문서가 삭제되지 않았는지 확인
        3. 올바른 구글 문서 링크인지 확인
        """)
        return False
    
    st.success(f"✅ 문서 읽기 성공: {doc_data['title']}")
    
    # 4. AI 분석
    with st.spinner("🤖 AI가 문서를 분석하고 있습니다..."):
        feedback = analyze_document_content(doc_data['content'])
    
    if not feedback:
        st.error("❌ AI 분석에 실패했습니다.")
        return False
    
    # 5. 피드백을 섹션별로 나누기
    feedback_sections = parse_feedback_sections(feedback)
    
    # 6. 구글 문서에 댓글로 추가
    st.markdown("### 📝 구글 문서에 댓글 추가 중...")
    success = commenter.add_structured_feedback(doc_id, feedback_sections)
    
    if success:
        st.success("✅ 피드백이 구글 문서에 댓글로 추가되었습니다!")
        st.balloons()
        
        # 바로가기 링크
        st.markdown(f"""
        ### 🔗 다음 단계
        [📝 구글 문서에서 댓글 확인하기]({doc_url})
        
        **💡 팁:**
        - 각 댓글을 클릭하면 답변을 달 수 있습니다
        - 피드백을 참고하여 문서를 수정해보세요
        - 궁금한 점은 교사에게 문의하세요
        """)
        return True
    else:
        st.error("❌ 댓글 추가에 실패했습니다.")
        return False

def process_document_demo_mode(doc_url):
    """Google API 설정이 없을 때의 데모 모드"""
    st.info("📋 Google API 설정이 없어 데모 모드로 실행됩니다.")
    
    # 샘플 문서 분석
    sample_content = """
    제목: K-Pop 가사에 나타난 청년 세대의 가치관 변화 연구
    
    서론: 현대 사회에서 K-Pop은 전 세계적인 문화 현상이다...
    본론: 주요 아티스트별 가사 분석을 통해...
    결론: K-Pop은 청년 세대의 가치관 형성에 영향을 미친다...
    """
    
    with st.spinner("🤖 AI 분석 중..."):
        feedback = analyze_document_content(sample_content)
        time.sleep(3)  # 분석 시간 시뮬레이션
    
    if feedback:
        st.success("✅ 분석 완료! (데모 모드)")
        
        # 댓글 형태로 포맷팅해서 보여주기
        formatted_feedback = format_as_comments(feedback)
        
        st.markdown("### 💬 생성될 댓글 미리보기")
        for i, comment in enumerate(formatted_feedback, 1):
            with st.expander(f"댓글 {i}: {comment['title']}"):
                st.markdown(comment['content'])
        
        st.info(f"""
        **📌 실제 운영 시:**
        - 위의 댓글들이 구글 문서에 자동으로 추가됩니다
        - [문서 링크]({doc_url})에서 확인할 수 있습니다
        """)
        return True
    
    return False

def parse_feedback_sections(feedback_text):
    """AI 피드백을 섹션별로 파싱"""
    sections = {
        "전체 평가": "",
        "구조와 논리성": "",
        "내용의 충실성": "",
        "학술적 글쓰기": "",
        "창의성과 독창성": "",
        "형식과 표현": "",
        "추가 제안사항": ""
    }
    
    # 키워드 기반으로 섹션 분류
    lines = feedback_text.split('\n')
    current_section = "전체 평가"
    
    for line in lines:
        line = line.strip()
        if line:
            # 섹션 감지 (더 정교한 로직으로 개선 가능)
            if any(keyword in line.lower() for keyword in ["구조", "논리", "체계"]):
                current_section = "구조와 논리성"
            elif any(keyword in line.lower() for keyword in ["내용", "충실", "깊이", "자료"]):
                current_section = "내용의 충실성"
            elif any(keyword in line.lower() for keyword in ["학술", "인용", "출처", "객관"]):
                current_section = "학술적 글쓰기"
            elif any(keyword in line.lower() for keyword in ["창의", "독창", "새로운", "관점"]):
                current_section = "창의성과 독창성"
            elif any(keyword in line.lower() for keyword in ["형식", "표현", "문법", "맞춤법"]):
                current_section = "형식과 표현"
            elif any(keyword in line.lower() for keyword in ["제안", "추가", "향후", "발전"]):
                current_section = "추가 제안사항"
            
            sections[current_section] += line + "\n"
    
    # 빈 섹션 제거
    return {k: v.strip() for k, v in sections.items() if v.strip()}

def format_as_comments(feedback_text):
    """피드백을 댓글 형태로 포맷팅"""
    sections = parse_feedback_sections(feedback_text)
    comments = []
    
    for section_name, content in sections.items():
        if content:
            comment = {
                'title': f"AI 피드백 - {section_name}",
                'content': f"""🤖 **{section_name}**

{content}

---
📌 이 피드백은 AI에 의해 생성되었습니다.
💡 참고용으로 활용하시고, 궁금한 점은 교사에게 문의하세요."""
            }
            comments.append(comment)
    
    return comments

# main.py의 분석 버튼 처리 부분을 다음과 같이 수정
def updated_main_analysis_section():
    """메인 앱의 분석 섹션 (업데이트된 버전)"""
    
    # 분석 버튼
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_button = st.button("🚀 피드백 분석 시작", type="primary", disabled=not st.session_state.current_doc_id)
    
    # 분석 실행
    if analyze_button and st.session_state.current_doc_id:
        st.markdown("---")
        
        # 실제 Google API를 사용하여 댓글 추가 시도
        success = process_document_with_real_comments(st.session_state.get('current_doc_url', ''))
        
        if success:
            st.session_state.analysis_complete = True
        
    elif analyze_button and not st.session_state.current_doc_id:
        st.error("❌ 유효한 구글 문서 링크를 먼저 입력해주세요.")

# 환경 변수 체크 함수
def check_environment():
    """환경 설정 상태 확인"""
    st.sidebar.markdown("### 🔧 시스템 상태")
    
    # Anthropic API 체크
    anthropic_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        st.sidebar.success("✅ Anthropic API 연결됨")
    else:
        st.sidebar.error("❌ Anthropic API 키 없음")
    
    # Google API 체크
    try:
        google_config = st.secrets.get("google_service_account")
        if google_config:
            st.sidebar.success("✅ Google API 연결됨")
            st.sidebar.info("📝 실제 댓글 추가 가능")
        else:
            st.sidebar.warning("⚠️ Google API 설정 없음")
            st.sidebar.info("📋 데모 모드로 실행")
    except:
        st.sidebar.warning("⚠️ Google API 설정 없음")
        st.sidebar.info("📋 데모 모드로 실행")
