# Import formatter from goat.py
import importlib.util
import sys
from pathlib import Path

GOAT_PATH = Path(__file__).resolve().parents[1] / "goat.py"
spec = importlib.util.spec_from_file_location("goat_module", GOAT_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

SAMPLE_JSON = {
    "status": {"success": True},
    "report": {
        "status": {"success": True},
        "report": {
            "histogram": {
                "histograms": {
                    "buckets": [
                        2, 3.7306715, 6.958955, 12.980788, 24.213528,
                        45.166359, 84.250425, 157.15533, 293.14746,
                        546.81844, 1020
                    ],
                    "allValues": [
                        18523, 125304, 481016, 561095, 366611,
                        266440, 29735, 10105, 28, 58, 1
                    ],
                    "valueType": "integer",
                    "zDomain": [1, 561095],
                    "params": {},
                    "fields": ["chromosome_number"],
                    "xLabel": "chromosome_number"
                },
                "field": "chromosome_number",
                "summary": "value",
                "scale": "log2",
                "query": "tax_tree%28Magnoliopsida%29%20AND%20tax_rank%28species%29",
                "stats": {
                    "count": 1858916,
                    "min": 2,
                    "max": 1020,
                    "avg": 26.1936,
                    "sum": 48691704
                },
                "type": "short",
                "domain": [2, 1020],
                "tickCount": 11,
                "showOther": False,
                "bounds": {},
                "xQuery": {"result": "taxon"},
                "x": 1858916
            },
            "name": "histogram"
        }
    }
}


def main():
    # Pass the full sample JSON to ensure both parsing paths work
    text = mod.format_histogram_report(SAMPLE_JSON)
    print(text)


if __name__ == "__main__":
    main()
