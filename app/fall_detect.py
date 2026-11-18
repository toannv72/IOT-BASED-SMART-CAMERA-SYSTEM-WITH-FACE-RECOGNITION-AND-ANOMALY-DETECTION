"""
Bộ phát hiện ngã thông minh theo tư thế:
- STANDING / SITTING / BENDING / LYING (+ FALL khi chuyển đứng/ngồi -> nằm)
- Ngồi ghế ≠ ngã; cúi người ≠ ngã
- Kết hợp YOLOv8-fall + YOLOv8-pose + sụt chiều cao
"""
from __future__ import annotations

import collections
import math
import time
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np
import torch

FallBox = Tuple[int, int, int, int, str, float, str]  # x1,y1,x2,y2,label,conf,source
POSTURE_STANDING = "STANDING"
POSTURE_SITTING = "SITTING"
POSTURE_BENDING = "BENDING"
POSTURE_LYING = "LYING"
POSTURE_UNKNOWN = "UNKNOWN"

# Nhãn vẽ trên khung (không phải fall)
SAFE_POSTURE_LABELS = {
    POSTURE_STANDING: "standing",
    POSTURE_SITTING: "sitting",
    POSTURE_BENDING: "bending",
    POSTURE_LYING: "lying",
    POSTURE_UNKNOWN: "normal",
}


def is_fall_class_name(name: Any) -> bool:
    text = str(name or "").strip().lower()
    return text in ("fall", "falling", "nga", "ngã") or text.startswith("fall")


def is_down_posture(name: Any) -> bool:
    text = str(name or "").strip().upper()
    return text in (POSTURE_LYING, "FALL", "FALLING") or is_fall_class_name(name)


def is_upright_posture(name: Any) -> bool:
    text = str(name or "").strip().upper()
    return text in (POSTURE_STANDING, POSTURE_SITTING, POSTURE_BENDING)


def _angle_at(a, b, c) -> Optional[float]:
    """Góc tại điểm b tạo bởi a-b-c (độ)."""
    try:
        ba = np.array([a[0] - b[0], a[1] - b[1]], dtype=np.float32)
        bc = np.array([c[0] - b[0], c[1] - b[1]], dtype=np.float32)
        nba = np.linalg.norm(ba)
        nbc = np.linalg.norm(bc)
        if nba < 1e-3 or nbc < 1e-3:
            return None
        cos = float(np.clip(np.dot(ba, bc) / (nba * nbc), -1.0, 1.0))
        return abs(math.degrees(math.acos(cos)))
    except Exception:
        return None


def _kpt_ok(kpt, thr: float = 0.35) -> bool:
    return (kpt.shape[0] >= 3 and float(kpt[2]) >= thr) if kpt is not None else False


def _mid(a, b):
    return ((float(a[0]) + float(b[0])) / 2.0, (float(a[1]) + float(b[1])) / 2.0)


def classify_posture(kpts, bbox) -> str:
    """
    Phân loại tư thế thông minh từ keypoints + bbox.
    STANDING | SITTING | BENDING | LYING | UNKNOWN

    Quy tắc tách ngồi vs ngã:
    - SITTING: thân còn nghiêng đứng, chân gập, bbox cao hơn nằm, ar < ~1.05
    - LYING: thân gần ngang hoặc bbox rất rộng/thấp (ar lớn)
    - BENDING: cúi người (thân nghiêng) nhưng chưa nằm, chân có thể thẳng
    """
    x1, y1, x2, y2 = bbox
    w = max(1.0, float(x2 - x1))
    h = max(1.0, float(y2 - y1))
    ar = w / h

    nose = kpts[0]
    l_sho, r_sho = kpts[5], kpts[6]
    l_hip, r_hip = kpts[11], kpts[12]
    l_knee, r_knee = kpts[13], kpts[14]
    l_ank, r_ank = kpts[15], kpts[16]

    # Góc thân so với phương thẳng đứng: 0° = đứng thẳng, 90° = nằm ngang
    torso_from_vertical = None
    sho_y = hip_y = None
    if _kpt_ok(l_sho) and _kpt_ok(r_sho) and _kpt_ok(l_hip) and _kpt_ok(r_hip):
        sho_x, sho_y = _mid(l_sho, r_sho)
        hip_x, hip_y = _mid(l_hip, r_hip)
        dx, dy = sho_x - hip_x, sho_y - hip_y
        # vector thân hip->shoulder; so với (0,-1) hướng lên trong ảnh (y tăng xuống)
        # góc với trục dọc: atan2(|dx|, |dy|)
        torso_from_vertical = abs(math.degrees(math.atan2(abs(dx), max(abs(dy), 1e-3))))

    torso_horizontal = torso_from_vertical is not None and torso_from_vertical >= 55
    torso_upright = torso_from_vertical is not None and torso_from_vertical <= 35
    torso_lean = torso_from_vertical is not None and 35 < torso_from_vertical < 55

    nose_near_hip = False
    if _kpt_ok(nose, 0.25) and hip_y is not None:
        if abs(float(nose[1]) - hip_y) < max(28.0, 0.22 * h):
            nose_near_hip = True

    # Góc gối (hip-knee-ankle) và góc thân-đùi (shoulder-hip-knee)
    knee_angles = []
    hip_angles = []
    for sho, hip, knee, ank in (
        (l_sho, l_hip, l_knee, l_ank),
        (r_sho, r_hip, r_knee, r_ank),
    ):
        if _kpt_ok(hip) and _kpt_ok(knee) and _kpt_ok(ank):
            ang = _angle_at(hip, knee, ank)
            if ang is not None:
                knee_angles.append(ang)
        if _kpt_ok(sho) and _kpt_ok(hip) and _kpt_ok(knee):
            ang = _angle_at(sho, hip, knee)
            if ang is not None:
                hip_angles.append(ang)

    avg_knee = sum(knee_angles) / len(knee_angles) if knee_angles else None
    avg_hip = sum(hip_angles) / len(hip_angles) if hip_angles else None
    # Gối gập mạnh (~90°) khi ngồi; gần 180° khi đứng/nằm duỗi
    knees_bent = avg_knee is not None and avg_knee < 140
    knees_very_bent = avg_knee is not None and avg_knee < 120
    hips_flexed = avg_hip is not None and avg_hip < 140

    # Hip thấp hơn vai rõ (ngồi/cúi) — trong ảnh y tăng xuống => hip_y > sho_y
    hip_below_sho = False
    if sho_y is not None and hip_y is not None:
        hip_below_sho = (hip_y - sho_y) > max(20.0, 0.12 * h)

    # --- LYING (ngã / nằm sàn): ưu tiên cao ---
    # Khác ngồi: thân ngang hoặc bbox rất rộng, chiều cao thấp
    if ar >= 1.35 and h <= 0.85 * w:
        return POSTURE_LYING
    if torso_horizontal and ar >= 0.90:
        return POSTURE_LYING
    if nose_near_hip and ar >= 1.05 and h < 180:
        return POSTURE_LYING
    if torso_from_vertical is not None and torso_from_vertical >= 65 and ar >= 0.85:
        return POSTURE_LYING

    # --- SITTING (ngồi): thân còn đứng, chân gập, bbox không nằm ---
    # Quan trọng: không báo ngã khi chỉ ngồi ghế / ngồi xổm
    if ar <= 1.05 and h >= 90:
        if knees_very_bent and (torso_upright or torso_lean or torso_from_vertical is None):
            if h < 240:
                return POSTURE_SITTING
        if knees_bent and hips_flexed and hip_below_sho and h < 220 and not torso_horizontal:
            return POSTURE_SITTING
        if knees_bent and ar < 0.95 and 100 <= h < 200 and not torso_horizontal:
            return POSTURE_SITTING

    # --- BENDING (cúi): thân nghiêng, chưa nằm, có thể đang cúi nhặt đồ ---
    if torso_lean and ar < 1.15 and h >= 110:
        return POSTURE_BENDING
    if torso_from_vertical is not None and 40 <= torso_from_vertical < 55 and ar < 1.1:
        return POSTURE_BENDING

    # --- STANDING ---
    if h >= 160 and ar <= 0.95 and not torso_horizontal:
        if avg_knee is None or avg_knee >= 130:
            return POSTURE_STANDING
        # Đứng nhưng gối hơi gập nhẹ vẫn standing
        if not knees_very_bent:
            return POSTURE_STANDING
    if h >= 140 and ar <= 0.85 and (torso_upright or torso_from_vertical is None):
        return POSTURE_STANDING

    # Fallback
    if knees_bent and ar < 1.1 and h < 210 and not torso_horizontal:
        return POSTURE_SITTING
    if ar >= 1.15 and h < 170:
        return POSTURE_LYING
    return POSTURE_UNKNOWN


def posture_to_draw_label(posture: str, is_fall_event: bool) -> str:
    """Nhãn hiển thị: chỉ 'fall' khi đang trong sự kiện ngã và người đang nằm."""
    if is_fall_event and posture == POSTURE_LYING:
        return "fall"
    return SAFE_POSTURE_LABELS.get(posture, "normal")


def format_posture_overlay(label_name: Any, conf: float) -> Tuple[str, Tuple[int, int, int]]:
    """
    Trả về (text, BGR color) để vẽ khung theo tư thế.
    FALL đỏ | Lying cam | Sitting xanh dương | Bending vàng | Standing xanh lá
    """
    lab = str(label_name or "normal").strip().lower()
    conf_s = f"{float(conf):.2f}"
    if is_fall_class_name(lab):
        return f"FALL ({conf_s})", (0, 0, 255)
    if lab == "lying":
        return f"Lying ({conf_s})", (0, 140, 255)
    if lab == "sitting":
        return f"Sitting ({conf_s})", (255, 180, 0)
    if lab == "bending":
        return f"Bending ({conf_s})", (0, 220, 255)
    if lab == "standing":
        return f"Standing ({conf_s})", (0, 220, 0)
    return f"Normal ({conf_s})", (0, 200, 0)


def collapse_from_upright(history, current_h: float, current_cy: float) -> bool:
    """
    Sụt chiều cao từ tư thế đứng/ngồi cao.
    Chỉ đúng khi trước đó có chiều cao lớn (đã từng đứng).
    """
    if current_h <= 1 or len(history) < 8:
        return False
    recent = list(history)[-36:]
    upright_heights = [item[1] for item in recent if item[3] in (POSTURE_STANDING, POSTURE_SITTING)]
    if not upright_heights:
        max_h = max(item[1] for item in recent)
        if max_h < 150:
            return False
        upright_ref = max_h
    else:
        upright_ref = max(upright_heights)
        if upright_ref < 140:
            return False

    avg_cy = sum(item[2] for item in recent) / float(len(recent))
    height_drop = (upright_ref - current_h) / max(upright_ref, 1.0)
    center_drop = (current_cy - avg_cy) > 32
    return height_drop >= 0.45 and (center_drop or current_h < upright_ref * 0.62)


def _iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a[:4]
    bx1, by1, bx2, by2 = b[:4]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))
    return inter / float(area_a + area_b - inter)


def merge_person_boxes(boxes: List[FallBox], iou_thr: float = 0.35) -> List[FallBox]:
    """
    Gộp box trùng (model + pose trên cùng 1 người) -> 1 box.
    Ưu tiên box pose (có tư thế), rồi box fall, rồi conf cao hơn.
    """
    if not boxes:
        return []

    def _rank(b: FallBox) -> Tuple[int, int, float]:
        label, conf, src = b[4], float(b[5]), b[6]
        src_score = 2 if src == "pose" else (1 if src == "transition" else 0)
        lab = str(label).lower()
        if is_fall_class_name(lab):
            fall_score = 3
        elif lab == "lying":
            fall_score = 2
        elif lab in ("sitting", "standing", "bending"):
            fall_score = 1
        else:
            fall_score = 0
        return (src_score, fall_score, conf)

    ordered = sorted(boxes, key=_rank, reverse=True)
    kept: List[FallBox] = []
    for cand in ordered:
        overlapped = False
        for i, k in enumerate(kept):
            if _iou(cand, k) >= iou_thr:
                # Giữ box đang có nếu rank cao hơn; chỉ nâng nhãn fall nếu cand là fall
                if is_fall_class_name(cand[4]) and not is_fall_class_name(k[4]):
                    kept[i] = (k[0], k[1], k[2], k[3], "fall", max(float(k[5]), float(cand[5])), k[6])
                overlapped = True
                break
        if not overlapped:
            kept.append(cand)
    return kept


class FallTrackState:
    """Trạng thái theo dõi ngã cho 1 camera / 1 video test."""

    def __init__(self):
        # (t, h, cy, posture)
        self.person_height_history: Deque[Tuple[float, float, float, str]] = collections.deque(maxlen=90)
        self.posture_history: Deque[str] = collections.deque(maxlen=24)
        self.fall_counter = 0
        self.fall_active = False
        self.last_fall_boxes: List[FallBox] = []
        self.last_fall_in_frame = False
        self.seen_upright = False
        # Đếm theo FRAME suy luận — không dùng time.time() (máy chậm ~1.5s/frame sẽ hết hạn cửa sổ)
        self.upright_grace = 0  # còn bao nhiêu lần suy luận được tính "vừa đứng/ngồi"
        self.lying_streak = 0
        self.candidate_streak = 0
        self.fall_confirmed = False
        self.stand_streak = 0  # chỉ STANDING mới coi là đứng dậy


def _stable_posture(history: Deque[str], need: int = 3) -> str:
    if len(history) < need:
        return POSTURE_UNKNOWN
    recent = list(history)[-need:]
    counts: Dict[str, int] = {}
    for p in recent:
        counts[p] = counts.get(p, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _clear_fall_state(state: FallTrackState) -> None:
    state.fall_confirmed = False
    state.candidate_streak = 0
    state.lying_streak = 0
    state.fall_counter = 0
    state.fall_active = False


def detect_fall_hybrid(
    frame,
    state: FallTrackState,
    fall_model=None,
    pose_model=None,
    device=None,
    conf_thr: float = 0.25,
    imgsz: int = 640,
    lock=None,
):
    """
    Trả về (fall_in_frame, boxes, diagnostics).
    - Báo khi đứng/ngồi -> nằm (cửa sổ theo frame, chịu được máy chậm)
    - Đứng dậy (STANDING) -> tắt FALL
    - 1 người = 1 box
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    now = time.time()
    fall_candidate = False
    person_samples = []
    pose_entries = []  # (x1,y1,x2,y2,conf,posture,collapsed,h)
    diag = {
        "model_fall": 0,
        "model_normal": 0,
        "pose_fall": 0,
        "collapse": 0,
        "max_fall_conf": 0.0,
        "posture": POSTURE_UNKNOWN,
        "seen_upright": False,
    }

    def _infer(model, **kwargs):
        if lock is not None:
            with lock:
                with torch.no_grad():
                    return model(frame, **kwargs)
        with torch.no_grad():
            return model(frame, **kwargs)

    model_fall_hit = False
    model_fall_conf = 0.0
    model_boxes_raw: List[FallBox] = []

    # 1) Model fall — tín hiệu phụ
    if fall_model is not None:
        results = _infer(
            fall_model,
            verbose=False,
            device=device,
            conf=max(0.08, float(conf_thr) * 0.55),
            imgsz=imgsz,
        )
        names = getattr(fall_model, "names", {}) or {}
        if len(results) > 0 and results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls[0].cpu().item())
                conf = float(box.conf[0].cpu().item())
                if conf < conf_thr:
                    continue
                x1, y1, x2, y2 = [int(b) for b in box.xyxy[0].cpu().numpy()[:4]]
                class_name = names.get(cls_id, str(cls_id))
                is_fall = is_fall_class_name(class_name)
                label = "fall" if is_fall else "normal"
                if is_fall:
                    diag["model_fall"] += 1
                    diag["max_fall_conf"] = max(diag["max_fall_conf"], conf)
                    model_fall_hit = True
                    model_fall_conf = max(model_fall_conf, conf)
                else:
                    diag["model_normal"] += 1
                model_boxes_raw.append((x1, y1, x2, y2, label, conf, "model"))

    # 2) Pose — nguồn chính
    best_posture = POSTURE_UNKNOWN
    lying_now = False
    collapsed_now = False
    standing_now = False
    max_h_now = 0.0

    if pose_model is not None:
        pose_results = _infer(pose_model, verbose=False, device=device, conf=0.22, imgsz=imgsz)
        if (
            len(pose_results) > 0
            and pose_results[0].keypoints is not None
            and pose_results[0].boxes is not None
        ):
            keypoints_data = pose_results[0].keypoints.data.cpu().numpy()
            boxes = pose_results[0].boxes.xyxy.cpu().numpy()
            confs = (
                pose_results[0].boxes.conf.cpu().numpy()
                if pose_results[0].boxes.conf is not None
                else np.full((len(boxes),), 0.5, dtype=np.float32)
            )
            for i, kpts in enumerate(keypoints_data):
                x1, y1, x2, y2 = [int(b) for b in boxes[i][:4]]
                conf = float(confs[i]) if i < len(confs) else 0.5
                h = max(1, y2 - y1)
                w = max(1, x2 - x1)
                cy = (y1 + y2) / 2.0
                posture = classify_posture(kpts, (x1, y1, x2, y2))
                # Bbox nằm ngang rõ → LYING (không áp khi đang giống ngồi: ar vừa + cao vừa)
                if posture not in (POSTURE_LYING, POSTURE_SITTING) and (w / float(h)) >= 1.30 and h < 190:
                    posture = POSTURE_LYING
                if posture != POSTURE_UNKNOWN:
                    best_posture = posture
                person_samples.append((now, h, cy, posture))
                max_h_now = max(max_h_now, float(h))

                collapsed = collapse_from_upright(state.person_height_history, h, cy)
                # Ngồi xuống cũng sụt chiều cao — không coi collapse nếu đang SITTING rõ
                if posture == POSTURE_SITTING:
                    collapsed = False
                if posture == POSTURE_LYING:
                    lying_now = True
                if posture == POSTURE_STANDING:
                    standing_now = True
                if collapsed:
                    collapsed_now = True
                    diag["collapse"] += 1

                pose_entries.append((x1, y1, x2, y2, conf, posture, collapsed, h))

    sitting_now = any(p[3] == POSTURE_SITTING for p in person_samples)

    # Cập nhật lịch sử tư thế
    for item in person_samples:
        state.person_height_history.append(item)
        if item[3] in (POSTURE_STANDING, POSTURE_SITTING, POSTURE_BENDING):
            state.seen_upright = True
            state.upright_grace = 60
            state.posture_history.append(item[3])
        elif item[3] == POSTURE_LYING:
            state.posture_history.append(POSTURE_LYING)
        elif item[3] != POSTURE_UNKNOWN:
            state.posture_history.append(item[3])

    if state.upright_grace > 0 and not any(is_upright_posture(p[3]) for p in person_samples):
        state.upright_grace = max(0, int(state.upright_grace) - 1)

    stable = _stable_posture(state.posture_history, need=3)
    if stable != POSTURE_UNKNOWN:
        best_posture = stable
    diag["posture"] = best_posture
    diag["seen_upright"] = bool(state.seen_upright)

    # Chỉ LYING mới là "nằm/ngã" — SITTING/BENDING không kích hoạt ngã
    still_down = lying_now or stable == POSTURE_LYING
    if still_down:
        state.lying_streak = int(getattr(state, "lying_streak", 0)) + 1
    else:
        state.lying_streak = 0

    if standing_now and not lying_now and max_h_now >= 140:
        state.stand_streak = int(getattr(state, "stand_streak", 0)) + 1
    else:
        state.stand_streak = 0

    recovered = state.stand_streak >= 3
    if recovered:
        _clear_fall_state(state)

    recently_upright = bool(state.seen_upright) and (
        int(getattr(state, "upright_grace", 0)) > 0
        or any(is_upright_posture(p[3]) for p in person_samples)
    )
    model_strong = model_fall_hit and model_fall_conf >= max(float(conf_thr), 0.35)

    # Ứng viên ngã: bắt buộc có LYING (không báo khi chỉ ngồi/cúi)
    if recovered:
        fall_candidate = False
    elif sitting_now and not lying_now:
        fall_candidate = False
    elif recently_upright and still_down and state.lying_streak >= 2:
        fall_candidate = True
    elif recently_upright and collapsed_now and still_down and state.lying_streak >= 1:
        fall_candidate = True
    elif recently_upright and model_strong and still_down and not sitting_now:
        fall_candidate = True
        diag["pose_fall"] += 1
    elif getattr(state, "fall_confirmed", False) and still_down and not recovered:
        fall_candidate = True
        diag["pose_fall"] = max(int(diag["pose_fall"]), 1)
    else:
        fall_candidate = False

    if fall_candidate:
        state.candidate_streak = int(getattr(state, "candidate_streak", 0)) + 1
        if state.candidate_streak >= 2 or getattr(state, "fall_active", False):
            state.fall_confirmed = True
        if still_down:
            diag["pose_fall"] = max(diag["pose_fall"], 1)
    else:
        state.candidate_streak = 0
        if not still_down and not getattr(state, "fall_active", False):
            state.fall_confirmed = False

    # --- Vẽ: nhãn tư thế thông minh (Sitting/Standing/Bending/Lying/FALL) ---
    draw_boxes: List[FallBox] = []
    event_on = bool(
        fall_candidate
        or getattr(state, "fall_confirmed", False)
        or getattr(state, "fall_active", False)
    )

    if pose_entries:
        for x1, y1, x2, y2, conf, posture, collapsed, h in pose_entries:
            label = posture_to_draw_label(posture, is_fall_event=(event_on and not recovered))
            # Collapse giữa chừng + event: đánh fall ngay cả khi posture chưa chốt LYING
            if event_on and collapsed and posture != POSTURE_SITTING and not recovered:
                label = "fall"
            draw_boxes.append((x1, y1, x2, y2, label, conf, "pose"))
    elif model_boxes_raw:
        for x1, y1, x2, y2, label, conf, src in model_boxes_raw:
            if event_on and is_fall_class_name(label) and not recovered:
                draw_boxes.append((x1, y1, x2, y2, "fall", conf, src))
            else:
                draw_boxes.append((x1, y1, x2, y2, "normal", conf, src))
    elif event_on and getattr(state, "last_fall_boxes", None):
        for b in state.last_fall_boxes:
            if is_fall_class_name(b[4]):
                draw_boxes.append(b)

    if pose_entries and model_boxes_raw:
        for mb in model_boxes_raw:
            if any(_iou(mb, pb) >= 0.35 for pb in draw_boxes):
                if event_on and is_fall_class_name(mb[4]) and not recovered:
                    for i, db in enumerate(draw_boxes):
                        if _iou(mb, db) >= 0.35 and (
                            is_fall_class_name(db[4]) or db[4] in ("lying", "fall")
                        ):
                            draw_boxes[i] = (
                                db[0], db[1], db[2], db[3],
                                "fall", max(float(db[5]), float(mb[5])), db[6],
                            )
                            break
                continue
            if event_on and is_fall_class_name(mb[4]) and not recovered:
                draw_boxes.append((mb[0], mb[1], mb[2], mb[3], "fall", mb[5], "model"))

    detected_boxes = merge_person_boxes(draw_boxes, iou_thr=0.35)
    # Tương thích thuộc tính cũ trên CameraState
    state.upright_streak = int(getattr(state, "stand_streak", 0))

    state.last_fall_boxes = detected_boxes
    state.last_fall_in_frame = bool(fall_candidate)
    return bool(fall_candidate), detected_boxes, diag


def update_fall_alert_counter(state: FallTrackState, fall_in_frame: bool, frame_buffer: int = 8) -> bool:
    """Xác minh ngã theo số khung; đứng dậy (STANDING) thì tắt ngay."""
    need = max(4, int(frame_buffer))
    if getattr(state, "stand_streak", 0) >= 3 and not fall_in_frame:
        state.fall_counter = 0
        state.fall_active = False
        state.fall_confirmed = False
        return False

    if fall_in_frame:
        state.fall_counter += 1
        if state.fall_counter >= need:
            state.fall_active = True
            state.fall_confirmed = True
    else:
        step = 2
        state.fall_counter = max(0, state.fall_counter - step)
        if state.fall_counter == 0 and not getattr(state, "fall_confirmed", False):
            state.fall_active = False
        # Đang confirmed + vẫn nằm: giữ active nếu counter về 0 tạm thời
        elif getattr(state, "fall_confirmed", False) and getattr(state, "lying_streak", 0) >= 1:
            state.fall_active = True
            state.fall_counter = max(state.fall_counter, need)
    return bool(state.fall_active)
