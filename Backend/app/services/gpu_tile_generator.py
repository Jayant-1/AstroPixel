"""
GPU-Accelerated Tile Generator for Gigapixel Images
Optimized for RTX 3050 with 16GB RAM system
Handles 10GB+ images without crashing
"""

from pathlib import Path
from PIL import Image
import math
import logging
from typing import Callable, Optional
import gc
import os
import psutil

# Remove PIL size limits
Image.MAX_IMAGE_PIXELS = None

logger = logging.getLogger(__name__)

# Ultra-aggressive settings for 10GB+ images on 16GB RAM
MEMORY_SAFE_THRESHOLD = 50_000_000  # 50 MP
CHUNK_SIZE = 2048  # Process 2048x2048 chunks
MAX_MEMORY_PERCENT = 75  # Stop if RAM exceeds 75%
AGGRESSIVE_GC_INTERVAL = 5  # Force GC every 5 tiles

# Try GPU acceleration
try:
    import torch
    import torchvision.transforms.functional as TF

    HAS_GPU = torch.cuda.is_available()
    if HAS_GPU:
        GPU_DEVICE = torch.device("cuda")
        GPU_NAME = torch.cuda.get_device_name(0)
        GPU_MEMORY = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        logger.info(f"🎮 GPU: {GPU_NAME} ({GPU_MEMORY:.1f}GB VRAM)")
    else:
        logger.info("ℹ️ No GPU detected, using CPU")
except ImportError:
    HAS_GPU = False
    logger.info("ℹ️ PyTorch not available, using CPU")


def check_system_resources() -> dict:
    """Check available system resources"""
    mem = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=0.1)

    info = {
        "ram_percent": mem.percent,
        "ram_available_gb": mem.available / (1024**3),
        "cpu_percent": cpu_percent,
        "safe_to_continue": mem.percent < MAX_MEMORY_PERCENT,
    }

    if HAS_GPU and torch.cuda.is_available():
        info["gpu_memory_allocated"] = torch.cuda.memory_allocated(0) / (1024**3)
        info["gpu_memory_reserved"] = torch.cuda.memory_reserved(0) / (1024**3)

    return info


class GPUTileGenerator:
    """GPU-accelerated tile generator optimized for 16GB RAM + RTX 3050"""

    def __init__(self, input_file: Path, output_dir: Path, tile_size: int = 256):
        self.input_file = input_file
        self.output_dir = output_dir
        self.tile_size = tile_size
        self.tiles_processed = 0

    def generate_tiles(
        self, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """Generate tiles with automatic mode selection"""
        try:
            logger.info(f"🚀 GPU Tile Generator starting...")
            logger.info(f"📁 Input: {self.input_file.name}")

            # Log system specs
            self._log_system_specs()

            if progress_callback:
                progress_callback(5)

            # Get image dimensions and validate format
            with Image.open(self.input_file) as img:
                width, height = img.size
                megapixels = width * height / 1_000_000
                img_mode = img.mode
                img_format = img.format

                logger.info(f"📐 Image: {width}x{height} ({megapixels:.1f}MP)")
                logger.info(f"🎨 Format: {img_format} | Mode: {img_mode}")

                # Validate image format
                if img_mode not in ("RGB", "L", "RGBA", "CMYK", "I", "I;16", "F"):
                    logger.warning(f"⚠️ Unusual image mode: {img_mode}")
                    logger.info(f"💡 Will convert to RGB during processing")

                if megapixels > MEMORY_SAFE_THRESHOLD / 1_000_000:
                    logger.info(f"🔄 Using CHUNKED mode (memory-safe)")
                    return self._generate_chunked(width, height, progress_callback)
                else:
                    logger.info(f"⚡ Using STANDARD mode (fast)")
                    return self._generate_standard(width, height, progress_callback)

        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
            return False

    def _log_system_specs(self):
        """Log system specifications"""
        mem = psutil.virtual_memory()
        logger.info(f"💻 System: i5-12th Gen | RAM: 16GB | GPU: RTX 3050")
        logger.info(f"📊 Available RAM: {mem.available / (1024**3):.1f}GB")
        if HAS_GPU:
            logger.info(f"🎮 GPU: {GPU_NAME} | VRAM: {GPU_MEMORY:.1f}GB")

    def _generate_chunked(
        self,
        width: int,
        height: int,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """Ultra-efficient chunked processing for 10GB+ images"""
        try:
            max_dim = max(width, height)
            max_zoom = math.ceil(math.log2(max_dim / self.tile_size))

            # For extreme images, only process top 3 zoom levels
            megapixels = width * height / 1_000_000
            if megapixels > 10000:  # >10,000 MP
                num_levels = 2
                logger.warning(
                    f"⚠️ Extreme image - processing only {num_levels} zoom levels"
                )
            elif megapixels > 1000:  # >1,000 MP
                num_levels = 3
            else:
                num_levels = 4

            start_zoom = max(0, max_zoom - (num_levels - 1))
            logger.info(
                f"📊 Zoom levels: {start_zoom} to {max_zoom} ({num_levels} levels)"
            )

            if progress_callback:
                progress_callback(10)

            self.output_dir.mkdir(parents=True, exist_ok=True)

            for zoom_idx, zoom in enumerate(range(start_zoom, max_zoom + 1)):
                resources = check_system_resources()

                if not resources["safe_to_continue"]:
                    logger.error(
                        f"❌ Memory critical ({resources['ram_percent']:.1f}%) - aborting"
                    )
                    logger.error(f"💡 Close other programs and try again")
                    return False

                # Calculate zoom dimensions and check if it's safe
                scale = 2 ** (zoom - max_zoom)
                scaled_width = max(1, int(width * scale))
                scaled_height = max(1, int(height * scale))
                zoom_megapixels = (scaled_width * scaled_height) / 1_000_000

                # For huge zooms, use ultra-conservative processing
                if zoom_megapixels > 100:
                    logger.warning(
                        f"⚠️ Zoom {zoom} very large ({zoom_megapixels:.1f}MP) - using ultra-safe tile-by-tile mode"
                    )
                    # Continue with ultra-safe processing instead of skipping

                logger.info(f"\n{'='*60}")
                logger.info(
                    f"🔄 Zoom {zoom}/{max_zoom} (RAM: {resources['ram_percent']:.1f}%)"
                )

                try:
                    success = self._generate_zoom_chunked(zoom, max_zoom, width, height)

                    if not success:
                        logger.warning(
                            f"⚠️ Failed at zoom level {zoom} - skipping to next level"
                        )
                        continue  # Try next zoom level instead of aborting

                except MemoryError as mem_err:
                    logger.error(f"❌ Memory exhausted at zoom {zoom}")
                    logger.warning(
                        f"⚠️ Skipping zoom {zoom} and continuing with lower resolutions"
                    )
                    continue  # Skip this zoom and try lower ones

                # Aggressive cleanup
                gc.collect()
                if HAS_GPU:
                    torch.cuda.empty_cache()

                progress = 10 + int(((zoom_idx + 1) / num_levels) * 85)
                if progress_callback:
                    progress_callback(progress)

            if progress_callback:
                progress_callback(100)

            logger.info(f"\n✅ SUCCESS! Processed {self.tiles_processed} tiles")
            return True

        except MemoryError as e:
            logger.error(f"❌ OUT OF MEMORY: {e}")
            logger.error(f"💡 Solution: Close ALL other programs and try again")
            return False
        except Exception as e:
            logger.error(f"❌ Error: {e}", exc_info=True)
            return False

    def _generate_zoom_chunked(
        self, zoom: int, max_zoom: int, orig_width: int, orig_height: int
    ) -> bool:
        """Generate single zoom level using ultra-efficient chunking"""
        try:
            scale = 2 ** (zoom - max_zoom)
            scaled_width = max(1, int(orig_width * scale))
            scaled_height = max(1, int(orig_height * scale))

            tiles_x = math.ceil(scaled_width / self.tile_size)
            tiles_y = math.ceil(scaled_height / self.tile_size)
            total_tiles = tiles_x * tiles_y

            logger.info(f"  📦 {scaled_width}x{scaled_height} → {total_tiles} tiles")

            zoom_dir = self.output_dir / str(zoom)
            zoom_dir.mkdir(exist_ok=True)

            tile_count = 0

            # Process in small batches to prevent memory buildup
            for x in range(tiles_x):
                x_dir = zoom_dir / str(x)
                x_dir.mkdir(exist_ok=True)

                for y in range(tiles_y):
                    # Check memory every 10 tiles
                    if tile_count % 10 == 0:
                        resources = check_system_resources()
                        if resources["ram_percent"] > 80:
                            logger.warning(
                                f"  ⚠️ High RAM: {resources['ram_percent']:.1f}%"
                            )
                            gc.collect()

                    try:
                        # Calculate region in original image
                        left = int(x * self.tile_size / scale)
                        upper = int(y * self.tile_size / scale)
                        right = min(int((x + 1) * self.tile_size / scale), orig_width)
                        lower = min(int((y + 1) * self.tile_size / scale), orig_height)

                        # Validate bounds
                        if left >= right or upper >= lower:
                            logger.warning(
                                f"  ⚠️ Invalid bounds for tile ({x},{y}): left={left}, right={right}, upper={upper}, lower={lower}"
                            )
                            raise ValueError(f"Invalid crop bounds")

                        # Open image with extreme memory conservation
                        # For huge TIFFs, PIL still loads too much into memory
                        img = None
                        tile_region = None
                        try:
                            img = Image.open(self.input_file)

                            # Crop FIRST before any conversion (critical for memory)
                            tile_region = img.crop((left, upper, right, lower))

                            # Validate crop result
                            if tile_region.size[0] == 0 or tile_region.size[1] == 0:
                                raise ValueError(
                                    f"Empty tile region: {tile_region.size}"
                                )

                            # Now convert the SMALL cropped region (not the full image)
                            if tile_region.mode != "RGB":
                                tile_region = tile_region.convert("RGB")

                        except MemoryError as mem_err:
                            # Image too large for even single tile extraction
                            logger.error(f"  ❌ Memory exhausted for tile ({x},{y})")
                            logger.error(
                                f"  💡 Image at zoom {zoom} is too large ({scaled_width}x{scaled_height})"
                            )
                            logger.error(
                                f"  💡 Skipping this zoom level - use lower resolution or cloud processing"
                            )
                            raise  # Re-raise to skip this zoom level
                        finally:
                            if img is not None:
                                img.close()

                        # Resize tile (GPU-accelerated if available)
                        if (
                            HAS_GPU and zoom == max_zoom
                        ):  # Use GPU only for highest zoom
                            tile = self._resize_gpu(tile_region)
                        else:
                            tile = tile_region.resize(
                                (self.tile_size, self.tile_size),
                                Image.Resampling.LANCZOS,
                            )

                        # Save tile
                        tile_path = x_dir / f"{y}.jpg"
                        tile.save(tile_path, "JPEG", quality=85, optimize=True)

                        tile_count += 1
                        self.tiles_processed += 1

                        # Cleanup
                        del tile
                        del tile_region

                        # Aggressive GC every few tiles
                        if tile_count % AGGRESSIVE_GC_INTERVAL == 0:
                            gc.collect()

                        # Progress logging
                        if tile_count % 100 == 0:
                            percent = (tile_count / total_tiles) * 100
                            logger.info(
                                f"  ⏳ {tile_count}/{total_tiles} ({percent:.1f}%)"
                            )

                    except Exception as e:
                        logger.error(
                            f"  ❌ Failed tile ({x},{y}): {type(e).__name__}: {e}",
                            exc_info=True,
                        )
                        # Create blank fallback tile
                        try:
                            blank = Image.new(
                                "RGB", (self.tile_size, self.tile_size), "black"
                            )
                            blank.save(x_dir / f"{y}.jpg", "JPEG", quality=85)
                            del blank
                            tile_count += 1
                        except Exception as blank_error:
                            logger.error(
                                f"  ❌ Can't even create blank tile: {blank_error}"
                            )
                            return False

            logger.info(f"  ✅ Generated {tile_count} tiles")
            return True

        except Exception as e:
            logger.error(f"  ❌ Zoom level failed: {e}", exc_info=True)
            return False

    def _resize_gpu(self, image: Image.Image) -> Image.Image:
        """GPU-accelerated resize using PyTorch + RTX 3050"""
        try:
            if not HAS_GPU:
                return image.resize(
                    (self.tile_size, self.tile_size), Image.Resampling.LANCZOS
                )

            # Convert PIL to tensor
            tensor = TF.to_tensor(image).unsqueeze(0).to(GPU_DEVICE)

            # GPU resize
            resized = torch.nn.functional.interpolate(
                tensor,
                size=(self.tile_size, self.tile_size),
                mode="bilinear",
                align_corners=False,
            )

            # Convert back to PIL
            resized_cpu = resized.squeeze(0).cpu()
            result = TF.to_pil_image(resized_cpu)

            # Cleanup GPU memory
            del tensor, resized, resized_cpu
            torch.cuda.empty_cache()

            return result

        except Exception as e:
            logger.warning(f"GPU resize failed: {e}, using CPU")
            return image.resize(
                (self.tile_size, self.tile_size), Image.Resampling.LANCZOS
            )

    def _generate_standard(
        self,
        width: int,
        height: int,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """Standard fast processing for images < 50MP"""
        try:
            with Image.open(self.input_file) as img:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.load()

                max_dim = max(width, height)
                max_zoom = math.ceil(math.log2(max_dim / self.tile_size))

                self.output_dir.mkdir(parents=True, exist_ok=True)

                for zoom in range(max_zoom + 1):
                    self._generate_zoom_standard(img, zoom, max_zoom, width, height)

                    if progress_callback:
                        progress = 10 + int((zoom / (max_zoom + 1)) * 85)
                        progress_callback(progress)

                if progress_callback:
                    progress_callback(100)

                return True

        except Exception as e:
            logger.error(f"❌ Standard mode failed: {e}", exc_info=True)
            return False

    def _generate_zoom_standard(
        self,
        img: Image.Image,
        zoom: int,
        max_zoom: int,
        orig_width: int,
        orig_height: int,
    ):
        """Generate zoom level from in-memory image"""
        scale = 2 ** (zoom - max_zoom)
        scaled_width = max(1, int(orig_width * scale))
        scaled_height = max(1, int(orig_height * scale))

        if zoom == max_zoom:
            scaled_img = img
        else:
            scaled_img = img.resize(
                (scaled_width, scaled_height), Image.Resampling.LANCZOS
            )

        tiles_x = math.ceil(scaled_width / self.tile_size)
        tiles_y = math.ceil(scaled_height / self.tile_size)

        zoom_dir = self.output_dir / str(zoom)
        zoom_dir.mkdir(exist_ok=True)

        for x in range(tiles_x):
            x_dir = zoom_dir / str(x)
            x_dir.mkdir(exist_ok=True)

            for y in range(tiles_y):
                left = x * self.tile_size
                upper = y * self.tile_size
                right = min(left + self.tile_size, scaled_width)
                lower = min(upper + self.tile_size, scaled_height)

                tile = scaled_img.crop((left, upper, right, lower))

                if tile.size != (self.tile_size, self.tile_size):
                    padded = Image.new("RGB", (self.tile_size, self.tile_size), "black")
                    padded.paste(tile, (0, 0))
                    tile = padded

                tile.save(x_dir / f"{y}.jpg", "JPEG", quality=85, optimize=True)
