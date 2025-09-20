import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime
import re
import pytz

# 메일 주소 유효성 검사
def validate_emails(email_string):
    if not email_string:
        return []
    
    email_list = [email.strip() for email in email_string.split(",")]  # strip() 추가
    valid_emails = []
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    for email in email_list:
        if email and re.match(pattern, email) is not None:  # 빈 문자열 체크 추가
            valid_emails.append(email)
        else:
            print(f"유효하지 않은 이메일 주소: '{email}'")  # 디버깅용
    
    return valid_emails


# 이메일 전송 함수
def send_automated_email(date, content):
    korea_timezone = pytz.timezone('Asia/Seoul')
    # 메일 정보
    SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
    SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")

    emails_string = os.environ.get("RECEIVER_EMAIL")
    RECEIVER_EMAIL = validate_emails(emails_string)
    print("메일 보낸 사람 수 : ", len(RECEIVER_EMAIL))
    print("유효한 이메일 목록:", RECEIVER_EMAIL)  # 디버깅용

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("오류: 이메일 사용자 이름 또는 비밀번호가 설정되지 않았습니다.")
        return False
    
    if not RECEIVER_EMAIL:
        print("오류: 수신자 이메일 주소가 설정되지 않았습니다.")
        return False
    
    current_time = datetime.now(korea_timezone).strftime("%Y-%m-%d %H:%M:%S")
    email_subject = f"오늘의 페이퍼 요약({current_time}(KST))"
    email_body = f"""
    안녕하세요, {date} 페이퍼입니다.
    {content}
    감사합니다.
    """
    
    msg = MIMEMultipart()
    msg['From'] = Header(SENDER_EMAIL, 'utf-8')
    msg['To'] = Header(', '.join(RECEIVER_EMAIL), 'utf-8')
    msg['Subject'] = Header(email_subject, 'utf-8')
    
    msg.attach(MIMEText(email_body, 'plain', 'utf-8'))
    
    try:
        # SMTP 연결 및 TLS 설정 (핵심!)
        smtp_obj = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        smtp_obj.ehlo()  # 서버와 인사
        smtp_obj.starttls()  # TLS 암호화 시작 - 이 부분이 누락되어 있었음!
        smtp_obj.ehlo()  # TLS 후 다시 인사
        
        # 로그인
        smtp_obj.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        # 메일 전송
        smtp_obj.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        
        smtp_obj.quit()
        print(f"[{current_time}] 이메일 전송 성공: '{email_subject}' to {', '.join(RECEIVER_EMAIL)}")
        return True
    
    except smtplib.SMTPAuthenticationError as e:
        print(f"[{current_time}] 이메일 전송 실패: 인증 오류 - {e}")
        print("확인사항: Gmail 2단계 인증 활성화 + 앱 비밀번호 사용")
        return False
    
    except smtplib.SMTPConnectError as e:
        print(f"[{current_time}] 이메일 전송 실패: SMTP 서버 연결 오류 - {e}")
        return False
    
    except Exception as e:
        print(f"[{current_time}] 이메일 전송 중 알 수 없는 오류 발생: {e}")
        print(f"사용된 이메일 목록: {RECEIVER_EMAIL}")
        return False