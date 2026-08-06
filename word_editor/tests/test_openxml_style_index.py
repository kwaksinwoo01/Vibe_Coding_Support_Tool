from pathlib import Path
import zipfile

from word_editor.infrastructure.openxml_style_index import OpenXmlStyleIndexReader


def write_styles(path: Path, styles: list[tuple[str, str, str]]) -> None:
    body = "".join(
        f'<w:style w:type="{style_type}" w:styleId="{style_id}">'
        f'<w:name w:val="{name}"/>'
        f'<w:rPr><w:b w:val="{bold}"/></w:rPr>'
        f'</w:style>'
        for style_id, name, bold, style_type in (
            (item[0], item[1], item[2], "paragraph") for item in styles
        )
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main">'
        + body
        + '</w:styles>'
    )
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("word/styles.xml", xml)


def test_compare_reports_only_changed_added_removed_styles(tmp_path: Path) -> None:
    before = tmp_path / "before.docx"
    after = tmp_path / "after.docx"
    write_styles(
        before,
        [
            ("Normal", "표준", "0"),
            ("Body", "SOP_본문", "0"),
            ("Old", "SOP_구형", "0"),
        ],
    )
    write_styles(
        after,
        [
            ("Normal", "표준", "0"),
            ("Body", "SOP_본문", "1"),
            ("New", "SOP_신규", "0"),
        ],
    )

    difference = OpenXmlStyleIndexReader().compare(before, after)

    assert difference.changed == ("SOP_본문",)
    assert difference.added == ("SOP_신규",)
    assert difference.removed == ("SOP_구형",)
