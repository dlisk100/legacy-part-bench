"""ASME-inspired orthographic drawing renderer for mounting plates."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

from legacy_part_bench.dataset import BenchmarkItem, PartMetadata

LINE_COLOR = "#111111"
VISIBLE_LINE_WIDTH = 1.35
THIN_LINE_WIDTH = 0.75
CENTER_LINE_STYLE = (0, (8, 4, 1.5, 4))
HIDDEN_LINE_STYLE = (0, (4, 3))


def render_mounting_plate_drawing(metadata: PartMetadata, output_path: Path | str) -> Path:
    """Render a single-sheet ASME-inspired mounting-plate drawing PNG."""

    _validate_drawing_metadata(metadata)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(14, 9), dpi=180, facecolor="white")
    fig.suptitle("LEGACYPARTBENCH GENERATED MECHANICAL DRAWING", fontsize=12, y=0.975)

    ax_top = fig.add_axes((0.06, 0.36, 0.67, 0.5))
    ax_front = fig.add_axes((0.06, 0.14, 0.67, 0.16))
    ax_title = fig.add_axes((0.72, 0.08, 0.25, 0.28))

    _draw_top_view(ax_top, metadata)
    _draw_front_view(ax_front, metadata)
    _draw_title_block(ax_title, metadata)

    fig.savefig(output, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    return output


def render_item_drawing(item: BenchmarkItem) -> Path:
    """Render the drawing for an existing benchmark item folder."""

    return render_mounting_plate_drawing(item.metadata, item.drawing_path)


def drawing_notes(metadata: PartMetadata) -> list[str]:
    """Return the drawing notes used by the renderer."""

    return [
        "ASME-INSPIRED BENCHMARK DRAWING",
        "NOT FOR MANUFACTURING RELEASE",
        "REMOVE ALL BURRS AND SHARP EDGES",
        *hole_callout_lines(metadata),
    ]


def title_block_lines(metadata: PartMetadata) -> list[tuple[str, str]]:
    """Return key-value rows shown in the drawing title block."""

    return [
        ("PART", metadata.id),
        ("FAMILY", metadata.family),
        ("UNITS", "mm"),
        ("SCALE", "AUTO FIT"),
        ("PROJECTION", "THIRD ANGLE"),
        ("MATERIAL", "UNSPECIFIED"),
    ]


def hole_callout_lines(metadata: PartMetadata) -> list[str]:
    """Return grouped through-hole callouts by diameter."""

    hole_counts = Counter(hole.diameter for hole in metadata.features.holes)
    return [f"{count}X DIA {diameter:g} THRU" for diameter, count in sorted(hole_counts.items())]


def dimension_text(metadata: PartMetadata) -> list[str]:
    """Return dimension labels expected to appear on the drawing."""

    dimensions = metadata.dimensions
    labels = [
        f"LENGTH {dimensions.length:g}",
        f"WIDTH {dimensions.width:g}",
        f"THICKNESS {dimensions.thickness:g}",
        *hole_callout_lines(metadata),
    ]
    for index, hole in enumerate(metadata.features.holes, start=1):
        labels.extend((f"H{index} X {hole.center[0]:g}", f"H{index} Y {hole.center[1]:g}"))
    return labels


def _draw_top_view(ax, metadata: PartMetadata) -> None:
    from matplotlib.patches import Circle, Rectangle

    dimensions = metadata.dimensions
    holes = metadata.features.holes
    margin = max(dimensions.length, dimensions.width) * 0.25
    x_dim_gap = max(dimensions.width * 0.105, 9.0)
    y_dim_gap = max(dimensions.length * 0.058, 9.0)

    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title("TOP VIEW", fontsize=10, pad=8)

    ax.add_patch(
        Rectangle(
            (0.0, 0.0),
            dimensions.length,
            dimensions.width,
            facecolor="#fbfbfb",
            edgecolor=LINE_COLOR,
            linewidth=VISIBLE_LINE_WIDTH,
        )
    )

    for index, hole in enumerate(holes, start=1):
        radius = hole.diameter / 2.0
        x, y = hole.center
        ax.add_patch(
            Circle(
                (x, y),
                radius,
                facecolor="white",
                edgecolor=LINE_COLOR,
                linewidth=VISIBLE_LINE_WIDTH,
            )
        )
        _draw_center_mark(ax, x=x, y=y, size=max(radius * 1.8, 4.0))
        ax.text(x, y - radius * 2.0, f"H{index}", ha="center", va="top", fontsize=7)

    _draw_horizontal_dimension(
        ax,
        x0=0.0,
        x1=dimensions.length,
        y=-x_dim_gap,
        label=f"LENGTH {dimensions.length:g}",
        text_offset=x_dim_gap * 0.32,
    )
    _draw_vertical_dimension(
        ax,
        y0=0.0,
        y1=dimensions.width,
        x=-y_dim_gap,
        label=f"WIDTH {dimensions.width:g}",
        text_offset=y_dim_gap * 0.55,
    )

    _draw_hole_baseline_dimensions(ax, metadata, x_dim_gap=x_dim_gap, y_dim_gap=y_dim_gap)
    _draw_hole_leader_callout(ax, metadata)

    x_tier_count = len(_unique_sorted(hole.center[0] for hole in holes))
    y_tier_count = len(_unique_sorted(hole.center[1] for hole in holes))
    ax.set_xlim(-max(margin, y_dim_gap * (y_tier_count + 2.2)), dimensions.length + margin * 1.25)
    ax.set_ylim(
        -max(margin * 1.18, x_dim_gap * (x_tier_count + 2.0)),
        dimensions.width + margin * 0.56,
    )


def _draw_front_view(ax, metadata: PartMetadata) -> None:
    from matplotlib.patches import Rectangle

    dimensions = metadata.dimensions
    margin_x = dimensions.length * 0.08
    margin_y = max(dimensions.thickness * 3.0, 10.0)

    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title("FRONT VIEW", fontsize=10, pad=6)

    ax.add_patch(
        Rectangle(
            (0.0, 0.0),
            dimensions.length,
            dimensions.thickness,
            facecolor="#fbfbfb",
            edgecolor=LINE_COLOR,
            linewidth=VISIBLE_LINE_WIDTH,
        )
    )
    for hole in metadata.features.holes:
        ax.plot(
            [hole.center[0], hole.center[0]],
            [0.0, dimensions.thickness],
            color=LINE_COLOR,
            linewidth=THIN_LINE_WIDTH,
            linestyle=HIDDEN_LINE_STYLE,
        )

    _draw_vertical_dimension(
        ax,
        y0=0.0,
        y1=dimensions.thickness,
        x=dimensions.length + margin_x * 0.95,
        label=f"THICKNESS {dimensions.thickness:g}",
        text_side="right",
        text_offset=margin_x * 0.42,
    )
    ax.text(
        dimensions.length / 2.0,
        -margin_y * 0.46,
        "HIDDEN LINES SHOW THROUGH-HOLE LOCATIONS",
        ha="center",
        va="top",
        fontsize=7,
    )

    ax.set_xlim(-margin_x, dimensions.length + margin_x * 2.1)
    ax.set_ylim(-margin_y, dimensions.thickness + margin_y * 0.7)


def _draw_title_block(ax, metadata: PartMetadata) -> None:
    from matplotlib.patches import Rectangle

    ax.axis("off")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.add_patch(Rectangle((0.0, 0.0), 1.0, 1.0, fill=False, edgecolor=LINE_COLOR, linewidth=1.2))

    row_height = 0.065
    y = 0.94
    ax.text(0.03, y, "TITLE BLOCK", ha="left", va="top", fontsize=9, fontweight="bold")
    y -= row_height
    for label, value in title_block_lines(metadata):
        ax.plot([0.0, 1.0], [y + row_height * 0.2, y + row_height * 0.2], color=LINE_COLOR, linewidth=0.5)
        ax.text(0.03, y, label, ha="left", va="top", fontsize=6.7)
        ax.text(0.34, y, value, ha="left", va="top", fontsize=6.7)
        y -= row_height

    y -= 0.02
    ax.text(0.03, y, "NOTES", ha="left", va="top", fontsize=8, fontweight="bold")
    y -= 0.055
    for note in drawing_notes(metadata):
        ax.text(0.03, y, note, ha="left", va="top", fontsize=6.2)
        y -= 0.052


def _draw_hole_baseline_dimensions(ax, metadata: PartMetadata, *, x_dim_gap: float, y_dim_gap: float) -> None:
    dimensions = metadata.dimensions
    holes = metadata.features.holes
    x_values = _unique_sorted(hole.center[0] for hole in holes)
    y_values = _unique_sorted(hole.center[1] for hole in holes)

    for stack_index, x in enumerate(x_values, start=1):
        y = -x_dim_gap * (1.0 + stack_index * 0.95)
        _draw_horizontal_dimension(
            ax,
            x0=0.0,
            x1=x,
            y=y,
            label=f"X {x:g}",
            fontsize=7,
            text_offset=x_dim_gap * 0.26,
        )

    for stack_index, y in enumerate(y_values, start=1):
        x = -y_dim_gap * (1.0 + stack_index * 0.95)
        _draw_vertical_dimension(
            ax,
            y0=0.0,
            y1=y,
            x=x,
            label=f"Y {y:g}",
            fontsize=7,
            text_offset=y_dim_gap * 0.55,
        )

    bottom_limit = -x_dim_gap * (len(x_values) + 1.45)
    left_limit = -y_dim_gap * (len(y_values) + 1.45)
    for hole in holes:
        ax.plot(
            [hole.center[0], hole.center[0]],
            [hole.center[1], bottom_limit],
            color=LINE_COLOR,
            linewidth=0.45,
            linestyle=CENTER_LINE_STYLE,
            alpha=0.65,
        )
        ax.plot(
            [hole.center[0], left_limit],
            [hole.center[1], hole.center[1]],
            color=LINE_COLOR,
            linewidth=0.45,
            linestyle=CENTER_LINE_STYLE,
            alpha=0.65,
        )

    ax.text(
        dimensions.length,
        dimensions.width + y_dim_gap * 0.52,
        "HOLES DIMENSIONED FROM LEFT AND BOTTOM EDGES",
        ha="right",
        va="bottom",
        fontsize=7,
    )


def _draw_hole_leader_callout(ax, metadata: PartMetadata) -> None:
    holes = metadata.features.holes
    if not holes:
        return

    hole = holes[0]
    radius = hole.diameter / 2.0
    dimensions = metadata.dimensions
    callout = hole_callout_lines(metadata)[0]
    text_x = dimensions.length + max(dimensions.length * 0.04, 5.0)
    text_y = min(dimensions.width * 0.82, hole.center[1] + dimensions.width * 0.38)

    ax.annotate(
        callout,
        xy=(hole.center[0] + radius * 0.7, hole.center[1] + radius * 0.7),
        xytext=(text_x, text_y),
        arrowprops={"arrowstyle": "->", "lw": THIN_LINE_WIDTH, "color": LINE_COLOR},
        ha="left",
        va="center",
        fontsize=8,
        bbox={"boxstyle": "square,pad=0.2", "facecolor": "white", "edgecolor": "none"},
    )


def _draw_center_mark(ax, *, x: float, y: float, size: float) -> None:
    ax.plot([x - size, x + size], [y, y], color=LINE_COLOR, linewidth=0.65, linestyle=CENTER_LINE_STYLE)
    ax.plot([x, x], [y - size, y + size], color=LINE_COLOR, linewidth=0.65, linestyle=CENTER_LINE_STYLE)


def _draw_horizontal_dimension(
    ax,
    *,
    x0: float,
    x1: float,
    y: float,
    label: str,
    fontsize: float = 8.0,
    text_offset: float = 3.0,
) -> None:
    ax.annotate(
        "",
        xy=(x1, y),
        xytext=(x0, y),
        arrowprops={"arrowstyle": "<->", "lw": THIN_LINE_WIDTH, "color": LINE_COLOR, "shrinkA": 0, "shrinkB": 0},
    )
    ax.plot([x0, x0], [0.0, y], color=LINE_COLOR, linewidth=0.55)
    ax.plot([x1, x1], [0.0, y], color=LINE_COLOR, linewidth=0.55)
    ax.text((x0 + x1) / 2.0, y - text_offset, label, ha="center", va="top", fontsize=fontsize)


def _draw_vertical_dimension(
    ax,
    *,
    y0: float,
    y1: float,
    x: float,
    label: str,
    fontsize: float = 8.0,
    text_side: str = "left",
    text_offset: float = 3.0,
) -> None:
    ax.annotate(
        "",
        xy=(x, y1),
        xytext=(x, y0),
        arrowprops={"arrowstyle": "<->", "lw": THIN_LINE_WIDTH, "color": LINE_COLOR, "shrinkA": 0, "shrinkB": 0},
    )
    ax.plot([0.0, x], [y0, y0], color=LINE_COLOR, linewidth=0.55)
    ax.plot([0.0, x], [y1, y1], color=LINE_COLOR, linewidth=0.55)
    x_offset = -text_offset if text_side == "left" else text_offset
    ha = "right" if text_side == "left" else "left"
    ax.text(x + x_offset, (y0 + y1) / 2.0, label, ha=ha, va="center", rotation=90, fontsize=fontsize)


def _validate_drawing_metadata(metadata: PartMetadata) -> None:
    if metadata.family != "mounting_plate":
        raise ValueError(f"Unsupported part family: {metadata.family}")
    if metadata.units != "mm":
        raise ValueError(f"Unsupported units: {metadata.units}")
    if metadata.features.slots:
        raise ValueError("Mounting plate drawings support through holes only, not slots.")


def _unique_sorted(values: Iterable[float]) -> list[float]:
    return sorted(set(values))
