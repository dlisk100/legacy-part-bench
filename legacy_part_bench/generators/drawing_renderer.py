"""ASME-inspired orthographic drawing renderers for benchmark parts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

from legacy_part_bench.dataset import BenchmarkItem, PartMetadata, SlotFeature

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


def render_stepped_block_drawing(metadata: PartMetadata, output_path: Path | str) -> Path:
    """Render a top and side view drawing for one stepped block."""

    _validate_stepped_block_drawing_metadata(metadata)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(14, 9), dpi=180, facecolor="white")
    fig.suptitle("LEGACYPARTBENCH GENERATED MECHANICAL DRAWING", fontsize=12, y=0.975)

    ax_top = fig.add_axes((0.06, 0.42, 0.67, 0.38))
    ax_side = fig.add_axes((0.06, 0.12, 0.67, 0.22))
    ax_title = fig.add_axes((0.72, 0.08, 0.25, 0.28))

    _draw_stepped_top_view(ax_top, metadata)
    _draw_stepped_side_view(ax_side, metadata)
    _draw_title_block(ax_title, metadata)

    fig.savefig(output, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    return output


def render_l_bracket_drawing(metadata: PartMetadata, output_path: Path | str) -> Path:
    """Render top, side, and front views for one L-bracket."""

    _validate_l_bracket_drawing_metadata(metadata)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(14, 9), dpi=180, facecolor="white")
    fig.suptitle("LEGACYPARTBENCH GENERATED MECHANICAL DRAWING", fontsize=12, y=0.975)

    ax_top = fig.add_axes((0.06, 0.47, 0.46, 0.34))
    ax_side = fig.add_axes((0.06, 0.12, 0.46, 0.27))
    ax_front = fig.add_axes((0.53, 0.42, 0.18, 0.36))
    ax_title = fig.add_axes((0.72, 0.08, 0.25, 0.28))

    _draw_l_bracket_top_view(ax_top, metadata)
    _draw_l_bracket_side_view(ax_side, metadata)
    _draw_l_bracket_front_view(ax_front, metadata)
    _draw_title_block(ax_title, metadata)

    fig.savefig(output, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    return output


def render_part_drawing(metadata: PartMetadata, output_path: Path | str) -> Path:
    """Render the appropriate drawing for a supported part family."""

    if metadata.family == "mounting_plate":
        return render_mounting_plate_drawing(metadata, output_path)
    if metadata.family == "stepped_block":
        return render_stepped_block_drawing(metadata, output_path)
    if metadata.family == "l_bracket":
        return render_l_bracket_drawing(metadata, output_path)
    raise ValueError(f"Unsupported part family: {metadata.family}")


def render_item_drawing(item: BenchmarkItem) -> Path:
    """Render the drawing for an existing benchmark item folder."""

    return render_part_drawing(item.metadata, item.drawing_path)


def drawing_notes(metadata: PartMetadata) -> list[str]:
    """Return the drawing notes used by the renderer."""

    return [
        "ASME-INSPIRED BENCHMARK DRAWING",
        "NOT FOR MANUFACTURING RELEASE",
        "REMOVE ALL BURRS AND SHARP EDGES",
        *hole_callout_lines(metadata),
        *slot_callout_lines(metadata),
        *step_callout_lines(metadata),
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


def slot_callout_lines(metadata: PartMetadata) -> list[str]:
    """Return grouped horizontal through-slot callouts."""

    slot_counts = Counter((slot.length, slot.width) for slot in metadata.features.slots)
    return [
        f"{count}X SLOT {length:g} X {width:g} THRU"
        for (length, width), count in sorted(slot_counts.items())
    ]


def step_callout_lines(metadata: PartMetadata) -> list[str]:
    """Return stepped-block side-view callouts."""

    if not metadata.features.steps:
        return []
    base_height = _numeric_parameter(metadata, "base_height", default=None)
    lines = []
    if base_height is not None:
        lines.append(f"BASE HEIGHT {base_height:g}")
    for index, step in enumerate(metadata.features.steps, start=1):
        lines.append(f"STEP {index} X {step.x_start:g} LEN {step.length:g} TOP {step.top_height:g}")
    return lines


def dimension_text(metadata: PartMetadata) -> list[str]:
    """Return dimension labels expected to appear on the drawing."""

    dimensions = metadata.dimensions
    labels = [
        f"LENGTH {dimensions.length:g}",
        f"WIDTH {dimensions.width:g}",
        f"THICKNESS {dimensions.thickness:g}" if metadata.family == "mounting_plate" else f"HEIGHT {dimensions.thickness:g}",
        *hole_callout_lines(metadata),
        *slot_callout_lines(metadata),
        *step_callout_lines(metadata),
    ]
    for index, hole in enumerate(metadata.features.holes, start=1):
        labels.extend((f"H{index} X {hole.center[0]:g}", f"H{index} Y {hole.center[1]:g}"))
    for index, slot in enumerate(metadata.features.slots, start=1):
        labels.extend((f"S{index} X {slot.center[0]:g}", f"S{index} Y {slot.center[1]:g}"))
    return labels


def _draw_top_view(ax, metadata: PartMetadata) -> None:
    from matplotlib.patches import Circle, Rectangle

    dimensions = metadata.dimensions
    holes = metadata.features.holes
    slots = metadata.features.slots
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

    for index, slot in enumerate(slots, start=1):
        _draw_slot_cutout(ax, slot)
        ax.text(
            slot.center[0],
            slot.center[1] - slot.width * 0.92,
            f"S{index}",
            ha="center",
            va="top",
            fontsize=7,
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

    _draw_feature_baseline_dimensions(ax, metadata, x_dim_gap=x_dim_gap, y_dim_gap=y_dim_gap)
    _draw_feature_leader_callout(ax, metadata)

    feature_centers = [hole.center for hole in holes] + [slot.center for slot in slots]
    x_tier_count = len(_unique_sorted(center[0] for center in feature_centers))
    y_tier_count = len(_unique_sorted(center[1] for center in feature_centers))
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
    for slot in metadata.features.slots:
        slot_half = slot.length / 2.0
        for x in (slot.center[0] - slot_half, slot.center[0] + slot_half):
            ax.plot(
                [x, x],
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


def _draw_feature_baseline_dimensions(ax, metadata: PartMetadata, *, x_dim_gap: float, y_dim_gap: float) -> None:
    dimensions = metadata.dimensions
    features = [*metadata.features.holes, *metadata.features.slots]
    x_values = _unique_sorted(feature.center[0] for feature in features)
    y_values = _unique_sorted(feature.center[1] for feature in features)

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
    for feature in features:
        ax.plot(
            [feature.center[0], feature.center[0]],
            [feature.center[1], bottom_limit],
            color=LINE_COLOR,
            linewidth=0.45,
            linestyle=CENTER_LINE_STYLE,
            alpha=0.65,
        )
        ax.plot(
            [feature.center[0], left_limit],
            [feature.center[1], feature.center[1]],
            color=LINE_COLOR,
            linewidth=0.45,
            linestyle=CENTER_LINE_STYLE,
            alpha=0.65,
        )

    ax.text(
        dimensions.length,
        dimensions.width + y_dim_gap * 0.52,
        "FEATURES DIMENSIONED FROM LEFT AND BOTTOM EDGES",
        ha="right",
        va="bottom",
        fontsize=7,
    )


def _draw_feature_leader_callout(ax, metadata: PartMetadata) -> None:
    holes = metadata.features.holes
    slots = metadata.features.slots
    if not holes and not slots:
        return

    dimensions = metadata.dimensions
    if holes:
        feature = holes[0]
        radius = feature.diameter / 2.0
        callout = hole_callout_lines(metadata)[0]
        xy = (feature.center[0] + radius * 0.7, feature.center[1] + radius * 0.7)
    else:
        feature = slots[0]
        radius = feature.width / 2.0
        callout = slot_callout_lines(metadata)[0]
        xy = (feature.center[0] + feature.length / 2.0 - radius, feature.center[1] + radius)
    text_x = dimensions.length + max(dimensions.length * 0.04, 5.0)
    text_y = min(dimensions.width * 0.82, feature.center[1] + dimensions.width * 0.38)

    ax.annotate(
        callout,
        xy=xy,
        xytext=(text_x, text_y),
        arrowprops={"arrowstyle": "->", "lw": THIN_LINE_WIDTH, "color": LINE_COLOR},
        ha="left",
        va="center",
        fontsize=8,
        bbox={"boxstyle": "square,pad=0.2", "facecolor": "white", "edgecolor": "none"},
    )


def _draw_slot_cutout(ax, slot: SlotFeature) -> None:
    from matplotlib.patches import Circle, Rectangle

    radius = slot.width / 2.0
    straight_length = slot.length - slot.width
    left_center = slot.center[0] - straight_length / 2.0
    right_center = slot.center[0] + straight_length / 2.0
    y = slot.center[1]
    ax.add_patch(
        Rectangle(
            (left_center, y - radius),
            straight_length,
            slot.width,
            facecolor="white",
            edgecolor=LINE_COLOR,
            linewidth=VISIBLE_LINE_WIDTH,
        )
    )
    ax.add_patch(
        Circle(
            (left_center, y),
            radius,
            facecolor="white",
            edgecolor=LINE_COLOR,
            linewidth=VISIBLE_LINE_WIDTH,
        )
    )
    ax.add_patch(
        Circle(
            (right_center, y),
            radius,
            facecolor="white",
            edgecolor=LINE_COLOR,
            linewidth=VISIBLE_LINE_WIDTH,
        )
    )
    _draw_center_mark(ax, x=slot.center[0], y=slot.center[1], size=max(slot.width * 1.3, 4.0))


def _draw_stepped_top_view(ax, metadata: PartMetadata) -> None:
    from matplotlib.patches import Rectangle

    dimensions = metadata.dimensions
    margin = max(dimensions.length, dimensions.width) * 0.18
    x_dim_gap = max(dimensions.width * 0.12, 10.0)
    y_dim_gap = max(dimensions.length * 0.065, 10.0)

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
    for index, step in enumerate(metadata.features.steps, start=1):
        ax.add_patch(
            Rectangle(
                (step.x_start, 0.0),
                step.length,
                dimensions.width,
                fill=False,
                edgecolor=LINE_COLOR,
                linewidth=THIN_LINE_WIDTH,
                linestyle=HIDDEN_LINE_STYLE,
            )
        )
        ax.text(
            step.x_start + step.length / 2.0,
            dimensions.width / 2.0,
            f"STEP {index}",
            ha="center",
            va="center",
            fontsize=7,
        )

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
    for stack_index, step in enumerate(metadata.features.steps, start=1):
        y = -x_dim_gap * (1.0 + stack_index * 0.95)
        _draw_horizontal_dimension(
            ax,
            x0=0.0,
            x1=step.x_start,
            y=y,
            label=f"STEP {stack_index} X {step.x_start:g}",
            fontsize=7,
            text_offset=x_dim_gap * 0.25,
        )
        y_length = -x_dim_gap * (1.38 + stack_index * 0.95)
        _draw_horizontal_dimension(
            ax,
            x0=step.x_start,
            x1=step.x_start + step.length,
            y=y_length,
            label=f"STEP {stack_index} LEN {step.length:g}",
            fontsize=7,
            text_offset=x_dim_gap * 0.25,
        )

    ax.set_xlim(-margin, dimensions.length + margin)
    ax.set_ylim(-margin * 1.35, dimensions.width + margin * 0.55)


def _draw_stepped_side_view(ax, metadata: PartMetadata) -> None:
    from matplotlib.patches import Rectangle

    dimensions = metadata.dimensions
    base_height = _numeric_parameter(metadata, "base_height")
    margin_x = dimensions.length * 0.08
    margin_y = dimensions.thickness * 0.45

    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title("SIDE VIEW", fontsize=10, pad=6)
    ax.add_patch(
        Rectangle(
            (0.0, 0.0),
            dimensions.length,
            base_height,
            facecolor="#fbfbfb",
            edgecolor=LINE_COLOR,
            linewidth=VISIBLE_LINE_WIDTH,
        )
    )
    for step in metadata.features.steps:
        ax.add_patch(
            Rectangle(
                (step.x_start, base_height),
                step.length,
                step.top_height - base_height,
                facecolor="#fbfbfb",
                edgecolor=LINE_COLOR,
                linewidth=VISIBLE_LINE_WIDTH,
            )
        )

    _draw_vertical_dimension(
        ax,
        y0=0.0,
        y1=dimensions.thickness,
        x=dimensions.length + margin_x * 0.9,
        label=f"HEIGHT {dimensions.thickness:g}",
        text_side="right",
        text_offset=margin_x * 0.38,
    )
    _draw_vertical_dimension(
        ax,
        y0=0.0,
        y1=base_height,
        x=-margin_x * 0.55,
        label=f"BASE {base_height:g}",
        text_offset=margin_x * 0.33,
    )

    ax.set_xlim(-margin_x * 1.4, dimensions.length + margin_x * 2.1)
    ax.set_ylim(-margin_y * 0.45, dimensions.thickness + margin_y)


def _draw_l_bracket_top_view(ax, metadata: PartMetadata) -> None:
    from matplotlib.patches import Circle, Rectangle

    dimensions = metadata.dimensions
    flange_thickness = _numeric_parameter(metadata, "flange_thickness")
    usable_base_width = dimensions.width - flange_thickness
    margin = max(dimensions.length, dimensions.width) * 0.2
    x_dim_gap = max(dimensions.width * 0.12, 10.0)
    y_dim_gap = max(dimensions.length * 0.065, 10.0)

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
    ax.add_patch(
        Rectangle(
            (0.0, usable_base_width),
            dimensions.length,
            flange_thickness,
            facecolor="#f0f0f0",
            edgecolor=LINE_COLOR,
            linewidth=THIN_LINE_WIDTH,
        )
    )
    ax.text(
        dimensions.length / 2.0,
        usable_base_width + flange_thickness / 2.0,
        "VERTICAL FLANGE FOOTPRINT",
        ha="center",
        va="center",
        fontsize=6.5,
    )

    for index, hole in enumerate(metadata.features.holes, start=1):
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
    if metadata.features.holes:
        _draw_feature_baseline_dimensions(ax, metadata, x_dim_gap=x_dim_gap, y_dim_gap=y_dim_gap)
        _draw_feature_leader_callout(ax, metadata)

    ax.set_xlim(-margin * 1.25, dimensions.length + margin * 1.25)
    ax.set_ylim(-margin * 1.35, dimensions.width + margin * 0.55)


def _draw_l_bracket_side_view(ax, metadata: PartMetadata) -> None:
    from matplotlib.patches import Rectangle

    dimensions = metadata.dimensions
    flange_thickness = _numeric_parameter(metadata, "flange_thickness")
    margin_x = dimensions.width * 0.18
    margin_y = dimensions.thickness * 0.22

    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title("SIDE VIEW", fontsize=10, pad=6)
    ax.add_patch(
        Rectangle(
            (0.0, 0.0),
            dimensions.width,
            flange_thickness,
            facecolor="#fbfbfb",
            edgecolor=LINE_COLOR,
            linewidth=VISIBLE_LINE_WIDTH,
        )
    )
    ax.add_patch(
        Rectangle(
            (dimensions.width - flange_thickness, 0.0),
            flange_thickness,
            dimensions.thickness,
            facecolor="#fbfbfb",
            edgecolor=LINE_COLOR,
            linewidth=VISIBLE_LINE_WIDTH,
        )
    )
    _draw_horizontal_dimension(
        ax,
        x0=0.0,
        x1=dimensions.width,
        y=-margin_y * 0.42,
        label=f"WIDTH {dimensions.width:g}",
        text_offset=margin_y * 0.22,
    )
    _draw_vertical_dimension(
        ax,
        y0=0.0,
        y1=dimensions.thickness,
        x=dimensions.width + margin_x * 0.6,
        label=f"HEIGHT {dimensions.thickness:g}",
        text_side="right",
        text_offset=margin_x * 0.35,
    )
    _draw_vertical_dimension(
        ax,
        y0=0.0,
        y1=flange_thickness,
        x=-margin_x * 0.4,
        label=f"THK {flange_thickness:g}",
        text_offset=margin_x * 0.33,
    )
    ax.set_xlim(-margin_x, dimensions.width + margin_x * 1.7)
    ax.set_ylim(-margin_y, dimensions.thickness + margin_y)


def _draw_l_bracket_front_view(ax, metadata: PartMetadata) -> None:
    from matplotlib.patches import Rectangle

    dimensions = metadata.dimensions
    flange_thickness = _numeric_parameter(metadata, "flange_thickness")
    margin_x = dimensions.length * 0.12
    margin_y = dimensions.thickness * 0.18

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
    ax.plot(
        [0.0, dimensions.length],
        [flange_thickness, flange_thickness],
        color=LINE_COLOR,
        linewidth=THIN_LINE_WIDTH,
        linestyle=HIDDEN_LINE_STYLE,
    )
    ax.set_xlim(-margin_x, dimensions.length + margin_x)
    ax.set_ylim(-margin_y, dimensions.thickness + margin_y)


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
    for index, slot in enumerate(metadata.features.slots):
        if not slot.through:
            raise ValueError(f"Slot {index} must be a through slot.")
        if abs(slot.angle_degrees) > 1e-9:
            raise ValueError(f"Slot {index} must be horizontal for the Phase 8 drawing renderer.")
        if slot.length <= slot.width:
            raise ValueError(f"Slot {index} length must be greater than its width.")


def _validate_stepped_block_drawing_metadata(metadata: PartMetadata) -> None:
    if metadata.family != "stepped_block":
        raise ValueError(f"Unsupported part family: {metadata.family}")
    if metadata.units != "mm":
        raise ValueError(f"Unsupported units: {metadata.units}")
    if not metadata.features.steps:
        raise ValueError("Stepped-block drawings require at least one step.")
    base_height = _numeric_parameter(metadata, "base_height")
    if not 0.0 < base_height < metadata.dimensions.thickness:
        raise ValueError("base_height must be between 0 and the overall part height.")


def _validate_l_bracket_drawing_metadata(metadata: PartMetadata) -> None:
    if metadata.family != "l_bracket":
        raise ValueError(f"Unsupported part family: {metadata.family}")
    if metadata.units != "mm":
        raise ValueError(f"Unsupported units: {metadata.units}")
    flange_thickness = _numeric_parameter(metadata, "flange_thickness")
    if flange_thickness <= 0.0:
        raise ValueError("flange_thickness must be positive.")


def _unique_sorted(values: Iterable[float]) -> list[float]:
    return sorted(set(values))


def _numeric_parameter(
    metadata: PartMetadata,
    name: str,
    *,
    default: float | None = ...,
) -> float | None:
    value = metadata.parameters.get(name, default)
    if value is ...:
        raise ValueError(f"Missing drawing parameter: {name}")
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise ValueError(f"Drawing parameter {name} must be numeric.")
    return float(value)
