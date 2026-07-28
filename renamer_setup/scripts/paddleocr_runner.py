from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import traceback
from typing import Any


def _collect_recognized_text(value: Any, target: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "rec_texts" and isinstance(child, list):
                target.extend(str(item).strip() for item in child if str(item).strip())
            else:
                _collect_recognized_text(child, target)
    elif isinstance(value, list):
        for child in value:
            _collect_recognized_text(child, target)


def _write_result(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", default="korean")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("inputs", nargs="*")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        from paddleocr import PaddleOCR

        pipeline = PaddleOCR(
            lang=args.language,
            ocr_version="PP-OCRv5",
            engine="onnxruntime",
            device="cpu",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        if args.health:
            _write_result(args.output, {"status": "ok", "engine": "onnxruntime"})
            return 0
        if not args.inputs:
            raise ValueError("at least one input image is required")

        recognized: list[str] = []
        for prediction in pipeline.predict([str(Path(item)) for item in args.inputs]):
            _collect_recognized_text(prediction.json, recognized)
        _write_result(
            args.output,
            {
                "status": "ok",
                "engine": "onnxruntime",
                "text": "\n".join(recognized),
            },
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - file result is the process contract
        _write_result(
            args.output,
            {
                "status": "error",
                "error": f"{type(exc).__name__}:{exc}",
                "traceback": traceback.format_exc(),
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
