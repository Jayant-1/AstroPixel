"""
Memory-efficient tile generator for NASA gigapixel images
Supports chunked processing with GPU acceleration
"""

from pathlib import Path
from PIL import Image, PsdImagePlugin
import math
import logging

# Explicitly register PSD/PSB format support
Image.register_open(
    PsdImagePlugin.PsdImageFile.format,
    PsdImagePlugin.PsdImageFile,
    PsdImagePlugin._accept,
)
Image.register_extension(PsdImagePlugin.PsdImageFile.format, ".psd")
Image.register_extension(PsdImagePlugin.PsdImageFile.format, ".psb")
from typing import Callable, Optional
import gc
import os
import psutil

# Increase PIL image size limit for large NASA datasets
Image.MAX_IMAGE_PIXELS = None  # Remove limit

logger = logging.getLogger(__name__)

# Aggressive memory management thresholds
MEMORY_SAFE_THRESHOLD = 50_000_000  # 50 MP - use standard processing
CHUNK_SIZE = 4096  # Process image in 4096x4096 pixel chunks
MAX_MEMORY_PERCENT = 70  # Stop if RAM usage exceeds 70%

# Try to use GPU acceleration if available
try:
    import pillow_simd as Image_SIMD

    logger.info("✅ GPU-accelerated SIMD processing available")
    USE_SIMD = True
except ImportError:
    USE_SIMD = False
    logger.info("ℹ️ Using standard PIL (install pillow-simd for GPU acceleration)")


def check_memory():
    """Check if system has enough memory to continue"""
    memory = psutil.virtual_memory()
    if memory.percent > MAX_MEMORY_PERCENT:
        logger.warning(
            f"⚠️ High memory usage: {memory.percent}% - forcing garbage collection"
        )
        gc.collect()
        return False
    return True


class SimpleTileGenerator:
    """Generate tiles using PIL without GDAL dependencies"""

    def __init__(self, input_file: Path, output_dir: Path, tile_size: int = 256):
        self.input_file = input_file
        self.output_dir = output_dir
        self.tile_size = tile_size

    def generate_tiles(
        self, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """
        Generate image pyramid tiles

        Args:
            progress_callback: Optional callback function that receives progress (0-100)

        Returns:
            True if successful
        """
        try:
            logger.info(f"Loading image: {self.input_file}")
            if progress_callback:
                progress_callback(5)

            # Open image lazily (don't load into memory yet)
            with Image.open(self.input_file) as img:
                width, height = img.size

                # Check if image is too large for memory
                megapixels = width * height
                logger.info(
                    f"Image size: {width}x{height} ({megapixels / 1_000_000:.1f}MP)"
                )

                if megapixels > MEMORY_SAFE_THRESHOLD:
                    logger.warning(f"⚠️ Large image detected - using streaming mode")
                    return self._generate_tiles_streaming(
                        width, height, progress_callback
                    )

                # For smaller images, use standard in-memory processing
                logger.info("Using standard in-memory processing")

                # Convert to RGB if needed
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Load full image into memory
                img.load()

                # Calculate max zoom level
                max_dim = max(width, height)
                max_zoom = math.ceil(math.log2(max_dim / self.tile_size))

                logger.info(f"Generating tiles with max zoom: {max_zoom}")

                if progress_callback:
                    progress_callback(10)

                # Create output directory
                self.output_dir.mkdir(parents=True, exist_ok=True)

                # Generate tiles for each zoom level
                total_zoom_levels = max_zoom + 1
                for zoom_index, zoom in enumerate(range(max_zoom + 1)):
                    # Calculate progress: 10% to 90% for tile generation
                    base_progress = 10 + int((zoom_index / total_zoom_levels) * 80)
                    self._generate_zoom_level(img, zoom, max_zoom, width, height)

                    # Force garbage collection between zoom levels
                    gc.collect()

                    if progress_callback:
                        progress_callback(base_progress)

            if progress_callback:
                progress_callback(95)

            logger.info(f"✅ Tile generation completed for {self.input_file.name}")

            if progress_callback:
                progress_callback(100)

            return True

        except MemoryError as e:
            logger.error(f"❌ Memory error - image too large: {e}")
            logger.error(f"💡 Solutions:")
            logger.error(f"   1. Reduce image size (max recommended: 50,000x50,000)")
            logger.error(f"   2. Increase system RAM")
            logger.error(f"   3. Deploy to cloud (Railway/Render/Fly.io)")
            return False
        except OSError as e:
            logger.error(f"❌ OS error generating tiles: {e}")
            logger.error(
                f"This may be due to insufficient disk space or file permissions"
            )
            return False
        except Exception as e:
            logger.error(
                f"❌ Error generating tiles: {type(e).__name__}: {e}", exc_info=True
            )
            return False

    def _generate_tiles_streaming(
        self,
        width: int,
        height: int,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """
        Ultra-efficient streaming mode for gigapixel images (10GB+)
        Uses chunked processing to prevent memory exhaustion
        Optimized for 16GB RAM systems
        """
        try:
            # Calculate max zoom level
            max_dim = max(width, height)
            max_zoom = math.ceil(math.log2(max_dim / self.tile_size))

            logger.info(f"🚀 Chunked streaming mode activated")
            logger.info(f"   Image: {width}x{height} ({width*height/1_000_000:.1f}MP)")
            logger.info(f"   Max zoom: {max_zoom}")
            logger.info(f"   Chunk size: {CHUNK_SIZE}x{CHUNK_SIZE}")

            # Log system resources
            memory = psutil.virtual_memory()
            logger.info(
                f"   Available RAM: {memory.available / (1024**3):.1f}GB / {memory.total / (1024**3):.1f}GB"
            )

            if progress_callback:
                progress_callback(10)

            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # For extremely large images (>1000MP), only process highest 2 zoom levels
            # For large images (100-1000MP), process highest 3 zoom levels
            megapixels = width * height / 1_000_000
            if megapixels > 1000:
                num_levels = 2
                logger.info(
                    f"   ⚠️ Extremely large image - processing only {num_levels} zoom levels"
                )
            else:
                num_levels = 3

            start_zoom = max(0, max_zoom - (num_levels - 1))
            logger.info(f"   Processing zoom levels: {start_zoom} to {max_zoom}")

            total_levels = max_zoom - start_zoom + 1
            for zoom_idx, zoom in enumerate(range(start_zoom, max_zoom + 1)):
                # Check memory before starting new zoom level
                memory = psutil.virtual_memory()
                if memory.percent > 85:
                    logger.error(
                        f"❌ Memory critical: {memory.percent}% - aborting to prevent crash"
                    )
                    return False

                logger.info(
                    f"\n  📊 Starting zoom level {zoom} (RAM: {memory.percent}%)"
                )

                # Calculate progress: 10% to 80%
                base_progress = 10 + int((zoom_idx / total_levels) * 70)

                self._generate_zoom_level_streaming(zoom, max_zoom, width, height)

                # Aggressive garbage collection between zoom levels
                gc.collect()

                memory_after = psutil.virtual_memory()
                logger.info(f"  ✅ Zoom {zoom} complete (RAM: {memory_after.percent}%)")

                if progress_callback:
                    progress_callback(base_progress)

            # Generate lower zoom levels by downsampling from start_zoom
            if start_zoom > 0:
                logger.info(
                    f"\n🔽 Generating lower zoom levels (0-{start_zoom-1}) by downsampling"
                )
                self._generate_lower_zoom_levels(start_zoom, max_zoom, width, height)

                if progress_callback:
                    progress_callback(90)

            logger.info(f"\n✅ Chunked streaming generation completed successfully")
            return True

        except MemoryError as e:
            logger.error(f"❌ Out of memory: {e}")
            logger.error(
                f"💡 Try: 1) Close other programs 2) Restart computer 3) Deploy to cloud"
            )
            return False
        except Exception as e:
            logger.error(f"❌ Error in streaming mode: {e}", exc_info=True)
            return False

    def _generate_zoom_level_streaming(
        self, zoom: int, max_zoom: int, orig_width: int, orig_height: int
    ):
        """
        Generate tiles using ultra-efficient chunked processing
        Processes image in small chunks to prevent memory exhaustion
        """
        try:
            # Calculate scale for this zoom level
            scale = 2 ** (zoom - max_zoom)

            # Calculate dimensions for this zoom level
            scaled_width = max(1, int(orig_width * scale))
            scaled_height = max(1, int(orig_height * scale))

            # Calculate number of tiles needed
            tiles_x = math.ceil(scaled_width / self.tile_size)
            tiles_y = math.ceil(scaled_height / self.tile_size)

            logger.info(
                f"  Zoom {zoom}: {scaled_width}x{scaled_height} -> {tiles_x}x{tiles_y} tiles"
            )

            # Create zoom directory
            zoom_dir = self.output_dir / str(zoom)
            zoom_dir.mkdir(exist_ok=True)

            # Process in chunks to minimize memory usage
            chunk_tiles_x = max(1, CHUNK_SIZE // self.tile_size)
            chunk_tiles_y = max(1, CHUNK_SIZE // self.tile_size)

            tile_count = 0
            total_tiles = tiles_x * tiles_y

            # Process image in chunks
            for chunk_x in range(0, tiles_x, chunk_tiles_x):
                for chunk_y in range(0, tiles_y, chunk_tiles_y):
                    # Check memory before processing chunk
                    if not check_memory():
                        logger.warning("⚠️ Memory pressure - slowing down")
                        gc.collect()

                    # Calculate chunk boundaries
                    chunk_x_end = min(chunk_x + chunk_tiles_x, tiles_x)
                    chunk_y_end = min(chunk_y + chunk_tiles_y, tiles_y)

                    # Calculate region in original image for this chunk
                    left = int(chunk_x * self.tile_size / scale)
                    upper = int(chunk_y * self.tile_size / scale)
                    right = min(int(chunk_x_end * self.tile_size / scale), orig_width)
                    lower = min(int(chunk_y_end * self.tile_size / scale), orig_height)

                    # Load only this chunk from the image file
                    try:
                        with Image.open(self.input_file) as img:
                            # Convert to RGB if needed
                            if img.mode not in ("RGB", "L"):
                                img = img.convert("RGB")
                            elif img.mode == "L":
                                img = img.convert("RGB")

                            # Crop just this chunk (not the whole image!)
                            chunk = img.crop((left, upper, right, lower))
                            chunk.load()  # Force load into memory

                        # Process each tile in this chunk
                        for x in range(chunk_x, chunk_x_end):
                            x_dir = zoom_dir / str(x)
                            x_dir.mkdir(exist_ok=True)

                            for y in range(chunk_y, chunk_y_end):
                                # Calculate tile position within chunk
                                tile_left = (x - chunk_x) * self.tile_size
                                tile_upper = (y - chunk_y) * self.tile_size
                                tile_right = min(
                                    tile_left + self.tile_size, chunk.size[0]
                                )
                                tile_lower = min(
                                    tile_upper + self.tile_size, chunk.size[1]
                                )

                                # Extract tile from chunk
                                tile = chunk.crop(
                                    (tile_left, tile_upper, tile_right, tile_lower)
                                )

                                # Resize to exact tile size
                                if tile.size != (self.tile_size, self.tile_size):
                                    tile = tile.resize(
                                        (self.tile_size, self.tile_size),
                                        Image.Resampling.LANCZOS,
                                    )

                                # Save tile with optimized settings
                                tile_path = x_dir / f"{y}.jpg"
                                tile.save(
                                    tile_path,
                                    "JPEG",
                                    quality=80,
                                    optimize=True,
                                    progressive=True,
                                )
                                tile_count += 1

                                # Progress logging
                                if tile_count % 100 == 0:
                                    progress = (tile_count / total_tiles) * 100
                                    memory = psutil.virtual_memory()
                                    logger.info(
                                        f"    Progress: {tile_count}/{total_tiles} ({progress:.1f}%) - RAM: {memory.percent}%"
                                    )

                                # Free memory aggressively
                                del tile

                        # Free chunk memory
                        del chunk
                        gc.collect()

                    except Exception as e:
                        logger.error(
                            f"Error processing chunk ({chunk_x},{chunk_y}): {e}"
                        )
                        continue

            logger.info(f"    ✅ Generated {tile_count} tiles (chunked streaming mode)")

        except Exception as e:
            logger.error(
                f"Error generating zoom level {zoom} (streaming): {e}", exc_info=True
            )

    def _generate_zoom_level(
        self, img: Image, zoom: int, max_zoom: int, orig_width: int, orig_height: int
    ):
        """Generate tiles for a specific zoom level (in-memory processing)"""
        try:
            # Calculate scale for this zoom level (inverted - zoom 0 is smallest)
            scale = 2 ** (zoom - max_zoom)

            # Calculate dimensions for this zoom level
            scaled_width = max(1, int(orig_width * scale))
            scaled_height = max(1, int(orig_height * scale))

            # Resize image for this zoom level
            if zoom == max_zoom:
                scaled_img = img  # Use original for highest zoom
            else:
                scaled_img = img.resize(
                    (scaled_width, scaled_height), Image.Resampling.LANCZOS
                )

            # Calculate number of tiles needed
            tiles_x = math.ceil(scaled_width / self.tile_size)
            tiles_y = math.ceil(scaled_height / self.tile_size)

            logger.info(
                f"  Zoom {zoom}: {scaled_width}x{scaled_height} -> {tiles_x}x{tiles_y} tiles"
            )

            # Create zoom directory
            zoom_dir = self.output_dir / str(zoom)
            zoom_dir.mkdir(exist_ok=True)

            # Generate tiles
            tile_count = 0
            for x in range(tiles_x):
                x_dir = zoom_dir / str(x)
                x_dir.mkdir(exist_ok=True)

                for y in range(tiles_y):
                    # Calculate tile bounds
                    left = x * self.tile_size
                    upper = y * self.tile_size
                    right = min(left + self.tile_size, scaled_width)
                    lower = min(upper + self.tile_size, scaled_height)

                    # Crop tile from scaled image
                    tile = scaled_img.crop((left, upper, right, lower))

                    # If tile is smaller than tile_size, pad with black
                    if tile.size != (self.tile_size, self.tile_size):
                        padded_tile = Image.new(
                            "RGB", (self.tile_size, self.tile_size), color="black"
                        )
                        padded_tile.paste(tile, (0, 0))
                        tile = padded_tile

                    # Save tile
                    tile_path = x_dir / f"{y}.jpg"
                    tile.save(tile_path, "JPEG", quality=85, optimize=True)
                    tile_count += 1

            logger.info(f"    Generated {tile_count} tiles")

        except Exception as e:
            logger.error(f"Error generating zoom level {zoom}: {e}", exc_info=True)

    def _generate_lower_zoom_levels(
        self, start_zoom: int, max_zoom: int, orig_width: int, orig_height: int
    ):
        """
        Generate lower zoom levels by downsampling from start_zoom
        This fills in the missing zoom levels for large images
        """
        try:
            # Process from start_zoom-1 down to 0
            for zoom in range(start_zoom - 1, -1, -1):
                logger.info(f"  🔽 Generating zoom {zoom} from zoom {zoom + 1}")

                scale = 2 ** (zoom - max_zoom)
                scaled_width = max(1, int(orig_width * scale))
                scaled_height = max(1, int(orig_height * scale))

                tiles_x = math.ceil(scaled_width / self.tile_size)
                tiles_y = math.ceil(scaled_height / self.tile_size)

                zoom_dir = self.output_dir / str(zoom)
                zoom_dir.mkdir(exist_ok=True)

                # Create zoom directory structure
                for x in range(tiles_x):
                    x_dir = zoom_dir / str(x)
                    x_dir.mkdir(exist_ok=True)

                # Generate each tile by combining 4 tiles from zoom+1
                for x in range(tiles_x):
                    for y in range(tiles_y):
                        self._generate_tile_from_higher_zoom(zoom, x, y, zoom + 1)

                logger.info(
                    f"    ✓ Generated {tiles_x * tiles_y} tiles for zoom {zoom}"
                )

        except Exception as e:
            logger.error(f"❌ Error generating lower zoom levels: {e}", exc_info=True)

    def _generate_tile_from_higher_zoom(
        self, target_zoom: int, x: int, y: int, source_zoom: int
    ):
        """
        Generate a tile by downsampling from 4 tiles in the next higher zoom level
        """
        try:
            # Create a 2x tile_size image to hold the 4 source tiles
            combined = Image.new(
                "RGB", (self.tile_size * 2, self.tile_size * 2), "black"
            )

            # Each tile at target_zoom corresponds to 4 tiles at source_zoom (2x2 grid)
            source_x_base = x * 2
            source_y_base = y * 2

            # Load and place each of the 4 source tiles
            for dx in range(2):
                for dy in range(2):
                    source_x = source_x_base + dx
                    source_y = source_y_base + dy
                    source_tile_path = (
                        self.output_dir
                        / str(source_zoom)
                        / str(source_x)
                        / f"{source_y}.jpg"
                    )

                    if source_tile_path.exists():
                        try:
                            tile = Image.open(source_tile_path)
                            combined.paste(
                                tile, (dx * self.tile_size, dy * self.tile_size)
                            )
                            tile.close()
                        except Exception as e:
                            logger.warning(
                                f"Could not load source tile {source_tile_path}: {e}"
                            )

            # Downsample to target tile size
            downsampled = combined.resize(
                (self.tile_size, self.tile_size), Image.Resampling.BILINEAR
            )

            # Save the tile
            output_path = self.output_dir / str(target_zoom) / str(x) / f"{y}.jpg"
            downsampled.save(output_path, "JPEG", quality=80, optimize=True)

            combined.close()
            downsampled.close()

        except Exception as e:
            logger.error(f"Error generating tile {target_zoom}/{x}/{y}: {e}")

    def generate_preview(self, output_path: Path, max_size: int = 512) -> bool:
        """
        Generate preview thumbnail

        Args:
            output_path: Path to save preview
            max_size: Maximum dimension

        Returns:
            True if successful
        """
        try:
            img = Image.open(self.input_file)

            # Convert to RGB if needed
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Calculate thumbnail size maintaining aspect ratio
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save preview
            img.save(output_path, "JPEG", quality=90, optimize=True)

            logger.info(f"Generated preview: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error generating preview: {e}", exc_info=True)
            return False
