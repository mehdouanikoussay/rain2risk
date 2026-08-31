"""Combine provider outputs into structured, source-aware cell features."""


def build_features(cells, elevations, worldcover_cells, osm_payload, derive_slope):
    if len(elevations) != len(cells) or len(worldcover_cells) != len(cells):
        raise ValueError("provider output length does not match grid")
    for index, cell in enumerate(cells):
        cell["elevation_m"] = elevations[index]
        cell.update(worldcover_cells[index])
    slopes = derive_slope(cells, [cell["elevation_m"] for cell in cells])
    for cell, slope in zip(cells, slopes):
        cell["slope_deg"] = slope
    if osm_payload is None:
        return cells
    from .osm import extract_facts
    return extract_facts(cells, osm_payload)
