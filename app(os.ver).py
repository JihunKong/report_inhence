import streamlit as st
from openai import OpenAI
import re
import time
import os
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
import json

# 페이지 설정
st.set_page_config(
    page_title="AI 글쓰기 평가 시스템",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일링
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2E86AB;
        font-size: 2.5rem;
        margin-bottom: 1rem;
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
    .info-box {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #17a2b8;
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
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border: 1px solid #dee2e6;
    }
    .feedback-section {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# 타이틀
st.markdown('<h1 class="main-header">📝 AI 글쓰기 평가 시스템</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Google Docs 문서에 AI가 장르별 맞춤 평가를 제공합니다</p>', unsafe_allow_html=True)

# 사용법 안내
with st.expander("📖 사용법 안내", expanded=True):
    st.markdown("""
    ### 🚀 빠른 시작 가이드
    
    <div class='step-box'>
    <b>1단계: Google Docs 문서 준비</b>
    <ul>
    <li>평가받고 싶은 Google Docs 문서를 준비합니다</li>
    <li>문서를 열고 우측 상단의 '공유' 버튼을 클릭합니다</li>
    <li>'링크 복사'를 클릭하거나, 특정 사용자에게 '편집자' 권한을 부여합니다</li>
    <li><b>중요:</b> 이 앱의 서비스 계정에 '편집자' 권한이 있어야 피드백을 추가할 수 있습니다</li>
    </ul>
    </div>
    
    <div class='step-box'>
    <b>2단계: 글의 장르 선택</b>
    <ul>
    <li>감상문: 독서감상문, 영화감상문 등</li>
    <li>비평문: 문학비평, 예술비평 등</li>
    <li>보고서: 실험보고서, 조사보고서 등</li>
    <li>소논문: 학술적 논문, 연구논문 등</li>
    <li>논설문: 주장과 논거를 담은 글</li>
    </ul>
    </div>
    
    <div class='step-box'>
    <b>3단계: 평가 요청</b>
    <ul>
    <li>Google Docs URL을 입력하고 '평가 요청' 버튼을 클릭합니다</li>
    <li>AI가 문서를 분석하고 장르별 구조적 원리에 따라 평가합니다</li>
    <li>평가 결과가 문서에 직접 삽입됩니다</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

# Google Docs 인증 설정
@st.cache_resource
def get_google_service():
    """Google Docs 서비스 인스턴스 생성"""
    try:
        # 환경변수에서 가져오기
        service_account_info = os.environ.get("GOOGLE_SERVICE_ACCOUNT")
        if service_account_info:
            service_account_info = json.loads(service_account_info)
        else:
            st.error("Google 서비스 계정 정보가 없습니다.")
            return None
        
        # 문서 편집을 위한 권한
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=[
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/drive.file'
            ]
        )
        
        service = build('docs', 'v1', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Google 서비스 초기화 실패: {str(e)}")
        return None

def extract_document_id(url):
    """Google Docs URL에서 문서 ID 추출"""
    patterns = [
        r'/document/d/([a-zA-Z0-9-_]+)',
        r'/d/([a-zA-Z0-9-_]+)',
        r'docs\.google\.com/.*[?&]id=([a-zA-Z0-9-_]+)',
        r'^([a-zA-Z0-9-_]+)$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_document_content(service, document_id):
    """Google Docs 문서 내용과 구조 가져오기"""
    try:
        document = service.documents().get(documentId=document_id).execute()
        
        title = document.get('title', '제목 없음')
        content_with_positions = []
        
        for element in document.get('body', {}).get('content', []):
            if 'paragraph' in element:
                paragraph_text = []
                start_index = element.get('startIndex', 0)
                end_index = element.get('endIndex', 0)
                
                for text_element in element['paragraph'].get('elements', []):
                    if 'textRun' in text_element:
                        text = text_element['textRun'].get('content', '')
                        if text.strip():
                            paragraph_text.append(text)
                
                if paragraph_text:
                    full_text = ''.join(paragraph_text)
                    content_with_positions.append({
                        'text': full_text,
                        'start': start_index,
                        'end': end_index
                    })
        
        return title, content_with_positions
    except Exception as e:
        st.error(f"문서 읽기 오류: {str(e)}")
        return None, None

def insert_feedback_to_doc(service, document_id, feedbacks):
    """Google Docs에 피드백 직접 삽입"""
    try:
        requests = []
        
        # 피드백을 역순으로 삽입 (문서 끝부터 시작하여 인덱스가 밀리지 않도록)
        for feedback in reversed(feedbacks):
            # 피드백 텍스트 포맷팅
            feedback_text = f"\n\n[AI 평가 - {feedback['type']}]\n{feedback['content']}\n" + "-" * 50 + "\n"
            
            # 텍스트 삽입 요청
            requests.append({
                'insertText': {
                    'location': {
                        'index': feedback['insert_at']
                    },
                    'text': feedback_text
                }
            })
            
            # 피드백 스타일 적용 (색상과 배경)
            text_length = len(feedback_text)
            requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': feedback['insert_at'],
                        'endIndex': feedback['insert_at'] + text_length
                    },
                    'textStyle': {
                        'foregroundColor': {
                            'color': {
                                'rgbColor': {
                                    'red': 0.0,
                                    'green': 0.0,
                                    'blue': 0.8
                                }
                            }
                        },
                        'backgroundColor': {
                            'color': {
                                'rgbColor': {
                                    'red': 0.95,
                                    'green': 0.95,
                                    'blue': 1.0
                                }
                            }
                        },
                        'italic': True
                    },
                    'fields': 'foregroundColor,backgroundColor,italic'
                }
            })
        
        # 문서 업데이트 실행
        if requests:
            result = service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute()
            return True
        return False
        
    except HttpError as e:
        if e.resp.status == 403:
            st.error("❌ 문서를 편집할 권한이 없습니다. 문서에 '편집자' 권한을 부여해주세요.")
        else:
            st.error(f"피드백 삽입 중 오류 발생: {str(e)}")
        return False
    except Exception as e:
        st.error(f"피드백 삽입 중 오류 발생: {str(e)}")
        return False

# 글의 장르와 평가 기준
GENRES = {
    "감상문": {
        "description": "독서감상문, 영화감상문 등 작품에 대한 개인적 감상을 표현하는 글",
        "structure": [
            "도입부: 작품 소개와 첫인상",
            "전개부: 인상 깊은 장면/내용과 개인적 감상",
            "결론부: 작품이 주는 교훈이나 의미"
        ],
        "criteria": "개인적 감상의 진정성, 구체적 근거 제시, 감정 표현의 적절성"
    },
    "비평문": {
        "description": "문학작품, 예술작품 등을 객관적으로 분석하고 평가하는 글",
        "structure": [
            "서론: 작품 소개와 비평의 관점 제시",
            "본론: 작품의 특징 분석과 평가",
            "결론: 종합적 평가와 의의"
        ],
        "criteria": "분석의 객관성, 평가 기준의 명확성, 논리적 일관성"
    },
    "보고서": {
        "description": "조사, 실험, 관찰 등의 결과를 체계적으로 정리한 글",
        "structure": [
            "서론: 목적과 배경 설명",
            "방법: 조사/실험 방법 설명",
            "결과: 데이터와 발견사항 제시",
            "논의: 결과 해석과 의미 분석",
            "결론: 요약과 제언"
        ],
        "criteria": "객관성, 정확성, 체계성, 데이터의 신뢰성"
    },
    "소논문": {
        "description": "특정 주제에 대한 학술적 연구를 담은 글",
        "structure": [
            "서론: 연구 배경, 목적, 연구 문제",
            "이론적 배경: 선행연구 검토",
            "연구 방법: 연구 설계와 방법론",
            "연구 결과: 분석 결과 제시",
            "논의 및 결론: 시사점과 한계"
        ],
        "criteria": "학술적 엄밀성, 논리적 타당성, 독창성, 인용의 정확성"
    },
    "논설문": {
        "description": "특정 주제에 대한 주장과 논거를 제시하는 글",
        "structure": [
            "서론: 논제 제시와 주장 예고",
            "본론: 논거 제시와 반박 고려",
            "결론: 주장 강조와 설득"
        ],
        "criteria": "주장의 명확성, 논거의 타당성, 반박 고려, 설득력"
    }
}

# 사이드바 설정
with st.sidebar:
    st.markdown("### ⚙️ 설정")
    
    # API 키 입력 (환경변수에서 가져오기)
    api_key = os.environ.get("OPENAI_API_KEY", "")
    
    if not api_key:
        api_key = st.text_input("OpenAI API Key", type="password", help="GPT-4 API 키를 입력하세요")
    
    # 모델은 GPT-4o mini로 고정
    model_choice = "gpt-4o-mini"
    st.info("모델: GPT-4o-mini")
    
    st.markdown("---")
    
    # 글의 장르 선택
    genre = st.selectbox(
        "📄 글의 장르",
        list(GENRES.keys()),
        help="평가할 글의 장르를 선택하세요"
    )
    
    # 장르 설명 표시
    st.markdown(f"**설명:** {GENRES[genre]['description']}")
    
    # 구조적 원리 표시
    with st.expander("📐 평가 기준 보기"):
        st.markdown("**구조적 원리:**")
        for item in GENRES[genre]['structure']:
            st.markdown(f"- {item}")
        st.markdown(f"\n**평가 초점:** {GENRES[genre]['criteria']}")
    
    # 추가 지시사항
    custom_instructions = st.text_area(
        "📝 추가 지시사항 (선택)",
        placeholder="AI에게 특별히 요청하고 싶은 사항이 있다면 입력하세요",
        help="예: '고등학생 수준에 맞게 평가해주세요', '문법보다는 내용에 집중해주세요' 등"
    )
    
    st.markdown("---")
    st.markdown("### 🔍 시스템 상태")
    
    # API 키 상태
    if api_key:
        st.success("✅ OpenAI API 연결됨")
    else:
        st.warning("⚠️ API 키 필요")
    
    # Google 서비스 상태
    if os.environ.get("GOOGLE_SERVICE_ACCOUNT"):
        st.success("✅ Google API 연결됨")
    else:
        st.warning("⚠️ Google 인증 필요")

# 메인 컨텐츠
st.markdown("### 📄 문서 정보 입력")

# 현재 설정 표시
col1, col2 = st.columns(2)
with col1:
    st.info(f"**글의 장르:** {genre}")
with col2:
    st.info(f"**평가 모델:** GPT-4o-mini")

# Google Docs URL 입력
doc_url = st.text_input(
    "Google Docs 문서 URL 또는 ID",
    placeholder="https://docs.google.com/document/d/YOUR_DOCUMENT_ID/edit",
    help="편집자 권한이 부여된 Google Docs 링크를 입력하세요"
)

# 예시 문서 정보
with st.expander("💡 예시 파일 보기"):
    st.markdown("""
    예시 문서를 보려면 아래 링크를 클릭하세요:
    
    [📄 예시 문서 보기](https://docs.google.com/document/d/1PrPKPnSKlS69438XdS0qHBnqUSQ2zO6DNrxFxsu5Au8/edit?usp=sharing)
    
    **주의:** 실제 평가를 받으려면 문서에 편집자 권한을 부여해야 합니다.
    """)

# 평가 요청 버튼
if st.button("🚀 평가 요청", type="primary", use_container_width=True):
    if not api_key:
        st.error("⚠️ API 키를 입력해주세요!")
    elif not doc_url:
        st.error("⚠️ Google Docs URL을 입력해주세요!")
    else:
        # 문서 ID 추출
        document_id = extract_document_id(doc_url)
        
        if not document_id:
            st.error("⚠️ 유효한 Google Docs URL이 아닙니다!")
        else:
            # Google 서비스 가져오기
            docs_service = get_google_service()
            
            if docs_service:
                with st.spinner("📖 문서를 읽어오는 중..."):
                    title, content_with_positions = get_document_content(docs_service, document_id)
                
                if content_with_positions:
                    st.success(f"✅ 문서 로드 완료: **{title}**")
                    
                    # 전체 텍스트 추출
                    full_text = '\n'.join([item['text'] for item in content_with_positions])
                    
                    # 내용 미리보기
                    with st.expander("📄 문서 내용 미리보기", expanded=False):
                        st.text(full_text[:1000] + "..." if len(full_text) > 1000 else full_text)
                    
                    # 진행 상황 표시
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # OpenAI 클라이언트 초기화
                    client = OpenAI(api_key=api_key)
                    
                    # 피드백을 저장할 리스트
                    feedbacks = []
                    
                    # 먼저 전체 문서에 대한 종합 평가를 생성
                    status_text.text("🤖 전체 문서 분석 중...")
                    
                    try:
                        # 전체 문서 평가 프롬프트
                        overall_prompt = f"""
                        다음은 {genre}입니다. {genre}의 일반적인 구조적 원리에 따라 평가해주세요.
                        
                        평가 기준:
                        구조: {', '.join(GENRES[genre]['structure'])}
                        초점: {GENRES[genre]['criteria']}
                        
                        {f"추가 지시사항: {custom_instructions}" if custom_instructions else ""}
                        
                        문서 전체 내용:
                        {full_text[:3000]}...
                        
                        위 {genre}에 대해 다음 사항을 포함하여 종합적으로 평가해주세요:
                        1. 장르에 맞는 구조를 갖추었는지
                        2. 각 부분이 적절히 구성되었는지
                        3. 개선이 필요한 부분
                        4. 잘된 점
                        
                        평가는 구체적이고 건설적으로 작성해주세요.
                        """
                        
                        response = client.chat.completions.create(
                            model=model_choice,
                            messages=[{
                                "role": "system",
                                "content": f"당신은 {genre} 평가 전문가입니다. 학생들의 글을 건설적으로 평가해주세요."
                            }, {
                                "role": "user",
                                "content": overall_prompt
                            }],
                            max_tokens=3000,
                            temperature=0.7
                        )
                        
                        overall_feedback = response.choices[0].message.content
                        
                        # 전체 평가를 문서 시작 부분에 추가
                        if content_with_positions:
                            feedbacks.append({
                                'type': '전체 평가',
                                'content': overall_feedback,
                                'insert_at': content_with_positions[0]['start']
                            })
                        
                    except Exception as e:
                        st.warning(f"전체 평가 중 오류: {str(e)}")
                    
                    # 섹션별로 분석 및 피드백 생성
                    total_sections = len(content_with_positions)
                    
                    for idx, section in enumerate(content_with_positions):
                        if len(section['text'].strip()) > 50:  # 의미있는 길이의 텍스트만 분석
                            progress = (idx + 1) / total_sections
                            progress_bar.progress(progress)
                            status_text.text(f"🤖 섹션 {idx + 1}/{total_sections} 분석 중...")
                            
                            try:
                                # 섹션별 평가 프롬프트
                                section_prompt = f"""
                                이것은 {genre}의 일부분입니다.
                                현재 분석 중인 부분이 {genre}의 어느 구조에 해당하는지 파악하고,
                                해당 부분에 맞는 구체적인 피드백을 제공해주세요.
                                
                                {genre}의 구조: {', '.join(GENRES[genre]['structure'])}
                                
                                분석할 내용:
                                {section['text']}
                                
                                위 내용에 대해 2-3문장으로 구체적이고 건설적인 피드백을 작성해주세요.
                                개선 제안을 포함해주세요.
                                """
                                
                                response = client.chat.completions.create(
                                    model=model_choice,
                                    messages=[{
                                        "role": "system",
                                        "content": f"당신은 {genre} 평가 전문가입니다."
                                    }, {
                                        "role": "user",
                                        "content": section_prompt
                                    }],
                                    max_tokens=500,
                                    temperature=0.7
                                )
                                
                                feedback = response.choices[0].message.content
                                
                                # 피드백을 해당 섹션 끝에 추가
                                feedbacks.append({
                                    'type': f'섹션 {idx + 1} 평가',
                                    'content': feedback,
                                    'insert_at': section['end']
                                })
                                
                                # API 호출 제한을 위한 짧은 대기
                                time.sleep(1)
                                
                            except Exception as e:
                                st.warning(f"섹션 {idx + 1} 분석 중 오류: {str(e)}")
                    
                    progress_bar.progress(1.0)
                    status_text.text("✅ 분석 완료! 피드백을 문서에 삽입하는 중...")
                    
                    # 피드백을 문서에 삽입
                    if feedbacks:
                        if insert_feedback_to_doc(docs_service, document_id, feedbacks):
                            st.markdown(f"""
                            <div class='success-box'>
                            <h4>✅ 평가 완료!</h4>
                            <p>총 {len(feedbacks)}개의 평가가 문서에 추가되었습니다.</p>
                            <p>Google Docs에서 파란색 배경의 AI 평가를 확인하세요!</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # 문서 링크 제공
                            st.markdown(f"[📄 Google Docs에서 열기](https://docs.google.com/document/d/{document_id}/edit)")
                            
                            # 평가 결과 미리보기
                            with st.expander("💡 평가 결과 미리보기", expanded=True):
                                for feedback in feedbacks[:3]:  # 처음 3개만 표시
                                    st.markdown(f"**{feedback['type']}:**")
                                    st.info(feedback['content'])
                                if len(feedbacks) > 3:
                                    st.markdown(f"... 그 외 {len(feedbacks) - 3}개의 평가가 더 있습니다.")
                        else:
                            st.warning("⚠️ 피드백을 추가하지 못했습니다. 문서 권한을 확인해주세요.")
                    else:
                        st.warning("⚠️ 생성된 피드백이 없습니다.")
                else:
                    st.error("❌ 문서 내용을 가져올 수 없습니다. 문서 권한을 확인해주세요.")

# 푸터
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888;'>
        <p>Powered by GPT-4o-mini & Google Docs API | 교육 목적으로 제작됨</p>
        <p>피드백은 문서 내에 파란색 배경으로 표시됩니다</p>
    </div>
    """,
    unsafe_allow_html=True
)
