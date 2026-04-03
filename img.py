import torch

# Load a YOLOv5 model (options: yolov5n, yolov5s, yolov5m, yolov5l, yolov5x)
model = torch.hub.load("ultralytics/yolov5", "yolov5s")  # Default: yolov5s

# model.classes = [0]
# Define the input image source (URL, local file, PIL image, OpenCV frame, numpy array, or list)
img = "img/photo-2-15846847341501054864457-crop-15846847456791234560449.webp"  # Example image

# Perform inference (handles batching, resizing, normalization automatically)
results = model(img) 
# Process the results (options: .print(), .show(), .save(), .crop(), .pandas())
results.print()  # Print results to console
results.show()  # Display results in a window
results.save()  # Save results to runs/detect/exp