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
    def generate_annotated_image(image_bytes: bytes, blocks: list[dict[str, Any]]) -> bytes:
        """Draws spatial bounding boxes over extracted text tokens on the document image."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Failed to decode image bytes for annotation.")

        for block in blocks:
            bbox = block.get("bbox", {})
            if isinstance(bbox, dict):
                x1 = bbox.get("x_min", block.get("x_min", 0))
                y1 = bbox.get("y_min", block.get("y_min", 0))
                x2 = bbox.get("x_max", block.get("x_max", 0))
                y2 = bbox.get("y_max", block.get("y_max", 0))
            elif isinstance(bbox, list) and len(bbox) >= 4:
                x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
            else:
                continue

            # Draw green bounding box rectangle
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            
            # Draw text label above box
            text_label = str(block.get("text", "")).strip()[:15]
            if text_label:
                cv2.putText(
                    img, 
                    text_label, 
                    (int(x1), max(int(y1) - 6, 12)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.4, 
                    (255, 0, 0), 
                    1, 
                    cv2.LINE_AA
                )

        _, encoded_img = cv2.imencode(".png", img)
        return encoded_img.tobytes()