import streamlit as st
import anthropic
import re
import time
import os
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request

# 페이지 설정
st.set_page_config(
    page_title="연구 보고서 AI 피드백 시스템",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일링 (동일)
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2E86AB;
        font-size: 2.5rem;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #28a745;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        color: #856404;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #ffc107;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #dc3545;
        margin: 1rem 0;
    }
    .stButton > button {
        background-color: #2E86AB;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.75rem 2rem;
        font-weight: bold;
        font-size: 1.1rem;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'current_doc_id' not in st.session_state:
    st.session_state.current_doc_id = None
if 'current_doc_url' not in st.session_state:
    st.session_state.current_doc_url = None

class GoogleDocsCommenter:
    def __init__(self):
        """Google Docs 댓글 추가 클래스"""
        self.credentials = self._get_credentials()
        if self.credentials:
            try:
                self.docs_service = build('docs', 'v1', credentials=self.credentials)
                self.drive_service = build('drive', 'v3', credentials=self.credentials)
                self._test_connection()
            except Exception as e:
                st.error(f"Google API 서비스 초기화 실패: {str(e)}")
                self.docs_service = None
                self.drive_service = None
        else:
            self.docs_service = None
            self.drive_service = None
    
    def _get_credentials(self):
        """서비스 계정 인증 정보 가져오기"""
        try:
            service_account_info = st.secrets["google_service_account"]
            scopes = [
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.file'
            ]
            
            credentials = Credentials.from_service_account_info(
                service_account_info, 
                scopes=scopes
            )
            
            return credentials
            
        except Exception as e:
            st.sidebar.error(f"Google 인증 실패: {str(e)}")
            return None
    
    def _test_connection(self):
        """Google API 연결 테스트"""
        try:
            about = self.drive_service.about().get(fields="user").execute()
            st.sidebar.success("✅ Google API 연결 성공")
            
        except Exception as e:
            st.sidebar.error(f"❌ Google API 연결 실패: {str(e)}")
            # 상세 오류 정보 표시
            if 'No access token' in str(e):
                st.sidebar.error("🔍 Access Token 문제 발견!")
                st.sidebar.info("JSON 키를 다시 생성해주세요.")
            raise e
    
    def is_available(self):
        """Google API 사용 가능 여부 확인"""
        return self.credentials is not None and self.docs_service is not None
    
    def get_document_content(self, doc_id):
        """문서 내용 읽기"""
        if not self.is_available():
            return None
            
        try:
            # 먼저 Drive API로 파일 접근 권한 확인
            file_metadata = self.drive_service.files().get(
                fileId=doc_id, 
                fields="name,permissions"
            ).execute()
            
            st.info(f"📄 문서명: {file_metadata.get('name', '알 수 없음')}")
            
            # Docs API로 문서 내용 읽기
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            
            content = ""
            for element in document.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    paragraph = element['paragraph']
                    for text_run in paragraph.get('elements', []):
                        if 'textRun' in text_run:
                            content += text_run['textRun'].get('content', '')
            
            return {
                'title': document.get('title', '제목 없음'),
                'content': content.strip(),
                'doc_id': doc_id,
                'word_count': len(content.split())
            }
            
        except Exception as e:
            st.error(f"문서 읽기 실패: {str(e)}")
            return None
    
    def add_comment(self, doc_id, comment_text):
        """문서에 댓글 추가 - 수정된 버전"""
        if not self.is_available():
            return False
            
        try:
            # Google Drive API의 댓글 길이 제한 확인 (30,000자)
            MAX_COMMENT_LENGTH = 30000
            
            if len(comment_text) > MAX_COMMENT_LENGTH:
                # 긴 댓글을 여러 개로 분할
                comments_added = 0
                total_chunks = (len(comment_text) + MAX_COMMENT_LENGTH - 1) // MAX_COMMENT_LENGTH
                
                for i in range(0, len(comment_text), MAX_COMMENT_LENGTH):
                    chunk_num = (i // MAX_COMMENT_LENGTH) + 1
                    chunk = comment_text[i:i + MAX_COMMENT_LENGTH]
                    
                    # 첫 번째 부분이 아니면 계속 표시 추가
                    if chunk_num > 1:
                        chunk = f"(부분 {chunk_num}/{total_chunks}) {chunk}"
                    else:
                        chunk = f"(부분 {chunk_num}/{total_chunks}) {chunk}"
                    
                    comment_body = {
                        'content': chunk
                    }
                    
                    result = self.drive_service.comments().create(
                        fileId=doc_id,
                        body=comment_body,
                        fields="*"
                    ).execute()
                    
                    comments_added += 1
                    time.sleep(1)  # API 호출 간격
                
                return comments_added > 0
            else:
                comment_body = {
                    'content': comment_text
                }
                
                result = self.drive_service.comments().create(
                    fileId=doc_id,
                    body=comment_body,
                    fields="*"
                ).execute()
                
                return True
            
        except Exception as e:
            st.error(f"댓글 추가 실패: {str(e)}")
            st.error(f"댓글 길이: {len(comment_text)}자")
            return False

def extract_doc_id(url):
    """구글 문서 URL에서 문서 ID 추출"""
    patterns = [
        r'/document/d/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_anthropic_client():
    """Anthropic 클라이언트 초기화"""
    api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("❌ Anthropic API 키가 설정되지 않았습니다.")
        st.stop()
    return anthropic.Anthropic(api_key=api_key)

def analyze_document_content(content):
    """문서 내용을 분석하여 피드백 생성"""
    client = get_anthropic_client()
    
    system_prompt = """
    당신은 고등학교 국어 교사로서 학생들의 연구 보고서를 검토하는 전문가입니다.
    다음 기준에 따라 구체적이고 건설적인 피드백을 제공해주세요:

    **피드백 기준:**
    1. **구조와 논리성** (25점): 서론-본론-결론의 논리적 흐름, 목차의 체계성
    2. **내용의 충실성** (30점): 주제 탐구의 깊이, 자료의 다양성과 신뢰성
    3. **학술적 글쓰기** (20점): 객관적 서술, 적절한 인용, 출처 표기
    4. **창의성과 독창성** (15점): 새로운 관점, 비판적 사고
    5. **형식과 표현** (10점): 맞춤법, 문법, 일관된 형식

    각 섹션별로 명확히 구분하여 피드백을 작성하고, 섹션 제목은 다음과 같이 시작해주세요:
    - 1. 구조와 논리성:
    - 2. 내용의 충실성:
    - 3. 학술적 글쓰기:
    - 4. 창의성과 독창성:
    - 5. 형식과 표현:
    - 6. 추가 제안사항:
    
    구체적이고 실행 가능한 조언을 제공해주세요.
    """
    
    try:
        # 문서 내용이 너무 길 경우 요약
        if len(content) > 10000:
            content = content[:10000] + "\n\n[문서가 너무 길어 일부만 분석합니다]"
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,  # 토큰 수 증가
            temperature=0.3,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"다음 학생의 연구 보고서를 분석하여 상세한 피드백을 제공해주세요.\n\n{content}"
                }
            ]
        )
        
        return message.content[0].text
        
    except Exception as e:
        st.error(f"❌ AI 분석 중 오류가 발생했습니다: {str(e)}")
        return None

def parse_feedback_sections(feedback_text):
    """AI 피드백을 섹션별로 파싱 - 개선된 버전"""
    sections = {
        "전체 평가": "",
        "구조와 논리성": "",
        "내용의 충실성": "",
        "학술적 글쓰기": "",
        "창의성과 독창성": "",
        "형식과 표현": "",
        "추가 제안사항": ""
    }
    
    # 섹션 헤더 패턴 정의
    section_patterns = {
        "구조와 논리성": ["구조", "논리", "체계", "서론", "본론", "결론", "흐름"],
        "내용의 충실성": ["내용", "충실", "깊이", "자료", "근거", "탐구"],
        "학술적 글쓰기": ["학술", "인용", "출처", "객관", "참고문헌"],
        "창의성과 독창성": ["창의", "독창", "새로운", "관점", "비판적"],
        "형식과 표현": ["형식", "표현", "문법", "맞춤법", "어휘"],
        "추가 제안사항": ["제안", "추가", "향후", "개선", "보완"]
    }
    
    lines = feedback_text.split('\n')
    current_section = "전체 평가"
    section_changed = False
    
    for line in lines:
        line = line.strip()
        if line:
            # 섹션 헤더 감지 (더 정확한 매칭)
            section_changed = False
            for section_name, keywords in section_patterns.items():
                # 라인 시작 부분에 섹션 키워드가 있고 ':' 또는 숫자가 포함된 경우
                if (any(keyword in line.lower()[:20] for keyword in keywords) and 
                    (":" in line or any(char.isdigit() for char in line[:5]))):
                    current_section = section_name
                    section_changed = True
                    break
            
            # 현재 섹션에 내용 추가
            if not section_changed or current_section == "전체 평가":
                sections[current_section] += line + "\n"
    
    # 빈 섹션 제거 및 내용 정리
    result = {}
    for k, v in sections.items():
        content = v.strip()
        if content:
            # 섹션 이름이 내용에 중복되어 있으면 제거
            if content.startswith(k):
                content = content[len(k):].strip(": \n")
            result[k] = content
    
    return result

def check_system_status():
    """시스템 상태 확인"""
    with st.sidebar:
        st.markdown("### 🔧 시스템 상태")
        
        # Anthropic API 체크
        try:
            anthropic_key = st.secrets.get("ANTHROPIC_API_KEY")
            if anthropic_key:
                st.success("✅ AI 분석 엔진 연결됨")
            else:
                st.error("❌ AI 분석 엔진 연결 실패")
        except:
            st.error("❌ AI 분석 엔진 연결 실패")
        
        # Google API 체크
        try:
            google_config = st.secrets.get("google_service_account")
            if google_config:
                st.success("✅ 구글 API 설정 확인됨")
                
                # Google 연결 테스트
                commenter = GoogleDocsCommenter()
                if commenter.is_available():
                    st.success("✅ 구글 댓글 기능 활성화")
                else:
                    st.error("❌ 구글 연결 실패")
            else:
                st.warning("⚠️ 구글 댓글 기능 비활성화")
        except Exception as e:
            st.error(f"❌ 구글 연결 오류: {str(e)}")

def main():
    # 시스템 상태 확인
    check_system_status()
    
    # 헤더
    st.markdown('<h1 class="main-header">📝 연구 보고서 AI 피드백 시스템</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">구글 문서 링크를 입력하면 AI가 상세한 피드백을 댓글로 달아드립니다</p>', unsafe_allow_html=True)
    
    # 사용 안내
    with st.expander("📋 사용 방법 및 참고 자료", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 📖 사용 방법
            1. **구글 문서 준비**: 연구 보고서를 구글 문서로 작성
            2. **공유 설정**: "링크가 있는 모든 사용자 - 댓글 작성자" 권한 설정
            3. **링크 입력**: 아래에 구글 문서 링크 붙여넣기
            4. **분석 시작**: "피드백 분석 시작" 버튼 클릭
            5. **결과 확인**: 구글 문서에 추가된 댓글 확인 및 활용
            """)
        
        with col2:
            st.markdown("""
            ### 🔗 참고 자료
            - [📋 탐구 보고서 계획서](https://docs.google.com/document/d/1aAUtsWK8daVP1TVnd9Zn_WE-FNvG8a2FaXXWzL2oPt4/edit?usp=sharing)
            - [📖 보고서 작성 가이드](https://docs.google.com/document/d/16PuheEpWW8l6bbHwLCYCbeMpti_lk59qlqLYzxsRjD4/edit?usp=sharing)
            - [💡 예시 주제 목록](https://docs.google.com/document/d/1SvYyqBKpvOUNGfGTHs_xdGfs5TK3ppdDnnZeyM3Aw-E/edit?usp=sharing)
            - [📄 보고서 템플릿](https://docs.google.com/document/d/1lvZ916Xo5WTw7Gzuvv3kXBbRvrV6PW9buDQWK5byCKU/edit?usp=sharing)
            """)
    
    st.markdown("---")
    
    # 메인 입력 영역
    st.markdown("### 📎 구글 문서 링크 입력")
    
    # 경고 수정: label_visibility 사용
    doc_url = st.text_input(
        "구글 문서 링크",
        placeholder="https://docs.google.com/document/d/your-document-id/edit",
        help="구글 문서의 전체 URL을 입력해주세요",
        label_visibility="collapsed"
    )
    
    # 문서 링크 검증
    if doc_url:
        doc_id = extract_doc_id(doc_url)
        if doc_id:
            st.markdown(f'<div class="success-box">✅ 유효한 구글 문서 링크입니다<br><small>문서 ID: {doc_id}</small></div>', unsafe_allow_html=True)
            st.session_state.current_doc_id = doc_id
            st.session_state.current_doc_url = doc_url
        else:
            st.markdown('<div class="warning-box">⚠️ 올바른 구글 문서 링크를 입력해주세요<br><small>예시: https://docs.google.com/document/d/문서ID/edit</small></div>', unsafe_allow_html=True)
            st.session_state.current_doc_id = None
            st.session_state.current_doc_url = None
    
    # 분석 버튼
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_button = st.button("🚀 피드백 분석 시작", type="primary", disabled=not st.session_state.current_doc_id)
    
    # 분석 실행
    if analyze_button and st.session_state.current_doc_id:
        st.markdown("---")
        
        # Google Docs 연동 초기화
        commenter = GoogleDocsCommenter()
        
        if not commenter.is_available():
            st.warning("⚠️ Google API를 사용할 수 없습니다. 데모 모드로 실행됩니다.")
            
            # 데모 모드
            sample_content = """
            제목: K-Pop 가사에 나타난 청년 세대의 가치관 변화 연구
            
            서론: 현대 사회에서 K-Pop은 전 세계적인 문화 현상이다...
            본론: 주요 아티스트별 가사 분석을 통해...
            결론: K-Pop은 청년 세대의 가치관 형성에 영향을 미친다...
            """
            
            with st.spinner("🤖 AI 분석 중... (데모 모드)"):
                feedback = analyze_document_content(sample_content)
                time.sleep(3)
            
            if feedback:
                st.success("✅ 분석 완료! (데모 모드)")
                st.markdown("### 📋 생성된 피드백")
                st.markdown(feedback)
                st.info("💡 실제 운영 시 이 피드백이 구글 문서에 댓글로 추가됩니다.")
        
        else:
            # 실제 모드
            doc_id = st.session_state.current_doc_id
            
            # 문서 내용 읽기
            with st.spinner("📖 구글 문서 내용을 읽는 중..."):
                doc_data = commenter.get_document_content(doc_id)
            
            if doc_data:
                st.success(f"✅ 문서 읽기 성공: {doc_data['title']}")
                
                # AI 분석
                with st.spinner("🤖 AI가 문서를 분석하고 있습니다..."):
                    feedback = analyze_document_content(doc_data['content'])
                
                if feedback:
                    # 피드백 섹션 파싱
                    feedback_sections = parse_feedback_sections(feedback)
                    
                    # 댓글 추가
                    st.markdown("### 📝 구글 문서에 댓글 추가 중...")
                    
                    success_count = 0
                    total_sections = len(feedback_sections)
                    
                    # 프로그레스 바 추가
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, (section_name, content) in enumerate(feedback_sections.items()):
                        if content:
                            status_text.text(f"📝 {section_name} 댓글 추가 중...")
                            comment_text = f"🤖 AI 피드백 - {section_name}\n\n{content}"
                            
                            # 댓글 길이 확인
                            if len(comment_text) > 1000:
                                st.info(f"📏 {section_name} 섹션 길이: {len(comment_text)}자")
                            
                            if commenter.add_comment(doc_id, comment_text):
                                success_count += 1
                                st.success(f"✅ {section_name} 댓글 추가 완료")
                            else:
                                st.error(f"❌ {section_name} 댓글 추가 실패")
                            
                            # 프로그레스 바 업데이트
                            progress_bar.progress((idx + 1) / total_sections)
                            time.sleep(2)  # API 호출 간격
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    if success_count > 0:
                        st.balloons()
                        st.success(f"🎉 총 {success_count}개 댓글이 추가되었습니다!")
                        st.link_button("📝 구글 문서에서 댓글 확인하기", doc_url)
    
    elif analyze_button and not st.session_state.current_doc_id:
        st.error("❌ 유효한 구글 문서 링크를 먼저 입력해주세요.")
    
    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; margin-top: 2rem; padding: 1rem; background-color: #f8f9fa; border-radius: 10px;">
        <p><strong>🏫 완도고등학교</strong></p>
        <p>📧 개발: 국어교사 공지훈 | 💡 이 도구는 완도고등학교 학생들의 연구 보고서 작성을 돕기 위해 개발되었습니다</p>
        <p><small>⚠️ AI 피드백은 참고용이며, 최종 판단은 학생과 교사가 함께 해야 합니다</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
