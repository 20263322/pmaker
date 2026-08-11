import streamlit as st
import fitz  # PyMuPDF
import glob
import os
import re
import random
import io

st.set_page_config(page_title="맞춤형 시험지 생성기", page_icon="📝", layout="centered")

PROBLEMS_DIR = "problems"
os.makedirs(PROBLEMS_DIR, exist_ok=True)

st.title("📝 수능/모의고사 맞춤형 시험지 생성기")
st.caption("연도/월별 조건 필터링부터 정답 및 출처표 자동 첨부까지 지원합니다.")

def parse_file_info(filepath):
    """파일명에서 연도, 월, 문제 번호를 추출 (예: 2026_06_q12.png)"""
    filename = os.path.basename(filepath)
    match = re.search(r'(\d{4})_([A-Za-z0-9]+)_q(\d{2})\.png$', filename)
    if match:
        year = match.group(1)
        exam_type = match.group(2)
        q_num = int(match.group(3))
        
        exam_str = f"{int(exam_type):02d}월" if exam_type.isdigit() else exam_type
        source_str = f"{year}년 {exam_str} {q_num}번"
        
        return {
            "path": filepath,
            "filename": filename,
            "year": year,
            "exam": exam_str,
            "q_num": q_num,
            "source_str": source_str
        }
    return None

# 모든 문제 로드 및 정보 파싱
raw_files = sorted(glob.glob(os.path.join(PROBLEMS_DIR, "*.png")))
all_problems = [parse_file_info(f) for f in raw_files if parse_file_info(f) is not None]

if not all_problems:
    st.error("⚠️ `problems/` 폴더에 조건에 맞는 문제 이미지(.png)가 없습니다.")
    st.info("파일명이 `2026_06_q12.png` 형식으로 올바르게 저장되어 있는지 확인해 주세요.")
else:
    st.success(f"📂 현재 **총 {len(all_problems)}개**의 문제를 보유 중입니다.")

    st.subheader("1. 연도 및 월 필터 선택")
    
    # 1. 연도 필터링
    available_years = sorted(list(set(p["year"] for p in all_problems)))
    selected_year = st.selectbox("연도 선택", ["전체 연도"] + available_years)

    # 연도 필터 적용
    if selected_year != "전체 연도":
        year_filtered = [p for p in all_problems if p["year"] == selected_year]
    else:
        year_filtered = all_problems

    # 2. 월 필터링
    available_exams = sorted(list(set(p["exam"] for p in year_filtered)))
    selected_exam = st.selectbox("월/시험 선택", ["전체 월"] + available_exams)

    # 월 필터 적용
    if selected_exam != "전체 월":
        filtered_pool = [p for p in year_filtered if p["exam"] == selected_exam]
    else:
        filtered_pool = year_filtered

    st.info(f"🔍 필터링 조건 결과: 총 **{len(filtered_pool)}개**의 문제가 검색되었습니다.")

    st.markdown("---")
    st.subheader("2. 문제 구성 조건 선택")

    mode = st.radio("추출 방식 선택", ["특정 문제 번호 고르기", "완전 랜덤 추출"])

    selected_problems = []

    if mode == "특정 문제 번호 고르기":
        available_q_nums = sorted(list(set(p["q_num"] for p in filtered_pool)))
        
        target_nums = st.multiselect(
            "원하는 문제 번호를 선택하세요 (복수 선택 가능)",
            options=available_q_nums,
            default=available_q_nums[:1] if available_q_nums else []
        )

        q_filtered = [p for p in filtered_pool if p["q_num"] in target_nums]

        if q_filtered:
            st.write(f"👉 조건에 해당하는 문제가 총 **{len(q_filtered)}개** 있습니다.")
            sub_choice = st.radio("출력 방식", ["해당 문제 전부 넣기", "이 중 원하는 개수만 랜덤 추출"])
            
            if sub_choice == "해당 문제 전부 넣기":
                selected_problems = q_filtered
            else:
                cnt = st.number_input("원하는 문제 수", min_value=1, max_value=len(q_filtered), value=min(4, len(q_filtered)))
                selected_problems = random.sample(q_filtered, cnt)
        else:
            st.warning("선택하신 번호에 해당하는 문제가 없습니다.")

    else: # 완전 랜덤
        if filtered_pool:
            cnt = st.number_input("원하는 총 문제 수", min_value=1, max_value=len(filtered_pool), value=min(4, len(filtered_pool)))
            selected_problems = random.sample(filtered_pool, cnt)

    # A4 2단 시험지 + 출처 표기 + 정답/출처표 생성 함수
    def create_exam_and_answer_pdf(problems):
        doc = fitz.open()
        a4_w, a4_h = 595.27, 841.89  # A4 규격 (pt)
        margin = 30
        col_w = (a4_w - (margin * 2) - 20) / 2
        max_h = a4_h - margin - 80

        # --- Part 1: 시험지 본문 생성 ---
        for i in range(0, len(problems), 2):
            page = doc.new_page(width=a4_w, height=a4_h)

            # 헤더
            page.insert_text(fitz.Point(a4_w/2 - 75, 40), "수학 영역 맞춤 모의고사", fontsize=14, fontname="helv")
            page.draw_line(fitz.Point(margin, 52), fitz.Point(a4_w - margin, 52), width=1.2)

            # 왼쪽 문제 (1번)
            p1 = problems[i]
            pix1 = fitz.Pixmap(p1["path"])
            aspect1 = pix1.height / pix1.width
            target_h1 = min(col_w * aspect1, max_h)

            # 상단 문항 번호 + 출처 표기
            label_text1 = f"Question {i+1}   [{p1['source_str']}]"
            page.insert_text(fitz.Point(margin, 70), label_text1, fontsize=9.5, fontname="helv")
            
            rect1 = fitz.Rect(margin, 78, margin + col_w, 78 + target_h1)
            page.insert_image(rect1, filename=p1["path"])

            # 오른쪽 문제 (2번)
            if i + 1 < len(problems):
                p2 = problems[i+1]
                pix2 = fitz.Pixmap(p2["path"])
                aspect2 = pix2.height / pix2.width
                target_h2 = min(col_w * aspect2, max_h)

                right_x = margin + col_w + 20
                label_text2 = f"Question {i+2}   [{p2['source_str']}]"
                page.insert_text(fitz.Point(right_x, 70), label_text2, fontsize=9.5, fontname="helv")
                
                rect2 = fitz.Rect(right_x, 78, right_x + col_w, 78 + target_h2)
                page.insert_image(rect2, filename=p2["path"])

            # 중앙 구분선
            page.draw_line(fitz.Point(a4_w/2, 60), fitz.Point(a4_w/2, a4_h - margin), color=(0.85, 0.85, 0.85), width=0.5)

        # --- Part 2: 맨 뒤 정답 및 출처 확인표 페이지 추가 ---
        ans_page = doc.new_page(width=a4_w, height=a4_h)
        ans_page.insert_text(fitz.Point(a4_w/2 - 85, 45), "[ 정답 및 출처 확인표 ]", fontsize=14, fontname="helv")
        ans_page.draw_line(fitz.Point(margin, 60), fitz.Point(a4_w - margin, 60), width=1.2)

        start_y = 85
        row_height = 24
        
        # 표 헤더
        ans_page.insert_text(fitz.Point(margin + 10, start_y), "시험지 번호", fontsize=10, fontname="helv")
        ans_page.insert_text(fitz.Point(margin + 120, start_y), "원문항 출처", fontsize=10, fontname="helv")
        ans_page.insert_text(fitz.Point(margin + 320, start_y), "정답 확인 / 비고", fontsize=10, fontname="helv")
        ans_page.draw_line(fitz.Point(margin, start_y + 8), fitz.Point(a4_w - margin, start_y + 8), width=0.8)

        # 표 내용 채우기
        current_y = start_y + 25
        for idx, p in enumerate(problems, 1):
            ans_page.insert_text(fitz.Point(margin + 20, current_y), f"문항 {idx:02d}", fontsize=9.5, fontname="helv")
            ans_page.insert_text(fitz.Point(margin + 120, current_y), p["source_str"], fontsize=9.5, fontname="helv")
            ans_page.insert_text(fitz.Point(margin + 320, current_y), "(   )", fontsize=9.5, fontname="helv")
            
            ans_page.draw_line(fitz.Point(margin, current_y + 6), fitz.Point(a4_w - margin, current_y + 6), color=(0.9, 0.9, 0.9), width=0.5)
            current_y += row_height

            # 페이지를 넘어가면 새 페이지 생성
            if current_y > a4_h - 50 and idx < len(problems):
                ans_page = doc.new_page(width=a4_w, height=a4_h)
                current_y = 60

        pdf_buffer = io.BytesIO()
        doc.save(pdf_buffer)
        doc.close()
        return pdf_buffer.getvalue()

    st.markdown("---")
    
    if selected_problems:
        st.write(f"총 **{len(selected_problems)}개**의 문제가 선택되었습니다.")
        pdf_data = create_exam_and_answer_pdf(selected_problems)
        st.download_button(
            label="📄 시험지 및 답지(출처표) PDF 다운로드",
            data=pdf_data,
            file_name="Custom_Math_Exam_With_Answers.pdf",
            mime="application/pdf"
        )
