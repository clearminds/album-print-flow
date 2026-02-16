from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class IppBackendError(RuntimeError):
    pass


@dataclass
class IppCapabilities:
    media: list[str]
    media_type: list[str]
    print_quality: list[str]
    printer_name: str = ""
    borderless_zero_margins_supported: bool = False


def _import_pyipp():
    try:
        from pyipp import IPP  # type: ignore
        from pyipp.enums import IppOperation  # type: ignore
    except Exception as error:  # pragma: no cover - runtime dependency guard
        raise IppBackendError(
            "pyipp is not installed. Install with `pip install pyipp`."
        ) from error
    return IPP, IppOperation


def _as_list(value: object) -> list[str]:
    def normalize(item: object) -> str | None:
        if isinstance(item, str):
            return item
        if isinstance(item, bytes):
            try:
                return item.decode("utf-8", "ignore")
            except Exception:
                return None
        enum_value = getattr(item, "value", None)
        if enum_value is not None:
            if isinstance(enum_value, bytes):
                try:
                    return enum_value.decode("utf-8", "ignore")
                except Exception:
                    return None
            return str(enum_value)
        if isinstance(item, int | float | bool):
            return str(item)
        return None

    scalar = normalize(value)
    if scalar is not None:
        return [scalar]

    if isinstance(value, list | tuple | set):
        result: list[str] = []
        for item in value:
            normalized = normalize(item)
            if normalized is not None and normalized not in result:
                result.append(normalized)
        return result
    return []


def _extract_supported_values(
    payload: object, keys: tuple[str, ...], fallback_keys: tuple[str, ...] = ()
) -> list[str]:
    if isinstance(payload, list | tuple | set):
        for item in payload:
            nested_values = _extract_supported_values(item, keys, fallback_keys)
            if nested_values:
                return nested_values
        return []

    if not isinstance(payload, dict):
        object_dict = getattr(payload, "__dict__", None)
        if isinstance(object_dict, dict):
            return _extract_supported_values(object_dict, keys, fallback_keys)
        return []

    for key in keys + fallback_keys:
        if key in payload:
            values = _as_list(payload.get(key))
            if values:
                return values

    for value in payload.values():
        nested_values = _extract_supported_values(value, keys, fallback_keys)
        if nested_values:
            return nested_values

    return []


def _extract_first_value(payload: object, keys: tuple[str, ...]) -> object | None:
    if isinstance(payload, list | tuple | set):
        for item in payload:
            found = _extract_first_value(item, keys)
            if found is not None:
                return found
        return None

    if not isinstance(payload, dict):
        object_dict = getattr(payload, "__dict__", None)
        if isinstance(object_dict, dict):
            return _extract_first_value(object_dict, keys)
        return None

    for key in keys:
        if key in payload:
            return payload.get(key)

    for value in payload.values():
        found = _extract_first_value(value, keys)
        if found is not None:
            return found

    return None


def _as_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, int):
        return enum_value
    if isinstance(enum_value, str):
        try:
            return int(enum_value.strip())
        except ValueError:
            return None
    return None


def _extract_job_id(payload: object) -> int | None:
    found = _extract_first_value(payload, ("job-id",))
    if found is None:
        return None

    if isinstance(found, list | tuple | set):
        for item in found:
            value = _as_int(item)
            if value is not None:
                return value
        return None

    return _as_int(found)


def _job_state_name(payload: object) -> str:
    raw = _extract_first_value(payload, ("job-state",))
    if raw is None:
        return "unknown"

    if isinstance(raw, list | tuple | set):
        for item in raw:
            name = _job_state_name({"job-state": item})
            if name != "unknown":
                return name
        return "unknown"

    text = str(getattr(raw, "value", raw)).strip().lower().replace("_", "-")
    if text in {
        "pending",
        "pending-held",
        "processing",
        "processing-stopped",
        "canceled",
        "aborted",
        "completed",
    }:
        return text

    number = _as_int(raw)
    if number is None:
        return "unknown"

    mapping = {
        3: "pending",
        4: "pending-held",
        5: "processing",
        6: "processing-stopped",
        7: "canceled",
        8: "aborted",
        9: "completed",
    }
    return mapping.get(number, "unknown")


def _collect_job_entries(payload: object) -> list[dict[str, object]]:
    collected: list[dict[str, object]] = []

    def visit(node: object) -> None:
        if isinstance(node, list | tuple | set):
            for item in node:
                visit(item)
            return

        if not isinstance(node, dict):
            object_dict = getattr(node, "__dict__", None)
            if isinstance(object_dict, dict):
                visit(object_dict)
            return

        if "job-id" in node or "job-name" in node or "job-state" in node:
            collected.append(node)
        for value in node.values():
            visit(value)

    visit(payload)
    return collected


def _value_as_text(value: object) -> str:
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", "ignore")
        except Exception:
            return ""
    return str(getattr(value, "value", value))


def _extract_job_name(entry: dict[str, object]) -> str:
    raw = entry.get("job-name")
    if raw is None:
        return ""
    if isinstance(raw, list | tuple | set):
        for item in raw:
            text = _value_as_text(item).strip()
            if text:
                return text
        return ""
    return _value_as_text(raw).strip()


def _is_timeout_error(error: Exception) -> bool:
    if isinstance(error, TimeoutError | asyncio.TimeoutError):
        return True

    timeout_type_names = {
        "ReadTimeout",
        "ConnectTimeout",
        "TimeoutException",
        "TimeoutError",
    }
    if type(error).__name__ in timeout_type_names:
        return True

    text = str(error).lower()
    return "timed out" in text or "timeout" in text


def _is_borderless_media_name(value: str) -> bool:
    text = value.lower()
    keywords = (
        "borderless",
        "fullbleed",
        "full-bleed",
        "edge-to-edge",
        "edgetoedge",
    )
    return any(keyword in text for keyword in keywords)


def _choose_borderless_media(media: str, supported_media: list[str]) -> str:
    requested = media.strip()
    if not requested:
        return ""
    if not supported_media:
        return requested

    requested_lower = requested.lower()
    normalized = [(value, value.lower()) for value in supported_media if value]

    for original, lower in normalized:
        if lower == requested_lower:
            return original

    direct_candidates = [
        f"{requested}-borderless",
        f"{requested}.borderless",
        f"{requested}_borderless",
    ]
    for candidate in direct_candidates:
        candidate_lower = candidate.lower()
        for original, lower in normalized:
            if lower == candidate_lower:
                return original

    borderless_matches = [
        original
        for original, lower in normalized
        if requested_lower in lower and _is_borderless_media_name(lower)
    ]
    if borderless_matches:
        return borderless_matches[0]

    compact_requested = requested_lower.replace("_", "").replace("-", "")
    for original, lower in normalized:
        compact_supported = lower.replace("_", "").replace("-", "")
        if compact_requested in compact_supported and _is_borderless_media_name(
            compact_supported
        ):
            return original

    return requested


def get_ipp_capabilities(ipp_uri: str) -> IppCapabilities:
    if not ipp_uri.strip():
        return IppCapabilities([], [], [], "")

    IPP, IppOperation = _import_pyipp()

    async def _query() -> object:
        async with IPP(ipp_uri.strip()) as client:
            return await client.execute(
                IppOperation.GET_PRINTER_ATTRIBUTES,
                {
                    "operation-attributes-tag": {
                        "requested-attributes": [
                            "printer-name",
                            "printer-info",
                            "printer-make-and-model",
                            "media-supported",
                            "media-type-supported",
                            "print-quality-supported",
                            "output-mode-supported",
                            "media-top-margin-supported",
                            "media-left-margin-supported",
                            "media-right-margin-supported",
                            "media-bottom-margin-supported",
                        ]
                    }
                },
            )

    try:
        response = asyncio.run(_query())
    except Exception as error:
        raise IppBackendError(f"IPP capability query failed: {error}") from error

    media = _extract_supported_values(
        response,
        ("media-supported",),
    )
    media_type = _extract_supported_values(
        response,
        ("media-type-supported",),
        fallback_keys=("output-mode-supported",),
    )
    print_quality = _extract_supported_values(
        response,
        ("print-quality-supported",),
    )
    top_margins = _extract_supported_values(response, ("media-top-margin-supported",))
    left_margins = _extract_supported_values(response, ("media-left-margin-supported",))
    right_margins = _extract_supported_values(
        response, ("media-right-margin-supported",)
    )
    bottom_margins = _extract_supported_values(
        response, ("media-bottom-margin-supported",)
    )
    borderless_zero_margins_supported = all(
        "0" in values
        for values in (top_margins, left_margins, right_margins, bottom_margins)
    )
    printer_name = ""
    for key in ("printer-info", "printer-make-and-model", "printer-name"):
        values = _extract_supported_values(response, (key,))
        if values:
            printer_name = values[0].strip()
            if printer_name:
                break

    return IppCapabilities(
        media=media,
        media_type=media_type,
        print_quality=print_quality,
        printer_name=printer_name,
        borderless_zero_margins_supported=borderless_zero_margins_supported,
    )


def print_jobs_via_ipp(
    ipp_uri: str,
    image_files: list[Path],
    media: str,
    media_type: str,
    print_quality: str,
    borderless_mode: str = "default",
    wait_for_completion: bool = True,
    debug_logger: Callable[[str], None] | None = None,
) -> tuple[list[Path], list[str], str, dict[str, str]]:
    if not ipp_uri.strip():
        return [], [path.name for path in image_files], "IPP URI is empty.", {}

    IPP, IppOperation = _import_pyipp()

    printed_successfully: list[Path] = []
    failed: list[str] = []
    failure_details: list[str] = []
    timeout_details: list[str] = []
    job_ids: dict[str, str] = {}
    supported_media: list[str] = []
    effective_media = media

    if borderless_mode == "enabled":
        allow_borderless = True
        try:
            capabilities = get_ipp_capabilities(ipp_uri)
            supported_media = capabilities.media
            allow_borderless = capabilities.borderless_zero_margins_supported
        except Exception:
            supported_media = []
            allow_borderless = True

        effective_media = _choose_borderless_media(media, supported_media)

        borderless_candidates = [
            value for value in supported_media if _is_borderless_media_name(value)
        ]

        if debug_logger is not None:
            debug_logger(
                "IPP borderless media decision: "
                f"requested={media or '-'} "
                f"effective={effective_media or '-'} "
                f"supported={len(supported_media)} "
                f"borderless_candidates={len(borderless_candidates)}"
            )
            if borderless_candidates:
                debug_logger(
                    "IPP borderless candidates sample: "
                    + ", ".join(borderless_candidates[:8])
                )
            else:
                debug_logger(
                    "IPP media-supported sample: " + ", ".join(supported_media[:12])
                )
            if not allow_borderless:
                debug_logger(
                    "IPP borderless disabled: printer does not advertise "
                    "0-margin support for all sides"
                )

        if not allow_borderless:
            borderless_mode = "disabled"

    async def _lookup_job_id_by_name(client: object, job_name: str) -> int | None:
        if not job_name:
            return None
        await asyncio.sleep(0.6)
        response = await client.execute(
            IppOperation.GET_JOBS,
            {
                "operation-attributes-tag": {
                    "which-jobs": "not-completed",
                    "requested-attributes": [
                        "job-id",
                        "job-name",
                        "job-state",
                        "time-at-creation",
                    ],
                }
            },
        )

        candidates = _collect_job_entries(response)
        for entry in reversed(candidates):
            name = _extract_job_name(entry)
            if name != job_name:
                continue
            job_id = _extract_job_id(entry)
            if job_id is not None:
                return job_id
        return None

    async def _wait_for_terminal_state(
        client: object,
        job_id: int,
        timeout_seconds: float = 180.0,
        poll_seconds: float = 1.5,
    ) -> tuple[str, str]:
        started = time.monotonic()
        last_state = "unknown"
        while time.monotonic() - started <= timeout_seconds:
            response = await client.execute(
                IppOperation.GET_JOB_ATTRIBUTES,
                {
                    "operation-attributes-tag": {
                        "job-id": job_id,
                        "requested-attributes": [
                            "job-id",
                            "job-state",
                            "job-state-reasons",
                            "job-name",
                        ],
                    }
                },
            )
            state = _job_state_name(response)
            if state != "unknown":
                last_state = state

            if state in {"completed", "canceled", "aborted"}:
                reasons = _extract_supported_values(response, ("job-state-reasons",))
                detail = ",".join(reasons[:4]) if reasons else ""
                return state, detail

            await asyncio.sleep(poll_seconds)

        return "timeout", last_state

    async def _submit(path: Path) -> tuple[bool, str, str]:
        with path.open("rb") as fh:
            data = fh.read()

        job_name = f"{path.stem}-{int(time.time())}-{uuid.uuid4().hex[:8]}"

        operation_attributes: dict[str, object] = {
            "job-name": job_name,
            "document-format": "image/jpeg",
        }
        job_attributes: dict[str, object] = {}

        if effective_media:
            job_attributes["media"] = effective_media
        if media_type:
            job_attributes["media-type"] = media_type
        if print_quality:
            try:
                quality_value = int(print_quality)
                job_attributes["print-quality"] = quality_value
            except ValueError:
                job_attributes["print-quality"] = print_quality

        if print_quality in {"5", "high", "High"}:
            job_attributes["printer-resolution"] = "720dpi"
        elif print_quality:
            job_attributes["printer-resolution"] = "360dpi"

        if borderless_mode == "enabled":
            operation_attributes["ipp-attribute-fidelity"] = True
            job_attributes["print-borderless"] = True
            job_attributes["borderless"] = True
            job_attributes["print-scaling"] = "fill"
            job_attributes["media-col"] = {
                "media-top-margin": 0,
                "media-bottom-margin": 0,
                "media-left-margin": 0,
                "media-right-margin": 0,
            }
            if effective_media:
                job_attributes["media-col"]["media-size-name"] = effective_media
            if media_type:
                job_attributes["media-col"]["media-type"] = media_type
            media_key = (effective_media or "").lower()
            media_type_key = (media_type or "").lower()
            if "4x6" in media_key and media_type_key.startswith("photographic"):
                job_attributes["media-col"]["media-source"] = "photo"

            job_attributes.pop("media", None)
            job_attributes.pop("media-type", None)
        elif borderless_mode == "disabled":
            job_attributes["print-borderless"] = False
            job_attributes["borderless"] = False
            job_attributes["print-scaling"] = "fit"

        payload: dict[str, object] = {
            "operation-attributes-tag": operation_attributes,
            "data": data,
        }
        if job_attributes:
            payload["job-attributes-tag"] = job_attributes

        if debug_logger is not None:
            debug_logger(
                "IPP PRINT_JOB payload: "
                f"uri={ipp_uri.strip()} "
                f"file={path.name} "
                f"operation-attributes-tag={operation_attributes} "
                f"job-attributes-tag={job_attributes} "
                f"data-bytes={len(data)}"
            )

        async with IPP(ipp_uri.strip()) as client:
            submit_timeout: Exception | None = None
            submit_response: object | None = None
            try:
                submit_response = await client.execute(IppOperation.PRINT_JOB, payload)
            except Exception as error:
                if _is_timeout_error(error):
                    submit_timeout = error
                else:
                    raise

            job_id = _extract_job_id(submit_response) if submit_response else None
            if job_id is None:
                try:
                    job_id = await _lookup_job_id_by_name(client, job_name)
                except Exception:
                    job_id = None

            if job_id is None:
                if submit_timeout is not None:
                    return (
                        True,
                        "timeout without job-id; assumed submitted "
                        f"({type(submit_timeout).__name__})",
                        "",
                    )
                return True, "submitted without job-id", ""

            job_id_text = str(job_id)

            if not wait_for_completion:
                return True, f"job-id={job_id} queued", job_id_text

            state, detail = await _wait_for_terminal_state(client, job_id)
            if state == "completed":
                return True, f"job-id={job_id} completed", job_id_text
            if state in {"canceled", "aborted"}:
                suffix = f", reasons={detail}" if detail else ""
                return False, f"job-id={job_id} {state}{suffix}", job_id_text
            if state == "timeout":
                last_state = detail or "unknown"
                return (
                    True,
                    f"job-id={job_id} status timeout (last={last_state})",
                    job_id_text,
                )

            return True, f"job-id={job_id} state={state}", job_id_text

    for image_path in image_files:
        try:
            success, detail, job_id = asyncio.run(_submit(image_path))
            if job_id:
                job_ids[image_path.name] = job_id
            if success:
                printed_successfully.append(image_path)
                if detail and "timeout" in detail.lower():
                    timeout_details.append(f"{image_path.name}: {detail}")
            else:
                failed.append(image_path.name)
                if detail:
                    failure_details.append(f"{image_path.name}: {detail}")
        except Exception as error:
            detail = f"{image_path.name}: {type(error).__name__}: {error}"
            if _is_timeout_error(error):
                printed_successfully.append(image_path)
                timeout_details.append(detail)
            else:
                failed.append(image_path.name)
                failure_details.append(detail)

    error_text = ""
    if failure_details:
        if timeout_details:
            error_text = " | ".join(failure_details + timeout_details)
        else:
            error_text = " | ".join(failure_details)

    return printed_successfully, failed, error_text, job_ids


def cancel_ipp_job(ipp_uri: str, job_id: int | str) -> None:
    uri = ipp_uri.strip()
    if not uri:
        raise IppBackendError("IPP URI is empty.")

    try:
        numeric_job_id = int(str(job_id).strip())
    except ValueError as error:
        raise IppBackendError(f"Invalid IPP job id: {job_id}") from error

    IPP, IppOperation = _import_pyipp()

    async def _cancel() -> None:
        async with IPP(uri) as client:
            await client.execute(
                IppOperation.CANCEL_JOB,
                {
                    "operation-attributes-tag": {
                        "job-id": numeric_job_id,
                    }
                },
            )

    try:
        asyncio.run(_cancel())
    except Exception as error:
        raise IppBackendError(
            f"IPP cancel failed for job {numeric_job_id}: {error}"
        ) from error
