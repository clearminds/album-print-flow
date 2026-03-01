from __future__ import annotations


def paper_size_mm(paper_value: str) -> tuple[float, float]:
    if paper_value == "A3":
        return (297.0, 420.0)
    if paper_value == "A3+":
        return (329.0, 483.0)
    if paper_value == "A4":
        return (210.0, 297.0)
    if paper_value == "A4+":
        return (210.0, 330.0)
    return (100.0, 150.0)


__all__ = ["paper_size_mm"]
