from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import subprocess
import os
import re
import tempfile
import json
from collections import OrderedDict
import requests

app = Flask(__name__)
CORS(app, origins=['*'])  # 모든 오리진 허용

# 추가 CORS 헤더 설정
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def extract_video_id(url):
    """YouTube URL에서 비디오 ID 추출"""
    regex = r'(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})'
    match = re.search(regex, url)
    return match.group(1) if match else None

def extract_text_from_vtt(vtt_content):
    """VTT 파일에서 강력한 중복 제거하며 텍스트 추출"""
    lines = vtt_content.split('\n')
    raw_segments = []
    
    # 1단계: VTT에서 순수 텍스트만 추출
    for line in lines:
        line = line.strip()
        
        # VTT 헤더, 시간 정보, 빈 줄 건너뛰기
        if (not line or 
            line.startswith('WEBVTT') or 
            '-->' in line or 
            line.isdigit() or
            'Kind:' in line or
            'Language:' in line or
            line.startswith('NOTE') or
            line.startswith('<') or
            re.match(r'^\d+$', line)):
            continue
            
        # HTML 태그 제거
        clean_line = re.sub(r'<[^>]+>', '', line)
        clean_line = clean_line.strip()
        
        if clean_line and len(clean_line) > 3:
            raw_segments.append(clean_line)
    
    # 2단계: 강력한 중복 제거
    cleaned_segments = remove_all_duplicates(raw_segments)
    
    # 3단계: 최종 텍스트 조합
    return ' '.join(cleaned_segments)

def remove_all_duplicates(segments):
    """모든 종류의 중복을 제거하는 강력한 함수"""
    if not segments:
        return []
    
    # 1단계: 완전히 동일한 연속 세그먼트 제거
    no_consecutive = []
    prev_segment = ""
    
    for segment in segments:
        if segment != prev_segment:
            no_consecutive.append(segment)
            prev_segment = segment
    
    # 2단계: 유사도 기반 중복 제거 (더 엄격하게)
    final_segments = []
    
    for segment in no_consecutive:
        is_duplicate = False
        
        # 이미 추가된 세그먼트들과 비교
        for existing in final_segments:
            similarity = calculate_advanced_similarity(segment, existing)
            if similarity > 0.75:  # 75% 이상 유사하면 중복으로 간주
                is_duplicate = True
                break
        
        if not is_duplicate:
            final_segments.append(segment)
    
    # 3단계: 연속 반복 패턴 제거
    return remove_repetitive_patterns(final_segments)

def calculate_advanced_similarity(text1, text2):
    """고급 유사도 계산 (단어 기반 + 길이 고려)"""
    if not text1 or not text2:
        return 0.0
    
    # 단어 분할
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    # 자카드 유사도 계산
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    jaccard = intersection / union if union > 0 else 0.0
    
    # 길이 유사도 고려
    len_ratio = min(len(text1), len(text2)) / max(len(text1), len(text2))
    
    # 최종 유사도 (자카드 유사도 70% + 길이 유사도 30%)
    return jaccard * 0.7 + len_ratio * 0.3

def remove_repetitive_patterns(segments):
    """반복 패턴 제거 (예: A B A B A B -> A B)"""
    if len(segments) < 4:
        return segments
    
    result = []
    i = 0
    
    while i < len(segments):
        current_segment = segments[i]
        
        # 패턴 길이 1-3까지 확인
        pattern_found = False
        
        for pattern_length in range(1, min(4, len(segments) - i)):
            # 현재 위치에서 패턴 추출
            pattern = segments[i:i + pattern_length]
            
            # 패턴이 얼마나 반복되는지 확인
            repeat_count = 0
            j = i
            
            while j + pattern_length <= len(segments):
                if segments[j:j + pattern_length] == pattern:
                    repeat_count += 1
                    j += pattern_length
                else:
                    break
            
            # 3번 이상 반복되면 패턴으로 간주
            if repeat_count >= 3:
                result.extend(pattern)
                i = j
                pattern_found = True
                break
        
        if not pattern_found:
            result.append(current_segment)
            i += 1
    
    return result

def advanced_clean_subtitle(raw_text):
    """고급 자막 정리 함수 - 중복 제거 포함"""
    
    # 1. HTML 태그와 시간 정보 제거
    cleaned = re.sub(r'<[^>]+>', '', raw_text)
    cleaned = re.sub(r'\[음악\]', '♪', cleaned)
    
    # 2. 연속된 공백을 하나로
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    # 3. 문장 단위로 분할
    sentences = re.split(r'[.!?。]', cleaned)
    
    # 4. 중복 제거를 위한 OrderedDict 사용
    unique_sentences = OrderedDict()
    
    for sentence in sentences:
        sentence = sentence.strip()
        
        # 너무 짧은 조각 제거
        if len(sentence) < 10:
            continue
        
        # 의미있는 문장만 추가
        if is_meaningful_sentence(sentence):
            # 중복 체크 (유사한 문장 제거)
            if not is_duplicate_sentence(sentence, unique_sentences):
                unique_sentences[sentence] = True
    
    # 5. 최종 텍스트 생성
    final_sentences = []
    for sentence in unique_sentences.keys():
        final_sentences.append(sentence.strip() + '.')
    
    return '\n\n'.join(final_sentences)

def is_meaningful_sentence(sentence):
    """의미있는 문장인지 판단"""
    # 단순 반복이나 의미없는 단어들 제거
    meaningless_patterns = [
        r'^(네|아|어|음|그|이|저|요|해|할|된|되|수|것|걸|를|을|이|가|의|에|로|으로|와|과|도|만|부터|까지|에서|에게|한테|보다|처럼|같이|마다|마저|조차|라도|든지|거나)\s*$',
        r'^[ㄱ-ㅎㅏ-ㅣ]+$',  # 자음, 모음만
        r'^\s*$',  # 공백만
    ]
    
    for pattern in meaningless_patterns:
        if re.match(pattern, sentence):
            return False
    
    return True

def is_duplicate_sentence(new_sentence, existing_sentences):
    """중복 문장인지 확인 (유사도 기반)"""
    for existing in existing_sentences.keys():
        # 완전히 같은 경우
        if new_sentence == existing:
            return True
        
        # 유사도 체크
        similarity = calculate_text_similarity(new_sentence, existing)
        if similarity > 0.8:  # 80% 이상 유사하면 중복으로 간주
            return True
    
    return False

def calculate_text_similarity(text1, text2):
    """두 텍스트의 유사도 계산 (개선된 버전)"""
    if not text1 or not text2:
        return 0
    
    # 길이가 너무 다르면 유사도 낮음
    len_ratio = min(len(text1), len(text2)) / max(len(text1), len(text2))
    if len_ratio < 0.5:
        return 0
    
    # 단어 단위로 비교
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return 0
    
    # 교집합과 합집합으로 유사도 계산
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0

@app.route('/')
def index():
    """메인 페이지"""
    with open('youtube_subtitle_extractor.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    return html_content

@app.route('/manifest.json')
def manifest():
    """PWA 매니페스트 파일"""
    with open('manifest.json', 'r', encoding='utf-8') as f:
        manifest_content = f.read()
    response = app.response_class(
        response=manifest_content,
        status=200,
        mimetype='application/json'
    )
    return response

@app.route('/sw.js')
def service_worker():
    """Service Worker 파일"""
    with open('sw.js', 'r', encoding='utf-8') as f:
        sw_content = f.read()
    response = app.response_class(
        response=sw_content,
        status=200,
        mimetype='application/javascript'
    )
    return response

@app.route('/extract', methods=['POST', 'OPTIONS'])
def extract_subtitle():
    """자막 추출 API"""
    # OPTIONS 요청 처리 (CORS preflight)
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        headers = response.headers
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL이 제공되지 않았습니다.'}), 400
        
        # 비디오 ID 추출
        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({'error': '올바른 YouTube URL이 아닙니다.'}), 400
        
        # yt-dlp 설치 확인
        try:
            subprocess.run(['yt-dlp', '--version'], 
                         capture_output=True, text=True, shell=True, check=True)
        except subprocess.CalledProcessError:
            return jsonify({'error': 'yt-dlp가 설치되지 않았습니다. pip install yt-dlp로 설치해주세요.'}), 500
        
        # 임시 디렉토리 생성
        with tempfile.TemporaryDirectory() as temp_dir:
            # 자막 다운로드 명령
            cmd = [
                'yt-dlp',
                '--write-subs',
                '--write-auto-subs',
                '--sub-langs', 'ko,en',
                '--skip-download',
                '--sub-format', 'vtt',
                '-o', os.path.join(temp_dir, 'subtitle_%(id)s.%(ext)s'),
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
            if result.returncode != 0:
                return jsonify({'error': f'자막 다운로드 실패: {result.stderr}'}), 500
            
            # 다운로드된 자막 파일 찾기
            possible_files = [
                os.path.join(temp_dir, f'subtitle_{video_id}.ko.vtt'),
                os.path.join(temp_dir, f'subtitle_{video_id}.en.vtt'),
                os.path.join(temp_dir, f'subtitle_{video_id}.vtt')
            ]
            
            subtitle_content = None
            language = None
            
            for filename in possible_files:
                if os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # VTT에서 텍스트만 추출 - 개선된 방식
                    subtitle_content = extract_text_from_vtt(content)
                    
                    # 언어 판별
                    if '.ko.' in filename:
                        language = '한국어 (자동 생성) - 중복 제거됨'
                    elif '.en.' in filename:
                        language = '영어 (자동 생성) - 중복 제거됨'
                    else:
                        language = '자동 생성 - 중복 제거됨'
                    
                    break
            
            if not subtitle_content:
                return jsonify({'error': '사용 가능한 자막을 찾을 수 없습니다.'}), 404
            
            # 고급 텍스트 정리 (중복 제거 포함)
            cleaned_text = advanced_clean_subtitle(subtitle_content)
            
            return jsonify({
                'success': True,
                'video_id': video_id,
                'subtitle': cleaned_text,
                'language': language,
                'length': len(cleaned_text)
            })
            
    except Exception as e:
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

if __name__ == '__main__':
    print("🎬 YouTube 자막 추출기 서버 시작! (중복 제거 기능 포함)")
    print("📱 브라우저에서 http://localhost:5000 을 열어주세요!")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)  # 모든 인터페이스에서 접근 가능

# Vercel을 위한 WSGI app export
application = app 