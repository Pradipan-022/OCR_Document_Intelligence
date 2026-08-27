import re
from typing import Any

class MetadataAndTableExtractor:
    def __init__(self):
        self.patterns = {
            "invoice_number": r"(?i)(?:invoice|inv|bill)\s*(?:#|no|num)?[:.\s]*([A-Z0-9-]+)",
            # Removed the '?:' so it now properly captures the date in group 1
            "date": r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b",
            "grand_total": r"(?i)(?:grand\s*total|total\s*amount|total)[:.\s]*[$₹€]?\s*([\d,]+\.\d{2})",
            "subtotal": r"(?i)(?:subtotal|sub\s*total)[:.\s]*[$₹€]?\s*([\d,]+\.\d{2})",
            "tax": r"(?i)(?:tax|vat|gst)[:.\s]*[$₹€]?\s*([\d,]+\.\d{2})"
        }

    def extract_key_values(self, full_text: str) -> dict[str, Any]:
        extracted = {}
        for field, pattern in self.patterns.items():
            match = re.search(pattern, full_text)
            if match:
                try:
                    # Try to get the specific captured group
                    extracted[field] = match.group(1)
                except IndexError:
                    # Bulletproof fallback: if no group(1) exists, grab the whole match
                    extracted[field] = match.group(0)
            else:
                extracted[field] = None
        return extracted

    def extract_line_item_table(self, bounding_box_tokens: list[dict[str, Any]], y_threshold: int = 15) -> list[dict[str, Any]]:
        """Groups text tokens into rows by vertical proximity and sorts by horizontal spatial X coordinates."""
        if not bounding_box_tokens:
            return []

        # Sort tokens top-to-bottom
        sorted_tokens = sorted(bounding_box_tokens, key=lambda b: b["bbox"][1])
        
        rows: list[list[dict[str, Any]]] = []
        current_row: list[dict[str, Any]] = []

        # 1. Improved Grouping: Compare against the row's average Y to prevent drifting
        for token in sorted_tokens:
            y_min = token["bbox"][1]
            if not current_row:
                current_row.append(token)
            else:
                avg_y = sum(t["bbox"][1] for t in current_row) / len(current_row)
                if abs(y_min - avg_y) <= y_threshold:
                    current_row.append(token)
                else:
                    rows.append(current_row)
                    current_row = [token]
        if current_row:
            rows.append(current_row)

        parsed_line_items = []
        for row in rows:
            # Sort row left-to-right
            row_tokens = sorted(row, key=lambda b: b["bbox"][0])
            row_text = " ".join([t["text"] for t in row_tokens])
            
            # 2. Improved Regex: Supports commas for thousands (e.g., 1,250.00)
            numbers = re.findall(r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b|\b\d+\b", row_text)
            
            if len(numbers) >= 2:
                # 3. Safer Description Cleaning: Only remove the specific billing numbers extracted
                description = row_text
                for num in numbers:
                    # Replace only from the right side or specifically matched instances to protect model numbers
                    description = description.replace(num, "", 1) 
                
                # 4. Extract Unit Price to meet project specs
                parsed_line_items.append({
                    "raw_row_text": row_text,
                    "description": description.strip(" ,.-"),
                    "possible_quantity": numbers[0],
                    "possible_unit_price": numbers[-2] if len(numbers) >= 3 else None,
                    "possible_total": numbers[-1]
                })

        return parsed_line_items