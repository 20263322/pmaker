import streamlit as st
import fitz  # PyMuPDF
import glob
import os
import re
import random
import io

st.set_page_config(page_title="1초 시험지 생성기", page_icon="📝")

PROBLEMS_DIR = "problems"
os.makedirs(PROBLEMS_DIR, exist_ok=True)

st.title("📝 맞춤형 시험지 생성기")
st.caption("저장된 문제 중 원하는 번호와 수량만 고르면 A4 2단 시험지를 즉시 만들어 드립니다.")

# 1. 보유 중인 PNG 문제 파일 자동 로드
all_files = sorted(glob.glob(os.path.join(PROBLEMS_DIR, "*.png")))

def parse_q_num(filepath):
    """파일명에서 문제 번호 추출 (예: 2026_06_q12.png -> 12)"""
    match = re.search(r'_q(\d{2})\.png$', os.path.basename(filepath))
    return int(match.group(1)) if match else None

if not all_files:
    st.error("⚠️ `problems/` 폴더에 저장된 문제 이미지(.png)가 없습니다.")
    st.info("GitHub 저장소의 `problems/` 폴더 안에 문제 이미지들을 먼저 올려주세요!")
else:
    st.success(f"📂 현재 **총 {len(all_files)}개**의 문제를 보유 중입니다.")

    # 2. 조건 선택 영역
    st.subheader("⚙️ 시험지 구성 조건")
    mode = st.radio("추출 방식 선택", ["특정 문제 번호 고르기", "완전 랜덤 추출"])

    selected_files = []

    if mode == "특정 문제 번호 고르기":
        # 보유 중인 문제 번호 목록 자동 추출
        available_nums = sorted(list(set(parse_q_num(f) for f in all_files if parse_q_num(f) is not None)))
        
        target_nums = st.multiselect(
            "원하는 문제 번호를 선택하세요 (복수 선택 가능)",
            options=available_nums,
            default=available_nums[:1] if available_nums else []
        )

        filtered = [f for f in all_files if parse_q_num(f) in target_nums]

        if filtered:
            st.info(f"👉 선택한 [{', '.join(map(str, target_nums))}]번 문제가 **총 {len(filtered)}개** 존재합니다.")
            
            sub_choice = st.radio("출력 방식", ["해당 문제 전부 넣기", "이 중 원하는 개수만 랜덤 추출"])
            
            if sub_choice == "해당 문제 전부 넣기":
                selected_files = filtered
            else:
                cnt = st.number_input("원하는 문제 수", min_value=1, max_value=len(filtered), value=min(4, len(filtered)))
                selected_files = random.sample(filtered, cnt)
        else:
            st.warning("선택하신 번호에 해당하는 문제가 없습니다.")

    else: # 완전 랜덤
        cnt = st.number_input("원하는 총 문제 수", min_value=1, max_value=len(all_files), value=min(4, len(all_files)))
        selected_files = random.sample(all_files, cnt)

    # 3. A4 2단 PDF 생성 함수
    def create_pdf(files):
        doc = fitz.open()
        a4_w, a4_h = 595.27, 841.89  # A4 규격 포인트
        margin = 30
        col_w = (a4_w - (margin * 2) - 20) / 2

        for i in range(0, len(files), 2):
            page = doc.new_page(width=a4_w, height=a4_h)

            # 상단 헤더
            page.insert_text(fitz.Point(a4_w/2 - 80, 40), "수학 영역 맞춤 모의고사", fontsize=15, fontname="helv")
            page.draw_line(fitz.Point(margin, 52), fitz.Point(a4_w - margin, 52), width=1.5)

            # 왼쪽 문제 (1번/3번/5번...)
            f1 = files[i]
            page.insert_text(fitz.Point(margin, 70), f"Question {i+1}", fontsize=11)
            rect1 = fitz.Rect(margin, 80, margin + col_w, a4_h - margin)
            page.insert_image(rect1, filename=f1, keep_proportion=True)

            # 오른쪽 문제 (2번/4번/6번...)
            if i + 1 < len(files):
                f2 = files[i+1]
                right_x = margin + col_w + 20
                page.insert_text(fitz.Point(right_x, 70), f"Question {i+2}", fontsize=11)
                rect2 = fitz.Rect(right_x, 80, right_x + col_w, a4_h - margin)
                page.insert_image(rect2, filename=f2, keep_proportion=True)

            # 세로 중앙 구분선
            page.draw_line(fitz.Point(a4_w/2, 60), fitz.Point(a4_w/2, a4_h - margin), color=(0.85, 0.85, 0.85), width=0.5)

        pdf_buffer = io.BytesIO()
        doc.save(pdf_buffer)
        doc.close()
        return pdf_buffer.getvalue()

    st.markdown("---")
    
    # 4. 다운로드 버튼
    if selected_files:
        st.write(f"총 **{len(selected_files)}개**의 문제가 선택되었습니다.")
        pdf_data = create_pdf(selected_files)
        st.download_button(
            label="📄 완성된 시험지 PDF 다운로드",
            data=pdf_data,
            file_name="Custom_Math_Exam.pdf",
            mime="application/pdf"
        )