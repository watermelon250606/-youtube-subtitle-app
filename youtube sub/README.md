# 🎬 YouTube 자막 추출기

중복 제거 기능이 포함된 YouTube 자막 추출 웹앱입니다.

## ✨ 주요 기능

- 🔗 YouTube URL로 자막 추출
- 🧹 중복 문장 자동 제거
- 📱 모바일 반응형 디자인
- 📋 원클릭 복사 기능
- 💾 파일 다운로드 지원
- 🌐 한국어/영어 자막 지원

## 🚀 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python app.py

# 브라우저에서 접속
# http://localhost:5000
```

## 🌐 배포

### Vercel 배포
1. GitHub에 코드 업로드
2. [Vercel](https://vercel.com)에서 Import Project
3. 자동 배포 완료!

### 필요 조건
- Python 3.11+
- yt-dlp 지원 환경

## 📁 파일 구조

```
├── app.py                          # Flask 백엔드
├── youtube_subtitle_extractor.html # 프론트엔드
├── requirements.txt                # Python 의존성
├── vercel.json                     # Vercel 설정
├── runtime.txt                     # Python 버전
└── README.md                       # 이 파일
```

## 🛠️ 기술 스택

- **Backend**: Flask, yt-dlp
- **Frontend**: HTML5, CSS3, JavaScript
- **Deployment**: Vercel

## 📝 사용법

1. YouTube URL 입력
2. "자막 추출" 버튼 클릭
3. 깔끔한 자막 텍스트 확인
4. 복사 또는 다운로드

## 🔧 고급 기능

- **중복 제거**: 80% 이상 유사한 문장 자동 제거
- **의미 필터링**: 불필요한 단어/문장 자동 제거
- **스마트 정리**: 문장 단위로 깔끔하게 정리

---

Made with ❤️ for better subtitle experience 