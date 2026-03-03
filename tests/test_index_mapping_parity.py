import sys
import os

# Ensure project root on path
sys.path.append(os.getcwd())

from scripts.index_mapping_parity import compare_mappings


def test_compare_identical_mappings():
    a = {
        "mappings": {
            "properties": {
                "title": {"type": "text"},
                "created_at": {"type": "date"}
            }
        }
    }
    b = {
        "my_index": {
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "created_at": {"type": "date"}
                }
            }
        }
    }

    res = compare_mappings(a, b)
    assert res["equal"] is True
    assert res["differences"] == {}


def test_compare_different_property_type():
    left = {"mappings": {"properties": {"count": {"type": "integer"}}}}
    right = {"mappings": {"properties": {"count": {"type": "long"}}}}

    res = compare_mappings(left, right)
    assert res["equal"] is False
    # We expect a difference reported under the top-level mapping key(s)
    assert "properties" in res["differences"] or res["differences"]
