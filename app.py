import streamlit as st
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

def debug_comment_creation():
    """댓글 생성 문제를 단계별로 디버깅"""
    
    st.markdown("### 🔍 댓글 추가 디버깅")
    
    # 테스트할 문서 ID
    doc_id = "19EZcsfkxY0awvZGAkRtv3fZyknxOUb_qr9mNm2-uSVo"
    
    try:
        # 1. 인증 정보 확인
        service_account_info = st.secrets["google_service_account"]
        scopes = [
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file'
        ]
        
        credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
        drive_service = build('drive', 'v3', credentials=credentials)
        
        st.success("✅ 인증 및 서비스 빌드 성공")
        
        # 2. 파일 권한 확인
        st.markdown("#### 📋 파일 권한 확인")
        
        try:
            file_info = drive_service.files().get(
                fileId=doc_id,
                fields="name,permissions,capabilities"
            ).execute()
            
            st.success(f"✅ 파일 접근 성공: {file_info.get('name')}")
            
            # 권한 정보 표시
            permissions = file_info.get('permissions', [])
            capabilities = file_info.get('capabilities', {})
            
            st.info(f"📊 권한 수: {len(permissions)}개")
            st.info(f"💬 댓글 가능: {capabilities.get('canComment', False)}")
            st.info(f"✏️ 편집 가능: {capabilities.get('canEdit', False)}")
            
            # 권한 상세 정보
            with st.expander("권한 상세 정보"):
                for i, perm in enumerate(permissions):
                    st.write(f"권한 {i+1}: {perm.get('type')} - {perm.get('role')}")
            
        except Exception as e:
            st.error(f"❌ 파일 접근 실패: {str(e)}")
            return False
        
        # 3. 기존 댓글 확인
        st.markdown("#### 💬 기존 댓글 확인")
        
        try:
            comments = drive_service.comments().list(
                fileId=doc_id,
                fields="*"
            ).execute()
            
            existing_comments = comments.get('comments', [])
            st.info(f"📝 기존 댓글 수: {len(existing_comments)}개")
            
            # 기존 댓글 표시
            if existing_comments:
                with st.expander("기존 댓글 목록"):
                    for comment in existing_comments[-5:]:  # 최근 5개만
                        st.write(f"작성자: {comment.get('author', {}).get('displayName', 'Unknown')}")
                        st.write(f"내용: {comment.get('content', '')[:100]}...")
                        st.write(f"작성일: {comment.get('createdTime', '')}")
                        st.write("---")
            
        except Exception as e:
            st.error(f"❌ 기존 댓글 조회 실패: {str(e)}")
        
        # 4. 테스트 댓글 추가
        st.markdown("#### 🧪 테스트 댓글 추가")
        
        if st.button("💬 테스트 댓글 추가하기"):
            try:
                test_comment = {
                    'content': f'🤖 테스트 댓글입니다. ({st.session_state.get("test_count", 0) + 1}번째 시도)\n\n이 댓글이 보인다면 API가 정상 작동하는 것입니다.\n\n완도고등학교 AI 피드백 시스템'
                }
                
                result = drive_service.comments().create(
                    fileId=doc_id,
                    body=test_comment,
                    fields="*"
                ).execute()
                
                st.success("✅ 테스트 댓글 추가 성공!")
                st.json(result)
                
                # 카운터 증가
                st.session_state["test_count"] = st.session_state.get("test_count", 0) + 1
                
                st.info("🔄 구글 문서를 새로고침하여 댓글을 확인하세요.")
                
            except Exception as e:
                st.error(f"❌ 테스트 댓글 추가 실패: {str(e)}")
                
                # 상세 오류 분석
                error_str = str(e)
                if "permission" in error_str.lower():
                    st.error("🔍 권한 문제입니다. 서비스 계정에 댓글 작성 권한이 없습니다.")
                    st.markdown("""
                    **해결 방법:**
                    1. 구글 문서 공유 설정을 "편집자" 권한으로 변경하세요
                    2. 또는 서비스 계정 이메일을 직접 공유하세요: `feedback-bot@report-ai-461907.iam.gserviceaccount.com`
                    """)
                elif "not found" in error_str.lower():
                    st.error("🔍 문서를 찾을 수 없습니다.")
                elif "fields" in error_str.lower():
                    st.error("🔍 API 파라미터 문제입니다.")
                else:
                    st.error(f"🔍 알 수 없는 오류: {error_str}")
        
        # 5. 권한 문제 해결 방법 제시
        st.markdown("#### 🛠️ 권한 문제 해결 방법")
        
        service_account_email = "feedback-bot@report-ai-461907.iam.gserviceaccount.com"
        
        st.markdown(f"""
        **방법 1: 공유 설정 변경**
        1. 구글 문서에서 '공유' 버튼 클릭
        2. "링크가 있는 모든 사용자" → **"편집자"** 권한으로 변경
        3. (현재는 "댓글 작성자"로 되어 있을 가능성)
        
        **방법 2: 서비스 계정 직접 공유**
        1. 구글 문서에서 '공유' 버튼 클릭
        2. 다음 이메일 추가: `{service_account_email}`
        3. 권한을 "편집자"로 설정
        
        **방법 3: 소유자 권한 확인**
        - 현재 문서 소유자만 댓글 권한을 제어할 수 있습니다
        - 학생이 문서 소유자인지 확인하세요
        """)
        
        return True
        
    except Exception as e:
        st.error(f"❌ 전체 디버깅 실패: {str(e)}")
        return False

def check_current_permissions():
    """현재 권한 상태 확인"""
    st.markdown("### 🔐 현재 권한 상태")
    
    doc_id = "19EZcsfkxY0awvZGAkRtv3fZyknxOUb_qr9mNm2-uSVo"
    
    try:
        service_account_info = st.secrets["google_service_account"]
        scopes = [
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # 파일 정보 가져오기
        file_info = drive_service.files().get(
            fileId=doc_id,
            fields="name,permissions,capabilities,owners"
        ).execute()
        
        st.success(f"📄 문서: {file_info.get('name')}")
        
        # 소유자 정보
        owners = file_info.get('owners', [])
        if owners:
            st.info(f"👤 소유자: {owners[0].get('displayName')} ({owners[0].get('emailAddress')})")
        
        # 현재 권한
        capabilities = file_info.get('capabilities', {})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            can_comment = capabilities.get('canComment', False)
            st.metric("💬 댓글 가능", "✅ 예" if can_comment else "❌ 아니오")
        
        with col2:
            can_edit = capabilities.get('canEdit', False)
            st.metric("✏️ 편집 가능", "✅ 예" if can_edit else "❌ 아니오")
        
        with col3:
            can_share = capabilities.get('canShare', False)
            st.metric("🔗 공유 가능", "✅ 예" if can_share else "❌ 아니오")
        
        # 권한 목록
        permissions = file_info.get('permissions', [])
        
        st.markdown("#### 📋 권한 목록")
        for perm in permissions:
            perm_type = perm.get('type', 'unknown')
            role = perm.get('role', 'unknown')
            
            if perm_type == 'anyone':
                st.info(f"🌐 {perm_type}: {role}")
            elif perm_type == 'user':
                email = perm.get('emailAddress', 'unknown')
                st.info(f"👤 {email}: {role}")
            else:
                st.info(f"🔧 {perm_type}: {role}")
        
        return True
        
    except Exception as e:
        st.error(f"❌ 권한 확인 실패: {str(e)}")
        return False

# 메인 디버깅 함수
def main_comment_debug():
    st.title("🔧 댓글 추가 문제 진단")
    
    st.markdown("""
    현재 문서에 댓글이 추가되지 않는 문제를 진단합니다.
    """)
    
    # 현재 권한 상태 확인
    check_current_permissions()
    
    st.markdown("---")
    
    # 상세 디버깅
    debug_comment_creation()

if __name__ == "__main__":
    main_comment_debug()
