import os
import zipfile
import shutil

def package_project():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    zip_name = "SmartCamera_System.zip"
    zip_path = os.path.join(project_dir, "..", zip_name)
    
    print("==================================================")
    # Excluded directories (Datasets, cache, venv, temporary folders)
    exclude_dirs = {
        ".git",
        "__pycache__",
        "venv",
        ".venv",
        ".idea",
        ".vscode",
        "runs",
        ".tempmediaStorage",
        "output_events",
        "static/recordings",
        "dataset",          # Loại bỏ bộ dữ liệu ảnh gốc
        "dataset_fire",     # Loại bỏ bộ dữ liệu khói lửa gốc
        "videotest",        # Loại bỏ các video test phụ
        "kaggle_cache",     # Loại bỏ bộ nhớ đệm tải Kaggle
        "input_videos"      # Loại bỏ thư mục chứa video đầu vào test
    }
    
    # Excluded extensions
    exclude_extensions = {
        ".pyc",
        ".pyo",
        ".pyd",
        ".db-journal",
        ".log",
        ".aux",
        ".bcf",
        ".blg",
        ".run.xml",
        ".toc"
    }

    print(f"[PACKAGING] Starting package build for: {project_dir}")
    print(f"[PACKAGING] Output ZIP path: {zip_path}")
    
    zip_count = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_dir):
            relative_dir = os.path.relpath(root, project_dir)
            
            should_exclude = False
            for ex_dir in exclude_dirs:
                if relative_dir == ex_dir or relative_dir.startswith(ex_dir + os.sep):
                    should_exclude = True
                    break
            
            if should_exclude:
                continue
                
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in exclude_extensions:
                    continue
                
                if file == zip_name:
                    continue
                    
                file_path = os.path.join(root, file)
                archive_name = os.path.relpath(file_path, project_dir)
                
                # Exclude static/recordings files
                if archive_name.startswith("static" + os.sep + "recordings" + os.sep) and file.endswith(".mp4"):
                    continue
                # Exclude static/alerts files
                if archive_name.startswith("static" + os.sep + "alerts" + os.sep) and (file.endswith(".mp4") or file.endswith(".jpg")):
                    continue
                
                zipf.write(file_path, archive_name)
                zip_count += 1
                
    print(f"[PACKAGING] Packaged {zip_count} files successfully into {zip_name}!")
    print(f"[PACKAGING] Archive saved at: {os.path.abspath(zip_path)}")
    print("==================================================")

if __name__ == "__main__":
    package_project()
