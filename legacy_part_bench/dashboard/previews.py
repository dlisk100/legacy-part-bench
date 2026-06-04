"""Static STL preview rendering for dashboard part-detail pages."""

from __future__ import annotations

import hashlib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

PREVIEW_DIRNAME = "_previews"


def preview_path_for_stl(stl_path: Path | str, *, cache_dir: Path | str | None = None) -> Path:
    """Return the deterministic PNG cache path for an STL file."""

    path = Path(stl_path)
    digest = _file_digest(path)
    root = Path(cache_dir) if cache_dir is not None else path.parent / PREVIEW_DIRNAME
    return root / f"{path.stem}-{digest[:12]}.png"


def render_stl_preview(
    stl_path: Path | str,
    *,
    cache_dir: Path | str | None = None,
    output_path: Path | str | None = None,
    title: str | None = None,
    force: bool = False,
) -> Path | None:
    """Render one STL as a static PNG and return the preview path.

    Returns ``None`` when the STL is missing or cannot be loaded as a mesh.
    """

    path = Path(stl_path)
    if not path.exists():
        return None

    preview_path = (
        Path(output_path)
        if output_path is not None
        else preview_path_for_stl(path, cache_dir=cache_dir)
    )
    if preview_path.exists() and not force:
        return preview_path

    try:
        mesh = trimesh.load_mesh(path, force="mesh")
    except Exception:
        return None

    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)
    if vertices.size == 0 or faces.size == 0:
        return None

    preview_path.parent.mkdir(parents=True, exist_ok=True)
    _render_mesh(vertices=vertices, faces=faces, output_path=preview_path, title=title or path.name)
    return preview_path


def render_run_previews(
    *,
    target_stl_path: Path | str | None,
    generated_stl_path: Path | str | None,
    cache_dir: Path | str,
) -> tuple[Path | None, Path | None]:
    """Render target and generated STL previews into a shared cache folder."""

    target_preview = (
        render_stl_preview(target_stl_path, cache_dir=cache_dir, title="Target")
        if target_stl_path is not None
        else None
    )
    generated_preview = (
        render_stl_preview(generated_stl_path, cache_dir=cache_dir, title="Generated")
        if generated_stl_path is not None
        else None
    )
    return target_preview, generated_preview


def _render_mesh(
    *,
    vertices: np.ndarray,
    faces: np.ndarray,
    output_path: Path,
    title: str,
) -> None:
    face_vertices = vertices[faces]
    extents = vertices.max(axis=0) - vertices.min(axis=0)
    max_extent = float(max(extents.max(), 1.0))
    center = vertices.mean(axis=0)

    fig = plt.figure(figsize=(5.5, 4.2), dpi=140)
    ax = fig.add_subplot(111, projection="3d")
    collection = Poly3DCollection(
        face_vertices,
        facecolor="#7aa6c2",
        edgecolor="#334155",
        linewidth=0.12,
        alpha=0.95,
    )
    ax.add_collection3d(collection)
    ax.set_title(title, fontsize=10, pad=8)
    ax.view_init(elev=28, azim=-45)
    ax.set_box_aspect((1, 1, 0.55))

    for axis, value in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), center, strict=True):
        axis(value - max_extent * 0.55, value + max_extent * 0.55)

    ax.set_axis_off()
    fig.tight_layout(pad=0.1)
    fig.savefig(output_path, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
