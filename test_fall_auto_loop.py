# -*- coding: utf-8 -*-
"""
Vòng lặp tự động: tìm video ngã -> test -> chẩn đoán -> chỉnh ngưỡng -> test lại.
Không khởi chạy web server / camera threads.
"""
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

# Import trực tiếp file fall_detect — tránh app/__init__.py (không spawn camera/Telegram)
_fd_path = ROOT / "app" / "fall_detect.py"
_spec = importlib.util.spec_from_file_location("fall_detect_standalone", _fd_path)
_fd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fd)
FallTrackState = _fd.FallTrackState
detect_fall_hybrid = _fd.detect_fall_hybrid
is_fall_class_name = _fd.is_fall_class_name
update_fall_alert_counter = _fd.update_fall_alert_counter

FALL_NAME_HINTS = ("fall", "collaps", "nga", "ngã", "slip", "tumble", "heart attack")
PASS_ALERT = True
MAX_ROUNDS = 4


def discover_fall_videos():
    vids = []
    for p in ROOT.glob("*.mp4"):
        name = p.name.lower()
        if any(h in name for h in FALL_NAME_HINTS):
            vids.append(p)
    # Ưu tiên video demo rõ ràng
    preferred = [
        "ArcSpec Fall Detection Video software demonstration.mp4",
        "Man Collapses at Hospital After Heart Attack.mp4",
        "Man-Collapses-at-SnapYT.App.mp4",
    ]
    ordered = []
    for name in preferred:
        hit = ROOT / name
        if hit.exists() and hit not in ordered:
            ordered.append(hit)
    for v in vids:
        if v not in ordered:
            ordered.append(v)
    return ordered


def evaluate_video(path, fall_model, pose_model, device, conf_thr=0.12, frame_buf=6, step=6, imgsz=640):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"ok": False, "error": f"Không mở được video: {path.name}"}

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    state = FallTrackState()
    sampled = 0
    fall_hits = 0
    first_alert_frame = None
    first_alert_sec = None
    alerted = False
    sources = {"model": 0, "pose": 0, "collapse": 0}
    max_fall_conf = 0.0
    model_fall_boxes = 0
    pose_fall_boxes = 0
    collapse_boxes = 0

    for idx in range(0, max(total, 1), max(1, step)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.resize(frame, (640, 360))
        sampled += 1
        fall_in, boxes, diag = detect_fall_hybrid(
            frame,
            state,
            fall_model=fall_model,
            pose_model=pose_model,
            device=device,
            conf_thr=conf_thr,
            imgsz=imgsz,
            lock=None,
        )
        max_fall_conf = max(max_fall_conf, float(diag.get("max_fall_conf", 0.0)))
        model_fall_boxes += int(diag.get("model_fall", 0))
        pose_fall_boxes += int(diag.get("pose_fall", 0))
        collapse_boxes += int(diag.get("collapse", 0))
        for b in boxes:
            src = b[6] if len(b) > 6 else ""
            if is_fall_class_name(b[4]):
                sources[src] = sources.get(src, 0) + 1
        if fall_in:
            fall_hits += 1
        active = update_fall_alert_counter(state, fall_in, frame_buf)
        if active and not alerted:
            alerted = True
            first_alert_frame = idx
            first_alert_sec = idx / max(fps, 1e-6)

    cap.release()
    ratio = (fall_hits / sampled) if sampled else 0.0
    return {
        "ok": True,
        "video": path.name,
        "total_frames": total,
        "fps": round(fps, 2),
        "sampled": sampled,
        "fall_hits": fall_hits,
        "fall_ratio": round(ratio, 3),
        "alerted": alerted,
        "first_alert_frame": first_alert_frame,
        "first_alert_sec": None if first_alert_sec is None else round(first_alert_sec, 2),
        "max_fall_conf": round(max_fall_conf, 3),
        "model_fall_boxes": model_fall_boxes,
        "pose_fall_boxes": pose_fall_boxes,
        "collapse_boxes": collapse_boxes,
        "sources": sources,
        "conf_thr": conf_thr,
        "frame_buf": frame_buf,
        "passed": bool(alerted) if PASS_ALERT else True,
    }


def diagnose(results, conf_thr, frame_buf):
    """Đưa ra chỉnh sửa ngưỡng dựa trên kết quả test."""
    failed = [r for r in results if r.get("ok") and not r.get("passed")]
    notes = []
    new_conf = conf_thr
    new_buf = frame_buf
    changed = False

    if not failed:
        notes.append("Tất cả video đã kích hoạt cảnh báo ngã.")
        return conf_thr, frame_buf, notes, False

    for r in failed:
        notes.append(f"[FAIL] {r['video']}: chưa kích hoạt cảnh báo.")
        if r["model_fall_boxes"] == 0 and r["pose_fall_boxes"] == 0 and r["collapse_boxes"] == 0:
            notes.append("  -> Không có tín hiệu model/pose/collapse. Hạ conf và giảm frame buffer.")
            if new_conf > 0.08:
                new_conf = max(0.08, new_conf - 0.03)
                changed = True
            if new_buf > 3:
                new_buf = max(3, new_buf - 2)
                changed = True
        elif r["model_fall_boxes"] > 0 and r["max_fall_conf"] < conf_thr:
            notes.append(f"  -> Model có fall nhưng conf max={r['max_fall_conf']} < thr={conf_thr}. Hạ ngưỡng.")
            new_conf = max(0.08, min(new_conf, r["max_fall_conf"] * 0.9))
            changed = True
        elif r["pose_fall_boxes"] > 0 or r["collapse_boxes"] > 0:
            notes.append("  -> Có tín hiệu yếu nhưng chưa đủ khung xác minh. Giảm fall_frame_buffer.")
            if new_buf > 3:
                new_buf = max(3, new_buf - 2)
                changed = True
        else:
            notes.append("  -> Có box nhưng không đủ điều kiện fall. Hạ conf thêm.")
            new_conf = max(0.08, new_conf - 0.02)
            changed = True

    if not changed:
        notes.append("Không còn tham số để chỉnh trong vòng này.")
    else:
        notes.append(f"Đề xuất vòng sau: fall_conf_threshold={new_conf:.3f}, fall_frame_buffer={new_buf}")
    return new_conf, new_buf, notes, changed


def persist_settings(conf_thr, frame_buf):
    settings_path = ROOT / "settings.json"
    data = {}
    if settings_path.exists():
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    data["fall_conf_threshold"] = float(round(conf_thr, 3))
    data["fall_frame_buffer"] = int(frame_buf)
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"[SAVE] settings.json <- fall_conf_threshold={data['fall_conf_threshold']}, fall_frame_buffer={data['fall_frame_buffer']}")


def main():
    print("=" * 72)
    print("VÒNG LẶP TỰ ĐỘNG KIỂM THỬ / CHẨN ĐOÁN PHÁT HIỆN NGÃ")
    print("=" * 72)

    videos = discover_fall_videos()
    if not videos:
        print("[ERROR] Không tìm thấy video ngã trong thư mục dự án.")
        sys.exit(1)

    print(f"[INFO] Tìm thấy {len(videos)} video ngã:")
    for v in videos:
        print(f"  - {v.name} ({v.stat().st_size / 1024 / 1024:.1f} MB)")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] Device: {device}")

    fall_path = ROOT / "yolov8n_fall_best.pt"
    pose_path = ROOT / "yolov8n-pose.pt"
    if not fall_path.exists():
        print("[ERROR] Thiếu yolov8n_fall_best.pt")
        sys.exit(1)
    if not pose_path.exists():
        print("[ERROR] Thiếu yolov8n-pose.pt")
        sys.exit(1)

    fall_model = YOLO(str(fall_path))
    pose_model = YOLO(str(pose_path))
    print(f"[INFO] Fall class names: {fall_model.names}")

    # Kiểm tra class mapping chuẩn
    names = {int(k): str(v).lower() for k, v in (fall_model.names or {}).items()}
    fall_ids = [i for i, n in names.items() if is_fall_class_name(n)]
    normal_ids = [i for i, n in names.items() if "normal" in n]
    print(f"[CHECK] fall class ids={fall_ids}, normal class ids={normal_ids}")
    if 0 in fall_ids and 1 in normal_ids:
        print("[WARN] Class map đảo ngược so với kỳ vọng cũ (0=fall). Code mới đọc theo TÊN lớp nên vẫn đúng.")
    if not fall_ids:
        print("[ERROR] Model không có lớp fall theo tên!")
        sys.exit(1)

    conf_thr = 0.25
    frame_buf = 10
    settings_path = ROOT / "settings.json"
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                s = json.load(f)
            conf_thr = float(s.get("fall_conf_threshold", conf_thr))
            frame_buf = int(s.get("fall_frame_buffer", frame_buf))
        except Exception:
            pass

    all_round_reports = []
    final_results = []

    for round_i in range(1, MAX_ROUNDS + 1):
        print("\n" + "#" * 72)
        print(f"ROUND {round_i}/{MAX_ROUNDS} | conf={conf_thr:.3f} | buffer={frame_buf}")
        print("#" * 72)
        results = []
        for v in videos:
            t0 = time.time()
            print(f"\n[TEST] {v.name} ...")
            r = evaluate_video(v, fall_model, pose_model, device, conf_thr=conf_thr, frame_buf=frame_buf, step=6)
            r["elapsed_sec"] = round(time.time() - t0, 1)
            results.append(r)
            if not r.get("ok"):
                print(f"  ERROR: {r.get('error')}")
                continue
            status = "PASS" if r["passed"] else "FAIL"
            print(
                f"  [{status}] alert={r['alerted']} first@{r['first_alert_sec']}s "
                f"ratio={r['fall_ratio']} model={r['model_fall_boxes']} "
                f"pose={r['pose_fall_boxes']} collapse={r['collapse_boxes']} "
                f"max_conf={r['max_fall_conf']} ({r['elapsed_sec']}s)"
            )

        all_round_reports.append({"round": round_i, "conf_thr": conf_thr, "frame_buf": frame_buf, "results": results})
        final_results = results
        passed = all(r.get("passed") for r in results if r.get("ok"))
        if passed:
            print("\n[OK] Tất cả video PASS trong round này.")
            persist_settings(conf_thr, frame_buf)
            break

        conf_thr, frame_buf, notes, changed = diagnose(results, conf_thr, frame_buf)
        print("\n[DIAGNOSE]")
        for n in notes:
            print(" ", n)
        if not changed:
            print("[STOP] Không chỉnh thêm được tham số.")
            break
        persist_settings(conf_thr, frame_buf)

    # Báo cáo cuối
    out = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "device": device,
        "fall_class_names": fall_model.names,
        "rounds": all_round_reports,
        "final": final_results,
        "final_settings": {"fall_conf_threshold": conf_thr, "fall_frame_buffer": frame_buf},
    }
    report_path = ROOT / "ket_qua_test_fall.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 72)
    print("TỔNG KẾT")
    ok_n = sum(1 for r in final_results if r.get("passed"))
    tot_n = sum(1 for r in final_results if r.get("ok"))
    print(f"PASS {ok_n}/{tot_n} video")
    print(f"Settings: fall_conf_threshold={conf_thr}, fall_frame_buffer={frame_buf}")
    print(f"Report: {report_path}")
    print("=" * 72)
    sys.exit(0 if ok_n == tot_n and tot_n > 0 else 1)


if __name__ == "__main__":
    main()
