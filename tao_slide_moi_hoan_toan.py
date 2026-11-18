# -*- coding: utf-8 -*-
"""
Trình tạo Slide Bảo vệ Đồ án / Luận văn Tốt nghiệp (Phiên bản Mới Hoàn Toàn)
Thiết kế: Modern Executive Dark & Split-Tone Bento Architecture
Không sử dụng bất kỳ khung chờ (placeholder) nào — 100% biểu đồ thực nghiệm IEEE 300 DPI,
bảng biểu gốc PowerPoint (Native Table) và sơ đồ khối vector trực quan.
"""

import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUTPUT_PPTX = "Slide_Bao_Ve_Do_An_SmartCamera_Moi.pptx"

# ==============================================================================
# BẢNG MÀU THIẾT KẾ MỚI (EXECUTIVE CYBER-SECURITY & EMERALD/CYAN THEME)
# ==============================================================================
C_DARK_BG      = RGBColor(0x0B, 0x11, 0x20)  # Nền Dark Slate Midnight
C_DARK_CARD    = RGBColor(0x13, 0x1C, 0x31)  # Thẻ trên nền tối
C_DARK_BORDER  = RGBColor(0x1E, 0x29, 0x3B)  # Viền trên nền tối
C_LIGHT_BG     = RGBColor(0xF1, 0xF5, 0xF9)  # Nền sáng Slate-100 hiện đại
C_WHITE        = RGBColor(0xFF, 0xFF, 0xFF)
C_PANEL_DARK   = RGBColor(0x0F, 0x17, 0x2A)  # Cột bên tối (Split layout)
C_BORDER       = RGBColor(0xCB, 0xD5, 0xE1)

# Màu nhấn (Accents)
C_EMERALD      = RGBColor(0x10, 0xB9, 0x81)  # Xanh ngọc lục bảo
C_EMERALD_DARK = RGBColor(0x04, 0x78, 0x57)
C_EMERALD_SOFT = RGBColor(0xEC, 0xFD, 0xF5)
C_CYAN         = RGBColor(0x06, 0xB6, 0xD4)  # Xanh Cyan công nghệ
C_CYAN_DARK    = RGBColor(0x0E, 0x74, 0x90)
C_CYAN_SOFT    = RGBColor(0xEC, 0xFE, 0xFF)
C_INDIGO       = RGBColor(0x4F, 0x46, 0xE5)  # Tím Indigo hiện đại
C_INDIGO_SOFT  = RGBColor(0xEE, 0xF2, 0xFF)
C_AMBER        = RGBColor(0xF5, 0x9E, 0x0B)  # Vàng hổ phách
C_AMBER_DARK   = RGBColor(0xB4, 0x53, 0x09)
C_AMBER_SOFT   = RGBColor(0xFF, 0xFB, 0xEB)
C_ROSE         = RGBColor(0xE1, 0x1D, 0x48)  # Đỏ Rose cảnh báo
C_ROSE_SOFT    = RGBColor(0xFF, 0xF1, 0xF2)

# Màu chữ
C_TEXT_MAIN    = RGBColor(0x0F, 0x17, 0x2A)
C_TEXT_BODY    = RGBColor(0x33, 0x41, 0x55)
C_TEXT_MUTED   = RGBColor(0x64, 0x74, 0x8B)
C_TEXT_LIGHT   = RGBColor(0xF8, 0xFA, 0xFC)
C_TEXT_DIM     = RGBColor(0x94, 0xA3, 0xB8)

FONT_MAIN = "Segoe UI"


# ==============================================================================
# HÀM TIỆN ÍCH VẼ KHUNG & BỐ CỤC ĐỘC QUYỀN
# ==============================================================================
def new_slide(prs, dark=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = C_DARK_BG if dark else C_LIGHT_BG
    bg.line.fill.background()
    return slide


def add_rect(slide, x, y, w, h, fill_rgb, border_rgb=None, border_pt=1.0, rounded=False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    sh = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill_rgb
    if border_rgb is not None:
        sh.line.color.rgb = border_rgb
        sh.line.width = Pt(border_pt)
    else:
        sh.line.fill.background()
    if rounded and hasattr(sh, "adjustments") and len(sh.adjustments) > 0:
        sh.adjustments[0] = 0.04
    return sh


def add_text(slide, x, y, w, h, text, size=12, bold=False, color=C_TEXT_MAIN, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    p = tf.paragraphs[0]
    p.text = text
    p.font.name = FONT_MAIN
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.alignment = align
    return tf


def add_bullets(slide, x, y, w, h, items, size=11, color=C_TEXT_BODY, bullet_char="▸ ", title=None, title_color=C_TEXT_MAIN, title_size=12.5):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.05)
    tf.margin_right = Inches(0.05)
    tf.margin_top = Inches(0.04)
    tf.margin_bottom = Inches(0.04)
    first = True
    if title:
        p0 = tf.paragraphs[0]
        p0.text = title
        p0.font.name = FONT_MAIN
        p0.font.size = Pt(title_size)
        p0.font.bold = True
        p0.font.color.rgb = title_color
        p0.space_after = Pt(6)
        first = False
    for item in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = f"{bullet_char}{item}" if bullet_char else item
        p.font.name = FONT_MAIN
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.space_after = Pt(5)
    return tf


def add_chrome(slide, chapter_num, chapter_name, slide_title, page_no, total_pages=18, accent=C_EMERALD):
    """
    Thanh điều hướng dọc bên trái (Left Navigation Rail) + Top Header Bar hiện đại
    """
    # Left rail
    add_rect(slide, 0, 0, 0.22, 7.5, C_PANEL_DARK)
    add_rect(slide, 0, 0, 0.22, 1.15, accent)

    # Top bar
    add_rect(slide, 0.22, 0, 13.113, 1.05, C_WHITE, border_rgb=C_BORDER, border_pt=0.75)

    # Pill chapter badge
    pill = add_rect(slide, 0.50, 0.14, 2.75, 0.26, C_PANEL_DARK, rounded=True)
    tf_p = pill.text_frame
    p_p = tf_p.paragraphs[0]
    p_p.text = f"CHƯƠNG {chapter_num}  •  {chapter_name.upper()}"
    p_p.font.name = FONT_MAIN
    p_p.font.size = Pt(8.5)
    p_p.font.bold = True
    p_p.font.color.rgb = accent
    p_p.alignment = PP_ALIGN.CENTER

    # Main slide title
    add_text(slide, 0.48, 0.43, 11.2, 0.52, slide_title, size=19.5, bold=True, color=C_TEXT_MAIN)

    # Page counter badge on right
    pg_box = add_rect(slide, 12.10, 0.26, 0.90, 0.48, C_LIGHT_BG, border_rgb=C_BORDER, rounded=True)
    tf_pg = pg_box.text_frame
    p_pg = tf_pg.paragraphs[0]
    p_pg.text = f"{page_no:02d} / {total_pages}"
    p_pg.font.name = FONT_MAIN
    p_pg.font.size = Pt(10.5)
    p_pg.font.bold = True
    p_pg.font.color.rgb = C_TEXT_MAIN
    p_pg.alignment = PP_ALIGN.CENTER

    # Bottom status bar
    add_rect(slide, 0.22, 7.15, 13.113, 0.35, C_PANEL_DARK)
    add_text(
        slide, 0.48, 7.20, 8.5, 0.25,
        "ĐỒ ÁN TỐT NGHIỆP MSE  |  HỆ THỐNG SMART CAMERA GIÁM SÁT ĐA NGUY CƠ BIÊN (EDGE AI)",
        size=8.5, bold=True, color=C_TEXT_DIM
    )
    add_text(
        slide, 9.0, 7.20, 4.05, 0.25,
        "HV: Nguyễn Văn Toàn (MSE26HCM)  •  GVHD: TS. Đoàn Xuân Huy Minh",
        size=8.5, bold=False, color=accent, align=PP_ALIGN.RIGHT
    )


def add_feature_box(slide, x, y, w, h, badge_txt, title, lines, accent=C_EMERALD, dark_card=False):
    bg = C_PANEL_DARK if dark_card else C_WHITE
    bd = C_DARK_BORDER if dark_card else C_BORDER
    t_col = C_TEXT_LIGHT if dark_card else C_TEXT_MAIN
    b_col = C_TEXT_DIM if dark_card else C_TEXT_BODY

    add_rect(slide, x, y, w, h, bg, border_rgb=bd, border_pt=1.0, rounded=True)
    # Top accent bar inside card
    add_rect(slide, x, y, w, 0.08, accent)

    # Badge
    b = add_rect(slide, x + 0.18, y + 0.20, 0.44, 0.36, accent, rounded=True)
    p = b.text_frame.paragraphs[0]
    p.text = badge_txt
    p.font.name = FONT_MAIN
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = C_WHITE
    p.alignment = PP_ALIGN.CENTER

    add_text(slide, x + 0.70, y + 0.19, w - 0.85, 0.42, title, size=12.5, bold=True, color=t_col)
    add_bullets(slide, x + 0.18, y + 0.65, w - 0.36, h - 0.75, lines, size=10.2, color=b_col, bullet_char="• ")


def add_kpi_tile(slide, x, y, w, h, big_val, label, sub, accent=C_EMERALD, dark=True):
    bg = C_PANEL_DARK if dark else C_WHITE
    bd = accent if dark else C_BORDER
    add_rect(slide, x, y, w, h, bg, border_rgb=bd, border_pt=1.2, rounded=True)
    add_rect(slide, x, y, 0.10, h, accent)
    add_text(slide, x + 0.20, y + 0.10, w - 0.30, 0.50, big_val, size=22, bold=True, color=accent)
    add_text(slide, x + 0.20, y + 0.62, w - 0.30, 0.28, label, size=10.5, bold=True, color=C_TEXT_LIGHT if dark else C_TEXT_MAIN)
    add_text(slide, x + 0.20, y + 0.90, w - 0.30, 0.32, sub, size=9.0, bold=False, color=C_TEXT_DIM if dark else C_TEXT_MUTED)


def style_table(table, headers, rows, col_widths=None, header_bg=C_PANEL_DARK, accent_col=None):
    if col_widths:
        for idx, w in enumerate(col_widths):
            table.columns[idx].width = Inches(w)
    for c_idx, h_text in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = header_bg
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.text = h_text
        p.font.name = FONT_MAIN
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = C_WHITE
        p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT

    for r_idx, r_data in enumerate(rows):
        is_last_highlight = (r_idx == len(rows) - 1 and accent_col is not None)
        row_bg = C_EMERALD_SOFT if is_last_highlight else (C_WHITE if r_idx % 2 == 0 else C_LIGHT_BG)
        for c_idx, val in enumerate(r_data):
            cell = table.cell(r_idx + 1, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = row_bg
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.text = str(val)
            p.font.name = FONT_MAIN
            p.font.size = Pt(9.8)
            p.font.bold = is_last_highlight or (c_idx == 0)
            p.font.color.rgb = C_EMERALD_DARK if is_last_highlight else C_TEXT_MAIN
            p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT


def add_picture_fitted(slide, path, x, y, max_w, max_h):
    """Chèn ảnh giữ nguyên tỷ lệ khung hình và căn giữa trong hộp (x, y, max_w, max_h)."""
    if not os.path.exists(path):
        return None
    from PIL import Image
    with Image.open(path) as im:
        iw, ih = im.size
    aspect = iw / float(ih)
    box_aspect = max_w / float(max_h)
    if aspect >= box_aspect:
        w = max_w
        h = max_w / aspect
    else:
        h = max_h
        w = max_h * aspect
    dx = x + (max_w - w) / 2.0
    dy = y + (max_h - h) / 2.0
    return slide.shapes.add_picture(path, Inches(dx), Inches(dy), width=Inches(w), height=Inches(h))


# ==============================================================================
# XÂY DỰNG 18 SLIDES MỚI HOÀN TOÀN
# ==============================================================================
def build_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    TOTAL = 18

    # ==========================================================================
    # SLIDE 1: TRANG BÌA (DARK CYBER-SECURITY EXECUTIVE HERO)
    # ==========================================================================
    s1 = new_slide(prs, dark=True)
    # Decorative geometric accent bars on left & top
    add_rect(s1, 0, 0, 0.30, 7.5, C_EMERALD)
    add_rect(s1, 0.30, 0, 0.10, 7.5, C_CYAN)
    add_rect(s1, 0.40, 0.42, 12.40, 0.04, C_DARK_BORDER)

    # FPT Logo inside white badge
    if os.path.exists("Logo_Trường_Đại_học_FPT.png"):
        add_rect(s1, 0.70, 0.62, 2.35, 0.85, C_WHITE, rounded=True)
        add_picture_fitted(s1, "Logo_Trường_Đại_học_FPT.png", 0.80, 0.68, 2.15, 0.73)

    # Right header tag
    tag1 = add_rect(s1, 8.55, 0.68, 4.25, 0.48, C_DARK_CARD, border_rgb=C_EMERALD, border_pt=1.2, rounded=True)
    p = tag1.text_frame.paragraphs[0]
    p.text = "BẢO VỆ ĐỒ ÁN / LUẬN VĂN TỐT NGHIỆP MSE"
    p.font.name = FONT_MAIN
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = C_EMERALD
    p.alignment = PP_ALIGN.CENTER

    # Subtitle category
    add_text(
        s1, 0.70, 1.72, 12.0, 0.38,
        "CHUYÊN NGÀNH KỸ THUẬT PHẦN MỀM  •  TRƯỜNG ĐẠI HỌC FPT TP. HỒ CHÍ MINH",
        size=11.5, bold=True, color=C_CYAN
    )

    # Main Thesis Title
    add_text(
        s1, 0.70, 2.12, 12.1, 1.55,
        "HỆ THỐNG CAMERA THÔNG MINH DỰA TRÊN IoT\nTÍCH HỢP NHẬN DIỆN KHUÔN MẶT & PHÁT HIỆN BẤT THƯỜNG",
        size=28, bold=True, color=C_WHITE
    )
    add_text(
        s1, 0.70, 3.62, 12.0, 0.45,
        "Edge-Cloud Collaborative Smart Surveillance System on Raspberry Pi 4 with Masked Face Recognition & Multi-Hazard Detection",
        size=13, bold=False, color=C_TEXT_DIM
    )

    # 5 Capability Pills
    pills = [
        ("01", "MTCNN + FaceNet Khẩu trang (1 Ảnh mẫu)", C_EMERALD),
        ("02", "YOLOv8 Phát hiện Té ngã & Cháy khói", C_CYAN),
        ("03", "Hàng rào đa giác ROI & Đệm H.264", C_INDIGO),
        ("04", "GPIO: Khí ga MQ-2, Khóa Solenoid 3s, Còi", C_AMBER),
        ("05", "FastAPI Glassmorphic & Telegram 2 chiều", C_ROSE),
    ]
    for idx, (num, label, col) in enumerate(pills):
        px = 0.70 + idx * 2.44
        add_rect(s1, px, 4.25, 2.32, 0.78, C_DARK_CARD, border_rgb=col, border_pt=1.2, rounded=True)
        add_text(s1, px + 0.10, 4.30, 0.50, 0.25, f"#{num}", size=9.5, bold=True, color=col)
        add_text(s1, px + 0.10, 4.53, 2.12, 0.45, label, size=9.5, bold=True, color=C_WHITE)

    # Bottom Author & Advisor Split Cards
    add_rect(s1, 0.70, 5.32, 5.95, 1.65, C_DARK_CARD, border_rgb=C_DARK_BORDER, border_pt=1.2, rounded=True)
    add_rect(s1, 0.70, 5.32, 0.10, 1.65, C_EMERALD)
    add_text(s1, 0.98, 5.45, 5.5, 0.30, "HỌC VIÊN / SINH VIÊN THỰC HIỆN", size=9.5, bold=True, color=C_EMERALD)
    add_text(s1, 0.98, 5.75, 5.5, 0.45, "Nguyễn Văn Toàn", size=20, bold=True, color=C_WHITE)
    add_text(s1, 0.98, 6.22, 5.5, 0.30, "Lớp: MSE26HCM  |  Chuyên ngành: Kỹ thuật Phần mềm (MSE)", size=11, color=C_TEXT_DIM)
    add_text(s1, 0.98, 6.52, 5.5, 0.30, "Nền tảng triển khai: Raspberry Pi 4 Model B + FastAPI + PyTorch Edge CPU", size=10, color=C_CYAN)

    add_rect(s1, 6.85, 5.32, 5.95, 1.65, C_DARK_CARD, border_rgb=C_DARK_BORDER, border_pt=1.2, rounded=True)
    add_rect(s1, 6.85, 5.32, 0.10, 1.65, C_CYAN)
    add_text(s1, 7.13, 5.45, 5.5, 0.30, "GIẢNG VIÊN HƯỚNG DẪN KHOA HỌC", size=9.5, bold=True, color=C_CYAN)
    add_text(s1, 7.13, 5.75, 5.5, 0.45, "TS. Đoàn Xuân Huy Minh", size=20, bold=True, color=C_WHITE)
    add_text(s1, 7.13, 6.22, 5.5, 0.30, "Đơn vị: Trường Đại học FPT — Phân hiệu TP. Hồ Chí Minh", size=11, color=C_TEXT_DIM)
    add_text(s1, 7.13, 6.52, 5.5, 0.30, "Thời gian hoàn thành: Năm 2026", size=10, color=C_EMERALD)

    # ==========================================================================
    # SLIDE 2: LỘ TRÌNH TRÌNH BÀY (5 CHƯƠNG CHUẨN LUẬN VĂN)
    # ==========================================================================
    s2 = new_slide(prs)
    add_chrome(s2, "0", "Tổng quan", "Cấu Trúc Nội Dung Báo Cáo Bảo Vệ Đồ Án (5 Chương)", 2, TOTAL, C_EMERALD)

    chapters = [
        ("CHƯƠNG 1", "Giới Thiệu & Đặt Vấn Đề", C_EMERALD, [
            "Bối cảnh giám sát an ninh hiện đại & bất cập của mô hình Cloud-only truyền thống.",
            "3 bài toán kỹ thuật cốt lõi tại biên: Góc nghiêng/khẩu trang, nghẽn I/O cảnh báo, giới hạn CPU.",
            "4 mục tiêu định lượng & phạm vi triển khai thực tế của đề tài."
        ]),
        ("CHƯƠNG 2", "Tổng Quan Tài Liệu & Khoảng Trống Nghiên Cứu", C_CYAN, [
            "Kiến trúc tính toán biên – đám mây (Edge-Cloud IoT) tiết kiệm >90% băng thông.",
            "Phân tích họ mô hình YOLO anchor-free, MTCNN 3 tầng & không gian đặc trưng FaceNet.",
            "Xác định khoảng trống nghiên cứu: thiếu khung đa nguy cơ chạy thuần CPU trên Pi 4."
        ]),
        ("CHƯƠNG 3", "Thiết Kế Kiến Trúc & Giải Pháp Kỹ Thuật", C_INDIGO, [
            "Kiến trúc đa luồng với khóa đồng bộ gpu_lock, Lazy Loading & bộ đệm vòng H.264 150 frames.",
            "Nhận diện khuôn mặt đeo khẩu trang chỉ với 1 ảnh mẫu (Zero-out 45% vùng dưới, ngưỡng 0.80).",
            "Tích hợp GPIO (MQ-2, Solenoid 3s, Buzzer), Web Glassmorphic HMAC-SHA256 & Telegram 2 chiều."
        ]),
        ("CHƯƠNG 4", "Thực Nghiệm, Đo Lường & Đối Sánh Hiệu Năng", C_AMBER, [
            "Kiểm thử trên 4 bộ dữ liệu chuẩn (ImViA 42,030 frames, Roboflow Fire, COCO ROI, Face DB).",
            "Đo lường thực tế trên Raspberry Pi 4: 6,5 FPS (1 cam), 3,8 FPS (2 cam), RAM ~846 MB.",
            "Đối sánh vượt trội so với các Baseline (ArcFace, YOLOv8-pose, MobileNet-SSD)."
        ]),
        ("CHƯƠNG 5", "Kết Luận, Đóng Góp & Hướng Phát Triển", C_ROSE, [
            "Tổng hợp 4 đóng góp học thuật và thực tiễn nổi bật của đồ án.",
            "Đánh giá chi phí phần cứng (<3 triệu VNĐ) & tính sẵn sàng thương mại hóa.",
            "Định hướng lượng tử hóa ONNX/TensorRT INT8 và mã hóa đồng cấu bảo vệ sinh trắc học."
        ]),
    ]

    for i, (c_tag, c_title, col, items) in enumerate(chapters):
        y = 1.22 + i * 1.14
        add_rect(s2, 0.48, y, 12.55, 1.02, C_WHITE, border_rgb=C_BORDER, rounded=True)
        add_rect(s2, 0.48, y, 2.15, 1.02, C_PANEL_DARK, rounded=True)
        add_rect(s2, 0.48, y, 0.12, 1.02, col)
        add_text(s2, 0.70, y + 0.15, 1.85, 0.28, c_tag, size=10, bold=True, color=col)
        add_text(s2, 0.70, y + 0.42, 1.85, 0.50, c_title, size=10.5, bold=True, color=C_WHITE)
        add_bullets(s2, 2.78, y + 0.08, 10.10, 0.88, items, size=10.2, color=C_TEXT_BODY, bullet_char="▸ ")

    # ==========================================================================
    # SLIDE 3: CHƯƠNG 1 — BỐI CẢNH & 3 BÀI TOÁN CỐT LÕI
    # ==========================================================================
    s3 = new_slide(prs)
    add_chrome(s3, "1", "Giới thiệu & Đặt vấn đề", "Bối Cảnh Thực Tiễn: Hạn Chế Cloud-Only & 3 Bài Toán Kỹ Thuật Tại Biên", 3, TOTAL, C_EMERALD)

    # Left: Comparison table Cloud-only vs Edge-Cloud
    add_rect(s3, 0.48, 1.22, 6.20, 5.72, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_text(s3, 0.68, 1.35, 5.80, 0.35, "SO SÁNH KIẾN TRÚC GIÁM SÁT TRUYỀN THỐNG VÀ ĐỀ XUẤT", size=12, bold=True, color=C_TEXT_MAIN)

    t_shape = s3.shapes.add_table(6, 3, Inches(0.65), Inches(1.80), Inches(5.85), Inches(3.60))
    style_table(
        t_shape.table,
        ["Tiêu chí kỹ thuật", "Cloud-Only Truyền thống", "Edge-Cloud IoT (Đề xuất)"],
        [
            ["Băng thông (3 cam)", "~12 Mbps (~130 GB/ngày)", "< 0.5 Mbps (Tiết kiệm >95%)"],
            ["Độ trễ phản hồi", "~2,40 giây (Phụ thuộc mạng)", "1,63 giây (Xử lý ngay tại biên)"],
            ["Quyền riêng tư", "Rủi ro lộ video nhạy cảm", "100% xử lý On-Premise nội bộ"],
            ["Lưu trữ sinh trắc", "Lưu ảnh mặt gốc dễ rò rỉ", "Chỉ lưu Vector đặc trưng JSON"],
            ["Khi đứt cáp Internet", "Mất hoàn toàn khả năng AI", "Còi, Khóa & AI cục bộ vẫn chạy"],
        ],
        col_widths=[1.75, 2.05, 2.05],
        accent_col=2
    )

    add_rect(s3, 0.65, 5.58, 5.85, 1.15, C_EMERALD_SOFT, border_rgb=C_EMERALD, rounded=True)
    add_bullets(
        s3, 0.78, 5.65, 5.60, 1.00,
        [
            "Động lực cốt lõi: Chuyển dịch toàn bộ suy luận Deep Learning về nút biên Raspberry Pi 4.",
            "Cloud/Telegram chỉ nhận gói siêu dữ liệu nhẹ (~2 KB JSON + ~150 KB ảnh sự kiện)."
        ],
        size=10, color=C_TEXT_MAIN, title="Kết luận định hướng thiết kế:", title_color=C_EMERALD_DARK, title_size=11
    )

    # Right: 3 Core Technical Problems
    probs = [
        ("P1", "Suy giảm nhận diện do Góc nghiêng & Khẩu trang", C_ROSE, [
            "Camera gắn cao khiến khuôn mặt thường bị quay nghiêng hoặc cúi/ngửa.",
            "Người đeo khẩu trang che khuất 45% vùng mũi–miệng làm sai lệch vector đặc trưng.",
            "Yêu cầu nhận diện chính xác chỉ từ 1 ảnh đăng ký gốc không đeo khẩu trang."
        ]),
        ("P2", "Nghẽn luồng Video do Gửi cảnh báo Đồng bộ (Synchronous I/O)", C_AMBER, [
            "Gọi HTTP POST gửi ảnh/video Telegram trực tiếp trong vòng lặp đọc camera gây treo luồng.",
            "Thực nghiệm cơ sở: FPS tụt xuống 1,2 FPS và đóng băng hình ảnh tới 18,0 giây.",
            "Cần kiến trúc bất đồng bộ tách rời hoàn toàn luồng Capture và luồng Network I/O."
        ]),
        ("P3", "Xung đột Tài nguyên khi Chạy Đa mô hình trên CPU Biên", C_INDIGO, [
            "Chạy đồng thời MTCNN, FaceNet, YOLOv8-fall, YOLOv8-fire, YOLOv5 ROI trên Pi 4 không có GPU rời.",
            "Nếu thực thi song song tự do: CPU chạm 100%, tràn RAM (OOM) và quá nhiệt sau vài phút.",
            "Đòi hỏi cơ chế khóa đồng bộ tuần tự (gpu_lock) và quản lý Singleton + Lazy Loading."
        ]),
    ]
    for idx, (b_txt, title, col, lines) in enumerate(probs):
        add_feature_box(s3, 6.88, 1.22 + idx * 1.94, 6.15, 1.82, b_txt, title, lines, accent=col)

    # ==========================================================================
    # SLIDE 4: CHƯƠNG 1 — MỤC TIÊU ĐỊNH LƯỢNG & PHẠM VI ĐỀ TÀI
    # ==========================================================================
    s4 = new_slide(prs)
    add_chrome(s4, "1", "Mục tiêu & Phạm vi", "4 Mục Tiêu Kỹ Thuật Định Lượng & Phạm Vi Triển Khai Hệ Thống", 4, TOTAL, C_EMERALD)

    goals = [
        ("MỤC TIÊU 01", "Xác thực Khuôn mặt Đa góc nhìn & Khẩu trang", C_EMERALD, [
            "Tinh chỉnh ngưỡng MTCNN 3 tầng [0.5, 0.6, 0.6] kết hợp giảm mẫu 2x tăng tốc 4 lần.",
            "Đối sánh vector đặc trưng FaceNet đa góc nhìn + thuật toán Zero-out 45% mặt dưới.",
            "Đạt độ chính xác xác thực ~98,2% (trực diện) và >83% ở các góc nghiêng 30°–45°."
        ]),
        ("MỤC TIÊU 02", "Phát hiện Đa nguy cơ & Ghi hình Đệm vòng H.264", C_CYAN, [
            "Tích hợp YOLOv8-fall (té ngã), YOLOv8n-fire (lửa/khói), YOLOv5/v8 (xâm nhập ROI).",
            "Duy trì bộ đệm vòng (Circular Buffer) 150 khung hình (~10s) trong RAM cho mỗi kênh.",
            "Tự động kết xuất video sự kiện chuẩn H.264 (avc1) phát trực tiếp trên trình duyệt web."
        ]),
        ("MỤC TIÊU 03", "Điều phối Bất đồng bộ & Ngoại vi IoT Thời gian thực", C_INDIGO, [
            "Xây dựng Daemon Dispatcher + hàng đợi giao dịch ACID SQLite chống mất cảnh báo khi sập nguồn.",
            "Tương tác 2 chiều qua Telegram Long Polling (Mở khóa cửa từ xa, Tắt còi, Tạm dừng cam).",
            "Tích hợp cảm biến khí ga MQ-2 (GPIO 18), khóa Solenoid 3s (GPIO 23), còi Buzzer (GPIO 24)."
        ]),
        ("MỤC TIÊU 04", "Web Dashboard Glassmorphic & Bảo mật HMAC-SHA256", C_AMBER, [
            "Phát triển giao diện quản trị tập trung trên FastAPI hỗ trợ E-Map, Live Stream & Analytics.",
            "Tự xây dựng lớp bảo mật phiên HMACSessionMiddleware (HMAC-SHA256) và băm mật khẩu PBKDF2.",
            "Phân quyền RBAC 3 cấp (SuperAdmin, Admin, Operator) & giám sát Telemetry phần cứng."
        ]),
    ]
    for idx, (tag, title, col, lines) in enumerate(goals):
        gx = 0.48 + (idx % 2) * 6.38
        gy = 1.22 + (idx // 2) * 2.02
        add_feature_box(s4, gx, gy, 6.18, 1.88, str(idx + 1), f"{tag}: {title}", lines, accent=col)

    # Bottom Scope bar
    add_rect(s4, 0.48, 5.30, 6.18, 1.65, C_PANEL_DARK, rounded=True)
    add_rect(s4, 0.48, 5.30, 0.10, 1.65, C_EMERALD)
    add_bullets(
        s4, 0.70, 5.38, 5.80, 1.48,
        [
            "Xử lý đa luồng camera thời gian thực (Webcam USB, RTSP, Video File) tại biên.",
            "Nhận diện khuôn mặt đa góc nhìn/khẩu trang, phát hiện té ngã, cháy khói, xâm nhập ROI, khí ga.",
            "Điều khiển khóa cửa điện từ, còi báo động phân cấp và quản trị toàn diện qua Web + Telegram."
        ],
        size=9.8, color=C_TEXT_LIGHT, title="✔ PHẠM VI BAO GỒM (IN-SCOPE)", title_color=C_EMERALD, title_size=11.5
    )

    add_rect(s4, 6.86, 5.30, 6.18, 1.65, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_rect(s4, 6.86, 5.30, 0.10, 1.65, C_ROSE)
    add_bullets(
        s4, 7.08, 5.38, 5.80, 1.48,
        [
            "Chưa mở rộng mô hình hóa khói/lửa ngoài trời diện rộng dưới điều kiện sương mù cực đoan.",
            "Không phụ thuộc hệ sinh thái đóng bên thứ ba (Apple HomeKit, Google Home, AWS Rekognition).",
            "Giới hạn phần cứng Raspberry Pi 4 ở mức tối ưu 1–2 kênh camera đồng thời (chế độ thuần CPU)."
        ],
        size=9.8, color=C_TEXT_BODY, title="✖ PHẠM VI KHÔNG BAO GỒM & GIỚI HẠN (BOUNDARIES)", title_color=C_ROSE, title_size=11.5
    )

    # ==========================================================================
    # SLIDE 5: CHƯƠNG 2 — TỔNG QUAN NGHIÊN CỨU & KHOẢNG TRỐNG CÔNG NGHỆ
    # ==========================================================================
    s5 = new_slide(prs)
    add_chrome(s5, "2", "Tổng quan tài liệu", "Tổng Quan Nghiên Cứu Hiện Trạng & Khoảng Trống Công Nghệ Giải Quyết", 5, TOTAL, C_CYAN)

    lit_cards = [
        ("L1", "Kiến trúc Edge-Cloud IoT (Shi et al., Chen et al.)", C_CYAN, [
            "Shi et al. (2016) và Gupta et al. (2017) chứng minh đẩy tác vụ thị giác về biên giúp giảm >90% băng thông.",
            "Tuy nhiên, đa số công trình trước chỉ dừng ở mô phỏng hoặc chỉ chạy 1 mô hình đơn lẻ trên thiết bị biên."
        ]),
        ("L2", "Xác thực Khuôn mặt trên Thiết bị Biên (MTCNN, FaceNet, ArcFace)", C_EMERALD, [
            "ArcFace (ResNet-50, 145 MB) đạt độ chính xác 99,4% nhưng mất tới 4.500 ms/mặt trên CPU Pi 4 — không khả thi.",
            "MobileFaceNet (5,2 MB) nhanh (220 ms) nhưng độ chính xác giảm mạnh (91,2%) khi camera đặt xa hoặc nghiêng.",
            "Cặp MTCNN + FaceNet (23 MB) đạt điểm cân bằng lý tưởng: 98,2% chính xác với độ trễ hợp lý trên CPU."
        ]),
        ("L3", "Phát hiện Bất thường Thị giác: Té ngã & Hỏa hoạn (YOLOv8)", C_INDIGO, [
            "YOLOv8-pose (17 khớp xương, 11,6M tham số) chỉ đạt 0,8 FPS trên CPU biên do hồi quy điểm mốc nặng.",
            "Huấn luyện trực tiếp YOLOv8-fall (3,2M tham số) qua tỷ lệ hộp bao & quỹ đạo giúp tăng tốc gấp 3,5 lần (2,8 FPS)."
        ]),
    ]
    for idx, (b_txt, title, col, lines) in enumerate(lit_cards):
        add_feature_box(s5, 0.48, 1.22 + idx * 1.94, 7.35, 1.82, b_txt, title, lines, accent=col)

    # Right column: Research Gap Synthesis dark panel
    add_rect(s5, 8.05, 1.22, 4.98, 5.72, C_PANEL_DARK, rounded=True)
    add_rect(s5, 8.05, 1.22, 4.98, 0.10, C_CYAN)
    add_text(s5, 8.30, 1.45, 4.50, 0.40, "3 KHOẢNG TRỐNG NGHIÊN CỨU", size=14, bold=True, color=C_CYAN)
    add_text(s5, 8.30, 1.82, 4.50, 0.30, "Điểm khác biệt cốt lõi của Đồ án", size=10.5, color=C_TEXT_DIM)

    gaps = [
        ("1. Thiếu khung hợp nhất đa nguy cơ tại biên",
         "Các nghiên cứu hiện tại tách rời bài toán chấm công khuôn mặt, báo cháy, báo ngã và cảm biến khí ga. Đồ án hợp nhất toàn bộ 5 phân hệ trên duy nhất 1 nút Raspberry Pi 4."),
        ("2. Bài toán đeo khẩu trang không cần huấn luyện lại",
         "Thay vì thu thập hàng chục nghìn ảnh đeo khẩu trang để train lại mạng CNN, đề tài đề xuất kỹ thuật chuẩn hóa Zero-out 45% nửa dưới khuôn mặt ngay ở bước tiền xử lý."),
        ("3. Chưa giải quyết triệt để độ bền vận hành 24/7",
         "Đồ án kết hợp khóa đồng bộ gpu_lock, hàng đợi ACID SQLite, tự phục hồi Systemd sau mất điện và điều khiển xung khóa Solenoid 3s chống cháy cuộn hút.")
    ]
    for i, (g_title, g_desc) in enumerate(gaps):
        gy = 2.25 + i * 1.50
        add_rect(s5, 8.28, gy, 4.52, 1.36, C_DARK_CARD, border_rgb=C_DARK_BORDER, rounded=True)
        add_text(s5, 8.42, gy + 0.10, 4.25, 0.32, g_title, size=10.8, bold=True, color=C_EMERALD)
        add_text(s5, 8.42, gy + 0.42, 4.25, 0.88, g_desc, size=9.6, color=C_TEXT_LIGHT)

    # ==========================================================================
    # SLIDE 6: CHƯƠNG 3 — KIẾN TRÚC TỔNG THỂ EDGE-CLOUD IoT (SƠ ĐỒ KHỐI VECTOR)
    # ==========================================================================
    s6 = new_slide(prs)
    add_chrome(s6, "3", "Thiết kế & Triển khai", "Kiến Trúc Tổng Thể Hệ Thống Cộng Tác Edge–Cloud IoT (3 Lớp)", 6, TOTAL, C_INDIGO)

    # Draw 3 architectural columns as native visual diagram
    # Column 1: TẦNG THU NHẬN & NGOẠI VI VẬT LÝ
    add_rect(s6, 0.48, 1.22, 3.65, 5.72, C_WHITE, border_rgb=C_EMERALD, border_pt=1.5, rounded=True)
    add_rect(s6, 0.48, 1.22, 3.65, 0.48, C_EMERALD)
    add_text(s6, 0.58, 1.32, 3.45, 0.30, "1. TẦNG VẬT LÝ & NGOẠI VI (INPUT/IO)", size=11, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)

    io_nodes = [
        ("Luồng Camera Đa Kênh", "Webcam USB (MJPG 640x480)\nLuồng RTSP IP Cam / Video MP4", C_EMERALD_SOFT, C_EMERALD_DARK),
        ("Cảm biến Khí Ga MQ-2", "Chân Digital Output -> GPIO 18 (Pin 12)\nQuét chu kỳ 1s phát hiện rò rỉ LPG/Khói", C_AMBER_SOFT, C_AMBER_DARK),
        ("Khóa Cửa Điện Từ Solenoid 12V", "Điều khiển qua Rơ-le -> GPIO 23 (Pin 16)\nXung HIGH đúng 3.0s tự ngắt chống cháy", C_CYAN_SOFT, C_CYAN_DARK),
        ("Còi Báo Động Active Buzzer", "Chân điều khiển -> GPIO 24 (Pin 18)\nNháy 3 tần số: Cháy 0.1s | Ga 0.3s | Trộm 0.8s", C_ROSE_SOFT, C_ROSE),
    ]
    for idx, (nt, nd, bg_c, bd_c) in enumerate(io_nodes):
        ny = 1.88 + idx * 1.22
        add_rect(s6, 0.68, ny, 3.25, 1.06, bg_c, border_rgb=bd_c, border_pt=1.2, rounded=True)
        add_text(s6, 0.80, ny + 0.08, 3.00, 0.28, nt, size=10.5, bold=True, color=bd_c)
        add_text(s6, 0.80, ny + 0.38, 3.00, 0.62, nd, size=9.3, color=C_TEXT_BODY)

    # Arrow 1 -> 2
    arr1 = s6.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(4.18), Inches(3.85), Inches(0.38), Inches(0.45))
    arr1.fill.solid()
    arr1.fill.fore_color.rgb = C_INDIGO
    arr1.line.fill.background()

    # Column 2: TẦNG XỬ LÝ BIÊN (RASPBERRY PI 4 EDGE AI ENGINE)
    add_rect(s6, 4.62, 1.22, 4.35, 5.72, C_PANEL_DARK, border_rgb=C_INDIGO, border_pt=1.5, rounded=True)
    add_rect(s6, 4.62, 1.22, 4.35, 0.48, C_INDIGO)
    add_text(s6, 4.72, 1.32, 4.15, 0.30, "2. TẦNG XỬ LÝ BIÊN (RASPBERRY PI 4 CPU)", size=11, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)

    edge_nodes = [
        ("ThreadedCamera (Zero-Latency Buffer)", "Đọc phần cứng độc lập 25–30 FPS, xóa trễ V4L2/DirectShow", C_CYAN),
        ("Khóa Đồng Bộ Suy Luận (gpu_lock)", "Tuần tự hóa PyTorch (with torch.no_grad()), giới hạn 2 CPU threads", C_EMERALD),
        ("Tổ Hợp 4 Mô Hình Học Sâu Singleton", "• MTCNN + FaceNet (Khẩu trang 1 ảnh mẫu, L2=0.80)\n• YOLOv8-fall (Té ngã) & YOLOv8n-fire (Cháy/Khói)\n• YOLOv5/v8 Polygon ROI (Xâm nhập vùng cấm)", C_AMBER),
        ("Bộ Đệm Vòng RAM & Luồng Cảnh Báo", "• Circular Buffer 150 frames (~10s) -> Xuất MP4 H.264\n• Ghi ACID SQLite trước -> Daemon Worker gửi Telegram", C_ROSE),
    ]
    for idx, (nt, nd, col) in enumerate(edge_nodes):
        ny = 1.85 + (0 if idx == 0 else (0.98 if idx == 1 else (1.96 if idx == 2 else 3.56)))
        nh = 0.85 if idx < 2 else (1.48 if idx == 2 else 1.25)
        add_rect(s6, 4.82, ny, 3.95, nh, C_DARK_CARD, border_rgb=col, border_pt=1.2, rounded=True)
        add_text(s6, 4.95, ny + 0.06, 3.70, 0.28, nt, size=10.2, bold=True, color=col)
        add_text(s6, 4.95, ny + 0.34, 3.70, nh - 0.38, nd, size=9.1, color=C_TEXT_LIGHT)

    # Arrow 2 -> 3
    arr2 = s6.shapes.add_shape(MSO_SHAPE.LEFT_RIGHT_ARROW, Inches(9.02), Inches(3.85), Inches(0.38), Inches(0.45))
    arr2.fill.solid()
    arr2.fill.fore_color.rgb = C_CYAN
    arr2.line.fill.background()

    # Column 3: TẦNG QUẢN TRỊ WEB & ĐÁM MÂY TELEGRAM
    add_rect(s6, 9.45, 1.22, 3.58, 5.72, C_WHITE, border_rgb=C_CYAN, border_pt=1.5, rounded=True)
    add_rect(s6, 9.45, 1.22, 3.58, 0.48, C_CYAN_DARK)
    add_text(s6, 9.55, 1.32, 3.38, 0.30, "3. TẦNG WEB BACKEND & CLOUD BOT", size=11, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)

    app_nodes = [
        ("FastAPI Server & SQLite (smart_camera.db)", "Bảng User (PBKDF2), FaceRecord (Embedding JSON),\nSystemEventLog (Nhật ký & đường dẫn ảnh/video)", C_INDIGO_SOFT, C_INDIGO),
        ("Giao diện Web Glassmorphism", "Live MJPEG Stream, Bản đồ số E-Map đa tầng,\nĐăng ký khuôn mặt có Live Preview & Xác nhận", C_CYAN_SOFT, C_CYAN_DARK),
        ("Bảo mật HMACSessionMiddleware", "Ký xác thực Cookie bằng HMAC-SHA256 cục bộ,\nPhân quyền RBAC: SuperAdmin / Admin / Operator", C_EMERALD_SOFT, C_EMERALD_DARK),
        ("Telegram Cloud Bot 2 Chiều (Long Polling)", "Nhận ảnh/video cảnh báo tức thì (<1.7s);\nNút Inline mở cửa, tắt còi, bật/tắt từng camera", C_AMBER_SOFT, C_AMBER_DARK),
    ]
    for idx, (nt, nd, bg_c, bd_c) in enumerate(app_nodes):
        ny = 1.88 + idx * 1.22
        add_rect(s6, 9.65, ny, 3.18, 1.06, bg_c, border_rgb=bd_c, border_pt=1.2, rounded=True)
        add_text(s6, 9.77, ny + 0.08, 2.95, 0.28, nt, size=10.2, bold=True, color=bd_c)
        add_text(s6, 9.77, ny + 0.38, 2.95, 0.62, nd, size=9.1, color=C_TEXT_BODY)

    # ==========================================================================
    # SLIDE 7: CHƯƠNG 3 — ĐIỀU PHỐI ĐA LUỒNG, GPU_LOCK & ĐỆM VÒNG H.264
    # ==========================================================================
    s7 = new_slide(prs)
    add_chrome(s7, "3", "Điều phối đa luồng", "Cơ Chế Khóa Đồng Bộ gpu_lock, Tối Ưu Hóa CPU Biên & Đệm Vòng H.264", 7, TOTAL, C_INDIGO)

    # Top flow diagram of pipeline
    add_rect(s7, 0.48, 1.20, 12.55, 2.15, C_PANEL_DARK, rounded=True)
    add_text(s7, 0.70, 1.30, 12.0, 0.32, "LUỒNG XỬ LÝ BẤT ĐỒNG BỘ & ĐỒNG BỘ HÓA SUY LUẬN TRÊN CPU RASPBERRY PI 4", size=11.5, bold=True, color=C_CYAN)

    steps = [
        ("Bước 1: Thu nhận", "ThreadedCamera\nĐọc độc lập 30 FPS\nGiữ frame mới nhất", C_CYAN),
        ("Bước 2: Tiền xử lý", "CLAHE cân bằng sáng\nThu nhỏ ảnh 2x (320x180)\ncho phát hiện mặt", C_EMERALD),
        ("Bước 3: Khóa gpu_lock", "with gpu_lock:\n  with torch.no_grad():\nChạy tuần tự các mô hình", C_AMBER),
        ("Bước 4: Đệm vòng RAM", "Circular deque(150)\nLưu 10 giây gần nhất\nKết xuất H.264 (.mp4)", C_INDIGO),
        ("Bước 5: Cảnh báo ngầm", "Ghi SQLite (ACID)\nDaemon gửi Telegram\nKhông khóa luồng video", C_ROSE),
    ]
    for idx, (st_title, st_desc, col) in enumerate(steps):
        sx = 0.68 + idx * 2.46
        add_rect(s7, sx, 1.72, 2.18, 1.42, C_DARK_CARD, border_rgb=col, border_pt=1.5, rounded=True)
        add_rect(s7, sx, 1.72, 2.18, 0.34, col)
        add_text(s7, sx + 0.08, 1.76, 2.02, 0.28, st_title, size=10, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
        add_text(s7, sx + 0.10, 2.14, 1.98, 0.92, st_desc, size=9.5, color=C_TEXT_LIGHT, align=PP_ALIGN.CENTER)
        if idx < 4:
            ar = s7.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(sx + 2.22), Inches(2.30), Inches(0.20), Inches(0.28))
            ar.fill.solid()
            ar.fill.fore_color.rgb = col
            ar.line.fill.background()

    # Bottom 3 technical cards
    opt_cards = [
        ("1", "Khóa Đồng Bộ gpu_lock & Singleton Model", C_EMERALD, [
            "Mỗi mô hình AI chỉ khởi tạo 1 thực thể duy nhất (Singleton) kết hợp nạp lười (Lazy Loading) khi camera bật tính năng.",
            "Giới hạn torch.set_num_threads(2) và cv2.setNumThreads(1) chống bão hòa ngữ cảnh (context switching) trên 4 nhân ARM Cortex-A72.",
            "Bọc toàn bộ suy luận trong with gpu_lock: và with torch.no_grad(): giúp RAM giữ ổn định ở ~846,5 MB, không bị tràn bộ nhớ."
        ]),
        ("2", "Lập Lịch Giãn Cách Khung Hình (Frame Skipping)", C_CYAN, [
            "Tối ưu riêng cho chế độ CPU Pi 4: YOLO chạy mỗi 3 frames (imgsz=320), Té ngã mỗi 10 frames, Cháy nổ mỗi 12 frames, Khuôn mặt mỗi 20 frames.",
            "Giữa các kỳ suy luận, hệ thống tái sử dụng hộp bao (bounding boxes) gần nhất để vẽ overlay mượt mà mà không tốn chu kỳ CPU.",
            "Tự động điều tiết tốc độ vòng lặp (Frame Rate Throttling) giữ nhiệt độ Pi 4 trong ngưỡng an toàn khi chạy 24/7."
        ]),
        ("3", "Bộ Đệm Vòng H.264 & Chống Mất Cảnh Báo", C_INDIGO, [
            "Mỗi kênh camera duy trì hàng đợi vòng state.frame_buffer gồm 150 khung hình đã xử lý trong RAM.",
            "Khi phát hiện nguy cơ, Worker Thread riêng biệt đóng gói video bằng codec H.264 (avc1, fallback mp4v) xem ngay trên Web & Telegram.",
            "Ghi bản ghi sự kiện vào SQLite trước khi gửi mạng; nếu mất điện giữa chừng, hệ thống tự động quét và gửi bù khi khởi động lại."
        ]),
    ]
    for idx, (num, title, col, lines) in enumerate(opt_cards):
        add_feature_box(s7, 0.48 + idx * 4.22, 3.52, 4.10, 3.42, num, title, lines, accent=col)

    # ==========================================================================
    # SLIDE 8: CHƯƠNG 3 — NHẬN DIỆN KHUÔN MẶT ĐA GÓC NHÌN & KHẨU TRANG 1 ẢNH MẪU
    # ==========================================================================
    s8 = new_slide(prs)
    add_chrome(s8, "3", "Xác thực khuôn mặt", "Nhận Diện Khuôn Mặt Đa Góc Nhìn & Giải Pháp Khẩu Trang Với 1 Ảnh Mẫu", 8, TOTAL, C_EMERALD)

    # Left: Masked Face Zero-out Innovation
    add_rect(s8, 0.48, 1.22, 6.20, 5.72, C_PANEL_DARK, rounded=True)
    add_rect(s8, 0.48, 1.22, 6.20, 0.10, C_EMERALD)
    add_text(s8, 0.72, 1.42, 5.75, 0.38, "ĐỘT PHÁ: NHẬN DIỆN KHẨU TRANG CHỈ VỚI 1 ẢNH MẪU GỐC", size=13, bold=True, color=C_EMERALD)

    # Visual illustration of 160x160 crop masking
    add_rect(s8, 0.75, 1.92, 2.40, 2.35, C_DARK_CARD, border_rgb=C_CYAN, border_pt=1.5, rounded=True)
    add_rect(s8, 0.85, 2.02, 2.20, 1.15, C_CYAN_SOFT, border_rgb=C_CYAN, rounded=False)
    add_text(s8, 0.90, 2.35, 2.10, 0.50, "55% TRÊN (Rows 0..87)\nTrán • Mắt • Chân mày • Sống mũi\n(Giữ nguyên đặc trưng)", size=8.8, bold=True, color=C_CYAN_DARK, align=PP_ALIGN.CENTER)
    add_rect(s8, 0.85, 3.18, 2.20, 0.98, C_DARK_BG, border_rgb=C_ROSE, border_pt=1.2, rounded=False)
    add_text(s8, 0.90, 3.42, 2.10, 0.50, "45% DƯỚI (Rows 88..159)\nface[:, 88:, :] = 0.0\n(Zero-out vùng khẩu trang)", size=8.8, bold=True, color=C_ROSE, align=PP_ALIGN.CENTER)

    add_bullets(
        s8, 3.32, 1.92, 3.18, 2.40,
        [
            "Ảnh khuôn mặt sau căn chỉnh MTCNN có kích thước chuẩn 160 × 160 pixels.",
            "Khi đeo khẩu trang, 45% phần dưới (từ hàng pixel 88 đến 160) bị biến thiên màu sắc gây nhiễu vector đặc trưng.",
            "Hệ thống chủ động gán 0.0 (bôi đen đồng nhất) 45% vùng dưới cho cả ảnh đăng ký (routes.py) và ảnh thực tế (processors.py).",
            "Ép mạng Inception-ResNet-v1 tập trung 100% vào vùng mắt, chân mày và sống mũi trên."
        ],
        size=9.5, color=C_TEXT_LIGHT, bullet_char="▸ "
    )

    add_rect(s8, 0.75, 4.45, 5.68, 2.25, C_DARK_CARD, border_rgb=C_EMERALD, rounded=True)
    add_bullets(
        s8, 0.92, 4.55, 5.35, 2.05,
        [
            "Không cần huấn luyện lại mô hình Deep Learning hay thu thập bộ dữ liệu đeo khẩu trang.",
            "Người dùng chỉ cần đăng ký 1 ảnh không đeo khẩu trang duy nhất (hoặc 3–4 góc nghiêng).",
            "Ngưỡng khoảng cách L2-Norm chuẩn hóa được tối ưu cố định ở mức 0.80 (app/config.py).",
            "Hỗ trợ xem trực tiếp (Live Preview) và kiểm tra ảnh chụp trước khi xác nhận đăng ký trên Web."
        ],
        size=9.8, color=C_TEXT_LIGHT, title="Ưu điểm vượt trội trong triển khai thực tế:", title_color=C_EMERALD, title_size=11
    )

    # Right: Multi-angle Pipeline & Downscaling optimization
    add_feature_box(s8, 6.88, 1.22, 6.15, 2.75, "A", "Tối Ưu Hóa MTCNN Downscaling 2x & Căn Chỉnh Đa Góc Nhìn", [
        "Thu nhỏ khung hình đầu vào 2 lần (xuống 320 × 180) trước khi đưa qua 3 mạng P-Net, R-Net, O-Net giúp giảm khối lượng tính toán 4 lần (độ trễ phát hiện chỉ ~37,1 ms).",
        "Hạ ngưỡng phát hiện xuống θ_mtcnn = [0.5, 0.6, 0.6] để bắt nhạy các khuôn mặt nghiêng trái/phải hoặc cúi/ngửa.",
        "Nhân đôi tọa độ hộp bao về khung hình gốc 640 × 360 và gọi trực tiếp mtcnn.extract() để cắt mặt chất lượng cao mà không phải chạy lại mạng dò tìm lần hai."
    ], accent=C_CYAN)

    add_feature_box(s8, 6.88, 4.15, 6.15, 2.79, "B", "Đối Sánh Đa Góc Nhìn (Multi-Angle Matching) & Bảo Mật Sinh Trắc", [
        "Mỗi nhân sự i được lưu tập K vector đặc trưng {v_i^(1), ..., v_i^(K)} ứng với các góc nhìn thẳng, nghiêng trái, nghiêng phải, ngẩng/cúi trong bảng FaceRecord (SQLite).",
        "Khoảng cách đối sánh tính theo công thức cực tiểu: d_match = min_j || u - v_i^(j) ||_2 (hoặc khoảng cách Cosine tương đương trên vector chuẩn hóa L2).",
        "Bảo mật tuyệt đối: Hệ thống hủy ngay ảnh gốc sau khi trích xuất vector đặc trưng, ngăn chặn hoàn toàn nguy cơ phục hồi ảnh mặt nếu rò rỉ cơ sở dữ liệu."
    ], accent=C_INDIGO)

    # ==========================================================================
    # SLIDE 9: CHƯƠNG 3 — PHÁT HIỆN BẤT THƯỜNG ĐA NGUY CƠ (NGÃ, CHÁY, XÂM NHẬP ROI)
    # ==========================================================================
    s9 = new_slide(prs)
    add_chrome(s9, "3", "Phát hiện bất thường", "Phân Hệ Phát Hiện Bất Thường Đa Nguy Cơ: Té Ngã, Hỏa Hoạn & Hàng Rào ROI", 9, TOTAL, C_ROSE)

    hazards = [
        ("1", "Phát Hiện Té Ngã (YOLOv8-fall)", C_ROSE, [
            "Huấn luyện chuyên biệt trên tập dữ liệu ImViA (9,37 GB video gồm 35.041 ảnh train & 6.989 ảnh val tại 4 bối cảnh phòng).",
            "Trọng số yolov8n_fall_best.pt (3,2M tham số) phân tích tỷ lệ khung bao (Width/Height) và quỹ đạo trọng tâm cơ thể.",
            "Đạt 2,8 FPS trên CPU Pi 4 (nhanh gấp 3,5 lần so với YOLOv8-pose 0,8 FPS) với mAP50 đạt 91,5%."
        ]),
        ("2", "Cảnh Báo Sớm Lửa & Khói (YOLOv8n-fire)", C_AMBER, [
            "Huấn luyện trên 2.050 ảnh lửa và khói từ Roboflow Universe (80% train / 20% val) kết hợp tăng cường dữ liệu đa điều kiện sáng.",
            "Cơ chế tích lũy khung hình (fire_frame_buffer = 25, ngưỡng tự tin 0.55) loại bỏ báo giả do ánh đèn hoặc vật thể màu đỏ/cam.",
            "Đạt độ chính xác Precision 94,3%, Recall 89,1%, mAP50 92,2%, độ trễ suy luận 347,7 ms trên CPU."
        ]),
        ("3", "Xâm Nhập Vùng Đa Giác Cấm (ROI Polygon)", C_INDIGO, [
            "Cho phép quản trị viên vẽ trực tiếp đa giác vùng cấm (ROI) không giới hạn số đỉnh ngay trên giao diện Web Dashboard.",
            "Sử dụng kiểm tra hình học Point-in-Polygon (cv2.pointPolygonTest) đối với tâm đáy hộp bao người kết hợp ByteTrack.",
            "Tích hợp chế độ Khóa Nhà (house_locked) tự động kích hoạt còi hú vật lý và gửi video H.264 khi có đột nhập."
        ]),
    ]
    for idx, (num, title, col, lines) in enumerate(hazards):
        add_feature_box(s9, 0.48, 1.22 + idx * 1.94, 7.10, 1.82, num, title, lines, accent=col)

    # Right column: Actual training validation predictions image
    add_rect(s9, 7.78, 1.22, 5.25, 5.72, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_rect(s9, 7.78, 1.22, 5.25, 0.45, C_PANEL_DARK)
    add_text(s9, 7.92, 1.30, 5.00, 0.30, "KẾT QUẢ NHẬN DIỆN TRÊN TẬP KIỂM CHỨNG (VAL BATCH)", size=10.5, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    if os.path.exists("val_batch0_pred.jpg"):
        add_picture_fitted(s9, "val_batch0_pred.jpg", 7.92, 1.78, 4.96, 4.25)
    add_rect(s9, 7.92, 6.12, 4.96, 0.68, C_LIGHT_BG, border_rgb=C_BORDER, rounded=True)
    add_text(
        s9, 8.02, 6.18, 4.76, 0.56,
        "Hình ảnh trích xuất thực tế từ quá trình kiểm chứng mô hình YOLOv8-fall tùy chỉnh (val_batch0_pred.jpg): nhận diện chính xác trạng thái ngã dưới nhiều góc máy.",
        size=9.0, color=C_TEXT_BODY, align=PP_ALIGN.CENTER
    )

    # ==========================================================================
    # SLIDE 10: CHƯƠNG 3 — SƠ ĐỒ ĐẤU NỐI GPIO RASPBERRY PI 4 & TỰ PHỤC HỒI
    # ==========================================================================
    s10 = new_slide(prs)
    add_chrome(s10, "3", "Ngoại vi IoT & Phục hồi", "Sơ Đồ Đấu Nối Ngoại Vi GPIO Trên Raspberry Pi 4 & Tự Phục Hồi Sau Mất Điện", 10, TOTAL, C_AMBER)

    # Left: Actual wiring diagram image
    add_rect(s10, 0.48, 1.22, 6.30, 5.72, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_rect(s10, 0.48, 1.22, 6.30, 0.44, C_PANEL_DARK)
    add_text(s10, 0.62, 1.30, 6.00, 0.30, "SƠ ĐỒ ĐẤU NỐI PHẦN CỨNG TRÊN RASPBERRY PI 4 MODEL B", size=10.5, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    if os.path.exists("static/raspberry_pi_wiring_diagram.png"):
        add_picture_fitted(s10, "static/raspberry_pi_wiring_diagram.png", 0.62, 1.75, 6.02, 5.05)

    # Right top: GPIO Pinout Table
    add_rect(s10, 6.98, 1.22, 6.05, 3.05, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_text(s10, 7.15, 1.32, 5.70, 0.32, "BẢNG CẤU HÌNH CHÂN CẮM GPIO & CƠ CHẾ VẬN HÀNH AN TOÀN", size=11.5, bold=True, color=C_TEXT_MAIN)

    t_gpio = s10.shapes.add_table(5, 4, Inches(7.12), Inches(1.70), Inches(5.76), Inches(2.42))
    style_table(
        t_gpio.table,
        ["Thiết bị ngoại vi", "Chân BCM", "Pin Vật lý", "Logic điều khiển & Bảo vệ"],
        [
            ["Cảm biến Ga MQ-2", "GPIO 18", "Pin 12", "Đọc DO mỗi 1s; mức LOW -> Báo cháy/ga"],
            ["Khóa Solenoid 12V", "GPIO 23", "Pin 16", "Xuất HIGH đúng 3.0s rồi ngắt về LOW"],
            ["Còi Active Buzzer", "GPIO 24", "Pin 18", "Nháy 0.1s (Cháy) / 0.3s (Ga) / 0.8s (Trộm)"],
            ["Rơ-le Đèn cảnh báo", "GPIO 22", "Pin 15", "Bật sáng hỗ trợ ghi hình khi có sự cố"],
        ],
        col_widths=[1.55, 0.95, 0.85, 2.41]
    )

    # Right bottom: Cross-platform & Auto-recovery Systemd
    add_feature_box(s10, 6.98, 4.42, 6.05, 2.52, "⚡", "Tương Thích Đa Nền Tảng & Tự Khởi Động Cùng Hệ Điều Hành (Systemd)", [
        "Cơ chế Cross-Platform an toàn: Tự động kiểm tra import RPi.GPIO; nếu chạy trên Windows/Laptop phát triển sẽ chuyển sang chế độ Giả lập (Simulation Mode) không gây crash.",
        "Đóng gói dịch vụ Linux Systemd (smartcamera.service): Tự động nạp môi trường ảo Python và khởi chạy lại toàn bộ hệ thống trong < 45 giây sau khi có điện trở lại.",
        "Khởi tạo an toàn (Fail-Safe Boot): Ép toàn bộ chân GPIO 22, 23, 24 về mức điện áp thấp (LOW) ngay khi vừa cấp nguồn, ngăn chặn tuyệt đối hiện tượng tự mở khóa cửa hoặc hú còi giả."
    ], accent=C_EMERALD)

    # ==========================================================================
    # SLIDE 11: CHƯƠNG 3 — WEB DASHBOARD GLASSMORPHIC, BẢO MẬT & TELEGRAM 2 CHIỀU
    # ==========================================================================
    s11 = new_slide(prs)
    add_chrome(s11, "3", "Phần mềm & Điều khiển", "Web Dashboard Glassmorphic, Bảo Mật HMAC-SHA256 & Telegram Bot 2 Chiều", 11, TOTAL, C_CYAN)

    # Left: Web Dashboard & Security Architecture
    add_feature_box(s11, 0.48, 1.22, 6.18, 2.75, "W", "Giao Diện Quản Trị Web Glassmorphic & Bản Đồ Số E-Map", [
        "Xây dựng trên FastAPI + Jinja2 + Vanilla JS hiện đại, hiển thị đa luồng MJPEG thời gian thực kèm trạng thái CPU, RAM, FPS và nhật ký sự kiện trực tuyến.",
        "Tích hợp Bản đồ số E-Map đa tầng (Khu A, Khu B): trực quan hóa vị trí lắp đặt từng camera, đổi màu nhấp nháy đỏ khi khu vực có báo động và cho phép bấm xem nhanh (Live Preview).",
        "Trang Cơ sở dữ liệu khuôn mặt nâng cấp: hỗ trợ Chụp WebRTC, Tải file ảnh và Chụp Cam Hệ Thống có khung Xem trực tiếp (● LIVE) + Xem lại ảnh trước khi xác nhận đăng ký."
    ], accent=C_CYAN)

    add_feature_box(s11, 0.48, 4.15, 6.18, 2.79, "🔒", "Kiến Trúc Bảo Mật Đa Lớp & Phân Quyền RBAC", [
        "Tự triển khai lớp trung gian HMACSessionMiddleware ký số cookie phiên đăng nhập bằng thuật toán HMAC-SHA256, chống giả mạo phiên mà không phụ thuộc thư viện ngoài.",
        "Mật khẩu người dùng được băm một chiều bằng thuật toán PBKDF2-HMAC-SHA256 kèm chuỗi muối (salt) ngẫu nhiên trong bảng User.",
        "Phân quyền 3 cấp độ (Role-Based Access Control): SuperAdmin (quản lý tài khoản & toàn quyền), Admin (cấu hình camera, đăng ký mặt, xem log), Operator (chỉ giám sát trực tiếp)."
    ], accent=C_INDIGO)

    # Right: 2-Way Telegram Bot Interactive Control panel
    add_rect(s11, 6.86, 1.22, 6.17, 5.72, C_PANEL_DARK, rounded=True)
    add_rect(s11, 6.86, 1.22, 6.17, 0.10, C_EMERALD)
    add_text(s11, 7.10, 1.42, 5.70, 0.35, "ĐIỀU KHIỂN TỪ XA 2 CHIỀU QUA TELEGRAM LONG POLLING", size=12.5, bold=True, color=C_EMERALD)
    add_text(s11, 7.10, 1.76, 5.70, 0.28, "Tự động xóa Webhook cũ, chạy luồng Daemon Polling độc lập, không cần mở port NAT/Router", size=9.5, color=C_TEXT_DIM)

    tg_blocks = [
        ("Chiều đi (Edge -> Quản trị viên): Cảnh báo Đa phương tiện Tức thì", C_CYAN, [
            "Gửi đồng thời tin nhắn khẩn cấp + ảnh chụp đánh dấu vùng nguy cơ (JPEG) + đoạn video H.264 10 giây trích từ bộ đệm vòng.",
            "Áp dụng cơ chế Cooldown thông minh (30s cho khí ga, 45s cho đếm/xâm nhập) chống spam tin nhắn liên hoàn."
        ]),
        ("Chiều về (Quản trị viên -> Edge): Nút bấm Inline Keyboard & Lệnh Chat", C_EMERALD, [
            "🔓 Nút unlock_door hoặc lệnh /unlock, /mo_cua, 'mở cửa': Kích hoạt rơ-le GPIO 23 mở khóa cửa Solenoid trong 3 giây để đón khách/cứu hộ từ xa.",
            "🔇 Nút mute_alerts: Tắt nhanh còi báo động vật lý và tạm ngưng thông báo khi xác nhận an toàn.",
            "⏸️ Nút pause_<cam_id>_30: Tạm dừng cảnh báo của một camera cụ thể trong 30 phút.",
            "📹 Lệnh /cameras, /cam, /danh_sach_cam: Hiển thị menu Inline trạng thái từng camera để Bật/Tắt (Arm/Disarm) độc lập."
        ]),
        ("Kiểm soát Ủy quyền An toàn (Authorization Filter)", C_AMBER, [
            "Chỉ chấp nhận lệnh điều khiển từ đúng Chat ID quản trị viên đã cấu hình, từ chối mọi truy cập trái phép."
        ]),
    ]
    y_cursor = 2.15
    for title, col, items in tg_blocks:
        bh = 1.32 if len(items) == 2 else (1.98 if len(items) == 4 else 0.92)
        add_rect(s11, 7.08, y_cursor, 5.72, bh, C_DARK_CARD, border_rgb=col, border_pt=1.2, rounded=True)
        add_bullets(s11, 7.20, y_cursor + 0.06, 5.48, bh - 0.12, items, size=9.3, color=C_TEXT_LIGHT, bullet_char="• ", title=title, title_color=col, title_size=10.2)
        y_cursor += bh + 0.15

    # ==========================================================================
    # SLIDE 12: CHƯƠNG 4 — MÔI TRƯỜNG THỰC NGHIỆM & 4 BỘ DỮ LIỆU ĐÁNH GIÁ
    # ==========================================================================
    s12 = new_slide(prs)
    add_chrome(s12, "4", "Thiết lập thực nghiệm", "Cấu Hình Phần Cứng Thực Nghiệm & 4 Bộ Dữ Liệu Huấn Luyện / Kiểm Chứng", 12, TOTAL, C_AMBER)

    # Top Table: Workstation vs Raspberry Pi 4
    add_rect(s12, 0.48, 1.22, 12.55, 2.85, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_text(s12, 0.68, 1.32, 12.0, 0.32, "BẢNG 4.1: ĐỐI CHIẾU MÔI TRƯỜNG MÁY TRẠM PHÁT TRIỂN VÀ NÚT BIÊN RASPBERRY PI 4", size=11.5, bold=True, color=C_TEXT_MAIN)

    t_env = s12.shapes.add_table(6, 3, Inches(0.68), Inches(1.70), Inches(12.15), Inches(2.22))
    style_table(
        t_env.table,
        ["Thành phần hệ thống", "Máy trạm Phát triển & Huấn luyện (Workstation)", "Thiết bị Biên Triển khai Thực tế (Edge Node)"],
        [
            ["Vi xử lý trung tâm (CPU)", "Intel Core i7-11800H (8 nhân / 16 luồng @ 2.30 GHz)", "Broadcom BCM2711, 4 nhân ARM Cortex-A72 @ 1.8 GHz"],
            ["Bộ nhớ RAM", "16 GB DDR4", "4 GB / 8 GB LPDDR4 (Sử dụng thực tế ~846,5 MB)"],
            ["Tăng tốc tính toán AI", "GPU NVIDIA GeForce RTX 3050 (4 GB VRAM, CUDA 12.1)", "Không dùng GPU rời — Tối ưu CPU qua khóa đồng bộ gpu_lock"],
            ["Ngoại vi & Cảm biến", "Chế độ giả lập phần mềm (Simulation Mode)", "Webcam USB 2.0 + Cảm biến MQ-2 + Rơ-le Solenoid 12V + Buzzer"],
            ["Hệ điều hành & Nền tảng", "Windows 11 (x64) | Python, PyTorch, FastAPI, OpenCV", "Raspberry Pi OS 64-bit | Dịch vụ tự khởi động Linux Systemd"],
        ],
        col_widths=[2.65, 4.75, 4.75],
        accent_col=2
    )

    # Bottom 4 Dataset Cards
    datasets = [
        ("D1", "ImViA Fall Dataset (Té ngã)", C_ROSE, [
            "Dung lượng 9,37 GB video thực tế tại 4 môi trường: Nhà riêng, Văn phòng, Phòng chờ, Lớp học.",
            "Trích xuất 35.041 ảnh huấn luyện & 6.989 ảnh kiểm chứng; huấn luyện SGD 100 epochs (batch 16)."
        ]),
        ("D2", "Roboflow Fire & Smoke (Cháy nổ)", C_AMBER, [
            "Gồm 2.050 ảnh gán nhãn lửa và khói sớm (chia 80% Train / 20% Validation).",
            "Áp dụng Augmentation (lật ngang, biến đổi tỷ lệ, cân bằng màu) chống nhiễu ánh sáng."
        ]),
        ("D3", "Multi-Angle Face DB (Khuôn mặt)", C_EMERALD, [
            "Thu nhận trực tiếp ở độ phân giải 640 × 480 với 4–5 góc nhìn/người (thẳng, nghiêng trái/phải, cúi/ngửa).",
            "Kiểm thử cả hai kịch bản: không đeo khẩu trang và đeo khẩu trang y tế."
        ]),
        ("D4", "COCO Person & Local ROI", C_INDIGO, [
            "Kế thừa trọng số chuẩn COCO lớp Person (Class 0) kết hợp các kịch bản đi vào vùng cấm đa giác.",
            "Kiểm thử liên tục >25 phút với nhiều luồng video đồng thời."
        ]),
    ]
    for idx, (b_txt, title, col, lines) in enumerate(datasets):
        add_feature_box(s12, 0.48 + idx * 3.16, 4.22, 3.06, 2.72, b_txt, title, lines, accent=col)

    # ==========================================================================
    # SLIDE 13: CHƯƠNG 4 — ĐỘ TRỄ SUY LUẬN AI & TỐC ĐỘ KHUNG HÌNH (BIỂU ĐỒ 01)
    # ==========================================================================
    s13 = new_slide(prs)
    add_chrome(s13, "4", "Kết quả thực nghiệm", "Đánh Giá Độ Trễ Suy Luận Từng Mô Hình & Tốc Độ Xử Lý (FPS) Trên Pi 4", 13, TOTAL, C_AMBER)

    # Top 4 KPI Tiles
    add_kpi_tile(s13, 0.48, 1.20, 3.00, 1.25, "37,1 ms", "Phát hiện mặt MTCNN", "Nhờ giảm mẫu 2x (320×180)", C_CYAN)
    add_kpi_tile(s13, 3.66, 1.20, 3.00, 1.25, "6,5 FPS", "Tốc độ 1 Kênh Camera", "Tải CPU trung bình ~43,4%", C_EMERALD)
    add_kpi_tile(s13, 6.84, 1.20, 3.00, 1.25, "3,8 FPS", "Tốc độ 2 Kênh Đồng thời", "Hoạt động ổn định không treo", C_INDIGO)
    add_kpi_tile(s13, 10.02, 1.20, 3.01, 1.25, "1,63 giây", "Độ trễ Cảnh báo Telegram", "Nhanh hơn Cloud-only (2,40s)", C_AMBER)

    # Left: Embedded Chart 01
    add_rect(s13, 0.48, 2.60, 8.15, 4.35, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_picture_fitted(s13, "bieu_do_hieu_xuat/01_do_tre_suy_luan_cac_mo_hinh.png", 0.56, 2.68, 7.99, 4.19)

    # Right: Analysis commentary
    add_feature_box(s13, 8.80, 2.60, 4.23, 4.35, "📊", "Phân Tích Định Lượng Độ Trễ & FPS", [
        "MTCNN chỉ mất 37,1 ms nhờ thu nhỏ ảnh đầu vào 2 lần; FaceNet trích xuất đặc trưng mất 789,9 ms nhưng chỉ kích hoạt khi có mặt người và hết thời gian cooldown.",
        "Các mô hình phát hiện nguy cơ đạt tốc độ nhanh trên CPU biên: YOLOv8n ROI (198,5 ms), YOLOv8n-fire (347,7 ms), YOLOv8-fall (363,6 ms).",
        "Đọc cảm biến khí ga MQ-2 qua GPIO chỉ tốn 1,2 ms và kích hoạt rơ-le khóa cửa Solenoid chỉ tốn 25,0 ms.",
        "Khi bật đồng thời cả 5 phân hệ AI trên 1 camera (tải cực đại), hệ thống vẫn duy trì 3,7 FPS, CPU 55,0% và RAM phẳng ở mức 846,5 MB."
    ], accent=C_EMERALD)

    # ==========================================================================
    # SLIDE 14: CHƯƠNG 4 — ĐỘ CHÍNH XÁC, MA TRẬN NHẦM LẪN & ĐỐI SÁNH BASELINES
    # ==========================================================================
    s14 = new_slide(prs)
    add_chrome(s14, "4", "Độ chính xác & Baselines", "Độ Chính Xác Phát Hiện Đa Nguy Cơ, Ma Trận Nhầm Lẫn & Đối Sánh Baselines", 14, TOTAL, C_AMBER)

    # Left top: Chart 02
    add_rect(s14, 0.48, 1.22, 6.20, 2.82, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_picture_fitted(s14, "bieu_do_hieu_xuat/02_do_chinh_xac_cac_tinh_nang.png", 0.56, 1.28, 6.04, 2.70)

    # Left bottom: Confusion Matrix
    add_rect(s14, 0.48, 4.15, 6.20, 2.80, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_picture_fitted(s14, "confusion_matrix.png", 0.56, 4.22, 3.20, 2.65)
    add_bullets(
        s14, 3.85, 4.30, 2.72, 2.50,
        [
            "Xâm nhập ROI: Precision 98,2% | Recall 97,5% | F1 97,8%.",
            "Khí ga MQ-2: Precision 99,0% | Recall 98,5% | F1 98,7%.",
            "Cháy khói YOLOv8n-fire: Precision 94,3% | Recall 89,1% | mAP50 92,2%.",
            "Té ngã YOLOv8-fall: Precision 92,1% | Recall 90,4% | mAP50 91,5%."
        ],
        size=9.3, color=C_TEXT_BODY, title="Tổng hợp Ma trận Nhầm lẫn:", title_color=C_TEXT_MAIN, title_size=10.5
    )

    # Right: 3 Baseline Comparison Tables (Tables 4.6, 4.7, 4.8 from Thesis)
    add_rect(s14, 6.86, 1.22, 6.17, 5.73, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_text(s14, 7.05, 1.32, 5.80, 0.30, "ĐỐI SÁNH VỚI CÁC MÔ HÌNH CƠ SỞ (BASELINES) TRÊN CPU PI 4", size=11.5, bold=True, color=C_TEXT_MAIN)

    # Table A: Face models
    add_text(s14, 7.05, 1.66, 5.80, 0.24, "1. Xác thực khuôn mặt (FaceNet đề xuất nhanh gấp 5,7 lần ArcFace):", size=9.8, bold=True, color=C_EMERALD_DARK)
    t_f = s14.shapes.add_table(4, 4, Inches(7.05), Inches(1.92), Inches(5.80), Inches(1.35))
    style_table(
        t_f.table,
        ["Mô hình Khuôn mặt", "Dung lượng", "Độ trễ CPU", "Độ chính xác"],
        [
            ["ArcFace (ResNet-50)", "145,0 MB", "4.500,0 ms", "99,4%"],
            ["MobileFaceNet", "5,2 MB", "220,0 ms", "91,2%"],
            ["FaceNet (Đề xuất)", "23,0 MB", "789,9 ms", "98,2%"],
        ],
        col_widths=[1.85, 1.25, 1.35, 1.35],
        accent_col=3
    )

    # Table B: Fall models
    add_text(s14, 7.05, 3.38, 5.80, 0.24, "2. Phát hiện té ngã (YOLOv8-fall nhanh gấp 3,5 lần YOLOv8-pose):", size=9.8, bold=True, color=C_CYAN_DARK)
    t_fl = s14.shapes.add_table(3, 4, Inches(7.05), Inches(3.64), Inches(5.80), Inches(1.08))
    style_table(
        t_fl.table,
        ["Mô hình Té ngã", "Tham số", "Tốc độ CPU", "mAP50 (%)"],
        [
            ["YOLOv8-pose (17 khớp xương)", "11,6 M", "0,8 FPS", "93,5%"],
            ["YOLOv8-fall (Đề xuất)", "3,2 M", "2,8 FPS", "91,5%"],
        ],
        col_widths=[2.15, 1.15, 1.25, 1.25],
        accent_col=3
    )

    # Table C: Fire models
    add_text(s14, 7.05, 4.82, 5.80, 0.24, "3. Phát hiện cháy khói (YOLOv8n-fire vượt trội +17,8% Precision so với SSD):", size=9.8, bold=True, color=C_AMBER_DARK)
    t_fr = s14.shapes.add_table(4, 4, Inches(7.05), Inches(5.08), Inches(5.80), Inches(1.35))
    style_table(
        t_fr.table,
        ["Mô hình Báo cháy", "Precision", "Recall", "Độ trễ CPU"],
        [
            ["MobileNet-SSD", "76,5%", "72,1%", "210,0 ms"],
            ["NanoDet", "81,2%", "74,8%", "250,0 ms"],
            ["YOLOv8n-fire (Đề xuất)", "94,3%", "89,1%", "347,7 ms"],
        ],
        col_widths=[2.05, 1.25, 1.25, 1.25],
        accent_col=3
    )

    # ==========================================================================
    # SLIDE 15: CHƯƠNG 4 — PHÂN TÍCH GÓC NHÌN KHUÔN MẶT & NGƯỠNG FAR/FRR (BIỂU ĐỒ 03 & 06)
    # ==========================================================================
    s15 = new_slide(prs)
    add_chrome(s15, "4", "Phân tích chuyên sâu", "Đánh Giá Nhận Diện Theo Góc Nhìn, Ngưỡng FAR/FRR & Dung Lượng Mô Hình", 15, TOTAL, C_AMBER)

    # Left: Chart 03 (Face angle & threshold FAR/FRR)
    add_rect(s15, 0.48, 1.22, 6.20, 4.10, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_picture_fitted(s15, "bieu_do_hieu_xuat/03_nhan_dien_khuon_mat_goc_nhin_va_nguong.png", 0.56, 1.30, 6.04, 3.94)

    # Right: Chart 06 (Model footprint & parameters)
    add_rect(s15, 6.86, 1.22, 6.17, 4.10, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_picture_fitted(s15, "bieu_do_hieu_xuat/06_dung_luong_mo_hinh_va_tham_so.png", 6.94, 1.30, 6.01, 3.94)

    # Bottom 2 insight boxes
    add_rect(s15, 0.48, 5.45, 6.20, 1.50, C_PANEL_DARK, rounded=True)
    add_rect(s15, 0.48, 5.45, 0.10, 1.50, C_EMERALD)
    add_bullets(
        s15, 0.70, 5.52, 5.85, 1.35,
        [
            "Độ chính xác đạt ~98% (nhìn thẳng), ~88% (ngẩng/cúi), ~85% (nghiêng trái) và ~83% (nghiêng phải) nhờ đăng ký đa góc nhìn.",
            "Phân tích giao điểm FAR/FRR xác định vùng ngưỡng tối ưu giúp tối đa hóa F1-Score, đồng thời ngưỡng L2 = 0.80 xử lý hiệu quả trường hợp đeo khẩu trang."
        ],
        size=9.5, color=C_TEXT_LIGHT, title="Nhận xét Biểu đồ Góc nhìn & Ngưỡng so khớp:", title_color=C_EMERALD, title_size=10.8
    )

    add_rect(s15, 6.86, 5.45, 6.17, 1.50, C_PANEL_DARK, rounded=True)
    add_rect(s15, 6.86, 5.45, 0.10, 1.50, C_CYAN)
    add_bullets(
        s15, 7.08, 5.52, 5.80, 1.35,
        [
            "Tổng dung lượng toàn bộ tổ hợp 4 mô hình đề xuất (MTCNN + FaceNet + YOLOv8-fall + YOLOv8n-fire) chỉ ~36 MB — nhỏ hơn 4 lần so với một mô hình ArcFace đơn lẻ (145 MB).",
            "Thiết kế gọn nhẹ giúp nạp nhanh vào RAM và chạy mượt trên phần cứng nhúng chi phí thấp."
        ],
        size=9.5, color=C_TEXT_LIGHT, title="Nhận xét Tối ưu Dung lượng Bộ nhớ (Footprint):", title_color=C_CYAN, title_size=10.8
    )

    # ==========================================================================
    # SLIDE 16: CHƯƠNG 4 — TÀI NGUYÊN PI 4, MỞ RỘNG ĐA KÊNH & TIẾT KIỆM BĂNG THÔNG
    # ==========================================================================
    s16 = new_slide(prs)
    add_chrome(s16, "4", "Tài nguyên & Băng thông", "Tải Tài Nguyên Phần Cứng Biên, Mở Rộng Đa Kênh & Tiết Kiệm >95% Băng Thông", 16, TOTAL, C_AMBER)

    # Left: Chart 04 (Resource & multi-cam scaling)
    add_rect(s16, 0.48, 1.22, 6.20, 3.85, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_picture_fitted(s16, "bieu_do_hieu_xuat/04_tai_nguyen_va_kha_nang_mo_rong_pi4.png", 0.56, 1.30, 6.04, 3.70)

    # Right: Chart 05 (Async dispatcher & bandwidth)
    add_rect(s16, 6.86, 1.22, 6.17, 3.85, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_picture_fitted(s16, "bieu_do_hieu_xuat/05_dieu_phoi_canh_bao_va_bang_thong.png", 6.94, 1.30, 6.01, 3.70)

    # Bottom comparison table (Table 4.2 + Table 4.5 summary)
    add_rect(s16, 0.48, 5.20, 12.55, 1.75, C_WHITE, border_rgb=C_BORDER, rounded=True)
    t_sc = s16.shapes.add_table(4, 5, Inches(0.65), Inches(5.30), Inches(12.20), Inches(1.55))
    style_table(
        t_sc.table,
        ["Cấu hình vận hành trên Pi 4", "Tốc độ FPS", "Tải CPU (%)", "Bộ nhớ RAM", "Đóng băng luồng Video & Băng thông"],
        [
            ["Gửi cảnh báo Đồng bộ (Baseline cũ)", "1,2 FPS", "68,0%", "840,0 MB", "Bị treo cứng 18,0 giây mỗi lần gửi cảnh báo"],
            ["Bất đồng bộ — 2 Kênh Camera (Đề xuất)", "3,8 FPS", "82,0%", "~1.200,0 MB", "0 ms đóng băng  |  Chạy ổn định đa luồng"],
            ["Bất đồng bộ — 1 Kênh Camera (Đề xuất)", "6,5 FPS", "43,4% (Max 55%)", "846,5 MB (~21%)", "0 ms đóng băng  |  Tiết kiệm >95% băng thông mạng"],
        ],
        col_widths=[3.20, 1.40, 1.70, 1.80, 4.10],
        accent_col=4
    )

    # ==========================================================================
    # SLIDE 17: CHƯƠNG 4 — DASHBOARD TỔNG HỢP HIỆU SUẤT TOÀN HỆ THỐNG (BIỂU ĐỒ 00)
    # ==========================================================================
    s17 = new_slide(prs)
    add_chrome(s17, "4", "Tổng hợp thực nghiệm", "Bức Tranh Tổng Hợp Toàn Diện Hiệu Suất Hệ Thống Smart Camera Biên", 17, TOTAL, C_AMBER)

    add_rect(s17, 0.48, 1.20, 9.15, 5.75, C_WHITE, border_rgb=C_BORDER, rounded=True)
    add_picture_fitted(s17, "bieu_do_hieu_xuat/00_bieu_do_tong_hop_hieu_xuat.png", 0.56, 1.28, 8.99, 5.59)

    # Right summary card
    add_rect(s17, 9.80, 1.20, 3.23, 5.75, C_PANEL_DARK, rounded=True)
    add_rect(s17, 9.80, 1.20, 3.23, 0.10, C_EMERALD)
    add_text(s17, 9.98, 1.40, 2.88, 0.38, "TÓM TẮT KẾT QUẢ ĐẠT ĐƯỢC", size=12.5, bold=True, color=C_EMERALD)

    highlights = [
        ("96,2%", "Độ chính xác trung bình toàn hệ thống trên 5 tác vụ an ninh."),
        ("0 ms", "Thời gian đóng băng luồng video khi bắn cảnh báo Telegram."),
        ("> 95%", "Mức tiết kiệm băng thông mạng so với kiến trúc Cloud-only."),
        ("846,5 MB", "Mức tiêu thụ RAM ổn định khi chạy đồng thời cả 5 mô hình AI."),
        ("3,0 giây", "Chu kỳ xung mở khóa Solenoid an toàn tuyệt đối cho cuộn hút."),
        ("< 3 Triệu", "Tổng chi phí phần cứng nút biên, tiết kiệm >80% chi phí đầu tư.")
    ]
    for i, (val, desc) in enumerate(highlights):
        hy = 1.90 + i * 0.82
        add_rect(s17, 9.98, hy, 2.88, 0.72, C_DARK_CARD, border_rgb=C_DARK_BORDER, rounded=True)
        add_text(s17, 10.08, hy + 0.06, 1.15, 0.30, val, size=12, bold=True, color=C_CYAN if i % 2 else C_EMERALD)
        add_text(s17, 10.08, hy + 0.34, 2.68, 0.34, desc, size=8.5, color=C_TEXT_LIGHT)

    # ==========================================================================
    # SLIDE 18: CHƯƠNG 5 — KẾT LUẬN, HƯỚNG PHÁT TRIỂN & CẢM ƠN HỘI ĐỒNG
    # ==========================================================================
    s18 = new_slide(prs, dark=True)
    add_rect(s18, 0, 0, 0.28, 7.5, C_EMERALD)
    add_rect(s18, 0.28, 0, 0.08, 7.5, C_CYAN)

    add_text(s18, 0.65, 0.38, 12.1, 0.32, "CHƯƠNG 5  •  KẾT LUẬN, ĐÓNG GÓP CHÍNH & HƯỚNG NGHIÊN CỨU TIẾP THEO", size=11, bold=True, color=C_EMERALD)
    add_text(s18, 0.65, 0.70, 12.1, 0.48, "Tổng Kết Đồ Án & Định Hướng Mở Rộng Tương Lai", size=22, bold=True, color=C_WHITE)

    # Left card: 4 Core Contributions
    add_rect(s18, 0.65, 1.32, 6.00, 3.85, C_DARK_CARD, border_rgb=C_EMERALD, border_pt=1.2, rounded=True)
    add_bullets(
        s18, 0.85, 1.45, 5.60, 3.60,
        [
            "1. Khung giám sát đa nguy cơ hợp nhất tại biên: Chạy đồng thời Nhận diện mặt đeo khẩu trang (1 ảnh mẫu), Té ngã, Cháy khói, Xâm nhập ROI và Khí ga MQ-2 trên Raspberry Pi 4.",
            "2. Kiến trúc đồng bộ gpu_lock & Điều phối bất đồng bộ: Xóa bỏ hoàn toàn hiện tượng đóng băng video (0 ms freeze), giữ tốc độ 6,5 FPS và bảo toàn cảnh báo bằng giao dịch ACID SQLite.",
            "3. Tích hợp ngoại vi an toàn & Tự phục hồi: Điều khiển xung khóa Solenoid 3s chống cháy, còi Buzzer 3 cấp độ và tự khởi động lại trong <45s qua Linux Systemd.",
            "4. Quản trị bảo mật toàn diện: Giao diện Web Glassmorphic kèm E-Map, ký phiên HMAC-SHA256, lưu trữ ẩn danh vector đặc trưng và điều khiển 2 chiều qua Telegram Bot."
        ],
        size=9.8, color=C_TEXT_LIGHT, bullet_char="", title="4 ĐÓNG GÓP KHOA HỌC & THỰC TIỄN CỐT LÕI", title_color=C_EMERALD, title_size=12
    )

    # Right card: Future Works
    add_rect(s18, 6.85, 1.32, 5.95, 3.85, C_DARK_CARD, border_rgb=C_CYAN, border_pt=1.2, rounded=True)
    add_bullets(
        s18, 7.05, 1.45, 5.55, 3.60,
        [
            "1. Lượng tử hóa mô hình (Model Quantization): Chuyển đổi trọng số PyTorch sang ONNX Runtime / TensorRT ở định dạng FP16 và INT8 để nâng tốc độ xử lý biên lên >12–15 FPS.",
            "2. Mở rộng phần cứng NPU/GPU biên thế hệ mới: Triển khai container hóa trên Raspberry Pi 5 (kèm AI Hat+ Hailo-8L) hoặc NVIDIA Jetson Orin Nano để mở rộng lên 4–8 kênh camera.",
            "3. Bảo mật mật mã đồng cấu (Homomorphic Encryption): Mã hóa trực tiếp các vector đặc trưng khuôn mặt trong SQLite, cho phép tính khoảng cách đối sánh ngay trên miền mã hóa.",
            "4. Đa phương thức âm thanh – hình ảnh: Tích hợp thêm cảm biến âm thanh biên nhận diện tiếng kính vỡ và tiếng kêu cứu khẩn cấp."
        ],
        size=9.8, color=C_TEXT_LIGHT, bullet_char="", title="HƯỚNG NGHIÊN CỨU & PHÁT TRIỂN TIẾP THEO", title_color=C_CYAN, title_size=12
    )

    # Bottom Thank You Banner
    add_rect(s18, 0.65, 5.38, 12.15, 1.72, C_PANEL_DARK, border_rgb=C_AMBER, border_pt=1.5, rounded=True)
    add_text(
        s18, 0.85, 5.50, 11.75, 0.50,
        "TRÂN TRỌNG CẢM ƠN QUÝ THẦY CÔ HỘI ĐỒNG ĐÃ LẮNG NGHE!",
        size=20, bold=True, color=C_AMBER, align=PP_ALIGN.CENTER
    )
    add_text(
        s18, 0.85, 6.05, 11.75, 0.35,
        "Rất mong nhận được các ý kiến nhận xét, phản biện và đóng góp quý báu của Hội đồng.",
        size=11.5, bold=False, color=C_TEXT_LIGHT, align=PP_ALIGN.CENTER
    )
    add_text(
        s18, 0.85, 6.50, 11.75, 0.35,
        "Học viên thực hiện: Nguyễn Văn Toàn (MSE26HCM)   •   Giảng viên hướng dẫn: TS. Đoàn Xuân Huy Minh   •   Trường Đại học FPT",
        size=10.5, bold=True, color=C_CYAN, align=PP_ALIGN.CENTER
    )

    prs.save(OUTPUT_PPTX)
    print(f"[SUCCESS] Đã xuất file thuyết trình mới: {os.path.abspath(OUTPUT_PPTX)} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build_deck()
