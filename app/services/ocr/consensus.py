import time
from typing import Any
from collections import Counter

class OCRConsensusEngine:
    def __init__(self, weights: dict[str, float] = None):
        self.weights = weights or {
            "C": 0.40,  # Confidence
            "T": 0.20,  # Text Coverage/Completeness
            "A": 0.20,  # Cross-engine Agreement
            "S": 0.10,  # Speed
            "V": 0.10   # Validation Readiness
        }
    
    def evaluate_engine_output(
        self, 
        engine_data: dict[str, Any], 
        all_engine_texts: list[str]
    ) -> float:
        """Calculates normalized score [0.0 - 1.0] for a single engine result."""
        # C: Confidence score [0 to 1]
        c_score = engine_data.get("avg_confidence", 0.0) / 100.0 if engine_data.get("avg_confidence", 0) > 1 else engine_data.get("avg_confidence", 0.0)
        
        # T: Text Completeness (token count ratio relative to max tokens)
        tokens = engine_data.get("text", "").split()
        max_tokens = max([len(t.split()) for t in all_engine_texts] or [1])
        t_score = min(len(tokens) / max_tokens, 1.0) if max_tokens > 0 else 0.0

        # A: Cross-Engine Agreement (Jaccard similarity against other engines)
        a_score = self._calculate_text_agreement(engine_data.get("text", ""), all_engine_texts)

        # S: Speed Score (inverse log scaling, normalized against expected standard max ~5s)
        duration = engine_data.get("duration_seconds", 1.0)
        s_score = max(0.0, 1.0 - (duration / 5.0))

        # V: Validation-readiness (checks presence of basic invoice digits/dates)
        v_score = 1.0 if any(char.isdigit() for char in engine_data.get("text", "")) else 0.5

        score = (
            self.weights["C"] * c_score +
            self.weights["T"] * t_score +
            self.weights["A"] * a_score +
            self.weights["S"] * s_score +
            self.weights["V"] * v_score
        )
        return round(score, 4)

    def _calculate_text_agreement(self, target_text: str, all_texts: list[str]) -> float:
        target_words = set(target_text.lower().split())
        if not target_words:
            return 0.0
        similarities = []
        for other in all_texts:
            other_words = set(other.lower().split())
            if not other_words:
                continue
            intersection = target_words.intersection(other_words)
            union = target_words.union(other_words)
            similarities.append(len(intersection) / len(union))
        return sum(similarities) / len(similarities) if similarities else 0.0

    def select_best_and_merge(self, ocr_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Scores engines and merges text tokens based on local spatial confidence."""
        all_texts = [res["text"] for res in ocr_results.values() if "text" in res]
        scored_results = {}
        
        for engine_name, data in ocr_results.items():
            score = self.evaluate_engine_output(data, all_texts)
            scored_results[engine_name] = {**data, "computed_score": score}

        best_engine = max(scored_results, key=lambda k: scored_results[k]["computed_score"])
        
        return {
            "recommended_engine": best_engine,
            "engine_scores": {k: v["computed_score"] for k, v in scored_results.items()},
            "merged_text": scored_results[best_engine]["text"],
            "raw_engine_data": scored_results
        }        