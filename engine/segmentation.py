"""
SegmentationEngine
Groups contacts into logical segments (by Country, Company Size, Industry, Domain, Job Title)
and maintains historical performance matrices per segment for providers.
"""

from typing import Dict, List, Any, Tuple

class SegmentationEngine:
    @staticmethod
    def classify_contact(contact: Dict[str, Any]) -> str:
        """
        Returns a primary segment identifier for a contact.
        Default primary segment dimension: Country (or Country + Size if available).
        """
        country = contact.get("country", "").strip()
        size = contact.get("company_size", "").strip()

        if "United States" in country or country == "US" or country == "USA":
            c_code = "US"
        elif "United Kingdom" in country or country == "UK" or country == "GB":
            c_code = "UK"
        elif country in ["Germany", "France", "Netherlands", "Spain", "Italy", "Sweden", "EU"]:
            c_code = "EU"
        elif country in ["Singapore", "Australia", "India", "Japan", "APAC"]:
            c_code = "APAC"
        else:
            c_code = "Rest of World"

        if "Enterprise" in size:
            s_code = "Enterprise"
        elif "Mid-Market" in size:
            s_code = "Mid-Market"
        elif "SMB" in size:
            s_code = "SMB"
        else:
            s_code = "All"

        return f"{c_code} ({s_code})" if s_code != "All" else c_code

    @staticmethod
    def segment_contacts(contacts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Groups a list of contacts into segment buckets.
        """
        segments: Dict[str, List[Dict[str, Any]]] = {}
        for c in contacts:
            seg_key = SegmentationEngine.classify_contact(c)
            if seg_key not in segments:
                segments[seg_key] = []
            segments[seg_key].append(c)
        return segments

    @staticmethod
    def get_segment_stats(contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Returns breakdown of contact counts per segment.
        """
        segments = SegmentationEngine.segment_contacts(contacts)
        total = max(len(contacts), 1)
        result = []
        for seg_name, seg_list in sorted(segments.items(), key=lambda x: len(x[1]), reverse=True):
            count = len(seg_list)
            result.append({
                "segment": seg_name,
                "count": count,
                "percentage": round((count / total) * 100, 1),
                "contacts": seg_list
            })
        return result
