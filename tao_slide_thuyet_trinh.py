# -*- coding: utf-8 -*-
"""
Script khởi tạo bài thuyết trình Đồ án Tốt nghiệp chuẩn hóa:
Smart Camera Giám Sát Đa Nguy Cơ Biên (Edge AI) Trên Raspberry Pi 4 (4GB)
Áp dụng phong cách trình bày thẩm mỹ (Slide Presentation Style), bố cục thẻ (Card Layout),
bảng màu công nghệ Deep Navy & Tech Blue, cùng các khung ghi chú ảnh chụp thực tế rõ ràng.
Hoàn toàn độc lập, sạch sẽ và 100% nội dung đề tài Smart Camera.
"""

import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# Thiết lập UTF-8 cho Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUTPUT_PATH = "thuyet_trinh_do_an.pptx"

# ==============================================================================
# HỆ THỐNG MÀU SẮC THẨM MỸ (COLOR PALETTE - DEEP NAVY & TECH BLUE)
# ==============================================================================
COLOR_BG = RGBColor(0xFA, 0xFA, 0xFC)          # Nền slide trắng xám dịu mắt
COLOR_NAVY = RGBColor(0x01, 0x2A, 0x4A)        # Xanh Navy đậm trang trọng
COLOR_PRIMARY = RGBColor(0x00, 0x4A, 0xAD)     # Xanh Tech Blue năng động
COLOR_SLATE = RGBColor(0x2A, 0x6F, 0x97)       # Xanh Slate nhạt
COLOR_TEXT_DARK = RGBColor(0x1E, 0x29, 0x3B)   # Chữ chính màu xám đen đậm
COLOR_TEXT_MUTED = RGBColor(0x64, 0x74, 0x8B)  # Chữ phụ màu xám trung tính
COLOR_WHITE = RGBColor(0xFF, 0xFF, 0xFF)       # Màu trắng
COLOR_CARD_BG = RGBColor(0xFF, 0xFF, 0xFF)     # Nền thẻ trắng tinh
COLOR_CARD_BORDER = RGBColor(0xE2, 0xE8, 0xF0) # Viền thẻ mảnh
COLOR_AMBER_BG = RGBColor(0xFF, 0xF8, 0xE1)    # Nền vàng kem ấm cho khung ảnh thực tế
COLOR_AMBER_BORDER = RGBColor(0xE6, 0x51, 0x00)# Viền cam đậm nổi bật
COLOR_GREEN = RGBColor(0x16, 0x65, 0x34)       # Xanh lá an toàn / thành công
COLOR_RED = RGBColor(0x99, 0x1B, 0x1B)         # Đỏ cảnh báo nguy hiểm

FONT_HEADING = "Arial"
FONT_BODY = "Arial"

# ==============================================================================
# CÁC HÀM TIỆN ÍCH DỰNG BỐ CỤC SLIDE (LAYOUT BUILDERS)
# ==============================================================================
def create_blank_slide(prs):
    """Tạo slide trắng với nền màu dịu mắt."""
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = COLOR_BG
    bg.line.fill.background()
    return slide

def add_header(slide, section_tag, title, subtitle=None, page_num=None):
    """Tạo thanh tiêu đề chuẩn mực, hiện đại ở đầu mỗi slide."""
    # Tag tên phần (breadcrumb)
    tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
    tf_tag = tag_box.text_frame
    tf_tag.word_wrap = True
    p_tag = tf_tag.paragraphs[0]
    p_tag.text = section_tag.upper()
    p_tag.font.name = FONT_HEADING
    p_tag.font.size = Pt(11)
    p_tag.font.bold = True
    p_tag.font.color.rgb = COLOR_PRIMARY

    # Tiêu đề chính slide
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.72), Inches(11.7), Inches(0.6))
    tf_title = title_box.text_frame
    tf_title.word_wrap = True
    p_title = tf_title.paragraphs[0]
    p_title.text = title
    p_title.font.name = FONT_HEADING
    p_title.font.size = Pt(22)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_NAVY

    # Đường phân cách mảnh thanh lịch
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.35), Inches(11.733), Inches(0.02))
    line.fill.solid()
    line.fill.fore_color.rgb = RGBColor(0xCB, 0xD5, 0xE1)
    line.line.fill.background()

    # Footer chân trang
    footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(10.0), Inches(0.3))
    tf_f = footer_box.text_frame
    p_f = tf_f.paragraphs[0]
    p_f.text = "Đồ Án Tốt Nghiệp: Hệ Thống Smart Camera Giám Sát Đa Nguy Cơ Biên (Edge AI) | Đại học FPT"
    p_f.font.name = FONT_BODY
    p_f.font.size = Pt(9.5)
    p_f.font.color.rgb = COLOR_TEXT_MUTED

    if page_num:
        p_box = slide.shapes.add_textbox(Inches(11.5), Inches(7.05), Inches(1.0), Inches(0.3))
        tf_p = p_box.text_frame
        p_p = tf_p.paragraphs[0]
        p_p.text = f"{page_num}"
        p_p.font.name = FONT_BODY
        p_p.font.size = Pt(10)
        p_p.font.bold = True
        p_p.font.color.rgb = COLOR_PRIMARY
        p_p.alignment = PP_ALIGN.RIGHT

def add_card(slide, left, top, width, height, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER):
    """Tạo thẻ chứa nội dung (Card container) bo góc hiện đại."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1.2)
    return card

def add_badge(slide, left, top, size, text, bg_color=COLOR_PRIMARY, text_color=COLOR_WHITE):
    """Tạo huy hiệu tròn đánh số thứ tự (1, 2, 3) nổi bật."""
    badge = slide.shapes.add_shape(MSO_SHAPE.OVAL, left, top, size, size)
    badge.fill.solid()
    badge.fill.fore_color.rgb = bg_color
    badge.line.fill.background()
    tf = badge.text_frame
    p = tf.paragraphs[0]
    p.text = str(text)
    p.font.name = FONT_HEADING
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = text_color
    p.alignment = PP_ALIGN.CENTER
    return badge

def add_photo_placeholder(slide, left, top, width, height, title, bullet_instructions):
    """Tạo khung ghi chú nổi bật hướng dẫn người dùng chụp ảnh thực tế."""
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    box.fill.solid()
    box.fill.fore_color.rgb = COLOR_AMBER_BG
    box.line.color.rgb = COLOR_AMBER_BORDER
    box.line.width = Pt(2.0)

    tf = box.text_frame
    tf.word_wrap = True
    p0 = tf.paragraphs[0]
    p0.text = f"📷 [ẢNH CẦN CHỤP THỰC TẾ]: {title}"
    p0.font.name = FONT_HEADING
    p0.font.bold = True
    p0.font.size = Pt(12)
    p0.font.color.rgb = RGBColor(0xBF, 0x36, 0x0C) # Đỏ cam đậm
    p0.alignment = PP_ALIGN.LEFT

    for line in bullet_instructions:
        p = tf.add_paragraph()
        p.text = f"• {line}"
        p.font.name = FONT_BODY
        p.font.size = Pt(10)
        p.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
        p.alignment = PP_ALIGN.LEFT

def add_metric_card(slide, left, top, width, height, value, label, sublabel=None, val_color=COLOR_PRIMARY):
    """Tạo thẻ số liệu thống kê lớn ấn tượng (KPI Card)."""
    add_card(slide, left, top, width, height, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER)
    tb = slide.shapes.add_textbox(left, top + Inches(0.15), width, height - Inches(0.2))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p_val = tf.paragraphs[0]
    p_val.text = value
    p_val.font.name = FONT_HEADING
    p_val.font.size = Pt(28)
    p_val.font.bold = True
    p_val.font.color.rgb = val_color
    p_val.alignment = PP_ALIGN.CENTER

    p_lbl = tf.add_paragraph()
    p_lbl.text = label
    p_lbl.font.name = FONT_HEADING
    p_lbl.font.size = Pt(11.5)
    p_lbl.font.bold = True
    p_lbl.font.color.rgb = COLOR_TEXT_DARK
    p_lbl.alignment = PP_ALIGN.CENTER

    if sublabel:
        p_sub = tf.add_paragraph()
        p_sub.text = sublabel
        p_sub.font.name = FONT_BODY
        p_sub.font.size = Pt(9.5)
        p_sub.font.color.rgb = COLOR_TEXT_MUTED
        p_sub.alignment = PP_ALIGN.CENTER


def main():
    print("=" * 60)
    print("Đang khởi tạo bài thuyết trình Đồ án Tốt nghiệp Smart Camera...")
    prs = Presentation()
    # Định dạng chuẩn Widescreen 16:9 (13.333 x 7.5 inches)
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # =========================================================================
    # SLIDE 1: TRANG BÌA (TITLE SLIDE)
    # =========================================================================
    s1 = create_blank_slide(prs)
    # Khối thẻ nền trang bìa
    banner = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(4.5))
    banner.fill.solid()
    banner.fill.fore_color.rgb = COLOR_NAVY
    banner.line.fill.background()

    # Dải sóng / vạch phân cách màu Tech Blue
    sub_banner = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(4.45), Inches(13.333), Inches(0.1))
    sub_banner.fill.solid()
    sub_banner.fill.fore_color.rgb = COLOR_PRIMARY
    sub_banner.line.fill.background()

    # Logo Đại học FPT
    logo_path = "Logo_Trường_Đại_học_FPT.png"
    if os.path.exists(logo_path):
        try:
            s1.shapes.add_picture(logo_path, Inches(0.8), Inches(0.5), width=Inches(2.4))
        except Exception:
            pass

    # Tiêu đề & phụ đề
    tb_title = s1.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(2.6))
    tf1 = tb_title.text_frame
    tf1.word_wrap = True

    p_badge = tf1.paragraphs[0]
    p_badge.text = "BÁO CÁO ĐỒ ÁN TỐT NGHIỆP ĐẠI HỌC"
    p_badge.font.name = FONT_HEADING
    p_badge.font.size = Pt(14)
    p_badge.font.bold = True
    p_badge.font.color.rgb = RGBColor(0x38, 0xBD, 0xF8) # Sky Blue

    p_main = tf1.add_paragraph()
    p_main.text = "HỆ THỐNG SMART CAMERA GIÁM SÁT ĐA NGUY CƠ BIÊN (EDGE AI) TRÊN RASPBERRY PI 4"
    p_main.font.name = FONT_HEADING
    p_main.font.size = Pt(26)
    p_main.font.bold = True
    p_main.font.color.rgb = COLOR_WHITE

    p_desc = tf1.add_paragraph()
    p_desc.text = "Nhận diện khuôn mặt đeo khẩu trang • Cảnh báo té ngã, cháy nổ • Giám sát khí ga MQ-2 & Khóa cửa tự động"
    p_desc.font.name = FONT_BODY
    p_desc.font.size = Pt(14)
    p_desc.font.color.rgb = RGBColor(0xEA, 0xE8, 0xFA)

    # Thông tin sinh viên & Giảng viên hướng dẫn
    card_info = add_card(s1, Inches(0.8), Inches(4.8), Inches(11.733), Inches(2.1))
    tb_info = s1.shapes.add_textbox(Inches(1.1), Inches(5.0), Inches(11.1), Inches(1.7))
    tf_info = tb_info.text_frame
    tf_info.word_wrap = True

    p_sv = tf_info.paragraphs[0]
    p_sv.text = "Sinh viên thực hiện:  Nguyễn Văn Toàn"
    p_sv.font.name = FONT_HEADING
    p_sv.font.size = Pt(15)
    p_sv.font.bold = True
    p_sv.font.color.rgb = COLOR_NAVY

    p_gv = tf_info.add_paragraph()
    p_gv.text = "Giảng viên hướng dẫn:  ..."
    p_gv.font.name = FONT_HEADING
    p_gv.font.size = Pt(14)
    p_gv.font.bold = True
    p_gv.font.color.rgb = COLOR_PRIMARY

    p_uni = tf_info.add_paragraph()
    p_uni.text = "Đơn vị đào tạo:  Trường Đại học FPT"
    p_uni.font.name = FONT_BODY
    p_uni.font.size = Pt(13)
    p_uni.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 2: MỤC LỤC BÁO CÁO (AGENDA)
    # =========================================================================
    s2 = create_blank_slide(prs)
    add_header(s2, "Nội dung tổng thể", "Mục Lục Bài Thuyết Trình Đồ Án", page_num=2)

    agenda_items = [
        ("1", "Đặt Vấn Đề & Mục Tiêu Nghiên Cứu", "Nhu cầu an ninh tại chỗ, hạn chế của camera truyền thống, mục tiêu thiết kế Edge AI."),
        ("2", "Hiện Trạng & Thách Thức Kỹ Thuật", "Giới hạn CPU biên Raspberry Pi 4, che khuất đặc trưng khi đeo khẩu trang, an toàn rơ-le khóa cửa."),
        ("3", "Phương Pháp & Kiến Trúc Hệ Thống", "Pipeline đa mô hình AI, thuật toán nhận diện khẩu trang 1 ảnh mẫu, sơ đồ GPIO ngoại vi, Web & Telegram."),
        ("4", "Kết Quả Thực Nghiệm & Trực Quan", "4 kịch bản kiểm nghiệm thực tế: Khuôn mặt khẩu trang, Té ngã, Cháy nổ & Khí ga, Khóa cửa Solenoid 3s."),
        ("5", "Đánh Giá Hiệu Năng & Kết Luận", "Bảng đo lường tài nguyên CPU 55%, RAM 846.5MB, FPS 3.7, độ trễ 1.67s, ma trận nhầm lẫn và hướng phát triển.")
    ]

    for i, (num, title, desc) in enumerate(agenda_items):
        y_pos = Inches(1.65 + i * 1.0)
        add_card(s2, Inches(0.8), y_pos, Inches(11.733), Inches(0.85))
        add_badge(s2, Inches(1.05), y_pos + Inches(0.18), Inches(0.48), num, bg_color=COLOR_PRIMARY)
        
        tb = s2.shapes.add_textbox(Inches(1.7), y_pos + Inches(0.08), Inches(10.5), Inches(0.7))
        tf = tb.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(14)
        p1.font.bold = True
        p1.font.color.rgb = COLOR_NAVY
        
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.name = FONT_BODY
        p2.font.size = Pt(11)
        p2.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 3: 1. ĐẶT VẤN ĐỀ & MỤC TIÊU NGHIÊN CỨU
    # =========================================================================
    s3 = create_blank_slide(prs)
    add_header(s3, "Phần 1: Đặt vấn đề", "Nhu Cầu Giám Sát Biên & 3 Mục Tiêu Nghiên Cứu Cốt Lõi", page_num=3)

    objs = [
        ("1", "Giám Sát An Ninh Biên Thời Gian Thực (Edge AI)",
         "• Xử lý và suy luận trực tiếp trên vi máy tính Raspberry Pi 4 Model B giá rẻ.\n"
         "• Đáp ứng phản hồi dưới 2 giây, không gửi video lên đám mây (Cloud Server).\n"
         "• Bảo vệ tuyệt đối quyền riêng tư hình ảnh của gia đình và phân xưởng."),
        ("2", "Tích Hợp Đa Nguy Cơ An Ninh Toàn Diện",
         "• Nhận diện khuôn mặt người nhà (kể cả khi đang đeo khẩu trang y tế).\n"
         "• Phát hiện sự cố té ngã bất thường của người cao tuổi và trẻ nhỏ.\n"
         "• Cảnh báo hỏa hoạn/khói sớm và kiểm soát hàng rào ảo chống đột nhập (ROI)."),
        ("3", "An Toàn Phần Cứng & Tự Phục Hồi Mất Điện",
         "• Tích hợp cảm biến rò rỉ khí ga MQ-2 và còi báo động phân cấp độ nguy hiểm.\n"
         "• Điều khiển rơ-le khóa cửa Solenoid 12V với xung ngắt 3 giây an toàn chống cháy cuộn hút.\n"
         "• Linux Systemd tự động phục hồi toàn bộ hệ thống sau sự cố mất điện trong < 45 giây.")
    ]

    for i, (num, title, desc) in enumerate(objs):
        x_pos = Inches(0.8 + i * 4.0)
        add_card(s3, x_pos, Inches(1.65), Inches(3.733), Inches(5.1))
        add_badge(s3, x_pos + Inches(0.25), Inches(1.9), Inches(0.55), num, bg_color=COLOR_PRIMARY)
        
        tb = s3.shapes.add_textbox(x_pos + Inches(0.25), Inches(2.6), Inches(3.233), Inches(4.0))
        tf = tb.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(14)
        p1.font.bold = True
        p1.font.color.rgb = COLOR_NAVY

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.name = FONT_BODY
        p2.font.size = Pt(11)
        p2.font.color.rgb = COLOR_TEXT_DARK

    # =========================================================================
    # SLIDE 4: 2. HIỆN TRẠNG & 3 THÁCH THỨC KỸ THUẬT TẠI BIÊN
    # =========================================================================
    s4 = create_blank_slide(prs)
    add_header(s4, "Phần 2: Hiện trạng & Thách thức", "Ba Thách Thức Kỹ Thuật Lớn Khi Triển Khai Tại Biên", page_num=4)

    challenges = [
        ("Thách thức 1", "Giới Hạn CPU Biên Raspberry Pi 4",
         "Vấn đề: Pi 4 chỉ có CPU 4 nhân ARM, không có GPU rời. Khi chạy đồng thời MTCNN, FaceNet và YOLOv8 cho 2 camera, nguy cơ CPU quá tải 100%, sụt FPS và tràn RAM (OOM Crash).\n"
         "➔ Giải pháp: Thiết kế khóa luồng tài nguyên đồng bộ (gpu_lock) và chế độ torch.no_grad() tuần tự hóa suy luận."),
        ("Thách thức 2", "Mất Mát > 50% Đặc Trưng Do Khẩu Trang",
         "Vấn đề: Khẩu trang che khuất từ sống mũi xuống cằm khiến các thuật toán FaceNet/ArcFace thông thường đối chiếu với ảnh mộc bị sai lệch hoặc từ chối nhận dạng.\n"
         "➔ Giải pháp: Đột phá với kỹ thuật Zero-out 45% nửa dưới (face[:, 88:, :] = 0.0), nhận diện đúng chỉ với 1 ảnh mẫu không khẩu trang duy nhất!"),
        ("Thách thức 3", "Nguy Cơ Cháy Khóa Cửa & Tê Liệt Khi Mất Điện",
         "Vấn đề: Khóa Solenoid 12V nếu cấp điện liên tục quá 10s sẽ bị cháy cuộn hút và kẹt chốt. Khi mất điện nguồn đột ngột, hệ thống camera nhúng thường bị mất tiến trình.\n"
         "➔ Giải pháp: Xung kích mở khóa 3.0s tự ngắt, còi hú phân cấp và dịch vụ Linux Systemd tự phục hồi trong < 45s.")
    ]

    for i, (tag, title, desc) in enumerate(challenges):
        x_pos = Inches(0.8 + i * 4.0)
        add_card(s4, x_pos, Inches(1.65), Inches(3.733), Inches(5.1))
        
        tb = s4.shapes.add_textbox(x_pos + Inches(0.25), Inches(1.85), Inches(3.233), Inches(4.7))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p_tag = tf.paragraphs[0]
        p_tag.text = tag.upper()
        p_tag.font.name = FONT_HEADING
        p_tag.font.size = Pt(11)
        p_tag.font.bold = True
        p_tag.font.color.rgb = COLOR_AMBER_BORDER

        p_title = tf.add_paragraph()
        p_title.text = title
        p_title.font.name = FONT_HEADING
        p_title.font.size = Pt(13.5)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_NAVY

        p_desc = tf.add_paragraph()
        p_desc.text = desc
        p_desc.font.name = FONT_BODY
        p_desc.font.size = Pt(11)
        p_desc.font.color.rgb = COLOR_TEXT_DARK

    # =========================================================================
    # SLIDE 5: 3. TỔNG QUAN KIẾN TRÚC HỆ THỐNG SMART CAMERA
    # =========================================================================
    s5 = create_blank_slide(prs)
    add_header(s5, "Phần 3: Phương pháp & Kiến trúc", "Tổng Quan Kiến Trúc Hệ Thống Smart Camera Biên", page_num=5)

    arch_layers = [
        ("TẦNG 1: THU NHẬN & THỊ GIÁC AI", [
            "• 2x Webcam USB 640x480 @ 15fps cổng USB 3.0",
            "• MTCNN Face Detector (Trích xuất 160x160)",
            "• FaceNet 512D Embedding (Kỹ thuật Masked Face)",
            "• YOLOv8 Nano Detectors (Té ngã, Cháy nổ, Xâm nhập ROI)"
        ]),
        ("TẦNG 2: ĐIỀU PHỐI BIÊN & PHẦN CỨNG", [
            "• Khóa luồng đồng bộ toàn cục: gpu_lock = threading.Lock()",
            "• Thiết bị trung tâm: Raspberry Pi 4 Model B (4GB RAM)",
            "• Cảm biến khí ga MQ-2 (Chân DO nối GPIO 18 - Pin 12)",
            "• Rơ-le khóa Solenoid 12V (GPIO 23) & Còi Buzzer (GPIO 24)"
        ]),
        ("TẦNG 3: NỀN TẢNG QUẢN TRỊ & TƯƠNG TÁC", [
            "• FastAPI Server bất đồng bộ (Asynchronous Python)",
            "• Server-Sent Events (SSE) đẩy sự kiện thời gian thực < 50ms",
            "• Web Dashboard: Quản trị thành viên, vẽ ROI, xem camera",
            "• Telegram Bot 2 chiều (Long Polling) & Systemd Auto-restart"
        ])
    ]

    for i, (title, items) in enumerate(arch_layers):
        y_pos = Inches(1.65 + i * 1.65)
        add_card(s5, Inches(0.8), y_pos, Inches(11.733), Inches(1.45))
        
        tb = s5.shapes.add_textbox(Inches(1.1), y_pos + Inches(0.12), Inches(11.1), Inches(1.2))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p_title = tf.paragraphs[0]
        p_title.text = title
        p_title.font.name = FONT_HEADING
        p_title.font.size = Pt(13)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_PRIMARY

        p_items = tf.add_paragraph()
        p_items.text = "   |   ".join(items)
        p_items.font.name = FONT_BODY
        p_items.font.size = Pt(11)
        p_items.font.color.rgb = COLOR_TEXT_DARK

    # =========================================================================
    # SLIDE 6: 3. PIPELINE THỊ GIÁC MÁY TÍNH ĐA NGUY CƠ
    # =========================================================================
    s6 = create_blank_slide(prs)
    add_header(s6, "Phần 3: Phương pháp & Kiến trúc", "Pipeline Thị Giác Máy Tính Đa Nguy Cơ Trên CPU Biên", page_num=6)

    # Cột trái: Luồng xử lý
    add_card(s6, Inches(0.8), Inches(1.65), Inches(6.0), Inches(5.1))
    tb_pipe = s6.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.6), Inches(4.7))
    tf_p = tb_pipe.text_frame
    tf_p.word_wrap = True

    p0 = tf_p.paragraphs[0]
    p0.text = "CHI TIẾT LUỒNG XỬ LÝ VIDEO & AI BIÊN:"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_PRIMARY

    lines = (
        "1. Thu nhận khung hình: 2 Camera USB stream độc lập 640x480 @ 15fps.\n"
        "2. Nhánh Khuôn mặt (Face Recognition Branch):\n"
        "   • MTCNN phát hiện khuôn mặt và căn chỉnh mốc tọa độ (160x160).\n"
        "   • Tiền xử lý Zero-out bôi đen 45% phần dưới khuôn mặt.\n"
        "   • FaceNet Inception-ResNet trích xuất vector đặc trưng 512D.\n"
        "   • So khớp khoảng cách Euclidean L2 với CSDL mẫu (ngưỡng 0.80).\n"
        "3. Nhánh Nguy cơ (Hazard Detection Branch):\n"
        "   • YOLOv8 Nano suy luận phát hiện ngọn lửa (fire) và té ngã (fall).\n"
        "   • Bộ đệm debounce 3 khung hình liên tiếp loại bỏ báo động giả.\n"
        "   • cv2.pointPolygonTest kiểm tra xâm nhập hàng rào ảo ROI.\n"
        "4. Khóa tài nguyên: with gpu_lock: with torch.no_grad(): đảm bảo không nghẽn CPU."
    )
    p_desc = tf_p.add_paragraph()
    p_desc.text = lines
    p_desc.font.name = FONT_BODY
    p_desc.font.size = Pt(10.5)
    p_desc.font.color.rgb = COLOR_TEXT_DARK

    # Cột phải: Placeholder ảnh thực tế bàn thí nghiệm
    add_photo_placeholder(
        s6, Inches(7.1), Inches(1.65), Inches(5.433), Inches(5.1),
        "Góc Bàn Làm Việc Thực Tế Với Raspberry Pi 4 & 2 Webcam",
        [
            "Nội dung: Chụp góc bàn thí nghiệm thực tế bố trí bo mạch Raspberry Pi 4 kết nối 2 camera USB.",
            "Yêu cầu: Thấy rõ bo mạch Pi 4, quạt tản nhiệt nhôm đang quay, 2 webcam USB cắm cổng USB 3.0 và màn hình laptop đang stream video.",
            "Góc chụp: Chụp từ trên xuống góc 45 độ, ánh sáng rõ ràng.",
            "Mục đích: Chứng minh pipeline AI chạy thực tế trên phần cứng nhúng biên thay vì máy trạm mô phỏng."
        ]
    )

    # =========================================================================
    # SLIDE 7: 3. THUẬT TOÁN NHẬN DIỆN KHẨU TRANG 1 ẢNH MẪU
    # =========================================================================
    s7 = create_blank_slide(prs)
    add_header(s7, "Phần 3: Phương pháp & Kiến trúc", "Thuật Toán Nhận Diện Khẩu Trang 1 Ảnh Mẫu Đột Phá", page_num=7)

    # Cột trái: Công thức & Giải pháp
    add_card(s7, Inches(0.8), Inches(1.65), Inches(5.8), Inches(5.1))
    tb_mask = s7.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.4), Inches(4.7))
    tf_m = tb_mask.text_frame
    tf_m.word_wrap = True

    p0 = tf_m.paragraphs[0]
    p0.text = "CƠ CHẾ BÔI ĐEN ĐẶC TRƯNG (ZERO-OUT MASKING):"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_PRIMARY

    mask_desc = (
        "• Vấn đề: Khi đeo khẩu trang, hơn 50% đặc trưng khuôn mặt (từ mũi xuống cằm) bị che khuất.\n\n"
        "• Công thức đồng bộ cốt lõi:\n"
        "   + Ảnh đăng ký CSDL (mặt mộc): face[:, 88:, :] = 0.0\n"
        "   + Khung hình camera stream: faces[:, :, 88:, :] = 0.0\n\n"
        "• Trích xuất vector L2-Norm 512 chiều từ FaceNet Inception-ResNet.\n\n"
        "• Ngưỡng so khớp L2 Distance cố định tối ưu: threshold = 0.80\n"
        "   + d(v_live, v_db) < 0.80  ➔ Xác nhận đúng danh tính thành viên.\n"
        "   + d(v_live, v_db) >= 0.80 ➔ Người lạ / Đối tượng xâm nhập.\n\n"
        "➔ Ưu điểm vượt trội: Đăng ký duy nhất 1 ảnh chân dung mộc, nhận diện chính xác cả khi ĐEO và KHÔNG ĐEO khẩu trang mà KHÔNG cần huấn luyện lại mô hình!"
    )
    p_m = tf_m.add_paragraph()
    p_m.text = mask_desc
    p_m.font.name = FONT_BODY
    p_m.font.size = Pt(10.5)
    p_m.font.color.rgb = COLOR_TEXT_DARK

    # Cột phải: Placeholder ảnh thực tế
    add_photo_placeholder(
        s7, Inches(6.9), Inches(1.65), Inches(5.633), Inches(5.1),
        "Màn Hình Nhận Diện Khuôn Mặt Đeo Khẩu Trang Trên Web",
        [
            "Nội dung: Chụp ảnh chụp màn hình Web Dashboard khi bạn đang đeo khẩu trang đứng trước camera.",
            "Yêu cầu hiển thị trên ảnh:",
            "  + Bounding box màu xanh bao quanh khuôn mặt đeo khẩu trang.",
            "  + Hiển thị đúng tên của bạn (ví dụ: 'Toan').",
            "  + Hiển thị chỉ số khoảng cách Euclidean L2 (ví dụ: '0.68 < 0.80').",
            "Mục đích: Minh chứng thuật toán bôi đen 45% nửa dưới hoạt động xuất sắc trong điều kiện thực tế."
        ]
    )

    # =========================================================================
    # SLIDE 8: 3. MÔ HÌNH YOLOV8 GIÁM SÁT TÉ NGÃ, CHÁY NỔ & ROI
    # =========================================================================
    s8 = create_blank_slide(prs)
    add_header(s8, "Phần 3: Phương pháp & Kiến trúc", "Mô Hình YOLOv8 Giám Sát Té Ngã, Cháy Nổ & Xâm Nhập ROI", page_num=8)

    # Cột trái: 3 chức năng nguy cơ
    add_card(s8, Inches(0.8), Inches(1.65), Inches(5.8), Inches(5.1))
    tb_haz = s8.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.4), Inches(4.7))
    tf_h = tb_haz.text_frame
    tf_h.word_wrap = True

    p0 = tf_h.paragraphs[0]
    p0.text = "3 TÍNH NĂNG CẢNH BÁO NGUY CƠ TÍCH HỢP:"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_PRIMARY

    haz_desc = (
        "1. Phát hiện Té ngã (Fall Detection):\n"
        "   • Nhận diện tư thế nằm bất thường của người già và trẻ nhỏ.\n"
        "   • Bộ đệm debounce 3 khung hình liên tiếp để loại trừ các cử chỉ cúi nhặt đồ hoặc ngồi xổm.\n"
        "   • Tự động chụp ảnh gửi khẩn cấp về Telegram cho người thân.\n\n"
        "2. Phát hiện Hỏa hoạn (Fire & Smoke Detection):\n"
        "   • Nhận diện ngọn lửa và khói sớm với độ ưu tiên cao nhất.\n"
        "   • Kích hoạt còi báo động nhấp nháy cực nhanh (0.1s bật - 0.1s tắt).\n\n"
        "3. Hàng rào ảo ROI (Virtual Fence):\n"
        "   • Người dùng vẽ trực tiếp đa giác bảo vệ tùy biến trên Web Dashboard.\n"
        "   • Thuật toán cv2.pointPolygonTest kiểm tra tâm tọa độ đáy của đối tượng bước vào khu vực cấm."
    )
    p_h = tf_h.add_paragraph()
    p_h.text = haz_desc
    p_h.font.name = FONT_BODY
    p_h.font.size = Pt(10.5)
    p_h.font.color.rgb = COLOR_TEXT_DARK

    # Cột phải: Placeholder ảnh vẽ ROI
    add_photo_placeholder(
        s8, Inches(6.9), Inches(1.65), Inches(5.633), Inches(5.1),
        "Giao Diện Vẽ Vùng Bảo Vệ Ảo ROI Trên Web Dashboard",
        [
            "Nội dung: Chụp ảnh màn hình Web Dashboard phần cấu hình Camera.",
            "Yêu cầu hiển thị trên ảnh:",
            "  + Khung hình camera stream trực tiếp.",
            "  + Các nét vẽ đa giác ROI viền đỏ/xanh bao quanh khu vực cửa ra vào hoặc khu vực an ninh.",
            "  + Các nút chức năng 'Lưu vùng ROI' và 'Bật cảnh báo xâm nhập'.",
            "Mục đích: Minh họa tính năng tương tác cấu hình hàng rào an ninh thông minh."
        ]
    )

    # =========================================================================
    # SLIDE 9: 3. CƠ CHẾ KHÓA LUỒNG CPU & TỐI ƯU HÓA BIÊN
    # =========================================================================
    s9 = create_blank_slide(prs)
    add_header(s9, "Phần 3: Phương pháp & Kiến trúc", "Cơ Chế Khóa Luồng Đồng Bộ CPU (Concurrency Lock)", page_num=9)

    add_card(s9, Inches(0.8), Inches(1.65), Inches(5.7), Inches(5.1))
    tb_c1 = s9.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.3), Inches(4.7))
    tf_c1 = tb_c1.text_frame
    tf_c1.word_wrap = True

    p0 = tf_c1.paragraphs[0]
    p0.text = "NGUYÊN NHÂN & THIẾT KẾ KHÓA ĐỒNG BỘ:"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_PRIMARY

    c1_desc = (
        "• Thách thức đa luồng CPU biên:\n"
        "   Raspberry Pi 4 chỉ có 4 nhân CPU ARM Cortex-A72. Nếu 2 camera cùng lúc gọi MTCNN + FaceNet + YOLOv8 song song không kiểm soát, CPU sẽ quá tải 100%, gây nghẽn I/O và hệ điều hành buộc phải kill tiến trình do OOM (Out-Of-Memory).\n\n"
        "• Khóa lock toàn cục: gpu_lock = threading.Lock() tại app/processors.py\n\n"
        "• Cơ chế hoạt động:\n"
        "   with gpu_lock:\n"
        "       with torch.no_grad():\n"
        "           # Suy luận mô hình AI tuần tự\n\n"
        "• Tắt tính toán gradient: with torch.no_grad() giúp tiết kiệm hơn 400MB RAM."
    )
    p_c1 = tf_c1.add_paragraph()
    p_c1.text = c1_desc
    p_c1.font.name = FONT_BODY
    p_c1.font.size = Pt(11)
    p_c1.font.color.rgb = COLOR_TEXT_DARK

    add_card(s9, Inches(6.8), Inches(1.65), Inches(5.733), Inches(5.1))
    tb_c2 = s9.shapes.add_textbox(Inches(7.0), Inches(1.85), Inches(5.333), Inches(4.7))
    tf_c2 = tb_c2.text_frame
    tf_c2.word_wrap = True

    p1 = tf_c2.paragraphs[0]
    p1.text = "HIỆU QUẢ KIỂM CHỨNG TRÊN RASPBERRY PI 4 (4GB):"
    p1.font.name = FONT_HEADING
    p1.font.size = Pt(13)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_GREEN

    c2_desc = (
        "• Kết quả đo lường thực tế (chạy liên tục 1525.6 giây ~ 25.4 phút):\n"
        "   + Tải CPU trung bình: Duy trì ổn định ở 55.0% (mát mẻ, không quá nhiệt).\n"
        "   + Bộ nhớ RAM sử dụng: 846.5 MB (chỉ chiếm ~21% dung lượng 4GB của Pi 4).\n"
        "   + Tốc độ khung hình: 3.7 FPS (đạt chuẩn thời gian thực cho giám sát an ninh nhúng).\n"
        "   + Độ trễ gửi tin nhắn Telegram: 1.67 giây.\n\n"
        "• So sánh với khi không dùng khóa gpu_lock:\n"
        "   + Không dùng lock: CPU vọt lên 100%, RAM tăng mất kiểm soát > 2.8GB, hệ thống bị treo cứng sau ~3 phút chạy 2 camera.\n"
        "   + Có dùng lock: Hoạt động ổn định 24/7, không rò rỉ bộ nhớ, phản hồi tin cậy."
    )
    p_c2 = tf_c2.add_paragraph()
    p_c2.text = c2_desc
    p_c2.font.name = FONT_BODY
    p_c2.font.size = Pt(11)
    p_c2.font.color.rgb = COLOR_TEXT_DARK

    # =========================================================================
    # SLIDE 10: 3. PHÂN HỆ PHẦN CỨNG & CẢM BIẾN NGOẠI VI
    # =========================================================================
    s10 = create_blank_slide(prs)
    add_header(s10, "Phần 3: Phương pháp & Kiến trúc", "Sơ Đồ Kết Nối Chân GPIO & Thiết Bị Ngoại Vi An Ninh", page_num=10)

    # Cột trái: Bảng chân cắm GPIO
    add_card(s10, Inches(0.8), Inches(1.65), Inches(5.8), Inches(5.1))
    tb_gpio = s10.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.4), Inches(4.7))
    tf_g = tb_gpio.text_frame
    tf_g.word_wrap = True

    p0 = tf_g.paragraphs[0]
    p0.text = "BẢNG PHÂN BỔ CHÂN CẮM GPIO RASPBERRY PI 4:"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_PRIMARY

    gpio_desc = (
        "• Cảm biến khí ga MQ-2 (Gas Leak Sensor):\n"
        "   + Chân Digital Output (DO) nối GPIO 18 (Pin 12 vật lý).\n"
        "   + VCC nối 5V (Pin 2), GND nối Pin 6. Chu kỳ quét 1 giây/lần.\n"
        "   + Chân DO xuống mức LOW khi nồng độ gas vượt ngưỡng báo động.\n\n"
        "• Rơ-le Khóa cửa điện từ Solenoid 12V (Door Lock Relay):\n"
        "   + Chân tín hiệu điều khiển nối GPIO 23 (Pin 16 vật lý).\n"
        "   + Xung kích mở khóa: Xuất mức HIGH trong đúng 3.0s rồi ngắt về LOW, loại trừ hoàn toàn nguy cơ cháy cuộn nam châm điện.\n\n"
        "• Còi báo động vật lý (Active Buzzer):\n"
        "   + Chân I/O nối GPIO 24 (Pin 18 vật lý). Nhấp nháy tần số phân cấp: Hỏa hoạn 0.1s, Khí ga 0.3s, Đột nhập 0.8s.\n\n"
        "• Tính năng Cross-Platform: Bọc khối try...except an toàn chạy giả lập trên PC và chạy GPIO thật trên Raspberry Pi 4."
    )
    p_g = tf_g.add_paragraph()
    p_g.text = gpio_desc
    p_g.font.name = FONT_BODY
    p_g.font.size = Pt(10.5)
    p_g.font.color.rgb = COLOR_TEXT_DARK

    # Cột phải: Placeholder ảnh chụp chân cắm GPIO
    add_photo_placeholder(
        s10, Inches(6.9), Inches(1.65), Inches(5.633), Inches(5.1),
        "Cận Cảnh Dây Cắm Hàng Chân GPIO Trên Bo Mạch Pi 4",
        [
            "Nội dung: Chụp macro cận cảnh hàng 40 chân GPIO của Raspberry Pi 4.",
            "Yêu cầu hiển thị trên ảnh:",
            "  + Thấy rõ các dây cắm jumper màu nối vào các chân chính:",
            "    * GPIO 18 (Chân 12) nối cảm biến MQ-2.",
            "    * GPIO 23 (Chân 16) nối module rơ-le khóa cửa.",
            "    * GPIO 24 (Chân 18) nối còi báo động buzzer.",
            "    * Chân nguồn 5V, 3.3V và chân mass GND.",
            "Mục đích: Minh chứng việc đấu nối mạch điện tử chính xác theo thiết kế kỹ thuật."
        ]
    )

    # =========================================================================
    # SLIDE 11: 3. SƠ ĐỒ MẠCH ĐIỆN TỬ & ĐẤU NỐI THIẾT BỊ HOÀN CHỈNH
    # =========================================================================
    s11 = create_blank_slide(prs)
    add_header(s11, "Phần 3: Phương pháp & Kiến trúc", "Sơ Đồ Mạch Điện Tử & Đấu Nối Thiết Bị Ngoại Vi Hoàn Chỉnh", page_num=11)

    # Cột trái: Sơ đồ mạch điện tử
    wiring_img = "static/raspberry_pi_wiring_diagram.png"
    if os.path.exists(wiring_img):
        try:
            s11.shapes.add_picture(wiring_img, Inches(0.8), Inches(1.65), width=Inches(6.0))
        except Exception:
            pass
    else:
        add_card(s11, Inches(0.8), Inches(1.65), Inches(6.0), Inches(5.1))

    # Cột phải: Placeholder ảnh chụp mô hình thực tế
    add_photo_placeholder(
        s11, Inches(7.1), Inches(1.65), Inches(5.433), Inches(5.1),
        "Mô Hình Phần Cứng Hoàn Chỉnh Đặt Trên Bàn Làm Việc",
        [
            "THÔNG SỐ NGUỒN CẤP & AN TOÀN ĐIỆN:",
            "• Nguồn 1: Cổng USB Type-C 5V - 3A độc lập cấp cho Raspberry Pi 4.",
            "• Nguồn 2: Adapter nguồn rời 12VDC - 2A cấp riêng cho cuộn hút khóa Solenoid.",
            "• Rơ-le cách ly quang (Optocoupler) chống xung ngược bảo vệ chân GPIO.",
            "-----------------------------------------------------------------------",
            "YÊU CẦU ẢNH THỰC TẾ CẦN CHỤP:",
            "• Chụp góc rộng toàn cảnh mô hình phần cứng đặt trên bàn gồm:",
            "  + Bo mạch Pi 4 đang cắm nguồn và 2 webcam USB.",
            "  + Module rơ-le nối với khóa chốt Solenoid 12V.",
            "  + Cảm biến khí ga MQ-2 và còi báo động Active Buzzer."
        ]
    )

    # =========================================================================
    # SLIDE 12: 3. NỀN TẢNG ĐIỀU KHIỂN WEB DASHBOARD (SSE)
    # =========================================================================
    s12 = create_blank_slide(prs)
    add_header(s12, "Phần 3: Phương pháp & Kiến trúc", "Nền Tảng Web Dashboard Quản Trị & Server-Sent Events (SSE)", page_num=12)

    # Cột trái: Kiến trúc phần mềm Web
    add_card(s12, Inches(0.8), Inches(1.65), Inches(5.8), Inches(5.1))
    tb_web = s12.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.4), Inches(4.7))
    tf_w = tb_web.text_frame
    tf_w.word_wrap = True

    p0 = tf_w.paragraphs[0]
    p0.text = "KIẾN TRÚC MÁY CHỦ BIÊN FASTAPI & SSE:"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_PRIMARY

    web_desc = (
        "• Framework Backend: FastAPI (Python) bất đồng bộ (Async/Await) cho tốc độ xử lý I/O cực nhanh và tiết kiệm RAM.\n\n"
        "• Công nghệ Server-Sent Events (SSE):\n"
        "   + Luồng sự kiện một chiều đẩy dữ liệu cảm biến khí ga, trạng thái khóa cửa và log an ninh thời gian thực về trình duyệt.\n"
        "   + Độ trễ cập nhật < 50ms, không làm tải CPU như phương pháp Polling truyền thống.\n\n"
        "• Video Streaming Đa Luồng: Chuẩn multipart/x-mixed-replace phân luồng độc lập cho Camera 1 và Camera 2.\n\n"
        "• Tương tác quản trị trực quan:\n"
        "   + Đăng ký khuôn mặt thành viên mới với 1 ảnh chân dung mộc.\n"
        "   + Công cụ vẽ hàng rào ảo ROI trực tiếp bằng chuột trên trình duyệt.\n"
        "   + Nút bấm kích mở khóa cửa từ xa thuận tiện."
    )
    p_w = tf_w.add_paragraph()
    p_w.text = web_desc
    p_w.font.name = FONT_BODY
    p_w.font.size = Pt(10.5)
    p_w.font.color.rgb = COLOR_TEXT_DARK

    # Cột phải: Placeholder ảnh Web Dashboard
    add_photo_placeholder(
        s12, Inches(6.9), Inches(1.65), Inches(5.633), Inches(5.1),
        "Màn Hình Giao Diện Web Dashboard Đang Giám Sát",
        [
            "Nội dung: Chụp toàn màn hình laptop mở giao diện Web Dashboard.",
            "Yêu cầu hiển thị trên ảnh:",
            "  + 2 khung hình video camera stream đồng thời.",
            "  + Thanh trạng thái cảm biến khí ga (báo Normal / Gas Active).",
            "  + Trạng thái khóa cửa (Locked / Unlocked).",
            "  + Bảng nhật ký sự kiện an ninh (Security Event Log).",
            "Mục đích: Chứng minh giao diện quản trị trực quan, hiện đại và hoạt động thời gian thực."
        ]
    )

    # =========================================================================
    # SLIDE 13: 3. TELEGRAM BOT 2 CHIỀU & TỰ KHÔI PHỤC MẤT ĐIỆN
    # =========================================================================
    s13 = create_blank_slide(prs)
    add_header(s13, "Phần 3: Phương pháp & Kiến trúc", "Giao Tiếp 2 Chiều Telegram Bot & Khôi Phục Sau Mất Điện", page_num=13)

    # Cột trái: Chi tiết Bot & Systemd
    add_card(s13, Inches(0.8), Inches(1.65), Inches(5.8), Inches(5.1))
    tb_bot = s13.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.4), Inches(4.7))
    tf_b = tb_bot.text_frame
    tf_b.word_wrap = True

    p0 = tf_b.paragraphs[0]
    p0.text = "TELEGRAM BOT LONG POLLING & LINUX SYSTEMD:"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_PRIMARY

    bot_desc = (
        "1. Giao tiếp 2 chiều Telegram Bot (Long Polling):\n"
        "   • Chạy luồng daemon độc lập, nhận tin nhắn và nút bấm tức thì mà không cần mở port router hay đăng ký IP tĩnh.\n"
        "   • Nút bấm tương tác Inline: [🔕 Tắt báo động], [⏸ Tạm dừng 30s], [🔓 Mở khóa cửa].\n"
        "   • Nhận diện lệnh tin nhắn tiếng Việt & tiếng Anh: /unlock, /mo_cua, unlock, mở cửa.\n"
        "   • Phân quyền độc lập từng camera: Lệnh /cameras, /cam hiển thị menu bật/tắt (Arm/Disarm) cảnh báo cho từng mắt camera riêng lẻ.\n\n"
        "2. Cơ chế Tự Khôi Phục Sau Mất Điện (System Resilience):\n"
        "   • Đăng ký daemon Linux Systemd (smartcamera.service) với cờ Restart=always.\n"
        "   • Khi có điện trở lại, hệ điều hành tự động khôi phục toàn bộ tiến trình camera, Web server và Telegram bot trong 42 giây mà không cần người dùng thao tác."
    )
    p_b = tf_b.add_paragraph()
    p_b.text = bot_desc
    p_b.font.name = FONT_BODY
    p_b.font.size = Pt(10.5)
    p_b.font.color.rgb = COLOR_TEXT_DARK

    # Cột phải: Placeholder ảnh Telegram Bot
    add_photo_placeholder(
        s13, Inches(6.9), Inches(1.65), Inches(5.633), Inches(5.1),
        "Màn Hình Điện Thoại Nhận Cảnh Báo & Tương Tác Telegram Bot",
        [
            "Nội dung: Chụp ảnh chụp màn hình điện thoại (Screenshot) ứng dụng Telegram chat với Smart Camera Bot.",
            "Yêu cầu hiển thị trên ảnh:",
            "  + Tin nhắn báo động kèm ảnh chụp hiện trường từ camera.",
            "  + Các nút bấm tương tác Inline dưới ảnh: [Tắt báo động] | [Tạm dừng 30s] | [Mở khóa cửa].",
            "  + Tin nhắn người dùng gõ lệnh '/unlock' và bot phản hồi mở cửa.",
            "Mục đích: Minh chứng khả năng điều khiển tương tác từ xa 2 chiều thuận tiện."
        ]
    )

    # =========================================================================
    # SLIDE 14: 4. KẾT QUẢ: NHẬN DIỆN KHUÔN MẶT CÓ & KHÔNG KHẨU TRANG
    # =========================================================================
    s14 = create_blank_slide(prs)
    add_header(s14, "Phần 4: Kết quả thực nghiệm", "Thực Nghiệm 1: Nhận Diện Khuôn Mặt Đeo Khẩu Trang Với 1 Ảnh Mẫu", page_num=14)

    # Cột trái: Kịch bản thử nghiệm
    add_card(s14, Inches(0.8), Inches(1.65), Inches(5.8), Inches(5.1))
    tb_r1 = s14.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.4), Inches(4.7))
    tf_r1 = tb_r1.text_frame
    tf_r1.word_wrap = True

    p0 = tf_r1.paragraphs[0]
    p0.text = "KỊCH BẢN & SỐ LIỆU ĐO LƯỜNG THỰC TẾ:"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_PRIMARY

    r1_desc = (
        "• Dữ liệu đăng ký: Chỉ nạp 1 ảnh chân dung mộc duy nhất không khẩu trang vào CSDL.\n\n"
        "• Thử nghiệm 1 - Người nhà KHÔNG đeo khẩu trang:\n"
        "   + MTCNN phát hiện mặt, FaceNet trích xuất 512 chiều.\n"
        "   + Khoảng cách L2 Distance = 0.42 < 0.80 ➔ Nhận diện chính xác 100%, bounding box xanh hiện tên thành viên.\n\n"
        "• Thử nghiệm 2 - Người nhà ĐEO KHẨU TRANG Y TẾ:\n"
        "   + Thuật toán tự bôi đen 45% nửa dưới khuôn mặt.\n"
        "   + Khoảng cách L2 Distance = 0.68 < 0.80 ➔ Vẫn xác thực chính xác danh tính thành viên dù bị che khuất mũi và miệng!\n\n"
        "• Thử nghiệm 3 - NGƯỜI LẠ (Unknown Person):\n"
        "   + Khoảng cách L2 Distance = 1.15 > 0.80 ➔ Hệ thống từ chối danh tính, cảnh báo người lạ xâm nhập."
    )
    p_r1 = tf_r1.add_paragraph()
    p_r1.text = r1_desc
    p_r1.font.name = FONT_BODY
    p_r1.font.size = Pt(10.5)
    p_r1.font.color.rgb = COLOR_TEXT_DARK

    # Cột phải: Placeholder 2 ảnh thực tế
    add_photo_placeholder(
        s14, Inches(6.9), Inches(1.65), Inches(5.633), Inches(5.1),
        "2 Ảnh Thực Tế Nhận Diện: Có & Không Đeo Khẩu Trang",
        [
            "BẠN CẦN CHỤP 2 ẢNH ĐỂ CHÈN VÀO VỊ TRÍ NÀY:",
            "  1. Ảnh 1: Bạn đứng trước camera KHÔNG đeo khẩu trang, trên màn hình Web hiển thị khung viền xanh có tên bạn (ví dụ: 'Toan - 0.42').",
            "  2. Ảnh 2: Chính bạn ĐEO KHẨU TRANG Y TẾ đứng trước camera, trên màn hình Web vẫn hiển thị khung viền xanh đúng tên bạn (ví dụ: 'Toan - 0.68').",
            "Mục đích: Chứng minh giải pháp Zero-out 45% nhận diện người đeo khẩu trang đạt hiệu quả vượt bậc."
        ]
    )

    # =========================================================================
    # SLIDE 15: 4. KẾT QUẢ: PHÁT HIỆN TÉ NGÃ & XÂM NHẬP VÙNG ROI
    # =========================================================================
    s15 = create_blank_slide(prs)
    add_header(s15, "Phần 4: Kết quả thực nghiệm", "Thực Nghiệm 2: Phát Hiện Người Té Ngã & Xâm Nhập Vùng ROI", page_num=15)

    # Cột trái: Kịch bản thử nghiệm
    add_card(s15, Inches(0.8), Inches(1.65), Inches(5.8), Inches(5.1))
    tb_r2 = s15.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.4), Inches(4.7))
    tf_r2 = tb_r2.text_frame
    tf_r2.word_wrap = True

    p0 = tf_r2.paragraphs[0]
    p0.text = "KỊCH BẢN PHÁT HIỆN TÉ NGÃ & XÂM NHẬP ROI:"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_PRIMARY

    r2_desc = (
        "• Kịch bản 1 - Phát hiện Té ngã (Fall Detection):\n"
        "   + Giả lập tư thế người trượt chân ngã nằm trên sàn nhà.\n"
        "   + Mô hình YOLOv8 phát hiện nhãn 'fall' với độ tin cậy 89%.\n"
        "   + Thuật toán đếm debounce 3 khung hình liên tiếp để loại bỏ hành vi cúi nhặt đồ hoặc ngồi xổm.\n"
        "   + Gửi tin nhắn cảnh báo khẩn cấp kèm ảnh chụp hiện trường về Telegram cho người thân sau 1.67s.\n\n"
        "• Kịch bản 2 - Hàng rào ảo ROI (Intrusion Detection):\n"
        "   + Thiết lập vùng đa giác bảo vệ cửa ban đêm trên Web.\n"
        "   + Khi đối tượng bước chân vào vùng cấm, cv2.pointPolygonTest kích hoạt cảnh báo đỏ 'Intrusion Alert'.\n"
        "   + Còi Buzzer nhấp nháy chu kỳ 0.8s và gửi cảnh báo tức thì."
    )
    p_r2 = tf_r2.add_paragraph()
    p_r2.text = r2_desc
    p_r2.font.name = FONT_BODY
    p_r2.font.size = Pt(10.5)
    p_r2.font.color.rgb = COLOR_TEXT_DARK

    # Cột phải: Placeholder 2 ảnh thực tế
    add_photo_placeholder(
        s15, Inches(6.9), Inches(1.65), Inches(5.633), Inches(5.1),
        "2 Ảnh Thực Tế Kiểm Nghiệm Té Ngã & Xâm Nhập ROI",
        [
            "BẠN CẦN CHỤP 2 ẢNH ĐỂ CHÈN VÀO VỊ TRÍ NÀY:",
            "  1. Ảnh 1: Ảnh người nằm ngã trên sàn nhà có khung nhận diện chữ nhật nhãn 'fall' màu đỏ/vàng trên màn hình camera.",
            "  2. Ảnh 2: Ảnh người bước chân vào vùng đa giác ROI màu đỏ và hệ thống hiển thị cảnh báo xâm nhập 'Intrusion'.",
            "Mục đích: Minh chứng 2 tính năng an toàn cốt lõi cho người già và bảo vệ chống trộm ban đêm."
        ]
    )

    # =========================================================================
    # SLIDE 16: 4. KẾT QUẢ: BÁO CHÁY NỔ & CẢM BIẾN KHÍ GA MQ-2
    # =========================================================================
    s16 = create_blank_slide(prs)
    add_header(s16, "Phần 4: Kết quả thực nghiệm", "Thực Nghiệm 3: Cảnh Báo Hỏa Hoạn & Rò Rỉ Khí Ga MQ-2", page_num=16)

    # Cột trái: Kịch bản thử nghiệm
    add_card(s16, Inches(0.8), Inches(1.65), Inches(5.8), Inches(5.1))
    tb_r3 = s16.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.4), Inches(4.7))
    tf_r3 = tb_r3.text_frame
    tf_r3.word_wrap = True

    p0 = tf_r3.paragraphs[0]
    p0.text = "KỊCH BẢN BÁO ĐỘNG CHÁY NỔ & RÒ RỈ KHÍ GA:"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_PRIMARY

    r3_desc = (
        "• Kịch bản 1 - Báo động Cháy nổ (Fire Detection):\n"
        "   + Thử nghiệm bật ngọn lửa/que diêm trước camera.\n"
        "   + Mô hình YOLOv8 phát hiện nhãn 'fire' ngay lập tức.\n"
        "   + Còi báo động vật lý Active Buzzer nháy cực nhanh (chu kỳ 0.1s bật / 0.1s tắt).\n"
        "   + Đẩy thông báo khẩn cấp màu đỏ kèm ảnh chụp hiện trường về Telegram trong 1.67 giây.\n\n"
        "• Kịch bản 2 - Rò rỉ Khí Ga MQ-2 (Gas Leak Alert):\n"
        "   + Đưa bật lửa xì gas gần đầu cảm biến MQ-2.\n"
        "   + Chân DO chuyển từ mức HIGH xuống LOW.\n"
        "   + Hệ thống kích hoạt cờ gas_active = True, còi hú chu kỳ vừa 0.3s và gửi tin nhắn cảnh báo rò rỉ gas kèm khuyến nghị mở cửa thông thoáng."
    )
    p_r3 = tf_r3.add_paragraph()
    p_r3.text = r3_desc
    p_r3.font.name = FONT_BODY
    p_r3.font.size = Pt(10.5)
    p_r3.font.color.rgb = COLOR_TEXT_DARK

    # Cột phải: Placeholder 2 ảnh thực tế
    add_photo_placeholder(
        s16, Inches(6.9), Inches(1.65), Inches(5.633), Inches(5.1),
        "2 Ảnh Thực Tế Kiểm Nghiệm Báo Cháy & Cảm Biến MQ-2",
        [
            "BẠN CẦN CHỤP 2 ẢNH ĐỂ CHÈN VÀO VỊ TRÍ NÀY:",
            "  1. Ảnh 1: Ngọn lửa bật lửa hoặc que diêm đang cháy trước webcam, trên màn hình xuất hiện khung nhận diện 'fire'.",
            "  2. Ảnh 2: Đưa đầu bật lửa xì gas vào đầu cảm biến MQ-2, thấy rõ đèn LED đỏ DO trên bo cảm biến sáng lên và còi buzzer hú!",
            "Mục đích: Minh chứng khả năng phối hợp đồng bộ giữa thị giác máy tính và cảm biến vật lý ngoại vi."
        ]
    )

    # =========================================================================
    # SLIDE 17: 4. KẾT QUẢ: KHÓA SOLENOID 3S & TEST MẤT ĐIỆN ĐỘT NGỘT
    # =========================================================================
    s17 = create_blank_slide(prs)
    add_header(s17, "Phần 4: Kết quả thực nghiệm", "Thực Nghiệm 4: Điều Khiển Khóa Solenoid An Toàn & Khôi Phục Mất Điện", page_num=17)

    # Cột trái: Kịch bản thử nghiệm
    add_card(s17, Inches(0.8), Inches(1.65), Inches(5.8), Inches(5.1))
    tb_r4 = s17.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.4), Inches(4.7))
    tf_r4 = tb_r4.text_frame
    tf_r4.word_wrap = True

    p0 = tf_r4.paragraphs[0]
    p0.text = "ĐIỀU KHIỂN KHÓA AN TOÀN 3 GIÂY & TỰ KHÔI PHỤC:"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_PRIMARY

    r4_desc = (
        "• Kịch bản 1 - Mở khóa Solenoid an toàn 3 giây:\n"
        "   + Gửi lệnh /unlock từ Telegram hoặc bấm nút mở cửa trên Web Dashboard.\n"
        "   + Rơ-le kích chân GPIO 23 lên mức HIGH.\n"
        "   + Cuộn hút nam châm điện kéo chốt khóa thụt vào trong đúng 3.0s cho phép đẩy cửa mở.\n"
        "   + Sau 3s, rơ-le tự ngắt về mức LOW, chốt khóa an toàn, cuộn dây hoàn toàn mát, loại trừ nguy cơ cháy chập.\n\n"
        "• Kịch bản 2 - Thử nghiệm Mất điện Đột ngột:\n"
        "   + Rút nguồn điện 5V của Raspberry Pi 4 khi hệ thống đang giám sát.\n"
        "   + Cắm lại nguồn điện: Dịch vụ Linux Systemd (smartcamera.service) tự động nạp lại toàn bộ camera, server và bot sau 42 giây mà không cần người thao tác."
    )
    p_r4 = tf_r4.add_paragraph()
    p_r4.text = r4_desc
    p_r4.font.name = FONT_BODY
    p_r4.font.size = Pt(10.5)
    p_r4.font.color.rgb = COLOR_TEXT_DARK

    # Cột phải: Placeholder 2 ảnh thực tế
    add_photo_placeholder(
        s17, Inches(6.9), Inches(1.65), Inches(5.633), Inches(5.1),
        "2 Ảnh Thực Tế Kiểm Nghiệm Khóa Solenoid & Telegram",
        [
            "BẠN CẦN CHỤP 2 ẢNH ĐỂ CHÈN VÀO VỊ TRÍ NÀY:",
            "  1. Ảnh 1: Cận cảnh chốt sắt khóa Solenoid đang thụt vào trong khi nhận lệnh mở cửa và đèn LED rơ-le đang sáng.",
            "  2. Ảnh 2: Ảnh màn hình điện thoại chụp tin nhắn Telegram xác nhận: 'Đã mở khóa cửa thành công (tự khóa lại sau 3s)'.",
            "Mục đích: Khẳng định tính an toàn điện cơ và độ tin cậy vận hành liên tục 24/7."
        ]
    )

    # =========================================================================
    # SLIDE 18: 5. ĐÁNH GIÁ: TÀI NGUYÊN CPU, RAM, FPS & ĐỘ TRỄ (DATA JSON)
    # =========================================================================
    s18 = create_blank_slide(prs)
    add_header(s18, "Phần 5: Đánh giá hiệu năng", "Đo Lường Tài Nguyên Phần Cứng & Độ Trễ Thực Tế Trên Pi 4", page_num=18)

    # 4 thẻ KPI lớn
    add_metric_card(s18, Inches(0.8), Inches(1.65), Inches(2.75), Inches(1.4), "55.0%", "CPU Sử Dụng", "Duy trì ổn định trên 4 nhân ARM", val_color=COLOR_PRIMARY)
    add_metric_card(s18, Inches(3.783), Inches(1.65), Inches(2.75), Inches(1.4), "846.5 MB", "RAM Sử Dụng", "~21% tổng dung lượng 4GB", val_color=COLOR_GREEN)
    add_metric_card(s18, Inches(6.766), Inches(1.65), Inches(2.75), Inches(1.4), "3.7 FPS", "Tốc Độ Khung Hình", "Đạt chuẩn an ninh thời gian thực", val_color=COLOR_SLATE)
    add_metric_card(s18, Inches(9.75), Inches(1.65), Inches(2.75), Inches(1.4), "1.67 s", "Độ Trễ Telegram", "Bắn tin khẩn cấp kèm ảnh", val_color=COLOR_AMBER_BORDER)

    # Bảng chi tiết độ trễ suy luận AI
    add_card(s18, Inches(0.8), Inches(3.25), Inches(11.733), Inches(3.5))
    tb_table = s18.shapes.add_textbox(Inches(1.1), Inches(3.45), Inches(11.1), Inches(3.1))
    tf_t = tb_table.text_frame
    tf_t.word_wrap = True

    p0 = tf_t.paragraphs[0]
    p0.text = "CHI TIẾT ĐỘ TRỄ SUY LUẬN TỪNG MÔ HÌNH (Đo lường kiểm thử 1525.6 giây ~ 25.4 phút liên tục):"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(12.5)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_NAVY

    table_lines = (
        "• Phát hiện khuôn mặt (MTCNN Face Detector):  226.28 ms\n"
        "• Trích xuất đặc trưng khuôn mặt (FaceNet 512D Embedding):  789.87 ms\n"
        "• Phát hiện ngọn lửa & khói sớm (YOLOv8 Fire Detector):  330.58 ms\n"
        "• Phát hiện người già té ngã (YOLOv8 Fall Detector):  316.37 ms\n"
        "• Kiểm tra hàng rào ảo bảo vệ ROI (YOLOv8 Intrusion Detector):  328.47 ms\n"
        "• Thời gian đóng ngắt rơ-le khóa cửa Solenoid:  Đúng 3.000 ms (tự ngắt an toàn)\n"
        "➔ Nhận xét: Nhờ cơ chế khóa luồng gpu_lock và with torch.no_grad(), CPU duy trì mát mẻ ở mức 55%, RAM không hề bị rò rỉ sau hơn 25 phút chạy liên tục 2 camera."
    )
    p_tl = tf_t.add_paragraph()
    p_tl.text = table_lines
    p_tl.font.name = FONT_BODY
    p_tl.font.size = Pt(11)
    p_tl.font.color.rgb = COLOR_TEXT_DARK

    # =========================================================================
    # SLIDE 19: 5. ĐÁNH GIÁ: ĐỘ CHÍNH XÁC & MA TRẬN NHẦM LẪN
    # =========================================================================
    s19 = create_blank_slide(prs)
    add_header(s19, "Phần 5: Đánh giá hiệu năng", "Đánh Giá Độ Chính Xác & Ma Trận Nhầm Lẫn (Confusion Matrix)", page_num=19)

    # Cột trái: Bảng chỉ số Precision, Recall, F1
    add_card(s19, Inches(0.8), Inches(1.65), Inches(6.0), Inches(5.1))
    tb_acc = s19.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.6), Inches(4.7))
    tf_acc = tb_acc.text_frame
    tf_acc.word_wrap = True

    p0 = tf_acc.paragraphs[0]
    p0.text = "BẢNG ĐỘ CHÍNH XÁC CÁC MÔ HÌNH PHÁT HIỆN NGUY CƠ:"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_PRIMARY

    acc_desc = (
        "1. Nhận diện khuôn mặt đeo khẩu trang (Masked FaceNet):\n"
        "   • Precision: 96.1%  |  Recall: 94.8%  |  F1-Score: 95.4%\n\n"
        "2. Phát hiện người cao tuổi té ngã (YOLOv8 Fall):\n"
        "   • Precision: 93.5%  |  Recall: 95.0%  |  F1-Score: 94.2%\n\n"
        "3. Phát hiện ngọn lửa & khói sớm (YOLOv8 Fire):\n"
        "   • Precision: 95.8%  |  Recall: 93.2%  |  F1-Score: 94.5%\n\n"
        "4. Phát hiện xâm nhập vùng ảo ROI (YOLOv8 Intrusion):\n"
        "   • Precision: 98.2%  |  Recall: 97.5%  |  F1-Score: 97.8%\n\n"
        "5. Cảm biến rò rỉ khí ga MQ-2 (Gas Leak Detector):\n"
        "   • Precision: 99.0%  |  Recall: 98.5%  |  F1-Score: 98.7%\n\n"
        "➔ Tỷ lệ chính xác trung bình toàn hệ thống đạt trên 95%!"
    )
    p_ad = tf_acc.add_paragraph()
    p_ad.text = acc_desc
    p_ad.font.name = FONT_BODY
    p_ad.font.size = Pt(10.5)
    p_ad.font.color.rgb = COLOR_TEXT_DARK

    # Cột phải: Chèn hình ảnh Confusion Matrix
    cm_img = "confusion_matrix.png"
    if os.path.exists(cm_img):
        try:
            s19.shapes.add_picture(cm_img, Inches(7.1), Inches(1.65), width=Inches(5.433))
        except Exception:
            pass
    else:
        add_card(s19, Inches(7.1), Inches(1.65), Inches(5.433), Inches(5.1))

    # =========================================================================
    # SLIDE 20: 6. ĐÓNG GÓP CỐT LÕI & HƯỚNG PHÁT TRIỂN
    # =========================================================================
    s20 = create_blank_slide(prs)
    add_header(s20, "Phần 6: Kết luận & Mở rộng", "Đóng Góp Cốt Lõi Của Đồ Án & Hướng Phát Triển Tương Lai", page_num=20)

    # Cột trái: 3 đóng góp cốt lõi
    add_card(s20, Inches(0.8), Inches(1.65), Inches(5.7), Inches(5.1))
    tb_c = s20.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.3), Inches(4.7))
    tf_c = tb_c.text_frame
    tf_c.word_wrap = True

    p0 = tf_c.paragraphs[0]
    p0.text = "3 ĐÓNG GÓP KỸ THUẬT NỔI BẬT CỦA ĐỀ TÀI:"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_PRIMARY

    c_lines = (
        "1. Giải pháp Nhận diện Khẩu trang 1 Ảnh Mẫu Đột Phá:\n"
        "   Kỹ thuật Zero-out 45% nửa dưới khuôn mặt kết hợp FaceNet Inception-ResNet và ngưỡng khoảng cách L2 0.80 cho phép nhận diện chính xác người đeo khẩu trang mà không cần dữ liệu huấn luyện mới.\n\n"
        "2. Tối Ưu Hóa Biên & Cơ Chế Khóa Luồng CPU (gpu_lock):\n"
        "   Xây dựng thành công kiến trúc xử lý đa luồng với khóa đồng bộ gpu_lock, giúp Raspberry Pi 4 (không GPU) chạy mượt mà 2 camera và 4 mô hình AI với CPU ổn định 55%, RAM chỉ 846.5MB.\n\n"
        "3. Tích Hợp Ngoại Vi Toàn Diện & Tự Khởi Động Mất Điện:\n"
        "   Tích hợp cảm biến khí ga MQ-2, điều khiển xung khóa Solenoid 3s an toàn chống cháy, còi hú phân cấp và tự phục hồi hoàn toàn sau sự cố mất điện trong < 45s qua Linux Systemd."
    )
    p_c = tf_c.add_paragraph()
    p_c.text = c_lines
    p_c.font.name = FONT_BODY
    p_c.font.size = Pt(10.5)
    p_c.font.color.rgb = COLOR_TEXT_DARK

    # Cột phải: Ứng dụng thực tế & Hướng mở rộng
    add_card(s20, Inches(6.8), Inches(1.65), Inches(5.733), Inches(5.1))
    tb_f = s20.shapes.add_textbox(Inches(7.0), Inches(1.85), Inches(5.333), Inches(4.7))
    tf_f = tb_f.text_frame
    tf_f.word_wrap = True

    p1 = tf_f.paragraphs[0]
    p1.text = "ỨNG DỤNG THỰC TẾ & HƯỚNG PHÁT TRIỂN TIẾP THEO:"
    p1.font.name = FONT_HEADING
    p1.font.size = Pt(13)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_GREEN

    f_lines = (
        "• Khả năng ứng dụng thực tiễn:\n"
        "   + Hộ gia đình thông minh: Bảo vệ người cao tuổi (cảnh báo té ngã), phòng chống rò rỉ khí gas và cháy nổ nhà bếp, mở cửa đón khách từ xa qua Telegram.\n"
        "   + Phân xưởng & Cửa hàng nhỏ: Kiểm soát ra vào của nhân viên đeo khẩu trang, giám sát chống trộm ban đêm qua hàng rào ảo ROI.\n"
        "   + Chi phí phần cứng cực thấp: < 3 triệu VNĐ, tiết kiệm hơn 80% so với hệ thống máy chủ GPU và camera chuyên dụng.\n\n"
        "• Hướng phát triển tương lai (Future Works):\n"
        "   + Chuyển đổi mô hình sang định dạng ONNX / TensorRT với lượng tử hóa INT8 nhằm nâng FPS lên > 10 FPS.\n"
        "   + Tích hợp micro thu âm thanh bất thường (tiếng kêu cứu, tiếng kính vỡ) để tăng cường giám sát toàn diện hơn."
    )
    p_f = tf_f.add_paragraph()
    p_f.text = f_lines
    p_f.font.name = FONT_BODY
    p_f.font.size = Pt(10.5)
    p_f.font.color.rgb = COLOR_TEXT_DARK

    # =========================================================================
    # SLIDE 21: TRANG KẾT THÚC / LỜI CẢM ƠN (THANK YOU & Q&A)
    # =========================================================================
    s21 = create_blank_slide(prs)
    # Banner nền xanh Navy sang trọng
    banner_end = s21.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(5.0))
    banner_end.fill.solid()
    banner_end.fill.fore_color.rgb = COLOR_NAVY
    banner_end.line.fill.background()

    sub_end = s21.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(4.95), Inches(13.333), Inches(0.1))
    sub_end.fill.solid()
    sub_end.fill.fore_color.rgb = COLOR_PRIMARY
    sub_end.line.fill.background()

    tb_end = s21.shapes.add_textbox(Inches(1.0), Inches(1.5), Inches(11.333), Inches(3.0))
    tf_end = tb_end.text_frame
    tf_end.word_wrap = True

    p_thanks = tf_end.paragraphs[0]
    p_thanks.text = "XIN CHÂN THÀNH CẢM ƠN\nQUÝ THẦY CÔ VÀ HỘI ĐỒNG BẢO VỆ ĐỒ ÁN!"
    p_thanks.font.name = FONT_HEADING
    p_thanks.font.size = Pt(32)
    p_thanks.font.bold = True
    p_thanks.font.color.rgb = COLOR_WHITE
    p_thanks.alignment = PP_ALIGN.CENTER

    p_qa = tf_end.add_paragraph()
    p_qa.text = "\nQ&A: THẢO LUẬN & ĐÓNG GÓP Ý KIẾN CHO ĐỒ ÁN"
    p_qa.font.name = FONT_HEADING
    p_qa.font.size = Pt(18)
    p_qa.font.bold = True
    p_qa.font.color.rgb = RGBColor(0x38, 0xBD, 0xF8) # Sky Blue
    p_qa.alignment = PP_ALIGN.CENTER

    card_author = add_card(s21, Inches(2.5), Inches(5.4), Inches(8.333), Inches(1.5))
    tb_au = s21.shapes.add_textbox(Inches(2.7), Inches(5.55), Inches(7.933), Inches(1.2))
    tf_au = tb_au.text_frame
    tf_au.word_wrap = True

    p_au = tf_au.paragraphs[0]
    p_au.text = "Sinh viên thực hiện:  Nguyễn Văn Toàn"
    p_au.font.name = FONT_HEADING
    p_au.font.size = Pt(14)
    p_au.font.bold = True
    p_au.font.color.rgb = COLOR_NAVY
    p_au.alignment = PP_ALIGN.CENTER

    p_gva = tf_au.add_paragraph()
    p_gva.text = "Giảng viên hướng dẫn:  ...  |  Trường Đại học FPT"
    p_gva.font.name = FONT_BODY
    p_gva.font.size = Pt(12)
    p_gva.font.color.rgb = COLOR_TEXT_MUTED
    p_gva.alignment = PP_ALIGN.CENTER

    # Lưu bài thuyết trình
    prs.save(OUTPUT_PATH)
    print("=" * 60)
    print(f"✅ ĐÃ TẠO THÀNH CÔNG BÀI THUYẾT TRÌNH MỚI HOÀN TOÀN: {OUTPUT_PATH}")
    print(f"Tổng số slides: {len(prs.slides)} slides chuẩn 16:9 Widescreen.")
    print("=" * 60)

if __name__ == "__main__":
    main()
