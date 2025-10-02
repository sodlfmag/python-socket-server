import os
import socket
from datetime import datetime

class SocketServer:
    def __init__(self):
        self.bufsize = 1024  # 버퍼 크기 설정
        with open('./response.bin', 'rb') as file:
            self.RESPONSE = file.read()  # 응답 파일 읽기
        self.DIR_PATH = './request'
        self.createDir(self.DIR_PATH)

    def createDir(self, path):
        """디렉토리 생성"""
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except OSError:
            print("Error: Failed to create the directory.")

    def process_multipart_data(self, request_data, timestamp):
        """멀티파트 데이터에서 이미지 파일 추출"""
        try:
            # 멀티파트 데이터 파싱
            if b'multipart/form-data' in request_data:
                # Content-Type에서 boundary 추출
                lines = request_data.split(b'\r\n')
                boundary = None
                for line in lines:
                    if b'Content-Type: multipart/form-data' in line:
                        if b'boundary=' in line:
                            boundary = line.split(b'boundary=')[1].strip()
                            break
                
                if boundary:
                    print(f"Found boundary: {boundary.decode()}")
                    # boundary로 데이터 분할
                    parts = request_data.split(b'--' + boundary)
                    
                    for i, part in enumerate(parts):
                        if b'Content-Disposition: form-data' in part:
                            print(f"Processing part {i}:")
                            
                            # 필드명 추출
                            if b'name=' in part:
                                field_name_start = part.find(b'name="') + 6
                                field_name_end = part.find(b'"', field_name_start)
                                field_name = part[field_name_start:field_name_end].decode()
                                print(f"  Field name: {field_name}")
                            
                            # 파일명 추출
                            filename = None
                            if b'filename=' in part:
                                # Content-Disposition 라인에서 파일명 추출
                                disposition_line = part.split(b'\r\n')[0]
                                if b'filename="' in disposition_line:
                                    filename_start = disposition_line.find(b'filename="') + 11
                                    filename_end = disposition_line.find(b'"', filename_start)
                                    if filename_end != -1:
                                        filename = disposition_line[filename_start:filename_end].decode()
                                        print(f"  Filename: {filename}")
                            
                            # Content-Type 확인
                            content_type = None
                            if b'Content-Type:' in part:
                                ct_start = part.find(b'Content-Type:') + 14
                                ct_end = part.find(b'\r\n', ct_start)
                                content_type = part[ct_start:ct_end].strip().decode()
                                print(f"  Content-Type: {content_type}")
                            
                            # 데이터 추출
                            header_end = part.find(b'\r\n\r\n')
                            if header_end != -1:
                                data = part[header_end + 4:]
                                # 마지막 boundary 제거
                                if data.endswith(b'\r\n'):
                                    data = data[:-2]
                                
                                if data and content_type and b'image/' in content_type.encode():
                                    # 이미지 파일 확장자 결정
                                    if 'image/jpeg' in content_type or 'image/jpg' in content_type:
                                        ext = '.jpg'
                                    elif 'image/png' in content_type:
                                        ext = '.png'
                                    elif 'image/gif' in content_type:
                                        ext = '.gif'
                                    else:
                                        ext = '.bin'
                                    
                                    # 이미지 파일 저장
                                    if filename:
                                        image_filename = f"{timestamp}_{filename}"
                                    else:
                                        image_filename = f"{timestamp}_image{ext}"
                                    
                                    image_filepath = os.path.join(self.DIR_PATH, image_filename)
                                    
                                    with open(image_filepath, 'wb') as f:
                                        f.write(data)
                                    print(f"  Image saved to: {image_filepath}")
                                elif data:
                                    # 텍스트 필드 데이터 출력
                                    try:
                                        text_data = data.decode('utf-8')
                                        print(f"  Text data: {text_data[:100]}...")
                                    except:
                                        print(f"  Binary data: {len(data)} bytes")
                                    
        except Exception as e:
            print(f"Error processing multipart data: {e}")

    def run(self, ip, port):
        """서버 실행"""
        # 소켓 생성
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((ip, port))
        self.sock.listen(10)
        print("Start the socket server...")
        print("\"Ctrl+C\" for stopping the server!\r\n")
        
        try:
            while True:
                # 클라이언트의 요청 대기
                clnt_sock, req_addr = self.sock.accept()
                clnt_sock.settimeout(5.0)  # 타임아웃 설정(5초)
                print("Request message...\r\n")
                
                # 클라이언트 요청 데이터 수신
                request_data = b""
                try:
                    while True:
                        data = clnt_sock.recv(self.bufsize)
                        if not data:
                            break
                        request_data += data
                except socket.timeout:
                    print("Request timeout")
                
                # 요청 데이터를 파일로 저장 (년-월-일-시-분-초.bin)
                if request_data:
                    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                    filename = f"{timestamp}.bin"
                    filepath = os.path.join(self.DIR_PATH, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(request_data)
                    print(f"Request saved to: {filepath}")
                    
                    # 멀티파트 데이터 처리 (이미지 파일 추출)
                    self.process_multipart_data(request_data, timestamp)
                
                # 응답 전송
                clnt_sock.sendall(self.RESPONSE)
                # 클라이언트 소켓 닫기
                clnt_sock.close()
        except KeyboardInterrupt:
            print("\r\nStop the server...")
            # 서버 소켓 닫기
            self.sock.close()

if __name__ == "__main__":
    server = SocketServer()
    server.run("127.0.0.1", 8000)
