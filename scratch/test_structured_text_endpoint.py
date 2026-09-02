import sys
import os
import uuid
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import SessionLocal, Base, engine as db_engine
from app.models.document_model import Document, DocumentPage, StatusEnum
from app.models.ocr_model import OCREngineResultModel, OCRBlockModel, OCRWordModel

# Ensure all tables exist in database
Base.metadata.create_all(bind=db_engine)

client = TestClient(app)

def seed_test_data():
    db = SessionLocal()
    
    # 1. Create Document & Page
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="test_invoice.pdf",
        file_path="/tmp/test_invoice.pdf",
        file_type="application/pdf",
        status=StatusEnum.COMPLETED,
        page_count=1,
        ocr_results={
            "pages": [{
                "recommended_engine": "paddle",
                "engine_scores": {"tesseract": 0.85, "easyocr": 0.88, "paddle": 0.95},
                "merged_text": "INVOICE # 10024 TOTAL $150.00"
            }]
        }
    )
    db.add(doc)
    db.flush()

    page_id = str(uuid.uuid4())
    page = DocumentPage(
        id=page_id,
        document_id=doc_id,
        page_number=1,
        image_path="/tmp/test_page1.png",
        width=800,
        height=1000,
        quality_score=0.92
    )
    db.add(page)
    db.flush()

    # 2. Add OCR Engine Results for Tesseract, EasyOCR, PaddleOCR
    engines_data = [
        ("tesseract", 0.91, 350.0, [
            ("Block 1", 0.95, 50, 50, 400, 100, [
                ("INVOICE", 0.99, 50, 50, 150, 80),
                ("#", 0.98, 160, 50, 180, 80),
                ("10024", 0.97, 190, 50, 280, 80),
            ]),
            ("Block 2", 0.90, 50, 120, 400, 170, [
                ("TOTAL", 0.95, 50, 120, 150, 160),
                ("$150.00", 0.92, 160, 120, 260, 160),
            ])
        ]),
        ("paddle", 0.96, 210.0, [
            ("Block 1", 0.98, 52, 48, 398, 102, [
                ("INVOICE", 0.99, 52, 48, 152, 82),
                ("#", 0.99, 162, 48, 182, 82),
                ("10024", 0.98, 192, 48, 282, 82),
            ]),
            ("Block 2", 0.95, 52, 118, 398, 168, [
                ("TOTAL", 0.97, 52, 118, 152, 158),
                ("$150.00", 0.96, 162, 118, 262, 158),
            ])
        ])
    ]

    for eng_name, avg_conf, time_ms, blocks in engines_data:
        eng_row = OCREngineResultModel(
            page_id=page_id,
            engine_name=eng_name,
            raw_text=" ".join([b[0] for b in blocks]),
            average_confidence=avg_conf,
            execution_time_ms=time_ms,
            status="SUCCESS"
        )
        db.add(eng_row)
        db.flush()

        for b_text, b_conf, x_min, y_min, x_max, y_max, words in blocks:
            b_row = OCRBlockModel(
                engine_result_id=eng_row.id,
                text=b_text,
                confidence=b_conf,
                x_min=x_min,
                y_min=y_min,
                x_max=x_max,
                y_max=y_max
            )
            db.add(b_row)
            db.flush()

            for w_text, w_conf, wx0, wy0, wx1, wy1 in words:
                w_row = OCRWordModel(
                    block_id=b_row.id,
                    text=w_text,
                    confidence=w_conf,
                    is_low_confidence=w_conf < 0.60,
                    x_min=wx0,
                    y_min=wy0,
                    x_max=wx1,
                    y_max=wy1
                )
                db.add(w_row)

    db.commit()
    db.close()
    return doc_id

def cleanup_test_data(doc_id):
    db = SessionLocal()
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        db.delete(doc)
        db.commit()
    db.close()

def test_structured_text_endpoint():
    print("Seeding database test data...")
    doc_id = seed_test_data()

    try:
        print(f"\n1. Testing GET /api/v1/ocr/{doc_id}/structured-text (All engines, Word granularity)")
        res = client.get(f"/api/v1/ocr/{doc_id}/structured-text?page_number=1")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["status"] == "success"
        assert data["document_id"] == doc_id
        assert data["page_number"] == 1
        assert "tesseract" in data["engines"]
        assert "paddle" in data["engines"]
        assert "tesseract" in data["engine_boxes"]
        assert "paddle" in data["engine_boxes"]
        
        # Check bounding box coordinates in SVG engine_boxes
        tess_boxes = data["engine_boxes"]["tesseract"]
        assert len(tess_boxes) == 5, f"Expected 5 word boxes for tesseract, got {len(tess_boxes)}"
        assert tess_boxes[0]["text"] == "INVOICE"
        assert tess_boxes[0]["x0"] == 50
        assert tess_boxes[0]["y0"] == 50
        assert tess_boxes[0]["x1"] == 150
        assert tess_boxes[0]["y1"] == 80
        print("   ✓ Passed: All engines returning correct word tokens & SVG bounding box coordinates.")

        print("\n2. Testing GET /api/v1/ocr/{doc_id}/structured-text with Line Granularity (Spatial Clustering)")
        res_line = client.get(f"/api/v1/ocr/{doc_id}/structured-text?page_number=1&granularity=line")
        assert res_line.status_code == 200
        data_line = res_line.json()
        tess_lines = data_line["engines"]["tesseract"]["structured_lines"]
        assert len(tess_lines) == 2, f"Expected 2 clustered lines, got {len(tess_lines)}"
        assert tess_lines[0]["text"] == "INVOICE # 10024"
        assert tess_lines[1]["text"] == "TOTAL $150.00"
        print("   ✓ Passed: Spatial line clustering correctly grouped words into lines using bounding boxes.")

        print("\n3. Testing GET /api/v1/ocr/{doc_id}/structured-text with Engine Filter (paddle)")
        res_pad = client.get(f"/api/v1/ocr/{doc_id}/structured-text?page_number=1&engine=paddle")
        assert res_pad.status_code == 200
        data_pad = res_pad.json()
        assert list(data_pad["engines"].keys()) == ["paddle"]
        assert data_pad["engines"]["paddle"]["average_confidence"] == 0.96
        print("   ✓ Passed: Engine filtering working as expected.")

        print("\n4. Testing GET /api/v1/ocr/documents/{doc_id}/structured-text (Alias Path)")
        res_alias = client.get(f"/api/v1/ocr/documents/{doc_id}/structured-text?page_number=1")
        assert res_alias.status_code == 200
        print("   ✓ Passed: Alias route /documents/{document_id}/structured-text verified.")

        print("\nAll structured text endpoint tests passed successfully!")

    finally:
        cleanup_test_data(doc_id)

if __name__ == "__main__":
    test_structured_text_endpoint()
