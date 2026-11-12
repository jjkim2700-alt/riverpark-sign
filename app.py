import os
import sys
import json
import base64
import time
import socket
import datetime
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import fitz  # PyMuPDF

PORT = int(os.environ.get('PORT', 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'signatures.json')
PDF_OUTPUT_PATH = os.path.join(BASE_DIR, '청주리버파크자이_입대의회의록_전자서명완료본.pdf')

# Font: Prefer bundled NanumGothic.ttf (cross-platform Linux/Render/Windows), fallback to Windows Malgun
FONT_PATH = os.path.join(BASE_DIR, 'NanumGothic.ttf')
if not os.path.exists(FONT_PATH):
    FONT_PATH = 'C:/Windows/Fonts/malgun.ttf'
    if not os.path.exists(FONT_PATH):
        FONT_PATH = 'C:/Windows/Fonts/malgunbd.ttf'

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

LOCAL_IP = get_local_ip()

INITIAL_STATE = {
    "admin_password": "1234",
    "server_url": f"http://{LOCAL_IP}:{PORT}",
    "meeting": {
        "title": "청주리버파크자이 제4기 제1차 비상 입주자대표회의",
        "date": "2026년 11월 20일 (금) 19:30",
        "place": "온라인 화상회의 (Zoom) 및 방재실 병행",
        "chair": "진상호 (회장 직무대행)",
        "attendees_desc": "총 재적 10명 중 10명 출석 (성원 보고 및 의결정족수 충족)",
        "agenda": [
            {
                "num": 1,
                "title": "2027년도 공동주택 관리비 예산안 심의의 건",
                "desc": "일반관리비 및 각 항목별 예산 적정성 검토 완료. 헬스장 등 주민공동시설 운영 개선 반영.",
                "result": "원안 가결 (찬성 10, 반대 0)"
            },
            {
                "num": 2,
                "title": "제8차 관리규약 전면 개정안 발의 및 주민동의 추진의 건",
                "desc": "선관위 권한남용 방지, 동대표 온라인 화상회의 및 모바일 전자서명 허용, 헬스장 주민체육시설 공간 혁신 조항 반영.",
                "result": "원안 가결 (찬성 10, 반대 0)"
            },
            {
                "num": 3,
                "title": "위탁관리업체(㈜일택) 계약위반 해지 통보 및 손해배상 청구의 건",
                "desc": "관리소장 인선 불이행, 감사 방해, 업무 해태에 따른 중대 계약위반으로 계약 해지 통보 및 58.5억 부당집행 손배 청구.",
                "result": "원안 가결 (찬성 10, 반대 0)"
            },
            {
                "num": 4,
                "title": "하자소송 대리인(법무법인 황해) 해임 및 법무법인 충정 선임의 건",
                "desc": "황해의 소송지연 및 수수료 8% 과다 청구 해소. 대형로펌 충정(성공보수 4.5%, 1심 종결약정)으로 교체 위임 체결.",
                "result": "원안 가결 (찬성 10, 반대 0)"
            }
        ]
    },
    "reps": [
        {"id": "rep_101", "dong": "101동", "name": "진상호", "role": "회장 직무대행", "phone": "010-1234-5678", "pin": None, "signed": False, "sign_time": None, "ip": None, "signature": None},
        {"id": "rep_102", "dong": "102동", "name": "김철수", "role": "동대표", "phone": "010-2345-6789", "pin": None, "signed": False, "sign_time": None, "ip": None, "signature": None},
        {"id": "rep_103", "dong": "103동", "name": "이영희", "role": "동대표", "phone": "010-3456-7890", "pin": None, "signed": False, "sign_time": None, "ip": None, "signature": None},
        {"id": "rep_104", "dong": "104동", "name": "박민우", "role": "동대표", "phone": "010-4567-8901", "pin": None, "signed": False, "sign_time": None, "ip": None, "signature": None},
        {"id": "rep_105", "dong": "105동", "name": "정수진", "role": "동대표", "phone": "010-5678-9012", "pin": None, "signed": False, "sign_time": None, "ip": None, "signature": None},
        {"id": "rep_106", "dong": "106동", "name": "최동훈", "role": "동대표", "phone": "010-6789-0123", "pin": None, "signed": False, "sign_time": None, "ip": None, "signature": None},
        {"id": "rep_107", "dong": "107동", "name": "강태양", "role": "동대표", "phone": "010-7890-1234", "pin": None, "signed": False, "sign_time": None, "ip": None, "signature": None},
        {"id": "rep_108", "dong": "108동", "name": "조하나", "role": "동대표", "phone": "010-8901-2345", "pin": None, "signed": False, "sign_time": None, "ip": None, "signature": None},
        {"id": "rep_aud1", "dong": "감사1", "name": "김재중", "role": "입주민 감사", "phone": "010-9012-3456", "pin": None, "signed": False, "sign_time": None, "ip": None, "signature": None},
        {"id": "rep_aud2", "dong": "감사2", "name": "김윤숙", "role": "입주민 감사", "phone": "010-0123-4567", "pin": None, "signed": False, "sign_time": None, "ip": None, "signature": None}
    ]
}

def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(INITIAL_STATE)
        return INITIAL_STATE
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "server_url" not in data:
                data["server_url"] = f"http://{LOCAL_IP}:{PORT}"
            if "admin_password" not in data:
                data["admin_password"] = "1234"
            return data
    except Exception:
        return INITIAL_STATE

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_signed_pdf():
    data = load_data()
    meeting = data["meeting"]
    reps = data["reps"]
    
    doc = fitz.open()
    
    # Page 1: 회의록 본문
    p1 = doc.new_page(width=595, height=842)
    p1.insert_font(fontname='malgun', fontfile=FONT_PATH)
    p1.draw_rect(fitz.Rect(35, 35, 560, 807), color=(0.1, 0.2, 0.4), width=1.5)
    
    p1.insert_text((70, 75), "청주리버파크자이 입주자대표회의 회의록", fontname='malgun', fontsize=18, color=(0.08, 0.15, 0.35))
    p1.draw_line(fitz.Point(70, 88), fitz.Point(525, 88), color=(0.1, 0.2, 0.4), width=1)
    
    y = 115
    info_items = [
        ("회 의 명 :", meeting["title"]),
        ("회의일시 :", meeting["date"]),
        ("회의장소 :", meeting["place"]),
        ("의    장 :", meeting.get("chair", "회장 직무대행")),
        ("출석현황 :", meeting.get("attendees_desc", f"총 재적 {len(reps)}명 중 {len([r for r in reps if r.get('signed')])}명 서명 완료"))
    ]
    for label, val in info_items:
        p1.insert_text((70, y), label, fontname='malgun', fontsize=10.5, color=(0.3, 0.3, 0.3))
        p1.insert_text((140, y), val, fontname='malgun', fontsize=10.5, color=(0.1, 0.1, 0.1))
        y += 22
        
    y += 8
    p1.draw_rect(fitz.Rect(70, y, 525, y+24), color=(0.9, 0.92, 0.96), fill=(0.93, 0.95, 0.98))
    p1.insert_text((80, y+16), "【 심의 및 의결 안건 총괄표 】", fontname='malgun', fontsize=10.5, color=(0.1, 0.2, 0.5))
    y += 32
    
    for item in meeting["agenda"]:
        p1.insert_text((70, y), f"제 {item['num']} 호", fontname='malgun', fontsize=10.5, color=(0.1, 0.3, 0.6))
        p1.insert_text((120, y), item["title"], fontname='malgun', fontsize=10.5, color=(0.1, 0.1, 0.1))
        y += 16
        if item.get("desc"):
            desc_rect = fitz.Rect(120, y, 520, y + 28)
            p1.insert_textbox(desc_rect, f"• 내용: {item['desc']}", fontname='malgun', fontsize=8.5, color=(0.35, 0.35, 0.35))
            y += 26
        p1.insert_text((120, y), f"▶ 의결결과 : {item['result']}", fontname='malgun', fontsize=9.5, color=(0.1, 0.5, 0.2))
        p1.draw_line(fitz.Point(70, y+10), fitz.Point(525, y+10), color=(0.88, 0.88, 0.88), width=0.5)
        y += 22

    y += 10
    notice_text = "위 안건에 관하여 공동주택관리법령 및 관리규약에 따라 적법하게 회의를 진행하고,\n" \
                  "출석 동별 대표자 및 감사의 동의를 받아 아래와 같이 모바일 전자서명으로 날인함."
    for line in notice_text.splitlines():
        p1.insert_text((70, y), line, fontname='malgun', fontsize=9, color=(0.4, 0.4, 0.4))
        y += 15
        
    reps_per_page = 10
    num_sig_pages = max(1, (len(reps) + reps_per_page - 1) // reps_per_page)
    
    for page_idx in range(num_sig_pages):
        page_reps = reps[page_idx * reps_per_page : (page_idx + 1) * reps_per_page]
        
        p = doc.new_page(width=595, height=842)
        p.insert_font(fontname='malgun', fontfile=FONT_PATH)
        p.draw_rect(fitz.Rect(35, 35, 560, 807), color=(0.1, 0.2, 0.4), width=1.5)
        
        page_title = "【 출석 임원 및 동별 대표자 전자서명 날인표 】"
        if num_sig_pages > 1:
            page_title += f" ({page_idx + 1}/{num_sig_pages})"
        p.insert_text((70, 75), page_title, fontname='malgun', fontsize=15, color=(0.08, 0.15, 0.35))
        p.insert_text((70, 95), "※ 본 서명은 전자서명법 제3조에 의거하여 자필 서명과 동일한 법적 효력을 갖습니다.", fontname='malgun', fontsize=9, color=(0.5, 0.5, 0.5))
        p.draw_line(fitz.Point(70, 105), fitz.Point(525, 105), color=(0.1, 0.2, 0.4), width=1)
        
        grid_start_y = 120
        box_w = 215
        box_h = 115
        
        for i, rep in enumerate(page_reps):
            col = i % 2
            row = i // 2
            x0 = 70 + col * (box_w + 25)
            y0 = grid_start_y + row * (box_h + 15)
            
            p.draw_rect(fitz.Rect(x0, y0, x0 + box_w, y0 + box_h), color=(0.8, 0.82, 0.88), width=1)
            p.draw_rect(fitz.Rect(x0, y0, x0 + box_w, y0 + 26), color=(0.92, 0.94, 0.98), fill=(0.92, 0.94, 0.98))
            header_text = f"[{rep['dong']}] {rep.get('role','동대표')}  {rep['name']}"
            p.insert_text((x0 + 10, y0 + 17), header_text, fontname='malgun', fontsize=10, color=(0.1, 0.2, 0.4))
            
            if rep.get("signed") and rep.get("signature"):
                try:
                    sig_data = rep["signature"]
                    if ',' in sig_data:
                        sig_data = sig_data.split(',')[1]
                    sig_bytes = base64.b64decode(sig_data)
                    
                    sig_rect = fitz.Rect(x0 + 35, y0 + 32, x0 + box_w - 35, y0 + box_h - 22)
                    p.insert_image(sig_rect, stream=sig_bytes)
                    
                    st = rep.get("sign_time", "")
                    p.insert_text((x0 + 10, y0 + box_h - 8), f"서명시각: {st}", fontname='malgun', fontsize=7.5, color=(0.2, 0.5, 0.2))
                except Exception as e:
                    p.insert_text((x0 + 20, y0 + 60), f"서명 오류: {e}", fontname='malgun', fontsize=8, color=(0.8, 0.2, 0.2))
            else:
                p.insert_text((x0 + 65, y0 + 65), "( 서명 대기 )", fontname='malgun', fontsize=11, color=(0.6, 0.6, 0.6))
                
    # Audit Trail Page
    p_audit = doc.new_page(width=595, height=842)
    p_audit.insert_font(fontname='malgun', fontfile=FONT_PATH)
    p_audit.draw_rect(fitz.Rect(35, 35, 560, 807), color=(0.1, 0.2, 0.4), width=1.5)
    
    p_audit.insert_text((70, 75), "【 전자서명 감사 추적 증적서 (Audit Trail) 】", fontname='malgun', fontsize=15, color=(0.08, 0.15, 0.35))
    p_audit.insert_text((70, 95), "본 문서는 위·변조 방지 및 법적 증빙을 위해 각 서명자의 전자 접속 기록을 영구 보관합니다.", fontname='malgun', fontsize=9, color=(0.5, 0.5, 0.5))
    p_audit.draw_line(fitz.Point(70, 105), fitz.Point(525, 105), color=(0.1, 0.2, 0.4), width=1)
    
    ty = 125
    p_audit.draw_rect(fitz.Rect(70, ty, 525, ty + 24), color=(0.9, 0.9, 0.9), fill=(0.9, 0.93, 0.97))
    p_audit.insert_text((78, ty + 16), "구분", fontname='malgun', fontsize=9, color=(0.1, 0.2, 0.4))
    p_audit.insert_text((130, ty + 16), "성명", fontname='malgun', fontsize=9, color=(0.1, 0.2, 0.4))
    p_audit.insert_text((180, ty + 16), "상태", fontname='malgun', fontsize=9, color=(0.1, 0.2, 0.4))
    p_audit.insert_text((230, ty + 16), "서명 일시 (타임스탬프)", fontname='malgun', fontsize=9, color=(0.1, 0.2, 0.4))
    p_audit.insert_text((375, ty + 16), "접속 IP / 단말 식별", fontname='malgun', fontsize=9, color=(0.1, 0.2, 0.4))
    ty += 24
    
    for rep in reps:
        ty += 20
        status_str = "완료 (인증됨)" if rep.get("signed") else "미서명"
        color = (0.1, 0.5, 0.2) if rep.get("signed") else (0.6, 0.6, 0.6)
        
        p_audit.insert_text((78, ty), rep["dong"], fontname='malgun', fontsize=8.5, color=(0.2, 0.2, 0.2))
        p_audit.insert_text((130, ty), rep["name"], fontname='malgun', fontsize=8.5, color=(0.2, 0.2, 0.2))
        p_audit.insert_text((180, ty), status_str, fontname='malgun', fontsize=8.5, color=color)
        p_audit.insert_text((230, ty), rep.get("sign_time") or "-", fontname='malgun', fontsize=8.5, color=(0.2, 0.2, 0.2))
        p_audit.insert_text((375, ty), rep.get("ip") or "-", fontname='malgun', fontsize=8.5, color=(0.3, 0.3, 0.3))
        p_audit.draw_line(fitz.Point(70, ty + 4), fitz.Point(525, ty + 4), color=(0.9, 0.9, 0.9), width=0.5)

    ty += 40
    p_audit.draw_rect(fitz.Rect(70, ty, 525, ty + 80), color=(0.85, 0.85, 0.9), fill=(0.97, 0.98, 1.0))
    p_audit.insert_text((85, ty + 22), "■ 법적 효력 고지 (Legal Notice)", fontname='malgun', fontsize=10, color=(0.1, 0.2, 0.5))
    p_audit.insert_text((85, ty + 42), "1. 본 문서는 전자서명법 제3조 및 전자문서 및 전자거래 기본법 제4조에 의거 효력이 보장됩니다.", fontname='malgun', fontsize=8.5, color=(0.3, 0.3, 0.3))
    p_audit.insert_text((85, ty + 58), "2. 서명자의 본인 PIN 인증 내역 및 접속 타임스탬프는 위·변조가 불가능하도록 시스템 로그에 영구 보관됩니다.", fontname='malgun', fontsize=8.5, color=(0.3, 0.3, 0.3))

    try:
        doc.subset_fonts()
    except Exception:
        pass
    doc.save(PDF_OUTPUT_PATH, garbage=4, deflate=True)
    doc.close()
    return PDF_OUTPUT_PATH

# ----------------- HTTP Server Handler -----------------

class RequestHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Password')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def check_admin_auth(self, req_json):
        # Admin auth check via header or request payload
        pw_header = self.headers.get('X-Admin-Password')
        pw_body = req_json.get('admin_password') if req_json else None
        data = load_data()
        correct_pw = data.get("admin_password", "1234")
        return (pw_header == correct_pw) or (pw_body == correct_pw)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        # User / Dong Rep Mobile View (Default)
        if path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(USER_HTML_TEMPLATE.encode('utf-8'))
            
        elif path == '/signature_pad.min.js':
            sig_file = os.path.join(BASE_DIR, 'signature_pad.min.js')
            with open(sig_file, 'rb') as f:
                js_bytes = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/javascript; charset=utf-8')
            self.end_headers()
            self.wfile.write(js_bytes)

        # Admin Dashboard View (Dedicated Admin Page)
        elif path == '/admin' or path == '/admin.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(ADMIN_HTML_TEMPLATE.encode('utf-8'))

        # Public API for Signers (No admin sensitive data)
        elif path == '/api/public-data':
            data = load_data()
            public_info = {
                "meeting": data["meeting"],
                "reps": [
                    {
                        "id": r["id"],
                        "dong": r["dong"],
                        "name": r["name"],
                        "role": r.get("role", "동대표"),
                        "has_pin": bool(r.get("pin")),
                        "signed": r["signed"],
                        "sign_time": r.get("sign_time")
                    }
                    for r in data["reps"]
                ]
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(public_info, ensure_ascii=False).encode('utf-8'))

        # Admin API for Dashboard
        elif path == '/api/admin-data':
            if not self.check_admin_auth({}):
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'error': '관리자 인증이 필요합니다.'}).encode('utf-8'))
                return
            
            data = load_data()
            admin_info = {
                "server_ip": LOCAL_IP,
                "server_port": PORT,
                "server_url": data.get("server_url", f"http://{LOCAL_IP}:{PORT}"),
                "meeting": data["meeting"],
                "reps": [
                    {
                        "id": r["id"],
                        "dong": r["dong"],
                        "name": r["name"],
                        "role": r.get("role", "동대표"),
                        "phone": r.get("phone", ""),
                        "has_pin": bool(r.get("pin")),
                        "signed": r["signed"],
                        "sign_time": r.get("sign_time"),
                        "ip": r.get("ip")
                    }
                    for r in data["reps"]
                ]
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(admin_info, ensure_ascii=False).encode('utf-8'))
            
        elif path == '/api/download-pdf':
            pdf_file = generate_signed_pdf()
            with open(pdf_file, 'rb') as f:
                pdf_bytes = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', 'attachment; filename="meeting_minutes_signed.pdf"')
            self.end_headers()
            self.wfile.write(pdf_bytes)
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len).decode('utf-8')
        req = json.loads(body) if body else {}

        # Public: Set PIN for rep
        if parsed.path == '/api/set-pin':
            rep_id = req.get('rep_id')
            new_pin = req.get('new_pin')
            old_pin = req.get('old_pin')
            
            if not new_pin or len(new_pin) < 4:
                self.send_json_error('비밀번호는 최소 4자리 이상이어야 합니다.')
                return

            data = load_data()
            found = False
            for rep in data['reps']:
                if rep['id'] == rep_id:
                    if rep.get('pin') and rep['pin'] != old_pin:
                        self.send_json_error('기존 비밀번호가 일치하지 않습니다.')
                        return
                    rep['pin'] = str(new_pin)
                    found = True
                    break
            
            if found:
                save_data(data)
                self.send_json_success({'message': '개인 PIN 번호가 성공적으로 설정되었습니다.'})
            else:
                self.send_json_error('해당 동대표를 찾을 수 없습니다.')

        # Public: Sign by rep
        elif parsed.path == '/api/sign':
            rep_id = req.get('rep_id')
            signature = req.get('signature')
            pin = req.get('pin')
            
            data = load_data()
            found = False
            for rep in data['reps']:
                if rep['id'] == rep_id:
                    if not rep.get('pin'):
                        self.send_json_error('먼저 본인만의 개인 PIN 번호를 설정해주세요.')
                        return
                    if str(rep['pin']) != str(pin):
                        self.send_json_error('PIN 번호가 일치하지 않습니다. 본인이 설정한 번호를 입력하세요.')
                        return
                    
                    rep['signed'] = True
                    rep['sign_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    rep['ip'] = self.client_address[0]
                    rep['signature'] = signature
                    found = True
                    break
            
            if found:
                save_data(data)
                generate_signed_pdf()
                self.send_json_success({'message': '전자서명이 성공적으로 등록되었습니다.'})
            else:
                self.send_json_error('해당 동대표를 찾을 수 없습니다.')

        # Admin Auth verification
        elif parsed.path == '/api/admin-login':
            pw = req.get('password')
            data = load_data()
            if pw == data.get("admin_password", "1234"):
                self.send_json_success({'message': '관리자 로그인 성공'})
            else:
                self.send_json_error('관리자 비밀번호가 일치하지 않습니다.')

        # Below are protected Admin actions
        elif parsed.path in ['/api/save-meeting', '/api/save-reps', '/api/reset-rep-pin', '/api/reset-rep-sign', '/api/set-server-url', '/api/change-admin-pw', '/api/reset']:
            if not self.check_admin_auth(req):
                self.send_json_error('관리자 권한이 없습니다. (비밀번호 불일치)')
                return

            if parsed.path == '/api/save-meeting':
                new_meeting = req.get('meeting')
                if not new_meeting:
                    self.send_json_error('회의록 데이터가 올바르지 않습니다.')
                    return
                data = load_data()
                data['meeting'] = new_meeting
                save_data(data)
                generate_signed_pdf()
                self.send_json_success({'message': '회의록 내용이 성공적으로 저장 및 반영되었습니다.'})

            elif parsed.path == '/api/save-reps':
                new_reps_list = req.get('reps')
                data = load_data()
                existing_reps_map = {r['id']: r for r in data['reps']}
                
                merged_reps = []
                for i, r in enumerate(new_reps_list):
                    rid = r.get('id')
                    if not rid or rid.startswith('new_'):
                        rid = f"rep_{int(time.time()*1000)}_{i}"
                    
                    old_rep = existing_reps_map.get(rid, {})
                    merged_reps.append({
                        "id": rid,
                        "dong": r.get('dong', '').strip() or f"제{i+1}동",
                        "name": r.get('name', '').strip() or f"동대표{i+1}",
                        "role": r.get('role', '').strip() or "동대표",
                        "phone": r.get('phone', '').strip(),
                        "pin": old_rep.get('pin', None),
                        "signed": old_rep.get('signed', False),
                        "sign_time": old_rep.get('sign_time', None),
                        "ip": old_rep.get('ip', None),
                        "signature": old_rep.get('signature', None)
                    })
                
                data['reps'] = merged_reps
                save_data(data)
                generate_signed_pdf()
                self.send_json_success({'message': '동대표 명단이 성공적으로 저장되었습니다!'})

            elif parsed.path == '/api/reset-rep-pin':
                rep_id = req.get('rep_id')
                data = load_data()
                for r in data['reps']:
                    if r['id'] == rep_id:
                        r['pin'] = None
                        save_data(data)
                        self.send_json_success({'message': f"{r['name']} 동대표의 PIN 번호가 초기화되었습니다."})
                        return
                self.send_json_error('해당 동대표를 찾을 수 없습니다.')

            elif parsed.path == '/api/reset-rep-sign':
                rep_id = req.get('rep_id')
                data = load_data()
                for r in data['reps']:
                    if r['id'] == rep_id:
                        r['signed'] = False
                        r['signature'] = None
                        r['sign_time'] = None
                        r['ip'] = None
                        save_data(data)
                        generate_signed_pdf()
                        self.send_json_success({'message': f"{r['name']} 동대표의 서명이 취소되었습니다."})
                        return
                self.send_json_error('해당 동대표를 찾을 수 없습니다.')

            elif parsed.path == '/api/set-server-url':
                new_url = req.get('server_url', '').strip()
                if new_url:
                    data = load_data()
                    data['server_url'] = new_url
                    save_data(data)
                    self.send_json_success({'message': '서비스 접속 주소가 설정되었습니다.'})
                else:
                    self.send_json_error('올바른 URL을 입력해주세요.')

            elif parsed.path == '/api/change-admin-pw':
                new_pw = req.get('new_password', '').strip()
                if len(new_pw) < 4:
                    self.send_json_error('관리자 비밀번호는 4자리 이상이어야 합니다.')
                    return
                data = load_data()
                data['admin_password'] = new_pw
                save_data(data)
                self.send_json_success({'message': '관리자 마스터 비밀번호가 성공적으로 변경되었습니다.'})

            elif parsed.path == '/api/reset':
                save_data(INITIAL_STATE)
                if os.path.exists(PDF_OUTPUT_PATH):
                    os.remove(PDF_OUTPUT_PATH)
                self.send_json_success({'message': '전체 데이터가 초기화되었습니다.'})
        else:
            self.send_error(404)

    def send_json_success(self, data_dict):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data_dict, ensure_ascii=False).encode('utf-8'))

    def send_json_error(self, message):
        self.send_response(400)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}, ensure_ascii=False).encode('utf-8'))

# =====================================================================
# 1. USER VIEW (동대표 모바일 전용 서명 화면 - 수정권한 0%, 오직 서명만 가능)
# =====================================================================
USER_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>청주리버파크자이 입대의 모바일 전자서명</title>
<script src="/signature_pad.min.js"></script>
<style>
  :root {
    --primary: #0F3875;
    --primary-light: #1E58A8;
    --bg: #F4F6F9;
    --card: #FFFFFF;
    --text: #2C3E50;
    --border: #E1E8EE;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Malgun Gothic", "맑은 고딕", sans-serif; }
  body { background-color: var(--bg); color: var(--text); padding-bottom: 50px; }
  
  header {
    background: linear-gradient(135deg, var(--primary), var(--primary-light));
    color: white; padding: 14px 20px; box-shadow: 0 4px 12px rgba(15,56,117,0.15);
    text-align: center;
  }
  .brand-title { font-size: 1.15rem; font-weight: 700; letter-spacing: -0.5px; }
  .brand-sub { font-size: 0.78rem; opacity: 0.85; margin-top: 2px; }
  
  .container { max-width: 520px; margin: 16px auto; padding: 0 16px; }
  
  .card {
    background: var(--card); border-radius: 14px; padding: 18px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 16px; border: 1px solid var(--border);
  }
  .card-title {
    font-size: 1.02rem; font-weight: 700; color: var(--primary);
    margin-bottom: 12px; border-bottom: 2px solid #EDF2F7; padding-bottom: 8px;
  }
  
  .agenda-list { list-style: none; }
  .agenda-item {
    padding: 10px 12px; border-radius: 8px; background: #F8FAFC;
    margin-bottom: 8px; border-left: 4px solid var(--primary); font-size: 0.88rem;
  }
  .agenda-desc { font-size: 0.8rem; color: #475569; margin: 3px 0; }
  .agenda-res { font-size: 0.82rem; color: #059669; font-weight: 700; }
  
  .form-group { margin-bottom: 12px; }
  .form-label { display: block; font-size: 0.85rem; font-weight: 700; color: #334155; margin-bottom: 4px; }
  .form-input {
    width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #CBD5E1; font-size: 0.95rem;
  }
  
  .canvas-container {
    border: 2px dashed #94A3B8; border-radius: 12px; background: white;
    position: relative; margin: 14px 0; touch-action: none; user-select: none; -webkit-user-select: none;
  }
  canvas {
    width: 100%; height: 200px; display: block; cursor: crosshair;
    touch-action: none; -webkit-user-select: none; user-select: none;
  }
  .canvas-hint {
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
    font-size: 0.9rem; color: #94A3B8; pointer-events: none; user-select: none;
  }
  
  .sig-actions { display: flex; gap: 8px; margin-bottom: 10px; }
  .btn-clear {
    flex: 1; padding: 12px; border: 1px solid #CBD5E1; background: #F1F5F9;
    border-radius: 8px; font-weight: 600; font-size: 0.85rem; cursor: pointer;
  }
  .btn-submit {
    flex: 2; padding: 12px; border: none; background: #10B981; color: white;
    border-radius: 8px; font-weight: 700; font-size: 1rem; cursor: pointer;
    box-shadow: 0 4px 10px rgba(16,185,129,0.3);
  }
  
  footer {
    text-align: center; margin-top: 30px; font-size: 0.75rem; color: #94A3B8;
  }
  footer a { color: #94A3B8; text-decoration: none; }
</style>
</head>
<body>

<header>
  <div class="brand-title">청주리버파크자이 모바일 전자서명</div>
  <div class="brand-sub">입주자대표회의 회의록 모바일 날인</div>
</header>

<div class="container">
  <!-- 1. Meeting Agenda View (Read-Only) -->
  <div class="card">
    <div class="card-title">📌 심의 및 의결 안건 확인</div>
    <div style="font-size: 0.85rem; line-height: 1.5; margin-bottom: 10px; color:#475569;">
      <div><strong>회의명 :</strong> <span id="m-title">로딩 중...</span></div>
      <div><strong>일시/장소 :</strong> <span id="m-date"></span> / <span id="m-place"></span></div>
    </div>
    <ul class="agenda-list" id="agenda-ul"></ul>
  </div>

  <!-- 2. Signer Verification & Signature Card -->
  <div class="card">
    <div class="card-title" style="display:flex; justify-content:space-between; align-items:center;">
      <span>✍️ 동대표 본인 확인 및 서명</span>
      <span id="pin-badge" style="font-size:0.75rem; padding:3px 8px; border-radius:6px; background:#FEF3C7; color:#D97706;">PIN 미설정</span>
    </div>

    <!-- Signer Selection (Auto-locked if accessed with ?rep=...) -->
    <div class="form-group" id="signer-group">
      <label class="form-label">본인 확인 (동대표 선택):</label>
      <select id="signer-select" class="form-input" onchange="onSignerChange()"></select>
    </div>
    
    <div id="signer-locked-card" style="display:none; background:#EFF6FF; border:1px solid #BFDBFE; padding:12px; border-radius:8px; margin-bottom:12px;">
      <div style="font-size:0.75rem; color:#1D4ED8; font-weight:700;">본인 확인 완료</div>
      <div style="font-size:1.05rem; font-weight:700; color:#1E3A8A; margin-top:2px;" id="signer-locked-name"></div>
    </div>

    <!-- PIN Setup for First-time user -->
    <div id="pin-setup-box" style="display:none; background:#FFFBEB; border:1px solid #FCD34D; padding:12px; border-radius:8px; margin-bottom:12px;">
      <div style="font-weight:700; font-size:0.85rem; color:#B45309; margin-bottom:4px;">🔐 최초 1회 개인 비밀번호(PIN) 직접 설정</div>
      <div style="font-size:0.78rem; color:#78350F; margin-bottom:8px;">다른 사람이 대리 서명할 수 없도록, 본인만 아는 4~6자리 비밀번호를 설정하세요.</div>
      <div style="display:flex; gap:6px;">
        <input type="password" id="new-pin-input" placeholder="새 비밀번호 (4~6자리)" class="form-input" style="flex:2;" maxlength="6" inputmode="numeric">
        <button onclick="saveNewPin()" style="background:#B45309; color:white; border:none; padding:8px 12px; border-radius:8px; font-weight:700; cursor:pointer; flex:1;">
          설정 완료
        </button>
      </div>
    </div>

    <!-- PIN Entry for Existing PIN -->
    <div id="pin-entry-box" class="form-group">
      <label class="form-label">본인확인 개인 비밀번호 (PIN):</label>
      <div style="display:flex; gap:6px;">
        <input type="password" id="signer-pin" placeholder="본인이 설정한 비밀번호 입력" class="form-input" maxlength="6" inputmode="numeric">
        <button onclick="promptChangePin()" style="background:#F1F5F9; border:1px solid #CBD5E1; border-radius:8px; padding:0 10px; font-size:0.75rem; color:#475569; cursor:pointer; white-space:nowrap;">
          비번 변경
        </button>
      </div>
    </div>

    <!-- Agreement -->
    <div style="background: #F8FAFC; padding: 12px; border-radius: 8px; margin: 12px 0; border: 1px solid #E2E8F0;">
      <div style="font-weight: 700; font-size: 0.82rem; color: var(--primary); margin-bottom: 4px;">의결 확인 및 전자서명 동의</div>
      <div style="font-size: 0.78rem; color: #475569; line-height: 1.5;">
        "본인은 제4기 입주자대표회의에 참석하여 상기 안건에 대하여 의결하였음을 확인하며, 전자서명법 제3조에 따라 자필 서명과 동일한 효력의 전자서명을 날인합니다."
      </div>
    </div>

    <!-- Touch Signature Canvas -->
    <div style="margin: 14px 0;">
      <label class="form-label">터치 서명 패드 (화면에 직접 사인):</label>
      <div class="canvas-container">
        <canvas id="sig-pad"></canvas>
        <div class="canvas-hint" id="canvas-hint">이곳에 손가락이나 펜으로 서명해 주세요</div>
      </div>
      <div class="sig-actions">
        <button class="btn-clear" onclick="clearCanvas()">지우기</button>
        <button class="btn-submit" onclick="submitSignature()">전자서명 완료 제출</button>
      </div>
    </div>

    <div id="sign-result" style="display: none; padding: 12px; border-radius: 8px; font-size: 0.9rem; font-weight: 600; text-align: center;"></div>
  </div>

  <footer>
    <div>청주리버파크자이 입주자대표회의 모바일 전자문서 시스템</div>
    <div style="margin-top:4px;"><a href="/admin">관리자 로그인</a></div>
  </footer>
</div>

<script>
let state = null;
let canvas, ctx, isDrawing = false, hasDrawn = false;
let lastPoint = null;
let lockedRepId = null;

window.onload = function() {
  initCanvas();
  loadPublicData();
};

function loadPublicData() {
  fetch('/api/public-data')
    .then(r => r.json())
    .then(data => {
      state = data;
      renderMeeting();
      renderSignerSelect();
      setTimeout(resizeCanvas, 100);
    });
}

function renderMeeting() {
  const m = state.meeting;
  document.getElementById('m-title').innerText = m.title;
  document.getElementById('m-date').innerText = m.date;
  document.getElementById('m-place').innerText = m.place;

  const agendaUl = document.getElementById('agenda-ul');
  agendaUl.innerHTML = m.agenda.map(a => `
    <li class="agenda-item">
      <strong>제${a.num}호 : ${a.title}</strong>
      ${a.desc ? `<div class="agenda-desc">${a.desc}</div>` : ''}
      <div class="agenda-res">▶ ${a.result}</div>
    </li>
  `).join('');
}

function renderSignerSelect() {
  const urlParams = new URLSearchParams(window.location.search);
  lockedRepId = urlParams.get('rep');

  const sel = document.getElementById('signer-select');
  sel.innerHTML = state.reps.map(r => `
    <option value="${r.id}" ${r.id === lockedRepId ? 'selected' : ''}>[${r.dong}] ${r.role} ${r.name} ${r.signed ? '(✓ 서명완료)' : ''}</option>
  `).join('');

  if (lockedRepId) {
    const rep = state.reps.find(r => r.id === lockedRepId);
    if (rep) {
      document.getElementById('signer-group').style.display = 'none';
      document.getElementById('signer-locked-card').style.display = 'block';
      document.getElementById('signer-locked-name').innerText = `[${rep.dong}] ${rep.role} ${rep.name}`;
    }
  }
  onSignerChange();
}

let signaturePad = null;
let currentSelectedRepId = null;

function onSignerChange() {
  const selId = lockedRepId || document.getElementById('signer-select').value;
  if (currentSelectedRepId !== selId) {
    clearCanvas();
    currentSelectedRepId = selId;
  }
  const rep = state.reps.find(r => r.id === selId);
  const resDiv = document.getElementById('sign-result');
  resDiv.style.display = 'none';

  if (!rep) return;

  const pinBadge = document.getElementById('pin-badge');
  const setupBox = document.getElementById('pin-setup-box');
  const entryBox = document.getElementById('pin-entry-box');
  const pinInput = document.getElementById('signer-pin');

  if (!rep.has_pin) {
    pinBadge.innerText = '비밀번호 미설정 (최초)';
    pinBadge.style.background = '#FEF3C7';
    pinBadge.style.color = '#B45309';
    setupBox.style.display = 'block';
    entryBox.style.display = 'none';
  } else {
    pinBadge.innerText = '개인 비밀번호 보호 중';
    pinBadge.style.background = '#D1FAE5';
    pinBadge.style.color = '#059669';
    setupBox.style.display = 'none';
    entryBox.style.display = 'block';
    pinInput.value = '';
  }

  if (rep.signed) {
    resDiv.style.display = 'block';
    resDiv.style.background = '#ECFDF5';
    resDiv.style.color = '#065F46';
    resDiv.innerText = `✓ 이미 서명이 완료된 동대표입니다. (서명시각: ${rep.sign_time})`;
  }
}

function saveNewPin() {
  const selId = lockedRepId || document.getElementById('signer-select').value;
  const newPin = document.getElementById('new-pin-input').value.trim();
  if (newPin.length < 4) {
    alert('비밀번호는 최소 4자리 이상 입력해주세요.');
    return;
  }

  fetch('/api/set-pin', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rep_id: selId, new_pin: newPin })
  })
  .then(r => r.json())
  .then(res => {
    if (res.error) alert('오류: ' + res.error);
    else {
      alert('비밀번호가 성공적으로 설정되었습니다! 이제 서명란에 서명 후 제출하세요.');
      loadPublicData();
    }
  });
}

function promptChangePin() {
  const oldPin = prompt('현재 사용 중인 비밀번호를 입력하세요:');
  if (!oldPin) return;
  const newPin = prompt('새로 변경할 비밀번호(4~6자리)를 입력하세요:');
  if (!newPin || newPin.length < 4) {
    alert('비밀번호는 최소 4자리 이상이어야 합니다.');
    return;
  }
  const selId = lockedRepId || document.getElementById('signer-select').value;
  fetch('/api/set-pin', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rep_id: selId, old_pin: oldPin, new_pin: newPin })
  })
  .then(r => r.json())
  .then(res => {
    if (res.error) alert('오류: ' + res.error);
    else alert('비밀번호가 성공적으로 변경되었습니다!');
  });
}

/* Battle-Tested SignaturePad Initialization */
function initCanvas() {
  canvas = document.getElementById('sig-pad');
  signaturePad = new SignaturePad(canvas, {
    minWidth: 1.8,
    maxWidth: 3.8,
    penColor: '#0F3875',
    backgroundColor: 'rgba(255, 255, 255, 0)',
    velocityFilterWeight: 0.7
  });

  signaturePad.addEventListener("beginStroke", () => {
    document.getElementById('canvas-hint').style.display = 'none';
  });

  window.addEventListener('resize', resizeCanvas);
  setTimeout(resizeCanvas, 50);
}

function resizeCanvas() {
  if (!canvas || !signaturePad) return;
  const ratio = Math.max(window.devicePixelRatio || 1, 1);
  const data = signaturePad.toData(); // Preserve all strokes in memory!
  
  canvas.width = canvas.offsetWidth * ratio;
  canvas.height = canvas.offsetHeight * ratio;
  canvas.getContext("2d").scale(ratio, ratio);
  
  signaturePad.clear();
  signaturePad.fromData(data); // Restore all strokes without losing a single pixel!
  
  if (data && data.length > 0) {
    document.getElementById('canvas-hint').style.display = 'none';
  }
}

function clearCanvas() {
  if (signaturePad) {
    signaturePad.clear();
    document.getElementById('canvas-hint').style.display = 'block';
  }
}

function submitSignature() {
  if (!signaturePad || signaturePad.isEmpty()) {
    alert('서명 패드에 서명을 먼저 작성해 주세요.');
    return;
  }
  const repId = lockedRepId || document.getElementById('signer-select').value;
  let pin = document.getElementById('signer-pin').value.trim();
  if (!pin) {
    alert('본인확인 비밀번호(PIN)를 입력해 주세요.');
    return;
  }

  const sigImg = signaturePad.toDataURL('image/png');

  fetch('/api/sign', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rep_id: repId, pin: pin, signature: sigImg })
  })
  .then(r => r.json())
  .then(res => {
    if (res.error) {
      alert('오류: ' + res.error);
    } else {
      const resDiv = document.getElementById('sign-result');
      resDiv.style.display = 'block';
      resDiv.style.background = '#ECFDF5';
      resDiv.style.color = '#065F46';
      resDiv.innerText = '✓ 전자서명이 정상적으로 등록 완료되었습니다. 감사합니다!';
      loadPublicData();
      alert('✓ 전자서명이 정상적으로 등록되었습니다!');
    }
  });
}
</script>

</body>
</html>
"""

# =====================================================================
# 2. ADMIN VIEW (관리자 전용 대시보드 - 비밀번호로 철저히 보호)
# =====================================================================
ADMIN_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>청주리버파크자이 관리자 대시보드</title>
<style>
  :root {
    --primary: #0F3875;
    --primary-light: #1E58A8;
    --kakao: #FEE500;
    --kakao-text: #191919;
    --bg: #F4F6F9;
    --card: #FFFFFF;
    --text: #2C3E50;
    --border: #E1E8EE;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Malgun Gothic", "맑은 고딕", sans-serif; }
  body { background-color: var(--bg); color: var(--text); padding-bottom: 60px; }
  
  header {
    background: linear-gradient(135deg, var(--primary), var(--primary-light));
    color: white; padding: 14px 20px; box-shadow: 0 4px 12px rgba(15,56,117,0.15);
    display: flex; justify-content: space-between; align-items: center;
  }
  .brand-title { font-size: 1.15rem; font-weight: 700; }
  .badge-admin { background: #E84118; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; }
  
  .container { max-width: 960px; margin: 16px auto; padding: 0 16px; }
  
  .card {
    background: var(--card); border-radius: 14px; padding: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 16px; border: 1px solid var(--border);
  }
  .card-title {
    font-size: 1.05rem; font-weight: 700; color: var(--primary);
    margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center;
    border-bottom: 2px solid #EDF2F7; padding-bottom: 10px; flex-wrap: wrap; gap: 8px;
  }
  
  .btn-sm {
    border: none; padding: 6px 12px; border-radius: 6px; font-size: 0.82rem; font-weight: 600; cursor: pointer;
  }
  
  .form-group { margin-bottom: 12px; }
  .form-label { display: block; font-size: 0.85rem; font-weight: 700; color: #334155; margin-bottom: 4px; }
  .form-input {
    width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #CBD5E1; font-size: 0.95rem;
  }
  
  .agenda-list { list-style: none; }
  .agenda-item {
    padding: 12px; border-radius: 8px; background: #F8FAFC;
    margin-bottom: 8px; border-left: 4px solid var(--primary); font-size: 0.9rem;
  }
  .agenda-desc { font-size: 0.82rem; color: #475569; margin: 4px 0; }
  .agenda-res { font-size: 0.85rem; color: #059669; font-weight: 700; }
  
  .rep-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px;
  }
  .rep-card {
    border: 1px solid var(--border); border-radius: 10px; padding: 14px;
    display: flex; flex-direction: column; justify-content: space-between;
    background: #FAFCFE;
  }
  .rep-card.signed {
    border-color: #10B981; background: #F0FDF4;
  }
  .rep-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
  .rep-dong { font-weight: 700; color: var(--primary); font-size: 0.95rem; }
  .status-tag {
    font-size: 0.75rem; padding: 3px 8px; border-radius: 6px; font-weight: 600;
  }
  .status-pending { background: #FEF3C7; color: #D97706; }
  .status-done { background: #D1FAE5; color: #059669; }
  
  .action-row { display: flex; gap: 6px; margin-top: 10px; }
  .btn-kakao {
    background: var(--kakao); color: var(--kakao-text); border: none; border-radius: 6px;
    padding: 7px 10px; font-size: 0.8rem; font-weight: 700; cursor: pointer; flex: 1;
    display: flex; align-items: center; justify-content: center; gap: 4px;
  }
  .btn-qr {
    background: #E2E8F0; color: #334155; border: none; border-radius: 6px;
    padding: 7px 10px; font-size: 0.8rem; font-weight: 600; cursor: pointer;
  }
  .btn-reset-sign {
    background: #F1F5F9; color: #EF4444; border: 1px solid #CBD5E1; border-radius: 6px;
    padding: 7px 10px; font-size: 0.8rem; font-weight: 600; cursor: pointer;
  }
  
  .progress-bar-bg { height: 12px; background: #E2E8F0; border-radius: 6px; overflow: hidden; }
  .progress-bar-fill { height: 100%; background: #10B981; width: 0%; transition: width 0.4s ease; }
  .progress-text { display: flex; justify-content: space-between; font-size: 0.85rem; margin-top: 6px; font-weight: 600; }
  
  .btn-action-main {
    background: #0284C7; color: white; border: none; border-radius: 10px;
    padding: 14px 20px; font-size: 1rem; font-weight: 700; cursor: pointer;
    width: 100%; display: flex; justify-content: center; align-items: center; gap: 8px;
    box-shadow: 0 4px 12px rgba(2,132,199,0.3); text-decoration: none;
  }
  .btn-kakao-all {
    background: var(--kakao); color: var(--kakao-text); border: none; border-radius: 10px;
    padding: 12px 18px; font-size: 0.95rem; font-weight: 700; cursor: pointer;
    width: 100%; margin-bottom: 10px; display: flex; justify-content: center; align-items: center; gap: 6px;
  }

  /* Modals */
  .modal-overlay {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5); display: none; align-items: center; justify-content: center;
    z-index: 1000; padding: 16px;
  }
  .modal-box {
    background: white; border-radius: 14px; max-width: 720px; width: 100%;
    max-height: 90vh; overflow-y: auto; padding: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.2);
  }
  
  .rep-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.85rem; }
  .rep-table th { background: #F1F5F9; padding: 8px; text-align: left; border-bottom: 2px solid #CBD5E1; color: #334155; }
  .rep-table td { padding: 8px; border-bottom: 1px solid #E2E8F0; vertical-align: middle; }
  .rep-input { padding: 6px 8px; border: 1px solid #CBD5E1; border-radius: 6px; width: 100%; font-size: 0.85rem; }
</style>
</head>
<body>

<header>
  <div>
    <div class="brand-title">청주리버파크자이 관리자 대시보드</div>
    <div style="font-size:0.75rem; opacity:0.85;">입주자대표회의 전자서명 관리 센터</div>
  </div>
  <div style="display:flex; align-items:center; gap:8px;">
    <span class="badge-admin">관리자 모드</span>
    <button onclick="logoutAdmin()" class="btn-sm" style="background:rgba(255,255,255,0.2); color:white;">로그아웃</button>
  </div>
</header>

<!-- Admin Login Overlay -->
<div id="login-overlay" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(15,56,117,0.92); z-index:2000; display:flex; align-items:center; justify-content:center;">
  <div style="background:white; border-radius:14px; padding:28px 24px; max-width:380px; width:90%; text-align:center; box-shadow:0 10px 25px rgba(0,0,0,0.3);">
    <h3 style="color:var(--primary); margin-bottom:6px;">🔒 관리자 인증</h3>
    <p style="font-size:0.82rem; color:#64748B; margin-bottom:16px;">관리자 마스터 비밀번호를 입력하세요.<br>(초기 비밀번호: 1234)</p>
    <input type="password" id="admin-pw-input" placeholder="비밀번호 입력" class="form-input" style="text-align:center; font-size:1.1rem; letter-spacing:2px; margin-bottom:12px;">
    <button onclick="loginAdmin()" class="btn-action-main" style="padding:10px;">관리자 로그인</button>
  </div>
</div>

<div class="container" id="admin-main-content">
  <!-- 1. Meeting Overview & Edit Button -->
  <div class="card">
    <div class="card-title">
      <span>📌 입대의 회의 개요 및 심의 결과</span>
      <div style="display:flex; gap:8px;">
        <button onclick="openEditMeetingModal()" class="btn-sm" style="background:#0F3875; color:white;">
          ✏️ 회의록 내용 편집
        </button>
        <button onclick="openManageRepsModal()" class="btn-sm" style="background:#0284C7; color:white;">
          👥 동대표 명단 설정/수정
        </button>
      </div>
    </div>
    <div style="font-size: 0.9rem; line-height: 1.6; margin-bottom: 12px;">
      <div><strong>회의명 :</strong> <span id="view-title"></span></div>
      <div><strong>일시/장소 :</strong> <span id="view-date"></span> / <span id="view-place"></span></div>
      <div><strong>의장/출석 :</strong> <span id="view-chair"></span> / <span id="view-attendees"></span></div>
    </div>
    <ul class="agenda-list" id="admin-agenda"></ul>
  </div>

  <!-- 2. Signing Progress & Kakao Dispatch -->
  <div class="card">
    <div class="card-title">
      <span>📊 실시간 전자서명 진행 현황 (<span id="total-reps-count">0</span>인)</span>
      <div style="font-size:0.8rem; color:#64748B; display:flex; align-items:center; gap:6px;">
        <span>🌐 접속주소:</span>
        <input type="text" id="server-url-input" style="padding:4px 8px; border-radius:6px; border:1px solid #CBD5E1; font-size:0.8rem; width:220px;" onchange="saveServerUrl()">
      </div>
    </div>
    
    <div style="margin-bottom: 16px;">
      <button class="btn-kakao-all" onclick="copyAllKakaoMessage()">
        💬 [전체 단톡방 공지문 일괄 복사] 클릭하여 입대의 단톡방에 붙여넣기
      </button>
      <div style="font-size:0.75rem; color:#64748B; text-align:center; margin-top:4px;">
        ※ 카카오톡에서 각 링크가 즉시 파란색 하이퍼링크로 클릭되도록 줄바꿈 서식이 적용되어 있습니다.
      </div>
    </div>

    <div class="progress-wrap" style="margin-bottom: 16px;">
      <div class="progress-bar-bg"><div class="progress-bar-fill" id="progress-fill"></div></div>
      <div class="progress-text">
        <span id="progress-status">서명 진행 중...</span>
        <span id="progress-count">0 / 0명 (0%)</span>
      </div>
    </div>

    <div class="rep-grid" id="admin-rep-grid"></div>

    <div style="margin-top: 24px; text-align: center;">
      <a href="/api/download-pdf" target="_blank" class="btn-action-main">
        📥 최종 전자서명 완료본 회의록 PDF 다운로드 (감사추적서 포함)
      </a>
      <div style="display:flex; justify-content:center; gap:12px; margin-top:12px;">
        <button onclick="promptChangeAdminPw()" style="background:transparent; color:#64748B; border:1px solid #CBD5E1; border-radius:6px; padding:6px 12px; font-size:0.8rem; cursor:pointer;">
          🔑 관리자 비밀번호 변경
        </button>
        <button onclick="resetAll()" style="background:transparent; color:#EF4444; border:1px solid #FCA5A5; border-radius:6px; padding:6px 12px; font-size:0.8rem; cursor:pointer;">
          🔄 전체 서명 데이터 초기화
        </button>
      </div>
    </div>
  </div>
</div>

<!-- Modal 1: Edit Meeting Minutes -->
<div class="modal-overlay" id="edit-modal">
  <div class="modal-box">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; border-bottom:2px solid #EDF2F7; padding-bottom:8px;">
      <h3 style="color:var(--primary); font-size:1.1rem;">📝 회의록 내용 및 안건 편집</h3>
      <button onclick="closeEditModal()" style="border:none; background:none; font-size:1.4rem; cursor:pointer;">&times;</button>
    </div>

    <div class="form-group">
      <label class="form-label">회의명:</label>
      <input type="text" id="edit-title" class="form-input">
    </div>
    <div style="display:flex; gap:10px;">
      <div class="form-group" style="flex:1;">
        <label class="form-label">회의 일시:</label>
        <input type="text" id="edit-date" class="form-input">
      </div>
      <div class="form-group" style="flex:1;">
        <label class="form-label">회의 장소:</label>
        <input type="text" id="edit-place" class="form-input">
      </div>
    </div>
    <div style="display:flex; gap:10px;">
      <div class="form-group" style="flex:1;">
        <label class="form-label">회의 의장 (진행자):</label>
        <input type="text" id="edit-chair" class="form-input">
      </div>
      <div class="form-group" style="flex:1;">
        <label class="form-label">출석 현황 설명:</label>
        <input type="text" id="edit-attendees" class="form-input">
      </div>
    </div>

    <div style="margin-top:16px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <label class="form-label" style="margin:0;">심의 안건 목록:</label>
        <button onclick="addAgendaItem()" style="background:#10B981; color:white; border:none; padding:4px 8px; border-radius:6px; font-size:0.75rem; font-weight:700; cursor:pointer;">
          ➕ 안건 추가
        </button>
      </div>
      <div id="edit-agenda-container"></div>
    </div>

    <div style="margin-top:20px; display:flex; gap:10px;">
      <button onclick="closeEditModal()" style="flex:1; padding:12px; border:1px solid #CBD5E1; background:#F8FAFC; border-radius:8px; font-weight:600; cursor:pointer;">
        취소
      </button>
      <button onclick="saveMeetingMinutes()" style="flex:2; padding:12px; border:none; background:var(--primary); color:white; border-radius:8px; font-weight:700; cursor:pointer;">
        💾 회의록 저장 및 서명요청 반영
      </button>
    </div>
  </div>
</div>

<!-- Modal 2: Manage Representatives -->
<div class="modal-overlay" id="reps-modal">
  <div class="modal-box">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-bottom:2px solid #EDF2F7; padding-bottom:8px;">
      <h3 style="color:var(--primary); font-size:1.1rem;">👥 동대표 명단 관리 (추가·수정·삭제)</h3>
      <button onclick="closeManageRepsModal()" style="border:none; background:none; font-size:1.4rem; cursor:pointer;">&times;</button>
    </div>
    <p style="font-size:0.8rem; color:#64748B; margin-bottom:10px;">
      실제 선출된 동대표의 동, 성명, 직책, 연락처를 등록하세요. 비밀번호를 잊은 분은 [PIN리셋]을 누르시면 됩니다.
    </p>

    <div style="max-height: 50vh; overflow-y: auto;">
      <table class="rep-table">
        <thead>
          <tr>
            <th style="width:75px;">동</th>
            <th style="width:90px;">성명</th>
            <th style="width:105px;">직책</th>
            <th>연락처</th>
            <th style="width:130px; text-align:center;">관리</th>
          </tr>
        </thead>
        <tbody id="manage-reps-tbody"></tbody>
      </table>
    </div>

    <div style="margin-top:12px; display:flex; justify-content:space-between; align-items:center;">
      <button onclick="addNewRepRow()" style="background:#10B981; color:white; border:none; padding:8px 14px; border-radius:6px; font-size:0.85rem; font-weight:700; cursor:pointer;">
        ➕ 새 동대표 추가
      </button>
    </div>

    <div style="margin-top:20px; display:flex; gap:10px;">
      <button onclick="closeManageRepsModal()" style="flex:1; padding:12px; border:1px solid #CBD5E1; background:#F8FAFC; border-radius:8px; font-weight:600; cursor:pointer;">
        취소
      </button>
      <button onclick="saveRepsList()" style="flex:2; padding:12px; border:none; background:var(--primary); color:white; border-radius:8px; font-weight:700; cursor:pointer;">
        💾 동대표 명단 저장 및 반영
      </button>
    </div>
  </div>
</div>

<!-- Modal 3: QR Code Modal -->
<div class="modal-overlay" id="qr-modal">
  <div class="modal-box" style="max-width:360px; text-align:center;">
    <h3 style="color:var(--primary); margin-bottom:8px;" id="qr-modal-title">스마트폰 QR 서명</h3>
    <p style="font-size:0.8rem; color:#64748B; margin-bottom:14px;">스마트폰 카메라로 아래 QR 코드를 비추면 즉시 모바일 서명 화면으로 이동합니다.</p>
    <div style="background:#F8FAFC; padding:16px; border-radius:12px; display:inline-block; border:1px solid #E2E8F0;">
      <img id="qr-modal-img" src="" alt="QR Code" style="width:200px; height:200px; display:block;">
    </div>
    <div style="margin-top:14px; font-size:0.75rem; word-break:break-all; color:#0284C7;" id="qr-modal-url"></div>
    <button onclick="closeQrModal()" style="margin-top:16px; width:100%; padding:10px; background:#F1F5F9; border:1px solid #CBD5E1; border-radius:8px; font-weight:600; cursor:pointer;">
      닫기
    </button>
  </div>
</div>

<script>
let state = null;
let adminPw = sessionStorage.getItem('admin_token') || '';
let editingReps = [];

window.onload = function() {
  if (!adminPw) {
    document.getElementById('login-overlay').style.display = 'flex';
  } else {
    loadAdminData();
  }
};

function loginAdmin() {
  const pw = document.getElementById('admin-pw-input').value.trim();
  if (!pw) return;

  fetch('/api/admin-login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: pw })
  })
  .then(r => r.json())
  .then(res => {
    if (res.error) {
      alert('오류: ' + res.error);
    } else {
      adminPw = pw;
      sessionStorage.setItem('admin_token', adminPw);
      document.getElementById('login-overlay').style.display = 'none';
      loadAdminData();
    }
  });
}

function logoutAdmin() {
  sessionStorage.removeItem('admin_token');
  window.location.reload();
}

function loadAdminData() {
  fetch('/api/admin-data', {
    headers: { 'X-Admin-Password': adminPw }
  })
  .then(r => {
    if (r.status === 401) {
      sessionStorage.removeItem('admin_token');
      document.getElementById('login-overlay').style.display = 'flex';
      throw new Error('Unauthorized');
    }
    return r.json();
  })
  .then(data => {
    state = data;
    document.getElementById('server-url-input').value = state.server_url;
    renderAdmin();
  })
  .catch(e => console.log(e));
}

function getEffectiveUrl() {
  return (state && state.server_url) ? state.server_url : window.location.origin;
}

function saveServerUrl() {
  const newUrl = document.getElementById('server-url-input').value.trim();
  fetch('/api/set-server-url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Password': adminPw },
    body: JSON.stringify({ server_url: newUrl })
  })
  .then(r => r.json())
  .then(res => {
    if (res.error) alert('오류: ' + res.error);
    else {
      state.server_url = newUrl;
      renderAdmin();
      alert('접속 주소가 업데이트되었습니다.');
    }
  });
}

function renderAdmin() {
  const m = state.meeting;
  document.getElementById('view-title').innerText = m.title;
  document.getElementById('view-date').innerText = m.date;
  document.getElementById('view-place').innerText = m.place;
  document.getElementById('view-chair').innerText = m.chair || '회장 직무대행';
  document.getElementById('view-attendees').innerText = m.attendees_desc || `총 재적 ${state.reps.length}명`;
  document.getElementById('total-reps-count').innerText = state.reps.length;

  const agendaUl = document.getElementById('admin-agenda');
  agendaUl.innerHTML = m.agenda.map(a => `
    <li class="agenda-item">
      <strong>제${a.num}호 : ${a.title}</strong>
      ${a.desc ? `<div class="agenda-desc">${a.desc}</div>` : ''}
      <div class="agenda-res">▶ ${a.result}</div>
    </li>
  `).join('');

  const grid = document.getElementById('admin-rep-grid');
  let signedCount = 0;
  const baseUrl = getEffectiveUrl();

  grid.innerHTML = state.reps.map(r => {
    if (r.signed) signedCount++;
    const personalUrl = `${baseUrl}/?rep=${r.id}`;
    return `
      <div class="rep-card ${r.signed ? 'signed' : ''}">
        <div>
          <div class="rep-header">
            <span class="rep-dong">[${r.dong}] ${r.role}</span>
            <span class="status-tag ${r.signed ? 'status-done' : 'status-pending'}">
              ${r.signed ? '✓ 서명완료' : (r.has_pin ? '서명대기 (PIN설정됨)' : 'PIN설정 대기')}
            </span>
          </div>
          <div style="font-size: 1.05rem; font-weight: 700; margin-bottom: 4px;">${r.name}</div>
          <div style="font-size: 0.75rem; color: #64748B;">
            ${r.signed ? `서명일시: ${r.sign_time}<br>접속IP: ${r.ip || '127.0.0.1'}` : `연락처: ${r.phone || '등록안됨'}`}
          </div>
        </div>

        <div class="action-row">
          <button class="btn-kakao" onclick="copyPersonalKakao('${r.name}', '${r.dong}', '${personalUrl}')" title="개인 카톡 전송용 링크 복사">
            💬 카톡 복사
          </button>
          <button class="btn-qr" onclick="showQrModal('${r.name}', '${personalUrl}')" title="스마트폰 카메라로 스캔">
            📱 QR
          </button>
          ${r.signed ? `
            <button class="btn-reset-sign" onclick="resetRepSign('${r.id}', '${r.name}')" title="서명 취소 후 다시 서명하게 하기">서명취소</button>
          ` : `
            <a href="${personalUrl}" target="_blank" style="text-decoration:none;" class="btn-sm" style="background:#0F3875; color:white; display:flex; align-items:center; justify-content:center;">서명창</a>
          `}
        </div>
      </div>
    `;
  }).join('');

  const pct = state.reps.length ? Math.round((signedCount / state.reps.length) * 100) : 0;
  document.getElementById('progress-fill').style.width = pct + '%';
  document.getElementById('progress-count').innerText = `${signedCount} / ${state.reps.length}명 (${pct}%)`;
  document.getElementById('progress-status').innerText = (pct === 100 && state.reps.length > 0) ? '🎉 전원 서명 완료!' : '동대표 모바일 전자서명 진행 중...';
}

function copyPersonalKakao(name, dong, url) {
  const msg = `[청주리버파크자이 입대의 회의록 모바일 서명]\n\n${dong} ${name} 대표님, 아래 링크를 터치하여 모바일 서명을 마쳐주세요.\n\n${url}\n\n(※ 최초 접속 시 본인만 사용할 비밀번호 4자리 설정 후 서명)`;
  navigator.clipboard.writeText(msg).then(() => {
    alert(`[${name} 대표님 개인 서명 링크]가 복사되었습니다!\n카카오톡에 붙여넣기(Ctrl+V) 하시면 100% 파란색 링크로 전달됩니다.`);
  });
}

function copyAllKakaoMessage() {
  const baseUrl = getEffectiveUrl();
  let msg = `[청주리버파크자이 입대의 회의록 모바일 전자서명 안내]\n\n`;
  msg += `일시: ${state.meeting.date}\n`;
  msg += `상정 안건이 모두 가결되었으니, 각 동대표님께서는 본인 링크를 터치하여 서명을 마쳐주시기 바랍니다.\n\n`;
  
  state.reps.forEach((r, idx) => {
    const personalUrl = `${baseUrl}/?rep=${r.id}`;
    msg += `---------------------------------\n`;
    msg += `▶ ${r.dong} ${r.name} 대표님\n`;
    msg += `${personalUrl}\n\n`;
  });
  msg += `---------------------------------\n`;
  msg += `※ 최초 1회 본인만 아는 비밀번호(4자리)를 설정 후 손가락으로 사인하시면 완료됩니다.`;

  navigator.clipboard.writeText(msg).then(() => {
    alert('전체 동대표 서명 링크 공지문이 클립보드에 복사되었습니다!\n카카오톡 단톡방에 그대로 붙여넣기(Ctrl+V) 하시면 링크가 파란색으로 깔끔하게 걸립니다.');
  });
}

function showQrModal(name, url) {
  document.getElementById('qr-modal-title').innerText = `${name} 대표님 모바일 서명 QR`;
  const qrApiUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(url)}`;
  document.getElementById('qr-modal-img').src = qrApiUrl;
  document.getElementById('qr-modal-url').innerText = url;
  document.getElementById('qr-modal').style.display = 'flex';
}

function closeQrModal() {
  document.getElementById('qr-modal').style.display = 'none';
}

/* Meeting Minutes Editor */
let editingAgenda = [];

function openEditMeetingModal() {
  const m = state.meeting;
  document.getElementById('edit-title').value = m.title;
  document.getElementById('edit-date').value = m.date;
  document.getElementById('edit-place').value = m.place;
  document.getElementById('edit-chair').value = m.chair || '진상호 (회장 직무대행)';
  document.getElementById('edit-attendees').value = m.attendees_desc || `총 재적 ${state.reps.length}명`;

  editingAgenda = JSON.parse(JSON.stringify(m.agenda));
  renderEditAgenda();
  document.getElementById('edit-modal').style.display = 'flex';
}

function closeEditModal() {
  document.getElementById('edit-modal').style.display = 'none';
}

function renderEditAgenda() {
  const cont = document.getElementById('edit-agenda-container');
  cont.innerHTML = editingAgenda.map((a, idx) => `
    <div style="border:1px solid #E2E8F0; border-radius:10px; padding:12px; margin-bottom:10px; background:#F8FAFC;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <span style="font-weight:700; color:var(--primary); font-size:0.85rem;">안건 ${idx+1}</span>
        <button onclick="removeAgendaItem(${idx})" style="background:#EF4444; color:white; border:none; padding:2px 6px; border-radius:4px; font-size:0.75rem; cursor:pointer;">삭제</button>
      </div>
      <input type="text" value="${a.title}" placeholder="안건 제목" class="form-input" style="margin-bottom:6px;" onchange="editingAgenda[${idx}].title = this.value">
      <textarea placeholder="제안 내용 / 주요 토의 기록" class="form-input" style="height:55px; resize:none; margin-bottom:6px; font-size:0.85rem;" onchange="editingAgenda[${idx}].desc = this.value">${a.desc || ''}</textarea>
      <input type="text" value="${a.result}" placeholder="의결 결과 (예: 원안 가결 (찬성 10, 반대 0))" class="form-input" onchange="editingAgenda[${idx}].result = this.value">
    </div>
  `).join('');
}

function addAgendaItem() {
  editingAgenda.push({
    num: editingAgenda.length + 1,
    title: "새 안건",
    desc: "",
    result: "원안 가결 (찬성 10, 반대 0)"
  });
  renderEditAgenda();
}

function removeAgendaItem(idx) {
  editingAgenda.splice(idx, 1);
  editingAgenda.forEach((a, i) => a.num = i + 1);
  renderEditAgenda();
}

function saveMeetingMinutes() {
  const updatedMeeting = {
    title: document.getElementById('edit-title').value.trim(),
    date: document.getElementById('edit-date').value.trim(),
    place: document.getElementById('edit-place').value.trim(),
    chair: document.getElementById('edit-chair').value.trim(),
    attendees_desc: document.getElementById('edit-attendees').value.trim(),
    agenda: editingAgenda
  };

  fetch('/api/save-meeting', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Password': adminPw },
    body: JSON.stringify({ meeting: updatedMeeting })
  })
  .then(r => r.json())
  .then(res => {
    if (res.error) alert('오류: ' + res.error);
    else {
      alert('회의록이 성공적으로 저장되었습니다!');
      closeEditModal();
      loadAdminData();
    }
  });
}

/* Reps Management */
function openManageRepsModal() {
  editingReps = JSON.parse(JSON.stringify(state.reps));
  renderManageReps();
  document.getElementById('reps-modal').style.display = 'flex';
}

function closeManageRepsModal() {
  document.getElementById('reps-modal').style.display = 'none';
}

function renderManageReps() {
  const tbody = document.getElementById('manage-reps-tbody');
  tbody.innerHTML = editingReps.map((r, idx) => `
    <tr>
      <td><input type="text" class="rep-input" value="${r.dong}" placeholder="101동" onchange="editingReps[${idx}].dong = this.value"></td>
      <td><input type="text" class="rep-input" value="${r.name}" placeholder="홍길동" onchange="editingReps[${idx}].name = this.value"></td>
      <td>
        <select class="rep-input" onchange="editingReps[${idx}].role = this.value">
          <option value="동대표" ${r.role === '동대표' ? 'selected' : ''}>동대표</option>
          <option value="회장 직무대행" ${r.role === '회장 직무대행' ? 'selected' : ''}>회장 직무대행</option>
          <option value="입주자대표회장" ${r.role === '입주자대표회장' ? 'selected' : ''}>입주자대표회장</option>
          <option value="입주민 감사" ${r.role === '입주민 감사' ? 'selected' : ''}>입주민 감사</option>
          <option value="이사" ${r.role === '이사' ? 'selected' : ''}>이사</option>
        </select>
      </td>
      <td><input type="text" class="rep-input" value="${r.phone || ''}" placeholder="010-0000-0000" onchange="editingReps[${idx}].phone = this.value"></td>
      <td style="text-align:center;">
        <button onclick="resetRepPin('${r.id}', '${r.name}')" style="background:#F59E0B; color:white; border:none; padding:4px 6px; border-radius:4px; font-size:0.7rem; cursor:pointer;" title="비밀번호 잊었을 때 초기화">PIN리셋</button>
        <button onclick="removeRepRow(${idx})" style="background:#EF4444; color:white; border:none; padding:4px 6px; border-radius:4px; font-size:0.7rem; cursor:pointer;" title="삭제">삭제</button>
      </td>
    </tr>
  `).join('');
}

function addNewRepRow() {
  const newNum = editingReps.length + 1;
  editingReps.push({
    id: `new_${Date.now()}_${newNum}`,
    dong: `${100 + newNum}동`,
    name: `새동대표${newNum}`,
    role: "동대표",
    phone: "",
    pin: null,
    signed: false
  });
  renderManageReps();
}

function removeRepRow(idx) {
  if (confirm(`'${editingReps[idx].dong} ${editingReps[idx].name}' 동대표를 명단에서 삭제하시겠습니까?`)) {
    editingReps.splice(idx, 1);
    renderManageReps();
  }
}

function resetRepPin(repId, name) {
  if (confirm(`'${name}' 동대표의 PIN 비밀번호를 초기화하시겠습니까?\n동대표가 다음 접속 시 새 비밀번호를 직접 설정하게 됩니다.`)) {
    fetch('/api/reset-rep-pin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Password': adminPw },
      body: JSON.stringify({ rep_id: repId })
    })
    .then(r => r.json())
    .then(res => {
      alert(res.message || '초기화되었습니다.');
      loadAdminData();
    });
  }
}

function resetRepSign(repId, name) {
  if (confirm(`'${name}' 동대표의 서명을 취소하시겠습니까?\n취소 후 다시 서명할 수 있습니다.`)) {
    fetch('/api/reset-rep-sign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Password': adminPw },
      body: JSON.stringify({ rep_id: repId })
    })
    .then(r => r.json())
    .then(res => {
      alert(res.message || '서명이 취소되었습니다.');
      loadAdminData();
    });
  }
}

function saveRepsList() {
  fetch('/api/save-reps', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Password': adminPw },
    body: JSON.stringify({ reps: editingReps })
  })
  .then(r => r.json())
  .then(res => {
    if (res.error) alert('오류: ' + res.error);
    else {
      alert('동대표 명단이 성공적으로 저장되었습니다!');
      closeManageRepsModal();
      loadAdminData();
    }
  });
}

function promptChangeAdminPw() {
  const newPw = prompt('새로 설정할 관리자 마스터 비밀번호(4자리 이상)를 입력하세요:');
  if (!newPw || newPw.length < 4) {
    alert('비밀번호는 최소 4자리 이상이어야 합니다.');
    return;
  }
  fetch('/api/change-admin-pw', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Password': adminPw },
    body: JSON.stringify({ new_password: newPw })
  })
  .then(r => r.json())
  .then(res => {
    if (res.error) alert('오류: ' + res.error);
    else {
      adminPw = newPw;
      sessionStorage.setItem('admin_token', adminPw);
      alert('관리자 비밀번호가 성공적으로 변경되었습니다!');
    }
  });
}

function resetAll() {
  if (confirm('모든 서명 데이터를 초기화하시겠습니까?')) {
    fetch('/api/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Password': adminPw }
    })
    .then(r => r.json())
    .then(() => {
      loadAdminData();
      alert('초기화 완료되었습니다.');
    });
  }
}
</script>

</body>
</html>
"""

def main():
    server = ThreadingHTTPServer(('0.0.0.0', PORT), RequestHandler)
    print(f"============================================================")
    print(f" 청주리버파크자이 모바일 전자서명 플랫폼 (v3.0 완벽 보안분리)")
    print(f" • [동대표 모바일 서명용 URL]: http://{LOCAL_IP}:{PORT}/")
    print(f" • [관리자 전용 대시보드 URL]: http://localhost:{PORT}/admin")
    print(f" • 관리자 초기 비밀번호: 1234")
    print(f" 종료하려면 Ctrl + C 를 누르세요.")
    print(f"============================================================")
    server.serve_forever()

if __name__ == '__main__':
    main()
