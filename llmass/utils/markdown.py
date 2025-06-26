from pathlib import Path
from typing import Any, Union
import re


class MdParser:
    subparsers = {
        "table": "_parse_table",
        "dated_notes": "_parse_dated_notes",
    }

    def __init__(
        self,
        path_to_md: Union[str, Path],
        schema: list[dict[str, Any]]
    ) -> None:
       self.path_to_md = path_to_md
       self.schema = schema

    def parse(self) -> dict[str, Any]:
        content = {}
        with open(self.path_to_md, "r") as f:
            block_name = None
            lines_buf = []
            for l in f.readlines():
                if l.strip() == "":  # empty line
                    continue

                if starts_with_n_hashes_exactly(l, 1):  # title, skip it
                    continue

                if starts_with_n_hashes_exactly(l, 2):  # new content block
                    if block_name:  # process all the previous lines
                        subparser = self.subparsers[self.schema[block_name]]
                        content[block_name] = getattr(self, subparser)(lines_buf)
                        lines_buf = []
                        
                    block_name = parse_name_from_header(
                        raw_header=l, 
                        replace_whitespaces_with_underscores=True,
                    )
                else:  # old content block
                    lines_buf.append(l)
                
            # process the last content block
            subparser = self.subparsers[self.schema[block_name]]
            content[block_name] = getattr(self, subparser)(lines_buf)

        return content

    def _parse_table(self, lines: list[str]) -> list[dict[str, str]]:
        res = []

        # First line defines the columns
        # Second line is merely a separator
        columns = parse_values_from_table_row(lines[0])

        # All the next lines are the actual content
        for row in lines[2:]:
            vals = parse_values_from_table_row(row)
            if len(columns) != len (vals):
                raise ValueError(f"Markdown table is broken at line\n{row}")

            res.append({})
            for col, val in zip(columns, vals):
                res[-1][col] = val
        
        return res

    def _parse_dated_notes(self, lines: list[str]) -> dict[str, str]:
        res = {}
        lines_buf = []
        date = None

        for l in lines:
            if starts_with_n_hashes_exactly(l, 3):  # new date
                if date:  # process all the previous lines
                    res[date] = "\n".join(lines_buf)
                    lines_buf = []

                date = parse_name_from_header(l)
            else:
                lines_buf.append(l)
            
        if date:
            res[date] = "\n".join(lines_buf)

        return res


def parse_name_from_header(
    raw_header: str,
    replace_whitespaces_with_underscores: bool = False
) -> str:
    res = raw_header.strip(" #\t\n").lower()

    if replace_whitespaces_with_underscores:
        res = re.sub(r"\s+", "_", res)

    return res


def parse_values_from_table_row(raw_row: str) -> str:
    return list(map(lambda s: s.strip(), raw_row.split("|")[1:-1:]))



def starts_with_n_hashes_exactly(s: str, n: int) -> bool:
    return re.match(r"^\s*" + "#"*n + r"(?!\#)", s)

