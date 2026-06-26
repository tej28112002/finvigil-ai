from pydantic import BaseModel


class CsvImportResponse(BaseModel):
    total_rows: int
    imported: int
    skipped: int
    errors: list[str]
