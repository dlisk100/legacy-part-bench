"""Dataset schemas for LegacyPartBench benchmark metadata."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictSchema(BaseModel):
    """Base model for small JSON-serializable dataset records."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class PartDimensions(StrictSchema):
    """Overall mounting-plate dimensions in millimeters."""

    length: float = Field(gt=0)
    width: float = Field(gt=0)
    thickness: float = Field(gt=0)


class HoleFeature(StrictSchema):
    """A circular hole whose center is measured from the lower-left corner."""

    diameter: float = Field(gt=0)
    center: tuple[float, float]
    through: bool = True


class SlotFeature(StrictSchema):
    """A slot feature schema reserved for metadata compatibility."""

    length: float = Field(gt=0)
    width: float = Field(gt=0)
    center: tuple[float, float]
    through: bool = True
    angle_degrees: float = 0.0


class PartFeatures(StrictSchema):
    """Feature lists included in metadata.json."""

    holes: tuple[HoleFeature, ...] = ()
    slots: tuple[SlotFeature, ...] = ()


class FileReferences(StrictSchema):
    """Relative artifact filenames for a benchmark item folder."""

    drawing_png: str = "drawing.png"
    target_step: str = "target.step"
    target_stl: str = "target.stl"


class PartMetadata(StrictSchema):
    """Metadata persisted as ``metadata.json`` for one generated part."""

    id: str = Field(min_length=1)
    family: Literal["mounting_plate"] = "mounting_plate"
    units: Literal["mm"] = "mm"
    difficulty: int = Field(ge=1)
    dimensions: PartDimensions
    features: PartFeatures = Field(default_factory=PartFeatures)
    files: FileReferences = Field(default_factory=FileReferences)


class BenchmarkItem(StrictSchema):
    """A benchmark item folder plus its parsed metadata."""

    root_dir: Path
    metadata: PartMetadata

    @property
    def metadata_path(self) -> Path:
        return self.root_dir / "metadata.json"

    @property
    def drawing_path(self) -> Path:
        return self.root_dir / self.metadata.files.drawing_png

    @property
    def target_step_path(self) -> Path:
        return self.root_dir / self.metadata.files.target_step

    @property
    def target_stl_path(self) -> Path:
        return self.root_dir / self.metadata.files.target_stl
