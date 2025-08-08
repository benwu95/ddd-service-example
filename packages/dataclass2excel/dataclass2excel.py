import dataclasses
from io import BytesIO
from typing import Iterable

from openpyxl import Workbook
from openpyxl.cell import Cell


def create_xlsx(title: str, dc_type: type, dc_list: list, output_fields: list[str] | None = None) -> BytesIO:
    """
    Creates an excel file from a list of dataclasses.

    :param title: The title of the excel file.

    :param dc_type: The type of the dataclasses, if field has metadata['alias'], then output will use this instead of field.name.

    :param dc_list: The list of dataclasses.

    :param output_fields: The name of fields to output, default is None. If None, all fields will be output.

    :return: The excel file.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = title

    if output_fields is not None:
        fields_mapping = {f.name: f.metadata.get("alias", f.name) for f in dataclasses.fields(dc_type)}
        fields = [(f, fields_mapping.get(f, f)) for f in output_fields]
    else:
        fields = [(f.name, f.metadata.get("alias", f.name)) for f in dataclasses.fields(dc_type)]

    ws.append([f[1] for f in fields])

    for dc in dc_list:
        ws.append([getattr(dc, f[0], "#N/A#") for f in fields])

    virtual_workbook = BytesIO()
    wb.save(virtual_workbook)
    wb.close()
    virtual_workbook.seek(0)
    return virtual_workbook


def get_field_names(dc_type: type) -> list[str]:
    """
    Returns a list of field names of the dataclass.

    :param dc_type: The type of the dataclass, if field has metadata['alias'], then output will use this instead of field.name.

    :return: A list of field names.
    """
    return [f.metadata.get("alias", f.name) for f in dataclasses.fields(dc_type)]


def parse_sheet_header_row(header_row: Iterable[Cell | str], dc_type: type) -> dict[int, str]:
    """
    Parses the sheet header row and returns a dictionary of header row index and field names.

    :param header_row: The row of the sheet header.

    :param dc_type: The type of the dataclasses, if field has metadata['alias'], then function will use this to parse instead of field.name.

    :return: A dictionary of header row index and field names.
    """
    fields_mapping = {f.metadata.get("alias", f.name): f.name for f in dataclasses.fields(dc_type)}
    result = {}
    for i, header in enumerate(header_row):
        if isinstance(header, Cell):
            header = header.value
        header = str(header or "").strip()
        if header in fields_mapping:
            result[i] = fields_mapping[header]
    return result
