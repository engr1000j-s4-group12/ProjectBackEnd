#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "building_map.json"
DEFAULT_OUTPUT = ROOT / "data" / "building_map_nodes.xlsx"

NODE_HEADERS = [
    "id",
    "floor",
    "kind",
    "room_number",
    "name_zh",
    "name_en",
    "aliases",
    "remark",
    "x_m",
    "y_m",
    "x_ratio",
    "y_ratio",
    "visual_landmark_aliases",
    "visual_landmark_weight",
    "source",
    "visual_landmarks_json",
]

EDGE_HEADERS = [
    "from",
    "to",
    "distance_m",
    "bidirectional",
    "accessible",
    "forward_zh",
    "forward_en",
    "reverse_zh",
    "reverse_en",
    "instructions_json",
]

METADATA_HEADERS = ["key", "value_json"]


def _join(values: list[Any]) -> str:
    return "|".join(str(value) for value in values if value is not None and str(value))


def _json(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _col_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _sheet_xml(rows: list[list[Any]], freeze_header: bool = True) -> str:
    xml_rows: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells: list[str] = []
        for column_index, value in enumerate(row):
            if value is None:
                value = ""
            ref = f"{_col_name(column_index)}{row_index}"
            escaped = html.escape(str(value), quote=False)
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escaped}</t></is></c>')
        xml_rows.append(f'<row r="{row_index}">' + "".join(cells) + "</row>")

    last_column = _col_name(max(len(rows[0]) - 1, 0)) if rows else "A"
    sheet_view = (
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        "</sheetView></sheetViews>"
        if freeze_header
        else ""
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  {sheet_view}
  <sheetFormatPr defaultRowHeight="15"/>
  <cols>
    <col min="1" max="{len(rows[0]) if rows else 1}" width="22" customWidth="1"/>
  </cols>
  <sheetData>
{chr(10).join(xml_rows)}
  </sheetData>
  <autoFilter ref="A1:{last_column}1"/>
</worksheet>
'''


def _write_xlsx(path: Path, sheets: list[tuple[str, list[list[Any]]]]) -> None:
    sheet_overrides = "\n".join(
        f'  <Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index, _ in enumerate(sheets, start=1)
    )
    workbook_sheets = "\n".join(
        f'    <sheet name="{html.escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _) in enumerate(sheets, start=1)
    )
    relationships = "\n".join(
        f'  <Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index, _ in enumerate(sheets, start=1)
    )
    styles_id = len(sheets) + 1

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{sheet_overrides}
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>
''',
        )
        archive.writestr(
            "_rels/.rels",
            '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
''',
        )
        archive.writestr(
            "xl/workbook.xml",
            f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
{workbook_sheets}
  </sheets>
</workbook>
''',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{relationships}
  <Relationship Id="rId{styles_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
''',
        )
        archive.writestr(
            "xl/styles.xml",
            '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border/></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
</styleSheet>
''',
        )
        for index, (_, rows) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet_xml(rows))


def node_row(node: dict[str, Any]) -> list[Any]:
    position = node.get("position", {})
    landmarks = node.get("visual_landmarks", [])
    first_landmark = landmarks[0] if landmarks else {}
    return [
        node.get("id", ""),
        node.get("floor", ""),
        node.get("kind", ""),
        node.get("room_number", ""),
        node.get("name_zh", ""),
        node.get("name_en", ""),
        _join(node.get("aliases", [])),
        node.get("remark", ""),
        position.get("x_m", ""),
        position.get("y_m", ""),
        position.get("x_ratio", ""),
        position.get("y_ratio", ""),
        _join(first_landmark.get("aliases", [])),
        first_landmark.get("weight", ""),
        node.get("source", ""),
        _json(landmarks),
    ]


def edge_row(edge: dict[str, Any]) -> list[Any]:
    instructions = edge.get("instructions", {})
    forward = instructions.get("forward", {}) if isinstance(instructions, dict) else {}
    reverse = instructions.get("reverse", {}) if isinstance(instructions, dict) else {}
    return [
        edge.get("from", ""),
        edge.get("to", ""),
        edge.get("distance_m", ""),
        edge.get("bidirectional", True),
        edge.get("accessible", True),
        forward.get("zh", ""),
        forward.get("en", ""),
        reverse.get("zh", ""),
        reverse.get("en", ""),
        _json(instructions),
    ]


def metadata_rows(data: dict[str, Any]) -> list[list[Any]]:
    return [
        METADATA_HEADERS,
        ["schema_version", _json(data.get("schema_version", 1))],
        ["building", _json(data.get("building", {}))],
        ["floor_plan", _json(data.get("floor_plan", {}))],
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从 data/building_map.json 导出可编辑的 Excel 地图表。"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with args.input.open(encoding="utf-8") as file:
        data = json.load(file)

    sheets = [
        ("nodes", [NODE_HEADERS] + [node_row(node) for node in data["nodes"]]),
        ("edges", [EDGE_HEADERS] + [edge_row(edge) for edge in data["edges"]]),
        ("metadata", metadata_rows(data)),
    ]
    _write_xlsx(args.output, sheets)
    print(
        f"wrote {len(data['nodes'])} nodes and {len(data['edges'])} edges to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
