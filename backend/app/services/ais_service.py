from decimal import Decimal
from uuid import UUID

from app.core.tax_utils import get_ay_date_range
from app.repositories.ais_line_repository import AisLineRepository
from app.repositories.ais_match_result_repository import AisMatchResultRepository
from app.repositories.ais_upload_repository import AisUploadRepository
from app.services.ais_matching_service import AisMatchingService
from app.services.ais_parser_service import AisParserService

ZERO = Decimal("0")


class AisService:
    """
    Orchestrates AIS upload versioning (FR-AIS-02), parsing (FR-AIS-01),
    the auto-match engine (FR-AIS-03), and mismatch resolution (FR-AIS-04).
    """

    def __init__(
        self,
        ais_upload_repository: AisUploadRepository,
        ais_line_repository: AisLineRepository,
        ais_match_result_repository: AisMatchResultRepository,
        ais_parser_service: AisParserService,
        ais_matching_service: AisMatchingService,
    ):
        self.ais_upload_repository = ais_upload_repository
        self.ais_line_repository = ais_line_repository
        self.ais_match_result_repository = ais_match_result_repository
        self.ais_parser_service = ais_parser_service
        self.ais_matching_service = ais_matching_service

    def upload(
        self,
        user_id: UUID,
        assessment_year: str,
        file_content: bytes,
        filename: str,
    ) -> dict:
        lower = filename.lower()
        if lower.endswith(".json"):
            parsed_lines = self.ais_parser_service.parse_json(file_content)
            # JSONB storage requires JSON-serializable values — Decimal
            # isn't, so amounts are stored as strings (same convention as
            # every other JSONB snapshot in this app, e.g. ReplayRun).
            raw_json = {
                "source_filename": filename,
                "lines": [
                    {
                        **line,
                        "reported_amount": (
                            str(line["reported_amount"])
                            if line["reported_amount"] is not None
                            else None
                        ),
                    }
                    for line in parsed_lines
                ],
            }
        elif lower.endswith(".csv"):
            parsed_lines = self.ais_parser_service.parse_csv(file_content)
            raw_json = None
        else:
            raise ValueError(
                "Unsupported AIS file format. Please upload a .json or .csv file."
            )

        if not parsed_lines:
            raise ValueError("AIS file contains no entries to import.")

        next_version = (
            self.ais_upload_repository.get_max_version(
                user_id=user_id, assessment_year=assessment_year
            )
            + 1
        )
        self.ais_upload_repository.clear_latest_flag(
            user_id=user_id, assessment_year=assessment_year
        )
        upload = self.ais_upload_repository.create_upload(
            user_id=user_id,
            assessment_year=assessment_year,
            version=next_version,
            is_latest=True,
            raw_json=raw_json,
        )

        lines = self.ais_line_repository.bulk_create(
            user_id=user_id,
            ais_upload_id=upload.id,
            lines=parsed_lines,
        )

        ay_start, ay_end = get_ay_date_range(assessment_year)
        match_results = self.ais_matching_service.run_match(
            user_id=user_id,
            assessment_year=assessment_year,
            lines=lines,
            ay_start=ay_start,
            ay_end=ay_end,
        )
        self.ais_match_result_repository.bulk_create(
            user_id=user_id,
            ais_upload_id=upload.id,
            results=match_results,
        )

        return self.get_upload_detail(user_id=user_id, upload_id=upload.id)

    def get_upload_detail(self, user_id: UUID, upload_id: UUID) -> dict | None:
        upload = self.ais_upload_repository.get_by_id_and_user(upload_id, user_id)
        if not upload:
            return None

        lines = self.ais_line_repository.get_by_upload(upload_id, user_id)
        match_results = self.ais_match_result_repository.get_by_upload(
            upload_id, user_id
        )
        match_by_line = {m.ais_line_id: m for m in match_results}

        line_rows = [
            {"line": line, "match_result": match_by_line.get(line.id)}
            for line in lines
        ]

        return {
            "summary": self._build_summary(upload, match_results),
            "lines": line_rows,
        }

    def get_upload_history(self, user_id: UUID, assessment_year: str) -> dict:
        uploads = self.ais_upload_repository.get_by_user_and_ay(
            user_id, assessment_year
        )
        versions = []
        for upload in uploads:
            match_results = self.ais_match_result_repository.get_by_upload(
                upload.id, user_id
            )
            versions.append(self._build_summary(upload, match_results))
        return {"assessment_year": assessment_year, "versions": versions}

    def get_mismatches(self, user_id: UUID, upload_id: UUID) -> list | None:
        upload = self.ais_upload_repository.get_by_id_and_user(upload_id, user_id)
        if not upload:
            return None
        mismatches = self.ais_match_result_repository.get_mismatches_by_upload(
            upload_id, user_id
        )
        lines_by_id = {
            line.id: line
            for line in self.ais_line_repository.get_by_upload(upload_id, user_id)
        }
        return [
            {"line": lines_by_id[m.ais_line_id], "match_result": m}
            for m in mismatches
            if m.ais_line_id in lines_by_id
        ]

    def resolve_match_result(
        self,
        user_id: UUID,
        match_result_id: UUID,
        resolution_notes: str,
    ):
        match_result = self.ais_match_result_repository.get_by_id_and_user(
            match_result_id, user_id
        )
        if not match_result:
            return None
        return self.ais_match_result_repository.update_resolution(
            match_result, resolution_notes
        )

    def bulk_resolve_exact(self, user_id: UUID, upload_id: UUID) -> int | None:
        upload = self.ais_upload_repository.get_by_id_and_user(upload_id, user_id)
        if not upload:
            return None
        return self.ais_match_result_repository.bulk_resolve_exact_matches(
            ais_upload_id=upload_id,
            user_id=user_id,
            resolution_notes="Auto-confirmed exact match.",
        )

    def delete_upload(self, user_id: UUID, upload_id: UUID) -> bool:
        upload = self.ais_upload_repository.get_by_id_and_user(upload_id, user_id)
        if not upload:
            return False
        was_latest = upload.is_latest
        self.ais_upload_repository.soft_delete(upload)
        if was_latest:
            remaining = self.ais_upload_repository.get_by_user_and_ay(
                user_id, upload.assessment_year
            )
            if remaining:
                # get_by_user_and_ay orders newest-version-first.
                self.ais_upload_repository.promote_to_latest(remaining[0])
        return True

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _build_summary(upload, match_results: list) -> dict:
        total = len(match_results)
        matched = sum(1 for m in match_results if m.match_status == "matched")
        mismatch = sum(1 for m in match_results if m.match_status == "mismatch")
        unresolved = sum(1 for m in match_results if m.match_status == "unresolved")
        pct = (
            (Decimal(matched) / Decimal(total) * Decimal(100))
            if total > 0
            else ZERO
        )
        return {
            "upload": upload,
            "total_lines": total,
            "matched_count": matched,
            "mismatch_count": mismatch,
            "unresolved_count": unresolved,
            "match_percentage": pct.quantize(Decimal("0.01")),
        }
