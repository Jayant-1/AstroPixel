"""
Tile generation service using GDAL
Processes GeoTIFF files into tile pyramids for web viewing
"""

from pathlib import Path
from typing import Dict, Any, Optional
import subprocess
import math
import logging
import shutil

try:
    from osgeo import gdal, osr

    HAVE_GDAL = True
except Exception:  # pragma: no cover - environment may not have GDAL
    gdal = None
    osr = None
    HAVE_GDAL = False
from PIL import Image, PsdImagePlugin
import os

from app.config import settings
from app.services.simple_tile_generator import SimpleTileGenerator

# Explicitly register PSD/PSB format support
Image.register_open(
    PsdImagePlugin.PsdImageFile.format,
    PsdImagePlugin.PsdImageFile,
    PsdImagePlugin._accept,
)
Image.register_extension(PsdImagePlugin.PsdImageFile.format, ".psd")
Image.register_extension(PsdImagePlugin.PsdImageFile.format, ".psb")

logger = logging.getLogger(__name__)

# Enable GDAL exceptions
if HAVE_GDAL and gdal is not None:
    gdal.UseExceptions()


class TileGenerator:
    """Generate tile pyramids from GeoTIFF files using GDAL"""

    def __init__(
        self,
        input_file: Path,
        output_dir: Path,
        tile_size: int = 256,
        tile_format: str = "jpg",
        quality: int = 85,
    ):
        """
        Initialize tile generator

        Args:
            input_file: Path to input GeoTIFF file
            output_dir: Directory to output tiles
            tile_size: Size of each tile (default 256x256)
            tile_format: Output format (jpg, png, webp)
            quality: JPEG quality (1-100)
        """
        self.input_file = input_file
        self.output_dir = output_dir
        self.tile_size = tile_size
        self.tile_format = tile_format
        self.quality = quality

    def get_metadata(self) -> Dict[str, Any]:
        """
        Extract metadata from GeoTIFF

        Returns:
            Dictionary containing image metadata
        """
        # If GDAL is available use it; otherwise fall back to PIL-based metadata
        if HAVE_GDAL and gdal is not None:
            try:
                dataset = gdal.Open(str(self.input_file))
                if dataset is None:
                    raise ValueError(f"Cannot open file: {self.input_file}")

                width = dataset.RasterXSize
                height = dataset.RasterYSize
                bands = dataset.RasterCount
                projection = dataset.GetProjection()
                geotransform = dataset.GetGeoTransform()

                # Calculate bounds
                ulx, xres, xskew, uly, yskew, yres = geotransform
                lrx = ulx + (width * xres)
                lry = uly + (height * yres)

                # Calculate max zoom level
                max_dim = max(width, height)
                max_zoom = math.ceil(math.log2(max_dim / self.tile_size))

                # Get driver info
                driver = dataset.GetDriver().ShortName

                metadata = {
                    "width": width,
                    "height": height,
                    "bands": bands,
                    "projection": projection,
                    "geotransform": list(geotransform),
                    "bounds": {
                        "minx": min(ulx, lrx),
                        "miny": min(uly, lry),
                        "maxx": max(ulx, lrx),
                        "maxy": max(uly, lry),
                    },
                    "max_zoom": max_zoom,
                    "driver": driver,
                    "pixel_size": {"x": abs(xres), "y": abs(yres)},
                }

                # Get band information
                band_info = []
                for i in range(1, bands + 1):
                    band = dataset.GetRasterBand(i)
                    band_info.append(
                        {
                            "band": i,
                            "datatype": gdal.GetDataTypeName(band.DataType),
                            "min": band.GetMinimum(),
                            "max": band.GetMaximum(),
                            "nodata": band.GetNoDataValue(),
                        }
                    )
                metadata["bands_info"] = band_info

                dataset = None  # Close file

                logger.info(
                    f"Extracted metadata from {self.input_file.name}: {width}x{height}, {max_zoom} zoom levels (GDAL)"
                )
                return metadata

            except Exception as e:
                logger.error(f"Error extracting metadata with GDAL: {e}")
                raise
        else:
            # Fallback using PIL to get basic image metadata
            try:
                logger.warning(
                    "GDAL not available -> using PIL fallback for metadata extraction"
                )

                # Check if file exists and log details
                if not self.input_file.exists():
                    raise FileNotFoundError(f"File not found: {self.input_file}")

                file_size = self.input_file.stat().st_size
                logger.info(
                    f"File exists: {self.input_file.name}, size: {file_size:,} bytes"
                )

                # For PSB/PSD files, read header directly since PIL doesn't support PSB well
                file_ext = self.input_file.suffix.lower()
                if file_ext in [".psb", ".psd"]:
                    # Check PSD/PSB signature and extract dimensions from header
                    with open(self.input_file, "rb") as fp:
                        signature = fp.read(4)
                        if signature != b"8BPS":
                            raise ValueError(
                                f"Invalid PSD/PSB signature: {signature.hex()}"
                            )

                        # Read version (2 bytes) - PSB = 2, PSD = 1
                        version = int.from_bytes(fp.read(2), "big")
                        logger.info(
                            f"Valid {'PSB' if version == 2 else 'PSD'} file detected (version {version})"
                        )

                        # Skip reserved bytes (6 bytes)
                        fp.read(6)

                        # Read number of channels (2 bytes)
                        channels = int.from_bytes(fp.read(2), "big")

                        # Read dimensions (depends on version)
                        if version == 2:  # PSB - 4 bytes per dimension
                            height = int.from_bytes(fp.read(4), "big")
                            width = int.from_bytes(fp.read(4), "big")
                        else:  # PSD - 4 bytes per dimension
                            height = int.from_bytes(fp.read(4), "big")
                            width = int.from_bytes(fp.read(4), "big")

                        # Read bit depth (2 bytes)
                        bit_depth = int.from_bytes(fp.read(2), "big")

                        logger.info(
                            f"PSB/PSD dimensions: {width}x{height}, {channels} channels, {bit_depth} bit"
                        )
                        bands = channels
                else:
                    img = Image.open(self.input_file)
                    width, height = img.size
                    bands = len(img.getbands())

                max_dim = max(width, height)
                max_zoom = math.ceil(math.log2(max_dim / self.tile_size))

                metadata = {
                    "width": width,
                    "height": height,
                    "bands": bands,
                    "projection": None,
                    "geotransform": None,
                    "bounds": {
                        "minx": 0.0,
                        "miny": 0.0,
                        "maxx": float(width),
                        "maxy": float(height),
                    },
                    "max_zoom": max_zoom,
                    "driver": "PIL",
                    "pixel_size": {"x": None, "y": None},
                }

                logger.info(
                    f"Extracted metadata from {self.input_file.name}: {width}x{height}, {max_zoom} zoom levels (PIL)"
                )
                return metadata

            except Exception as e:
                logger.error(f"Error extracting metadata with PIL fallback: {e}")
                raise

    def generate_tiles(self, callback: Optional[callable] = None) -> bool:
        """
        Generate tile pyramid using gdal2tiles

        Args:
            callback: Optional callback function for progress updates

        Returns:
            True if successful, False otherwise
        """
        # If GDAL is available try to use gdal2tiles, otherwise fall back to PIL generator
        if HAVE_GDAL and shutil.which("gdal2tiles.py"):
            try:
                logger.info(
                    f"Starting tile generation for {self.input_file.name} (GDAL gdal2tiles)"
                )

                # Create output directory
                self.output_dir.mkdir(parents=True, exist_ok=True)

                # Prepare gdal2tiles command
                gdal2tiles_script = shutil.which("gdal2tiles.py")
                cmd = [
                    gdal2tiles_script,
                    "--profile=raster",
                    "--resampling=lanczos",
                    "--zoom=0-{}".format(self.get_metadata()["max_zoom"]),
                    "--processes={}".format(settings.GDAL_PROCESSES),
                    "--webviewer=none",
                    "--xyz",
                    str(self.input_file),
                    str(self.output_dir),
                ]

                logger.info(f"Running command: {' '.join(cmd)}")

                # Run gdal2tiles
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=3600  # 1 hour timeout
                )

                if result.returncode != 0:
                    logger.error(f"gdal2tiles failed: {result.stderr}")
                    return False

                logger.info(f"Tile generation completed for {self.input_file.name}")

                # Optimize tiles if JPEG
                if self.tile_format == "jpg":
                    self._optimize_tiles()

                return True

            except subprocess.TimeoutExpired:
                logger.error("Tile generation timed out")
                return False
            except Exception as e:
                logger.error(f"Error generating tiles with GDAL: {e}")
                # Fall through to PIL fallback

        # PIL fallback
        try:
            logger.info(
                f"GDAL not available or failed -> using PIL SimpleTileGenerator for {self.input_file.name}"
            )
            pil_gen = SimpleTileGenerator(
                self.input_file, self.output_dir, tile_size=self.tile_size
            )
            success = pil_gen.generate_tiles(progress_callback=callback)

            if not success:
                logger.error("PIL tile generation failed")
                return False

            # Optionally re-optimize with configured quality
            if self.tile_format == "jpg":
                self._optimize_tiles()

            return True

        except Exception as e:
            logger.error(f"Error generating tiles with PIL fallback: {e}")
            return False

    def _optimize_tiles(self):
        """Optimize generated JPEG tiles for web delivery"""
        try:
            tile_count = 0
            for tile_path in self.output_dir.rglob("*.jpg"):
                try:
                    img = Image.open(tile_path)
                    img.save(
                        tile_path,
                        "JPEG",
                        quality=self.quality,
                        optimize=True,
                        progressive=True,
                    )
                    tile_count += 1
                except Exception as e:
                    logger.warning(f"Could not optimize {tile_path}: {e}")

            logger.info(f"Optimized {tile_count} tiles")
        except Exception as e:
            logger.warning(f"Error during tile optimization: {e}")

    def generate_preview(self, output_path: Path, max_size: int = 512) -> bool:
        """
        Generate a preview thumbnail

        Args:
            output_path: Path to save preview image
            max_size: Maximum dimension for preview

        Returns:
            True if successful
        """
        # Try GDAL-based preview if available
        if HAVE_GDAL and gdal is not None:
            try:
                dataset = gdal.Open(str(self.input_file))
                if dataset is None:
                    return False

                width = dataset.RasterXSize
                height = dataset.RasterYSize

                # Calculate preview size maintaining aspect ratio
                if width > height:
                    preview_width = max_size
                    preview_height = int(height * (max_size / width))
                else:
                    preview_height = max_size
                    preview_width = int(width * (max_size / height))

                # Use GDAL to create preview
                driver = gdal.GetDriverByName("JPEG")
                preview = driver.Create(
                    str(output_path),
                    preview_width,
                    preview_height,
                    min(dataset.RasterCount, 3),
                    gdal.GDT_Byte,
                )

                # Resample and write
                gdal.ReprojectImage(dataset, preview, None, None, gdal.GRA_Lanczos)

                preview = None
                dataset = None

                logger.info(f"Generated preview: {output_path} (GDAL)")
                return True

            except Exception as e:
                logger.error(f"Error generating preview with GDAL: {e}")
                # fall through to PIL fallback

        # PIL fallback preview
        try:
            logger.info(
                f"Generating preview with PIL fallback for {self.input_file.name}"
            )
            pil_gen = SimpleTileGenerator(
                self.input_file, self.output_dir, tile_size=self.tile_size
            )
            return pil_gen.generate_preview(output_path, max_size=max_size)

        except Exception as e:
            logger.error(f"Error generating preview with PIL fallback: {e}")
            return False

    @staticmethod
    def create_blank_tile(output_path: Path, tile_size: int = 256, format: str = "jpg"):
        """
        Create a blank tile for missing tiles

        Args:
            output_path: Path to save blank tile
            tile_size: Size of tile
            format: Image format
        """
        try:
            img = Image.new("RGB", (tile_size, tile_size), color="black")
            # PIL expects 'JPEG' not 'JPG'
            pil_format = "JPEG" if format.lower() == "jpg" else format.upper()
            img.save(output_path, pil_format)
            logger.info(f"Created blank tile: {output_path}")
        except Exception as e:
            logger.error(f"Error creating blank tile: {e}")
            raise


def calculate_tile_bounds(z: int, x: int, y: int) -> Dict[str, float]:
    """
    Calculate geographic bounds for a tile

    Args:
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate

    Returns:
        Dictionary with minx, miny, maxx, maxy
    """
    n = 2.0**z
    minx = x / n * 360.0 - 180.0
    maxx = (x + 1) / n * 360.0 - 180.0

    miny_rad = math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
    maxy_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))

    miny = math.degrees(miny_rad)
    maxy = math.degrees(maxy_rad)

    return {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy}
