import io
import csv
import json
import cv2
import numpy as np
from typing import Any

class ExportService:
    @staticmethod
    def to_json(data: dict[str, Any]) -> str:
        """Serializes document result payload to formatted JSON."""
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def to_csv(line_items: list[dict[str, Any]]) -> str:
        """Converts extracted line items into a CSV string."""
        output = io.StringIO()
        fieldnames = ["description", "possible_quantity", "inferred_unit_price", "possible_total", "raw_row_text"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        
        writer.writeheader()
        for item in line_items:
            writer.writerow(item)
            
        return output.getvalue()

    @staticmethod
    def generate_annotated_image(image_bytes: bytes, bounding_boxes: list[dict[str, Any]]) -> bytes:
        """Draws spatial bounding boxes over key extracted fields on the original document image."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        for box in bounding_boxes:
            bbox = box.get("bbox")  # Expecting [x, y, w, h] or [x1, y1, x2, y2]
            if not bbox or len(bbox) < 4:
                continue
            x, y, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
            
            # Draw green bounding box rectangle
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Tag text label above bounding box
            label = str(box.get("text", ""))[:15]
            cv2.putText(img, label, (x, max(y - 5, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

        _, encoded_img = cv2.imencode(".png", img)
        return encoded_img.tobytes()