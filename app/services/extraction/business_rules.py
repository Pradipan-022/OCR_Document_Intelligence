import re
from typing import Any

class BusinessValidationEngine:
    def __init__(self, tolerance: float = 0.02):
        self.tolerance = tolerance

    def validate_document(self, extracted_fields: dict[str, Any], line_items: list[dict[str, Any]]) -> dict[str, Any]:
        flags = []

        subtotal = self._parse_float(extracted_fields.get("subtotal"))
        tax = self._parse_float(extracted_fields.get("tax"))
        discount = self._parse_float(extracted_fields.get("discount")) 
        service_charge = self._parse_float(extracted_fields.get("service_charge"))
        grand_total = self._parse_float(extracted_fields.get("grand_total"))

        # Rule 1: Subtotal - Discount + Tax + Service Charge == Grand Total
        if grand_total is not None and subtotal is not None:
            expected_total = subtotal - (discount or 0.0) + (tax or 0.0) + (service_charge or 0.0)
            
            if abs(expected_total - grand_total) > self.tolerance:
                flags.append({
                    "field": "grand_total",
                    "severity": "error",
                    "message": f"Mathematical mismatch: Expected {round(expected_total, 2)} but extracted Grand Total is {grand_total}."
                })
            
            # Rule 2: Flag missing discounts when totals drop
            if grand_total < subtotal and not discount:
                flags.append({
                    "field": "grand_total",
                    "severity": "warning",
                    "message": "Grand total is lower than subtotal, but no discount was found."
                })

        # Rule 3: Line item price math (Quantity * Unit Price == Line Total)
        for idx, item in enumerate(line_items):
            qty = self._parse_float(item.get("possible_quantity"))
            unit_price = self._parse_float(item.get("possible_unit_price"))
            total = self._parse_float(item.get("possible_total"))
            
            if qty and total:
                # If we successfully extracted a unit price from OCR, validate the math
                if unit_price:
                    expected_line_total = qty * unit_price
                    if abs(expected_line_total - total) > self.tolerance:
                        flags.append({
                            "field": f"line_item_{idx}",
                            "severity": "warning",
                            "message": f"Line item '{item.get('description', '')}' math mismatch: {qty} qty * {unit_price} price != {total} total."
                        })
                else:
                    # Fallback: Infer it if missing and flag as info
                    inferred_unit_price = total / qty if qty > 0 else 0
                    item["inferred_unit_price"] = round(inferred_unit_price, 2)
                    flags.append({
                        "field": f"line_item_{idx}",
                        "severity": "info",
                        "message": f"Missing unit price. Inferred as {item['inferred_unit_price']} based on line total."
                    })
            else:
                flags.append({
                    "field": f"line_item_{idx}",
                    "severity": "warning",
                    "message": f"Line item '{item.get('description', '')}' is missing readable quantity or line total."
                })

        # Rule 4: Missing essential identifiers & dates
        if not extracted_fields.get("invoice_number"):
            flags.append({
                "field": "invoice_number",
                "severity": "warning",
                "message": "Missing invoice or receipt identifier."
            })
            
        if not extracted_fields.get("date"):
            flags.append({
                "field": "date",
                "severity": "warning",
                "message": "Missing or implausible invoice date."
            })

        return {
            "is_valid": not any(f["severity"] == "error" for f in flags),
            "validation_flags": flags
        }

    @staticmethod
    def _parse_float(val: Any) -> float | None:
        if val is None:
            return None
        try:
            clean_str = re.sub(r"[^\d.]", "", str(val))
            return float(clean_str)
        except ValueError:
            return None