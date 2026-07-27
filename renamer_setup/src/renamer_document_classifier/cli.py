from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
import traceback

from .config import (
    DEFAULT_KNOWN_NAMES,
    installation_root,
    load_user_config,
    log_path,
    save_user_config,
)
from .extractors import ExtractionLimits, health_report
from .logging_utils import clear_log
from .service import inspect_document


def _configure_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def _write_error_trace(command: str, exc: BaseException) -> Path | None:
    try:
        path = installation_root() / "logs" / "classifier_error.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8-sig")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = (
            "\n[ERROR]\n"
            f"time={timestamp}\n"
            f"command={command}\n"
            f"exception={type(exc).__name__}:{exc}\n"
            f"traceback=\n{traceback.format_exc()}"
            "[/ERROR]\n"
        )
        with path.open("a", encoding="utf-8") as stream:
            stream.write(payload)
        return path
    except OSError:
        return None


def _split_names(value: str) -> list[str]:
    normalized = value.replace(";", ",").replace("\n", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _configure_non_interactive(default_name: str, known_names: str) -> int:
    config = save_user_config(default_name, _split_names(known_names))
    print("STATUS=OK")
    print(f"DEFAULT_NAME={config.default_name}")
    print(f"KNOWN_NAMES={','.join(config.known_names)}")
    return 0


def _configure_gui() -> int:
    import tkinter as tk
    from tkinter import messagebox, ttk

    current = load_user_config()
    root = tk.Tk()
    root.title("ReNamer 문서 분류기 사용자 설정")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=18)
    frame.grid(row=0, column=0, sticky="nsew")

    ttk.Label(frame, text="기본 사용자 이름").grid(row=0, column=0, sticky="w")
    default_var = tk.StringVar(value=current.default_name)
    default_entry = ttk.Entry(frame, width=42, textvariable=default_var)
    default_entry.grid(row=1, column=0, sticky="ew", pady=(4, 12))

    ttk.Label(
        frame,
        text="파일명에서 인식할 이름 목록 (쉼표로 구분)",
    ).grid(row=2, column=0, sticky="w")
    names_var = tk.StringVar(value=", ".join(current.known_names))
    names_entry = ttk.Entry(frame, width=62, textvariable=names_var)
    names_entry.grid(row=3, column=0, sticky="ew", pady=(4, 8))

    ttk.Label(
        frame,
        text="파일명에서 이름을 찾지 못하면 기본 사용자 이름을 사용합니다.",
    ).grid(row=4, column=0, sticky="w", pady=(0, 14))

    button_frame = ttk.Frame(frame)
    button_frame.grid(row=5, column=0, sticky="e")

    def save_and_close() -> None:
        try:
            saved = save_user_config(
                default_var.get(),
                _split_names(names_var.get()),
            )
        except ValueError as exc:
            messagebox.showerror("입력 오류", str(exc), parent=root)
            default_entry.focus_set()
            return
        except OSError as exc:
            messagebox.showerror(
                "저장 실패",
                f"설정을 저장하지 못했습니다.\n\n{exc}",
                parent=root,
            )
            return

        messagebox.showinfo(
            "저장 완료",
            f"기본 사용자 이름: {saved.default_name}\n\n"
            "ReNamer 스크립트를 수정하지 않아도 다음 실행부터 적용됩니다.",
            parent=root,
        )
        root.destroy()

    ttk.Button(button_frame, text="취소", command=root.destroy).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(button_frame, text="저장", command=save_and_close).grid(row=0, column=1)

    default_entry.focus_set()
    root.mainloop()
    return 0


def _open_path(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8-sig")

    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="classifier.exe")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="문서 내용을 분석합니다.")
    inspect_parser.add_argument("--input", required=True)
    inspect_parser.add_argument("--original-name")
    inspect_parser.add_argument("--max-pages", type=int, default=2)
    inspect_parser.add_argument("--max-sheets", type=int, default=3)
    inspect_parser.add_argument("--max-rows", type=int, default=200)
    inspect_parser.add_argument("--max-columns", type=int, default=50)
    inspect_parser.add_argument("--max-characters", type=int, default=50_000)
    inspect_parser.add_argument("--ocr-dpi", type=int, default=220)
    inspect_parser.add_argument("--timeout", type=int, default=120)

    configure_parser = subparsers.add_parser("configure", help="사용자 이름 설정을 변경합니다.")
    configure_parser.add_argument("--default-name")
    configure_parser.add_argument(
        "--known-names",
        default=", ".join(DEFAULT_KNOWN_NAMES),
    )

    subparsers.add_parser("open-log", help="classification.log를 엽니다.")
    subparsers.add_parser("clear-log", help="classification.log를 초기화합니다.")
    subparsers.add_parser("health", help="외부 도구 상태를 확인합니다.")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_streams()
    args = build_parser().parse_args(argv)

    if args.command == "configure":
        if args.default_name:
            return _configure_non_interactive(args.default_name, args.known_names)
        return _configure_gui()

    if args.command == "open-log":
        _open_path(log_path())
        return 0

    if args.command == "clear-log":
        path = clear_log()
        print("STATUS=OK")
        print(f"LOG_PATH={path}")
        return 0

    if args.command == "health":
        print("STATUS=OK")
        for key, value in health_report().items():
            print(f"{key.upper()}={value}")
        return 0

    if args.command == "inspect":
        source = Path(args.input)
        if not source.is_file():
            print("STATUS=ERROR")
            print("ERROR=INPUT_NOT_FOUND")
            return 2

        limits = ExtractionLimits(
            max_pages=max(1, args.max_pages),
            max_sheets=max(1, args.max_sheets),
            max_rows=max(1, args.max_rows),
            max_columns=max(1, args.max_columns),
            max_characters=max(1_000, args.max_characters),
            ocr_dpi=max(100, args.ocr_dpi),
            timeout_seconds=max(10, args.timeout),
        )

        try:
            result = inspect_document(
                source,
                original_name=args.original_name,
                limits=limits,
            )
        except Exception as exc:  # noqa: BLE001 - stable CLI boundary
            trace_path = _write_error_trace("inspect", exc)
            print("STATUS=ERROR")
            print(f"ERROR={type(exc).__name__}:{exc}")
            if trace_path is not None:
                print(f"TRACE_LOG={trace_path}")
            return 1

        classification = result.classification
        extraction = result.extraction
        print("STATUS=OK")
        print(f"KIND={classification.kind.value}")
        print(f"PERSON={result.person_name}")
        print(f"QUOTE_SCORE={classification.quote_score}")
        print(f"TRANSACTION_SCORE={classification.transaction_score}")
        print(f"REASON={classification.reason}")
        print(f"METHODS={' | '.join(extraction.methods) or 'none'}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
