import streamlit as st
import anthropic
import re
import time
import os

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
if 'feedback_result' not in st.session_state:
    st.session_state.feedback_result = None

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
        st.error("❌ Anthropic API 키가 설정되지 않았습니다. 관리자에게 문의하세요.")
        st.stop()
    return anthropic.Anthropic(api_key=api_key)

def analyze_document_structure(content):
    """문서 구조 분석"""
    structure_feedback = []
    
    # 기본 구조 확인
    has_title = bool(re.search(r'^.{1,100}$', content.split('\n')[0]) if content.split('\n') else False)
    has_intro = any(keyword in content.lower() for keyword in ['서론', '도입', '시작', '배경'])
    has_body = any(keyword in content.lower() for keyword in ['본론', '내용', '분석', '연구'])
    has_conclusion = any(keyword in content.lower() for keyword in ['결론', '마무리', '정리', '요약'])
    has_references = any(keyword in content.lower() for keyword in ['참고문헌', '참고자료', '출처', '참조'])
    
    if not has_title:
        structure_feedback.append("📝 명확한 제목이 필요합니다.")
    if not has_intro:
        structure_feedback.append("📝 서론 부분을 명시적으로 구분해주세요.")
    if not has_body:
        structure_feedback.append("📝 본론 부분의 구조를 더 명확히 해주세요.")
    if not has_conclusion:
        structure_feedback.append("📝 결론 부분이 필요합니다.")
    if not has_references:
        structure_feedback.append("📝 참고문헌 목록을 추가해주세요.")
    
    return structure_feedback

def analyze_document_content(content):
    """문서 내용을 분석하여 피드백 생성"""
    client = get_anthropic_client()
    
    # 기본 구조 분석
    structure_issues = analyze_document_structure(content)
    
    system_prompt = """
    당신은 고등학교 국어 교사로서 학생들의 연구 보고서를 검토하는 전문가입니다.
    다음 기준에 따라 구체적이고 건설적인 피드백을 제공해주세요:

    **피드백 기준:**
    1. **구조와 논리성** (25점): 서론-본론-결론의 논리적 흐름, 목차의 체계성
    2. **내용의 충실성** (30점): 주제 탐구의 깊이, 자료의 다양성과 신뢰성
    3. **학술적 글쓰기** (20점): 객관적 서술, 적절한 인용, 출처 표기
    4. **창의성과 독창성** (15점): 새로운 관점, 비판적 사고
    5. **형식과 표현** (10점): 맞춤법, 문법, 일관된 형식

    **피드백 형식:**
    각 영역별로 다음과 같이 작성해주세요:
    - ✅ 잘된 점 (구체적인 칭찬)
    - 🔍 개선할 점 (실행 가능한 제안)
    - 💡 추가 제안 (심화 학습 방향)

    피드백은 학생이 이해하기 쉽고 동기부여가 되는 톤으로 작성해주세요.
    비판보다는 격려와 구체적인 개선 방안을 제시해주세요.
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
                    
                    각 영역별로 체계적인 피드백을 부탁드립니다.
                    """
                }
            ]
        )
        
        ai_feedback = message.content[0].text
        
        # 구조적 이슈가 있다면 추가
        if structure_issues:
            structure_section = "\n\n**📋 문서 구조 점검:**\n" + "\n".join(structure_issues)
            ai_feedback += structure_section
        
        return ai_feedback
        
    except Exception as e:
        st.error(f"❌ AI 분석 중 오류가 발생했습니다: {str(e)}")
        return None

def generate_comment_format_feedback(feedback_text, doc_url):
    """구글 문서 댓글 형태로 포맷팅된 피드백 생성"""
    
    formatted_feedback = f"""
🤖 **AI 피드백 시스템 분석 결과**

{feedback_text}

---
📌 **다음 단계:**
1. 위 피드백을 참고하여 문서를 수정해보세요
2. 수정 후 다시 분석을 요청할 수 있습니다
3. 궁금한 점은 담당 교사에게 문의하세요

📋 **참고 자료:**
- [보고서 작성 가이드](https://docs.google.com/document/d/16PuheEpWW8l6bbHwLCYCbeMpti_lk59qlqLYzxsRjD4/edit?usp=sharing)
- [예시 주제 목록](https://docs.google.com/document/d/1SvYyqBKpvOUNGfGTHs_xdGfs5TK3ppdDnnZeyM3Aw-E/edit?usp=sharing)

*이 피드백은 AI에 의해 생성되었습니다. 참고용으로 활용하시고, 최종 판단은 스스로 해주세요.*
    """
    
    return formatted_feedback

def main():
    # 헤더
    st.markdown('<h1 class="main-header">📝 연구 보고서 AI 피드백 시스템</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">구글 문서 링크를 입력하면 AI가 상세한 피드백을 제공합니다</p>', unsafe_allow_html=True)
    
    # 사용 안내
    with st.expander("📋 사용 방법 및 참고 자료", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 📖 사용 방법
            1. **구글 문서 준비**: 연구 보고서를 구글 문서로 작성
            2. **공유 설정**: "링크가 있는 모든 사용자 - 뷰어" 권한 설정
            3. **링크 입력**: 아래에 구글 문서 링크 붙여넣기
            4. **분석 시작**: "피드백 분석 시작" 버튼 클릭
            5. **결과 확인**: 생성된 피드백을 참고하여 보고서 개선
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
        else:
            st.markdown('<div class="warning-box">⚠️ 올바른 구글 문서 링크를 입력해주세요<br><small>예시: https://docs.google.com/document/d/문서ID/edit</small></div>', unsafe_allow_html=True)
            st.session_state.current_doc_id = None
    
    # 분석 버튼
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_button = st.button("🚀 피드백 분석 시작", type="primary", disabled=not st.session_state.current_doc_id)
    
    # 분석 실행
    if analyze_button and st.session_state.current_doc_id:
        st.markdown("---")
        
        # 진행 상태 표시
        st.markdown("### 🔄 분석 진행 상황")
        
        # 진행 바와 상태 메시지
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 단계별 분석 진행
        steps = [
            "🔗 문서 링크 검증 중...",
            "📄 문서 내용 분석 중...",
            "🤖 AI 피드백 생성 중...",
            "✅ 분석 완료!"
        ]
        
        for i, step in enumerate(steps):
            status_text.markdown(f'<div class="step-box">{step}</div>', unsafe_allow_html=True)
            progress_bar.progress((i + 1) / len(steps))
            time.sleep(1.5)
        
        # 샘플 문서 내용 (실제로는 문서에서 가져와야 함)
        # 현재는 데모용으로 샘플 콘텐츠 사용
        sample_content = f"""
        제목: K-Pop 가사에 나타난 사회적 메시지와 가치관 분석

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
        
        # AI 피드백 생성
        with st.spinner("AI가 문서를 꼼꼼히 분석하고 있습니다..."):
            feedback = analyze_document_content(sample_content)
        
        if feedback:
            st.session_state.feedback_result = feedback
            st.session_state.analysis_complete = True
            
            # 성공 메시지
            st.markdown("---")
            st.markdown("### ✅ 분석 완료!")
            st.markdown('<div class="success-box">문서 분석이 성공적으로 완료되었습니다!</div>', unsafe_allow_html=True)
            
            # 피드백 결과 표시
            st.markdown("### 📋 AI 피드백 결과")
            
            # 댓글 형태로 포맷팅
            formatted_feedback = generate_comment_format_feedback(feedback, doc_url)
            
            with st.container():
                st.markdown('<div class="feedback-box">', unsafe_allow_html=True)
                st.markdown(formatted_feedback)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 액션 버튼들
            st.markdown("### 🎯 다음 단계")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📝 피드백 복사하기"):
                    st.code(formatted_feedback, language=None)
                    st.success("피드백이 위에 표시되었습니다. 복사해서 활용하세요!")
            
            with col2:
                if st.button("🔄 다시 분석하기"):
                    st.session_state.analysis_complete = False
                    st.session_state.feedback_result = None
                    st.rerun()
            
            with col3:
                st.link_button("📄 구글 문서 열기", doc_url)
        
        else:
            st.markdown('<div class="error-box">❌ 분석 중 오류가 발생했습니다. 다시 시도해주세요.</div>', unsafe_allow_html=True)
    
    elif analyze_button and not st.session_state.current_doc_id:
        st.markdown('<div class="error-box">❌ 유효한 구글 문서 링크를 먼저 입력해주세요.</div>', unsafe_allow_html=True)
    
    # 기존 분석 결과가 있을 때 표시
    elif st.session_state.analysis_complete and st.session_state.feedback_result:
        st.markdown("---")
        st.markdown("### 📋 최근 분석 결과")
        
        formatted_feedback = generate_comment_format_feedback(st.session_state.feedback_result, doc_url or "")
        
        with st.container():
            st.markdown('<div class="feedback-box">', unsafe_allow_html=True)
            st.markdown(formatted_feedback)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; margin-top: 2rem; padding: 1rem; background-color: #f8f9fa; border-radius: 10px;">
        <p><strong>🏫 완도고등학교 국어과</strong></p>
        <p>📧 개발: 공지훈 교사 | 💡 이 도구는 학생들의 연구 보고서 작성을 돕기 위해 개발되었습니다</p>
        <p><small>⚠️ AI 피드백은 참고용이며, 최종 판단은 학생과 교사가 함께 해야 합니다</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
