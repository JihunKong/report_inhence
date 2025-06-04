import streamlit as st
import anthropic
import re
import time
import os
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# 페이지 설정
st.set_page_config(
    page_title="연구 보고서 AI 피드백 시스템",
    page_icon="📝",
    layout="wide"
)

# CSS 스타일링
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
    .feedback-box {
        background-color: #f0f8ff;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #2E86AB;
        margin: 1rem 0;
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
    .step-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 3px solid #2196f3;
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
    .stButton > button:hover {
        background-color: #1f5f7a;
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
if 'feedback_result' not in st.session_state:
    st.session_state.feedback_result = None

class GoogleDocsCommenter:
    def __init__(self):
        """Google Docs 댓글 추가 클래스"""
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
            # Google API 설정이 없어도 앱이 실행되도록 함
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
            return None
    
    def add_comment(self, doc_id, comment_text):
        """문서에 댓글 추가"""
        if not self.is_available():
            return False
            
        try:
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
        sections_to_process = [(k, v) for k, v in feedback_sections.items() if v.strip()]
        total_sections = len(sections_to_process)
        
        if total_sections == 0:
            return False
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, (section_name, feedback_content) in enumerate(sections_to_process):
            status_text.text(f"📝 댓글 추가 중: {section_name}")
            
            comment_text = f"""🤖 AI 피드백 - {section_name}

{feedback_content}

---
📌 이 피드백은 AI에 의해 생성되었습니다.
💡 참고용으로 활용하시고, 궁금한 점은 교사에게 문의하세요.
🏫 완도고등학교 국어과 AI 피드백 시스템"""
            
            if self.add_comment(doc_id, comment_text):
                success_count += 1
            
            progress_bar.progress((i + 1) / total_sections)
            time.sleep(2)  # API 호출 간격 조절
        
        status_text.empty()
        progress_bar.empty()
        
        return success_count > 0

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

    **피드백 작성 원칙:**
    - 구체적이고 실행 가능한 조언 제공
    - 잘된 점과 개선할 점의 균형 유지
    - 학생이 이해하기 쉬운 언어 사용
    - 격려와 동기부여를 포함한 건설적 톤

    각 영역별로 명확하게 구분하여 작성해주세요.
    """
    
    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2500,
            temperature=0.3,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"""
                    다음 학생의 연구 보고서를 분석하여 상세한 피드백을 제공해주세요.
                    
                    **분석할 문서:**
                    {content}
                    
                    각 평가 영역별로 체계적인 피드백을 부탁드립니다.
                    """
                }
            ]
        )
        
        return message.content[0].text
        
    except Exception as e:
        st.error(f"❌ AI 분석 중 오류가 발생했습니다: {str(e)}")
        return None

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
    
    lines = feedback_text.split('\n')
    current_section = "전체 평가"
    
    for line in lines:
        line = line.strip()
        if line:
            # 섹션 감지
            if any(keyword in line.lower() for keyword in ["구조", "논리", "체계", "흐름"]):
                current_section = "구조와 논리성"
            elif any(keyword in line.lower() for keyword in ["내용", "충실", "깊이", "자료", "탐구"]):
                current_section = "내용의 충실성"
            elif any(keyword in line.lower() for keyword in ["학술", "인용", "출처", "객관", "참고문헌"]):
                current_section = "학술적 글쓰기"
            elif any(keyword in line.lower() for keyword in ["창의", "독창", "새로운", "관점", "비판"]):
                current_section = "창의성과 독창성"
            elif any(keyword in line.lower() for keyword in ["형식", "표현", "문법", "맞춤법", "문체"]):
                current_section = "형식과 표현"
            elif any(keyword in line.lower() for keyword in ["제안", "추가", "향후", "발전", "개선"]):
                current_section = "추가 제안사항"
            
            sections[current_section] += line + "\n"
    
    # 빈 섹션 제거하고 정리
    return {k: v.strip() for k, v in sections.items() if v.strip()}

def process_document_with_comments(doc_url):
    """실제 구글 문서에 댓글을 추가하는 프로세스"""
    doc_id = extract_doc_id(doc_url)
    if not doc_id:
        st.error("❌ 유효하지 않은 문서 링크입니다.")
        return False
    
    commenter = GoogleDocsCommenter()
    
    if not commenter.is_available():
        return process_demo_mode(doc_url, doc_id)
    
    # 문서 내용 읽기
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
    
    st.success(f"✅ 문서 읽기 성공: **{doc_data['title']}**")
    
    # AI 분석
    with st.spinner("🤖 AI가 문서를 분석하고 있습니다..."):
        feedback = analyze_document_content(doc_data['content'])
    
    if not feedback:
        return False
    
    # 피드백 섹션 파싱
    feedback_sections = parse_feedback_sections(feedback)
    
    # 구글 문서에 댓글 추가
    st.markdown("### 📝 구글 문서에 댓글 추가 중...")
    success = commenter.add_structured_feedback(doc_id, feedback_sections)
    
    if success:
        st.success("✅ 피드백이 구글 문서에 댓글로 추가되었습니다!")
        st.balloons()
        
        st.markdown(f"""
        ### 🎉 분석 완료!
        
        **📊 추가된 댓글 수:** {len(feedback_sections)}개
        
        ### 🔗 다음 단계
        [📝 구글 문서에서 댓글 확인하기]({doc_url})
        
        **💡 활용 팁:**
        - 각 댓글을 클릭하면 답변을 달 수 있습니다
        - 피드백을 참고하여 문서를 수정해보세요
        - 궁금한 점은 교사에게 문의하세요
        - 수정 후 다시 분석을 요청할 수 있습니다
        """)
        return True
    else:
        st.error("❌ 댓글 추가에 실패했습니다.")
        return False

def process_demo_mode(doc_url, doc_id):
    """Google API 설정이 없을 때의 데모 모드"""
    st.warning("⚠️ Google API 설정이 없어 데모 모드로 실행됩니다.")
    
    # 샘플 문서 분석
    sample_content = f"""
    제목: K-Pop 가사에 나타난 청년 세대의 가치관 변화 연구

    서론:
    현대 한국 사회에서 K-Pop은 단순한 음악 장르를 넘어서 글로벌 문화 현상으로 자리잡았다. 
    본 연구는 K-Pop 가사에 담긴 사회적 메시지와 가치관을 분석하여, 현대 청년 세대의 
    문화적 특성과 사회 인식을 파악하고자 한다.

    본론:
    1. K-Pop의 역사적 발전과 사회적 영향
    2. 가사 분석 방법론 및 연구 대상  
    3. 주요 아티스트별 메시지 분석
    - BTS의 자아 정체성과 사회적 책임
    - BLACKPINK의 여성 독립성과 자신감
    - IU의 개인적 성장과 사회적 공감

    결론:
    K-Pop 가사는 시대의 가치관을 반영하며 전 세계 젊은 세대에게 긍정적 영향을 미치고 있다.
    """
    
    with st.spinner("🤖 AI 분석 중..."):
        feedback = analyze_document_content(sample_content)
        time.sleep(3)
    
    if feedback:
        st.success("✅ 분석 완료! (데모 모드)")
        
        feedback_sections = parse_feedback_sections(feedback)
        
        st.markdown("### 💬 생성될 댓글 미리보기")
        for i, (section_name, content) in enumerate(feedback_sections.items(), 1):
            with st.expander(f"댓글 {i}: AI 피드백 - {section_name}"):
                st.markdown(f"**{section_name}**")
                st.markdown(content)
                st.markdown("---")
                st.markdown("📌 이 피드백은 AI에 의해 생성되었습니다.")
        
        st.info(f"""
        **📌 실제 운영 시:**
        - 위의 {len(feedback_sections)}개 댓글이 구글 문서에 자동으로 추가됩니다
        - [문서 링크]({doc_url})에서 확인할 수 있습니다
        - Google API 설정 후 실제 댓글 기능을 사용하실 수 있습니다
        """)
        return True
    
    return False

def check_system_status():
    """시스템 상태 확인"""
    with st.sidebar:
        st.markdown("### 🔧 시스템 상태")
        
        # Anthropic API 체크
        try:
            anthropic_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
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
                st.success("✅ 구글 댓글 기능 활성화")
            else:
                st.warning("⚠️ 구글 댓글 기능 비활성화")
                st.info("데모 모드로 실행됩니다")
        except:
            st.warning("⚠️ 구글 댓글 기능 비활성화")
            st.info("데모 모드로 실행됩니다")

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
    
    doc_url = st.text_input(
        "",
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
        success = process_document_with_comments(st.session_state.current_doc_url)
        if success:
            st.session_state.analysis_complete = True
    
    elif analyze_button and not st.session_state.current_doc_id:
        st.error("❌ 유효한 구글 문서 링크를 먼저 입력해주세요.")
    
    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; margin-top: 2rem; padding: 1rem; background-color: #f8f9fa; border-radius: 10px;">
        <p><strong>🏫 완도고등학교 국어과</strong></p>
        <p>📧 개발: 공지훈 교사 | 💡 이 도구는 학생들의 연구 보고서 작성을 돕기 위해 개발되었습니다</p>
        <p><small>⚠️ AI 피드백은 참고용이며, 최종 판단은 학생과 교사가 함께 해야 합니다</small></p>
        <p><small>🔒 학생 문서는 분석 목적으로만 사용되며 저장되지 않습니다</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
