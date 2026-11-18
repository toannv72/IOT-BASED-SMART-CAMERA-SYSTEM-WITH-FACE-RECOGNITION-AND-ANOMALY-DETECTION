# -*- coding: utf-8 -*-
"""
HỆ THỐNG TẠO SLIDE THUYẾT TRÌNH CAO CẤP TOÀN DIỆN (FULL 12 SLIDES)
Dự án: Smart Camera Edge AI - Đồ án Tốt nghiệp MSE26HCM
Tác giả: Nguyễn Văn Toàn | GVHD: TS. Đoàn Xuân Huy Minh (Đại học FPT)
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN

ASSETS_DIR = "slides_assets"
os.makedirs(ASSETS_DIR, exist_ok=True)

C_DARK_BG    = RGBColor(10, 25, 47)      # Xanh Navy Đêm Deep Cyber
C_CARD_BG    = RGBColor(23, 42, 69)      # Thẻ nổi màu Navy nhạt
C_CYAN       = RGBColor(100, 255, 218)   # Xanh Neon Cyan
C_WHITE      = RGBColor(255, 255, 255)
C_TEXT_LIGHT = RGBColor(204, 214, 246)
C_MUTED      = RGBColor(138, 155, 182)
C_ACCENT_RED = RGBColor(255, 110, 64)    # Cam/Đỏ cảnh báo
C_GREEN      = RGBColor(52, 211, 153)    # Xanh lá thành công

FONT_MAIN = "Arial"

def generate_all_charts():
    print("[1/3] Đang sinh toàn bộ đồ thị và sơ đồ minh họa chi tiết...")
    plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Arial', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    # 1. Sơ đồ kiến trúc
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    fig.patch.set_facecolor('#0A192F')
    ax.set_facecolor('#0A192F')
    boxes = [
        {"title": "2x USB Webcams\n(640x480 @ 15fps)", "pos": (0.05, 0.55), "size": (0.25, 0.35), "color": "#172A45", "ec": "#64FFDA"},
        {"title": "Cảm biến & Ngoại vi\n• MQ-2 (Gas Leak)\n• Solenoid Lock 12V\n• Active Buzzer", "pos": (0.05, 0.1), "size": (0.25, 0.35), "color": "#172A45", "ec": "#FF6E40"},
        {"title": "Raspberry Pi 4 (4GB)\n\n• MTCNN + Masked FaceNet\n• YOLOv8 (Fall, Fire, ROI)\n• Concurrency Lock", "pos": (0.38, 0.15), "size": (0.3, 0.7), "color": "#1E3A8A", "ec": "#64FFDA"},
        {"title": "Web Dashboard & Bot\n\n• FastAPI (SSE <50ms)\n• Telegram Bot 2-way\n• Systemd Recovery", "pos": (0.75, 0.15), "size": (0.22, 0.7), "color": "#172A45", "ec": "#38BDF8"},
    ]
    for b in boxes:
        rect = patches.FancyBboxPatch(b["pos"], b["size"][0], b["size"][1], boxstyle="round,pad=0.03",
                                      facecolor=b["color"], edgecolor=b["ec"], linewidth=2)
        ax.add_patch(rect)
        ax.text(b["pos"][0] + b["size"][0]/2, b["pos"][1] + b["size"][1]/2, b["title"],
                color="white", weight="bold", fontsize=9.5, ha="center", va="center")
    arrow_props = dict(facecolor='#64FFDA', edgecolor='#64FFDA', width=2, headwidth=8, shrink=0.05)
    ax.annotate('', xy=(0.38, 0.7), xytext=(0.30, 0.7), arrowprops=arrow_props)
    ax.annotate('', xy=(0.38, 0.3), xytext=(0.30, 0.3), arrowprops=arrow_props)
    ax.annotate('', xy=(0.75, 0.5), xytext=(0.68, 0.5), arrowprops=arrow_props)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    plt.title("SƠ ĐỒ KIẾN TRÚC HỆ THỐNG SMART CAMERA EDGE AI", color="#64FFDA", fontsize=12, pad=10, weight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(ASSETS_DIR, "arch.png"), dpi=300)
    plt.close()

    # 2. Đồ thị độ trễ suy luận AI
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
    fig.patch.set_facecolor('#0A192F')
    ax.set_facecolor('#172A45')
    models = ['MQ-2 Gas', 'Solenoid', 'MTCNN', 'ROI YOLO', 'Fire YOLO', 'Fall YOLO', 'FaceNet']
    latencies = [1.2, 25.0, 37.1, 198.5, 347.7, 363.6, 789.9]
    colors = ['#34D399', '#38BDF8', '#0284C7', '#0D9488', '#D97706', '#DC2626', '#7C3AED']
    bars = ax.barh(models, latencies, color=colors, height=0.6)
    for b in bars:
        w = b.get_width()
        ax.text(w + 15, b.get_y() + b.get_height()/2, f"{w:.1f}ms", va='center', color='white', weight='bold', fontsize=9)
    ax.set_xlim(0, 920)
    ax.tick_params(colors='white')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#8A9BB6'); ax.spines['bottom'].set_color('#8A9BB6')
    plt.title("ĐỘ TRỄ SUY LUẬN TỪNG MÔ HÌNH TRÊN PI 4 (ms)", color="#64FFDA", fontsize=11, weight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(ASSETS_DIR, "latency.png"), dpi=300)
    plt.close()

    # 3. Đồ thị độ chính xác (Precision & Recall)
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
    fig.patch.set_facecolor('#0A192F')
    ax.set_facecolor('#172A45')
    feats = ['Fall', 'Fire', 'Intrusion', 'Face (Mask)', 'MQ-2 Gas']
    prec = [92.1, 94.3, 95.2, 98.2, 98.5]
    recall = [90.4, 89.1, 93.0, 96.8, 99.8]
    x = np.arange(len(feats))
    w = 0.35
    ax.bar(x - w/2, prec, w, label='Precision (%)', color='#38BDF8')
    ax.bar(x + w/2, recall, w, label='Recall (%)', color='#34D399')
    ax.set_xticks(x); ax.set_xticklabels(feats, color='white', weight='semibold')
    ax.set_ylim(70, 105)
    ax.legend(facecolor='#172A45', edgecolor='none', labelcolor='white')
    ax.tick_params(colors='white')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#8A9BB6'); ax.spines['bottom'].set_color('#8A9BB6')
    plt.title("ĐÁNH GIÁ CHỈ SỐ PRECISION & RECALL (%)", color="#64FFDA", fontsize=11, weight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(ASSETS_DIR, "accuracy.png"), dpi=300)
    plt.close()
    print("[1/3] Hoàn tất sinh đồ họa!")

def build_presentation():
    print("[2/3] Đang xây dựng bộ 12 Slides cao cấp...")
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    def add_slide():
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = C_DARK_BG
        bg.line.fill.background()
        return slide

    def header(slide, tag, title, pnum):
        tb_tag = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(10), Inches(0.3))
        tb_tag.text_frame.paragraphs[0].text = tag.upper()
        tb_tag.text_frame.paragraphs[0].font.size = Pt(10)
        tb_tag.text_frame.paragraphs[0].font.bold = True
        tb_tag.text_frame.paragraphs[0].font.color.rgb = C_CYAN

        tb_t = slide.shapes.add_textbox(Inches(0.8), Inches(0.65), Inches(11.733), Inches(0.6))
        tb_t.text_frame.paragraphs[0].text = title
        tb_t.text_frame.paragraphs[0].font.size = Pt(22)
        tb_t.text_frame.paragraphs[0].font.bold = True
        tb_t.text_frame.paragraphs[0].font.color.rgb = C_WHITE

        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.3), Inches(11.733), Inches(0.02))
        line.fill.solid(); line.fill.fore_color.rgb = C_CYAN; line.line.fill.background()

        tb_p = slide.shapes.add_textbox(Inches(11.5), Inches(7.0), Inches(1), Inches(0.3))
        tb_p.text_frame.paragraphs[0].text = f"{pnum}"
        tb_p.text_frame.paragraphs[0].font.size = Pt(10)
        tb_p.text_frame.paragraphs[0].font.bold = True
        tb_p.text_frame.paragraphs[0].font.color.rgb = C_CYAN
        tb_p.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

    def card(slide, l, t, w, h, ec=C_CYAN):
        c = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
        c.fill.solid(); c.fill.fore_color.rgb = C_CARD_BG
        c.line.color.rgb = ec; c.line.width = Pt(1.5)
        return c

    # --- SLIDE 1: TRANG BÌA ---
    s1 = add_slide()
    box = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.5), Inches(0.15), Inches(4.5))
    box.fill.solid(); box.fill.fore_color.rgb = C_CYAN; box.line.fill.background()

    tb = s1.shapes.add_textbox(Inches(1.3), Inches(1.6), Inches(11), Inches(3.0))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.paragraphs[0].text = "BÁO CÁO ĐỒ ÁN TỐT NGHIỆP THẠC SĨ (MSE)"
    tf.paragraphs[0].font.size = Pt(13); tf.paragraphs[0].font.bold = True; tf.paragraphs[0].font.color.rgb = C_CYAN

    p1 = tf.add_paragraph()
    p1.text = "HỆ THỐNG SMART CAMERA GIÁM SÁT ĐA NGUY CƠ BIÊN (EDGE AI) TRÊN RASPBERRY PI 4"
    p1.font.size = Pt(26); p1.font.bold = True; p1.font.color.rgb = C_WHITE

    p2 = tf.add_paragraph()
    p2.text = "Nhận diện khuôn mặt đeo khẩu trang • Cảnh báo té ngã, Cháy nổ & Khí ga • Khóa cửa Solenoid 3s"
    p2.font.size = Pt(13); p2.font.color.rgb = C_TEXT_LIGHT

    card(s1, Inches(1.3), Inches(5.0), Inches(10.733), Inches(1.8))
    tb_i = s1.shapes.add_textbox(Inches(1.6), Inches(5.2), Inches(10.1), Inches(1.4))
    tfi = tb_i.text_frame
    tfi.word_wrap = True
    tfi.paragraphs[0].text = "Sinh viên thực hiện:   Nguyễn Văn Toàn   (Lớp MSE26HCM)"
    tfi.paragraphs[0].font.size = Pt(14); tfi.paragraphs[0].font.bold = True; tfi.paragraphs[0].font.color.rgb = C_WHITE
    p_gv = tfi.add_paragraph()
    p_gv.text = "Giảng viên hướng dẫn:   TS. Đoàn Xuân Huy Minh   |   Trường Đại học FPT"
    p_gv.font.size = Pt(13); p_gv.font.bold = True; p_gv.font.color.rgb = C_CYAN

    # --- SLIDE 2: MỤC LỤC ---
    s2 = add_slide()
    header(s2, "Tổng quan", "Mục Lục Bài Thuyết Trình", 2)
    agenda = [
        ("01", "Đặt Vấn Đề & Mục Tiêu Nghiên Cứu", "Nhu cầu giám sát biên bảo mật, hạn chế của hệ thống cloud đắt đỏ."),
        ("02", "Thách Thức Kỹ Thuật Tại Biên", "Giới hạn CPU Pi 4, che khuất đặc trưng do khẩu trang, an toàn khóa Solenoid."),
        ("03", "Kiến Trúc & Phương Pháp AI", "Pipeline đa mô hình, Zero-out 45% khẩu trang, sơ đồ GPIO ngoại vi & FastAPI."),
        ("04", "Kết Quả Thực Nghiệm & Trực Quan", "4 kịch bản thực tế: Khuôn mặt khẩu trang, Té ngã, Cháy/Gas, Khóa 3 giây."),
        ("05", "Đánh Giá Hiệu Năng & Kết Luận", "Pi 4: CPU 55%, RAM 846MB, FPS ổn định, Telegram 1.67s, độ chính xác >95%.")
    ]
    for i, (num, title, desc) in enumerate(agenda):
        y = Inches(1.6 + i * 1.05)
        card(s2, Inches(0.8), y, Inches(11.733), Inches(0.9))
        tb = s2.shapes.add_textbox(Inches(1.1), y + Inches(0.1), Inches(11.2), Inches(0.7))
        tb.text_frame.word_wrap = True
        tb.text_frame.paragraphs[0].text = f"{num}.  {title}"
        tb.text_frame.paragraphs[0].font.size = Pt(13.5); tb.text_frame.paragraphs[0].font.bold = True; tb.text_frame.paragraphs[0].font.color.rgb = C_CYAN
        p = tb.text_frame.add_paragraph()
        p.text = desc; p.font.size = Pt(11); p.font.color.rgb = C_TEXT_LIGHT

    # --- SLIDE 3: ĐẶT VẤN ĐỀ ---
    s3 = add_slide()
    header(s3, "Phần 1: Dẫn nhập", "Đặt Vấn Đề & Nhu Cầu Thực Tiễn", 3)
    probs = [
        ("Hạn Chế Của Camera Thương Mại", "Google Nest & Ring đắt đỏ, phụ thuộc Cloud, rủi ro lộ dữ liệu riêng tư và chi phí duy trì hàng tháng cao."),
        ("Nhu Cầu An Ninh Gia Đình & Xưởng", "Cần hệ thống thông minh tại chỗ (Edge AI) tự động nhận diện người nhà, phát hiện kẻ lạ, té ngã và hỏa hoạn."),
        ("Bài Toán Đặt Ra Cho Đồ Án", "Thiết kế giải pháp nhúng chi phí thấp (< 3 triệu VNĐ) trên Raspberry Pi 4, chạy thời gian thực 24/7 không cần Internet.")
    ]
    for i, (title, desc) in enumerate(probs):
        x = Inches(0.8 + i * 4.0)
        card(s3, x, Inches(1.8), Inches(3.733), Inches(4.8))
        tb = s3.shapes.add_textbox(x + Inches(0.2), Inches(2.0), Inches(3.333), Inches(4.4))
        tb.text_frame.word_wrap = True
        tb.text_frame.paragraphs[0].text = title
        tb.text_frame.paragraphs[0].font.size = Pt(14); tb.text_frame.paragraphs[0].font.bold = True; tb.text_frame.paragraphs[0].font.color.rgb = C_CYAN
        p = tb.text_frame.add_paragraph()
        p.text = f"\n• {desc}"; p.font.size = Pt(11.5); p.font.color.rgb = C_TEXT_LIGHT

    # --- SLIDE 4: MỤC TIÊU NGHIÊN CỨU & SMART OBJECTIVES ---
    s4 = add_slide()
    header(s4, "Phần 1: Dẫn nhập", "Mục Tiêu Nghiên Cứu (SMART Objectives)", 4)
    objs = [
        ("Nhận Diện Khuôn Mặt Biên", "Đạt độ chính xác >= 90% với khuôn mặt người nhà, hỗ trợ đặc biệt khi đeo khẩu trang y tế."),
        ("Phát Hiện Đa Nguy Cơ Tự Động", "Tích hợp phát hiện té ngã (Fall), hỏa hoạn sớm (Fire) và xâm nhập hàng rào ảo ROI."),
        ("Phản Hồi Thời Gian Thực", "Độ trễ từ khi phát hiện nguy cơ đến khi đẩy tin báo khẩn cấp Telegram <= 5 giây.")
    ]
    for i, (title, desc) in enumerate(objs):
        y = Inches(1.8 + i * 1.6)
        card(s4, Inches(0.8), y, Inches(11.733), Inches(1.4))
        tb = s4.shapes.add_textbox(Inches(1.1), y + Inches(0.15), Inches(11.1), Inches(1.1))
        tb.text_frame.word_wrap = True
        tb.text_frame.paragraphs[0].text = f"🎯  {title}"
        tb.text_frame.paragraphs[0].font.size = Pt(15); tb.text_frame.paragraphs[0].font.bold = True; tb.text_frame.paragraphs[0].font.color.rgb = C_CYAN
        p = tb.text_frame.add_paragraph()
        p.text = desc; p.font.size = Pt(12); p.font.color.rgb = C_TEXT_LIGHT

    # --- SLIDE 5: 3 THÁCH THỨC KỸ THUẬT ---
    s5 = add_slide()
    header(s5, "Phần 2: Thách thức", "Ba Thách Thức Kỹ Thuật Lớn Tại Biên", 5)
    chal = [
        ("Thách thức 1", "Giới Hạn CPU Biên Raspberry Pi 4", "Pi 4 chỉ có CPU 4 nhân ARM, không GPU rời. Chạy song song nhiều mô hình AI dễ gây nghẽn CPU 100% và tràn RAM (OOM Crash)."),
        ("Thách thức 2", "Mất Mát Đặc Trưng Do Khẩu Trang", "Khẩu trang che khuất từ sống mũi xuống cằm khiến các mô hình nhận diện thông thường bị lệch đặc trưng và từ chối."),
        ("Thách thức 3", "An Toàn Phần Cứng & Mất Điện", "Khóa Solenoid 12V nếu cấp điện liên tục sẽ cháy cuộn hút. Mất điện đột ngột làm gián đoạn hệ thống giám sát 24/7.")
    ]
    for i, (tag, title, desc) in enumerate(chal):
        x = Inches(0.8 + i * 4.0)
        card(s5, x, Inches(1.8), Inches(3.733), Inches(4.8), ec=C_ACCENT_RED)
        tb = s5.shapes.add_textbox(x + Inches(0.2), Inches(2.0), Inches(3.333), Inches(4.4))
        tb.text_frame.word_wrap = True
        tb.text_frame.paragraphs[0].text = tag.upper()
        tb.text_frame.paragraphs[0].font.size = Pt(11); tb.text_frame.paragraphs[0].font.bold = True; tb.text_frame.paragraphs[0].font.color.rgb = C_ACCENT_RED
        p1 = tb.text_frame.add_paragraph()
        p1.text = title; p1.font.size = Pt(13); p1.font.bold = True; p1.font.color.rgb = C_WHITE
        p2 = tb.text_frame.add_paragraph()
        p2.text = f"\n• {desc}"; p2.font.size = Pt(11); p2.font.color.rgb = C_TEXT_LIGHT

    # --- SLIDE 6: KIẾN TRÚC HỆ THỐNG (SƠ ĐỒ TỰ SINH) ---
    s6 = add_slide()
    header(s6, "Phần 3: Kiến trúc", "Kiến Trúc Tổng Quan Hệ Thống Smart Camera Edge AI", 6)
    img_arch = os.path.join(ASSETS_DIR, "arch.png")
    if os.path.exists(img_arch):
        s6.shapes.add_picture(img_arch, Inches(1.5), Inches(1.6), width=Inches(10.333))

    # --- SLIDE 7: THUẬT TOÁN ZERO-OUT 45% KHẨU TRANG ---
    s7 = add_slide()
    header(s7, "Phần 3: Kiến trúc", "Thuật Toán Nhận Diện Khẩu Trang 1 Ảnh Mẫu Đột Phá", 7)
    card(s7, Inches(0.8), Inches(1.65), Inches(5.6), Inches(5.1))
    tb = s7.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.2), Inches(4.7))
    tb.text_frame.word_wrap = True
    tb.text_frame.paragraphs[0].text = "CƠ CHẾ BÔI ĐEN ĐẶC TRƯNG (ZERO-OUT MASKING):"
    tb.text_frame.paragraphs[0].font.size = Pt(12.5); tb.text_frame.paragraphs[0].font.bold = True; tb.text_frame.paragraphs[0].font.color.rgb = C_CYAN
    p = tb.text_frame.add_paragraph()
    p.text = (
        "• Vấn đề: Khi đeo khẩu trang, hơn 50% đặc trưng khuôn mặt bị che khuất.\n\n"
        "• Công thức đồng bộ cốt lõi:\n"
        "   + Ảnh DB (mặt mộc): face[:, 88:, :] = 0.0\n"
        "   + Khung hình live: faces[:, :, 88:, :] = 0.0\n\n"
        "• Vector 512D từ FaceNet Inception-ResNet.\n\n"
        "• Ngưỡng L2 Distance tối ưu: threshold = 0.80\n"
        "   + d < 0.80  ➔ Đúng thành viên.\n"
        "   + d >= 0.80 ➔ Người lạ xâm nhập."
    )
    p.font.size = Pt(10.5); p.font.color.rgb = C_TEXT_LIGHT

    img_zero = os.path.join(ASSETS_DIR, "diag_zero_out.png")
    if os.path.exists(img_zero):
        s7.shapes.add_picture(img_zero, Inches(6.7), Inches(1.65), width=Inches(5.833))

    # --- SLIDE 8: CƠ CHẾ KHÓA ĐỒNG BỘ GPU_LOCK ---
    s8 = add_slide()
    header(s8, "Phần 3: Kiến trúc", "Giải Pháp Tối Ưu Biên & Khóa Đồng Bộ GPU_LOCK", 8)
    card(s8, Inches(0.8), Inches(1.65), Inches(5.6), Inches(5.1))
    tb = s8.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.2), Inches(4.7))
    tb.text_frame.word_wrap = True
    tb.text_frame.paragraphs[0].text = "QUẢN LÝ TÀI NGUYÊN ĐA LUỒNG TRÊN PI 4:"
    tb.text_frame.paragraphs[0].font.size = Pt(12.5); tb.text_frame.paragraphs[0].font.bold = True; tb.text_frame.paragraphs[0].font.color.rgb = C_CYAN
    p = tb.text_frame.add_paragraph()
    p.text = (
        "• Thách thức: Pi 4 chạy 2 camera song song gọi MTCNN + FaceNet + YOLOv8 dễ gây nghẽn CPU và tràn RAM.\n\n"
        "• Giải pháp Khóa Toàn Cục:\n"
        "   gpu_lock = threading.Lock()\n"
        "   with gpu_lock:\n"
        "       with torch.no_grad():\n"
        "           # Suy luận tuần tự an toàn\n\n"
        "• Kết quả:\n"
        "   + CPU duy trì ổn định ở mức 55.0%\n"
        "   + RAM chỉ dùng 846.5 MB (~21%)\n"
        "   + Không rò rỉ bộ nhớ sau 24h chạy liên tục."
    )
    p.font.size = Pt(11); p.font.color.rgb = C_TEXT_LIGHT

    wiring_img = "static/raspberry_pi_wiring_diagram.png"
    if os.path.exists(wiring_img):
        s8.shapes.add_picture(wiring_img, Inches(6.7), Inches(1.65), width=Inches(5.833))

    # --- SLIDE 9: KẾT QUẢ THỰC NGHIỆM 1 & 2 ---
    s9 = add_slide()
    header(s9, "Phần 4: Thực nghiệm", "Thực Nghiệm: Nhận Diện Mặt & Phát Hiện Té Ngã", 9)
    res1 = [
        ("Nhận Diện Khuôn Mặt Đeo Khẩu Trang", "• Đăng ký 1 ảnh mộc duy nhất.\n• Kiểm tra thực tế: Cả khi không đeo và đeo khẩu trang y tế đều được nhận diện chính xác với L2 < 0.80.\n• Từ chối người lạ tin cậy."),
        ("Phát Hiện Té Ngã (Fall Detection)", "• Nhận diện tư thế ngã của người già/trẻ nhỏ.\n• Bộ đệm debounce 3 khung hình loại trừ báo động giả (ngồi xổm, cúi nhặt đồ).\n• Gửi cảnh báo khẩn cấp Telegram <= 1.67s.")
    ]
    for i, (title, desc) in enumerate(res1):
        x = Inches(0.8 + i * 6.0)
        card(s9, x, Inches(1.8), Inches(5.733), Inches(4.8))
        tb = s9.shapes.add_textbox(x + Inches(0.25), Inches(2.0), Inches(5.233), Inches(4.4))
        tb.text_frame.word_wrap = True
        tb.text_frame.paragraphs[0].text = title
        tb.text_frame.paragraphs[0].font.size = Pt(14); tb.text_frame.paragraphs[0].font.bold = True; tb.text_frame.paragraphs[0].font.color.rgb = C_CYAN
        p = tb.text_frame.add_paragraph()
        p.text = f"\n{desc}"; p.font.size = Pt(11.5); p.font.color.rgb = C_TEXT_LIGHT

    # --- SLIDE 10: KẾT QUẢ THỰC NGHIỆM 3 & 4 ---
    s10 = add_slide()
    header(s10, "Phần 4: Thực nghiệm", "Thực Nghiệm: Báo Cháy, Khí Ga MQ-2 & Khóa Solenoid", 10)
    res2 = [
        ("Báo Cháy & Khí Ga MQ-2", "• YOLOv8 phát hiện ngọn lửa/khói sớm, còi hú nhấp nháy 0.1s.\n• Cảm biến MQ-2 (GPIO 18) phát hiện rò rỉ khí ga, kích hoạt cảnh báo an toàn tức thì."),
        ("Khóa Solenoid & Mất Điện", "• Lệnh mở cửa xuất xung HIGH trong đúng 3.0s rồi ngắt về LOW, tuyệt đối không cháy cuộn hút.\n• Linux Systemd tự phục hồi sau mất điện trong < 45s.")
    ]
    for i, (title, desc) in enumerate(res2):
        x = Inches(0.8 + i * 6.0)
        card(s10, x, Inches(1.8), Inches(5.733), Inches(4.8))
        tb = s10.shapes.add_textbox(x + Inches(0.25), Inches(2.0), Inches(5.233), Inches(4.4))
        tb.text_frame.word_wrap = True
        tb.text_frame.paragraphs[0].text = title
        tb.text_frame.paragraphs[0].font.size = Pt(14); tb.text_frame.paragraphs[0].font.bold = True; tb.text_frame.paragraphs[0].font.color.rgb = C_CYAN
        p = tb.text_frame.add_paragraph()
        p.text = f"\n{desc}"; p.font.size = Pt(11.5); p.font.color.rgb = C_TEXT_LIGHT

    # --- SLIDE 11: ĐÁNH GIÁ HIỆN NĂNG & ĐỒ THỊ ---
    s11 = add_slide()
    header(s11, "Phần 5: Đánh giá hiệu năng", "Đo Lường Độ Trễ & Độ Chính Xác Toàn Hệ Thống", 11)
    img_lat = os.path.join(ASSETS_DIR, "latency.png")
    img_acc = os.path.join(ASSETS_DIR, "accuracy.png")
    if os.path.exists(img_lat):
        s11.shapes.add_picture(img_lat, Inches(0.8), Inches(1.65), width=Inches(5.7))
    if os.path.exists(img_acc):
        s11.shapes.add_picture(img_acc, Inches(6.8), Inches(1.65), width=Inches(5.7))

    # --- SLIDE 12: KẾT LUẬN & Q&A ---
    s12 = add_slide()
    tb_end = s12.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.333), Inches(3.0))
    tb_end.text_frame.word_wrap = True
    tb_end.text_frame.paragraphs[0].text = "XIN CHÂN THÀNH CẢM ƠN\nQUÝ THẦY CÔ VÀ HỘI ĐỒNG BẢO VỆ ĐỒ ÁN!"
    tb_end.text_frame.paragraphs[0].font.size = Pt(30); tb_end.text_frame.paragraphs[0].font.bold = True
    tb_end.text_frame.paragraphs[0].font.color.rgb = C_WHITE; tb_end.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    p = tb_end.text_frame.add_paragraph()
    p.text = "\nQ&A: THẢO LUẬN & ĐÓNG GÓP Ý KIẾN CHO ĐỀ TÀI"; p.font.size = Pt(17); p.font.bold = True
    p.font.color.rgb = C_CYAN; p.alignment = PP_ALIGN.CENTER

    card(s12, Inches(2.5), Inches(5.0), Inches(8.333), Inches(1.8))
    tb_f = s12.shapes.add_textbox(Inches(2.7), Inches(5.2), Inches(7.933), Inches(1.4))
    tb_f.text_frame.word_wrap = True
    tb_f.text_frame.paragraphs[0].text = "Đóng góp cốt lõi:"
    tb_f.text_frame.paragraphs[0].font.size = Pt(13); tb_f.text_frame.paragraphs[0].font.bold = True; tb_f.text_frame.paragraphs[0].font.color.rgb = C_CYAN
    pf = tb_f.text_frame.add_paragraph()
    pf.text = "• Thuật toán Zero-out 45% nhận diện khẩu trang 1 ảnh mẫu.\n• Tối ưu biên Raspberry Pi 4 với khóa đồng bộ gpu_lock.\n• Tích hợp ngoại vi toàn diện & tự phục hồi mất điện."
    pf.font.size = Pt(11); pf.font.color.rgb = C_TEXT_LIGHT

    output_filename = "Slide_Bao_Cao_Do_An_Master_V2.pptx"
    prs.save(output_filename)
    print(f"[3/3] Đã tạo thành công bộ Slide hoành tráng (12 Slides) vào tệp: {output_filename}")

def main():
    generate_all_charts()
    build_presentation()

if __name__ == "__main__":
    main()
