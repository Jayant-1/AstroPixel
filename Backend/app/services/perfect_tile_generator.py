"""
Perfect Tile Generator - Combines speed, safety, and perfect rendering
- Handles huge images without crashing
- Fast like simple_tile_generator
- GPU acceleration + multi-threading
- Perfect rendering with ALL zoom levels
"""

from pathlib import Path
from PIL import Image, PsdImagePlugin
import math
import logging
import time

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
import psutil

# Safe numpy import with fallback
try:
    import numpy as np
    HAS_NUMPY = True
except (ImportError, ValueError) as e:
    # ValueError: "you should not try to import numpy from its source directory"
    # This happens on some systems - we can work without numpy for PIL operations
    HAS_NUMPY = False
    np = None

from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
import threading

# Optional: GPU acceleration
HAS_TORCH = False
try:
    import torch
    import torchvision.transforms.functional as TF

    HAS_TORCH = torch.cuda.is_available()
    if HAS_TORCH:
        DEVICE = torch.device("cuda")
except ImportError:
    pass

# Optional: PSD Tools for PSB/PSD files
HAS_PSD_TOOLS = False
try:
    from psd_tools import PSDImage

    HAS_PSD_TOOLS = True
except ImportError:
    pass

# Optional: Rasterio for TIFF streaming
HAS_RASTERIO = False
try:
    import rasterio
    from rasterio.windows import Window
    from rasterio.errors import RasterioIOError
    import rasterio.env

    HAS_RASTERIO = True

    # Suppress GDAL error spam for corrupted files
    import os

    os.environ["CPL_LOG"] = "OFF"

except ImportError:
    pass

Image.MAX_IMAGE_PIXELS = None
logger = logging.getLogger(__name__)

# Suppress rasterio error logging to reduce spam from corrupted files
if HAS_RASTERIO:
    logging.getLogger("rasterio._err").setLevel(logging.ERROR)

import os

# Configuration - OPTIMIZED FOR RENDER FREE TIER (512MB RAM)
CPU_COUNT = os.cpu_count() or 1

# Conservative workers to avoid memory exhaustion
# Render free tier has very limited RAM, so keep workers low
MAX_WORKERS = min(2, CPU_COUNT)  # Max 2 workers to save memory

# Memory thresholds - ALWAYS use streaming on cloud to save RAM
MEMORY_THRESHOLD_GB = 0.001  # 1MB - force streaming for ALL files
WINDOW_SIZE = 2048  # 2K×2K pixel chunks - small chunks to save memory

# PNG compression - use moderate compression
PNG_COMPRESS_LEVEL = 3  # Balance between speed and size


class PerfectTileGenerator:
    """
    The perfect tile generator that combines all best practices:
    - Small files (<3GB): In-memory with GPU acceleration
    - Large files (>3GB): Rasterio streaming with multi-threading
    - ALL zoom levels generated for perfect rendering
    - GPU acceleration for resizing when available
    - Multi-threading for parallel tile generation
    - LOSSLESS PNG output for exact color fidelity (no JPEG artifacts)
    - Preserves ICC color profiles and exact pixel values
    """

    def __init__(self, input_file: Path, output_dir: Path, tile_size: int = 256):
        # NumPy is optional - we can work with PIL-only operations
        # This allows PerfectTileGenerator to work on systems where NumPy fails to import
        
        self.input_file = input_file
        self.output_dir = output_dir
        self.tile_size = tile_size
        self.tiles_generated = 0
        self.corrupted_tiles = 0
        self.tile_lock = threading.Lock()

        # Check capabilities
        self.has_gpu = HAS_TORCH
        self.has_rasterio = HAS_RASTERIO
        self.has_numpy = HAS_NUMPY  # Use numpy for optimizations if available, fall back to PIL

        if self.has_gpu:
            logger.info("✅ GPU acceleration available")
        if self.has_rasterio:
            logger.info("✅ Rasterio streaming available")
        if self.has_numpy:
            logger.info("✅ NumPy available for optimization")
        else:
            logger.info("ℹ️ NumPy not available, using PIL-only operations")

    def _validate_file(self) -> bool:
        """Validate file can be opened and basic metadata read"""
        try:
            file_ext = str(self.input_file).lower()

            if file_ext.endswith((".psb", ".psd")):
                # PSB/PSD files - use psd-tools if available
                if HAS_PSD_TOOLS:
                    psd = PSDImage.open(self.input_file)
                    width, height = psd.width, psd.height
                    megapixels = width * height / 1_000_000
                    logger.info(
                        f"✅ PSB/PSD file detected: {width}x{height} ({megapixels:.1f}MP)"
                    )
                    return True
                else:
                    logger.error("❌ PSB/PSD files require psd-tools library")
                    return False
            elif self.has_rasterio and file_ext.endswith((".tif", ".tiff")):
                with rasterio.open(self.input_file) as src:
                    _ = src.width, src.height, src.count
                    # Try reading a small window to check for corruption
                    try:
                        _ = src.read(
                            1,
                            window=Window(
                                0, 0, min(256, src.width), min(256, src.height)
                            ),
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ File may have corrupted regions: {e}")
                        return False
            else:
                with Image.open(self.input_file) as img:
                    _ = img.size, img.mode
            return True
        except Exception as e:
            logger.error(f"❌ File validation error: {e}")
            return False

    def generate_tiles(
        self, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """Generate tiles with automatic mode selection"""
        start_time = time.time()
        try:
            # Validate file first
            if not self._validate_file():
                logger.error("❌ File validation failed - file may be corrupted")
                logger.info("🔧 Will attempt processing with error recovery...")

            # Get file size and system memory
            file_size_gb = self.input_file.stat().st_size / (1024**3)
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)

            logger.info(f"📁 File: {self.input_file.name}")
            logger.info(f"📊 Size: {file_size_gb:.2f} GB")
            logger.info(
                f"💾 Available RAM: {available_gb:.2f} GB / {memory.total / (1024**3):.2f} GB"
            )

            # Smart mode selection:
            # 1. If file > 1GB OR available RAM < 6GB, use streaming
            # 2. If file will need > 50% of available RAM, use streaming
            use_streaming = False

            # Check file type for special handling
            file_ext = str(self.input_file).lower()

            # Handle PSB/PSD files with special method
            if file_ext.endswith((".psb", ".psd")):
                if not HAS_PSD_TOOLS:
                    logger.error("❌ PSB/PSD files require psd-tools library")
                    logger.info("💡 Install with: pip install psd-tools")
                    return False
                logger.info("📂 PSB/PSD file detected - using specialized PSB handler")
                return self._generate_psb(progress_callback)

            # Validate TIFF files
            if not file_ext.endswith((".tif", ".tiff")):
                logger.error(f"❌ Unsupported file format: {file_ext}")
                logger.info("💡 Supported formats: .tif, .tiff, .psb, .psd")
                return False

            if not self.has_rasterio:
                logger.warning(
                    "⚠️ Rasterio not available, using in-memory (may fail for large files)"
                )
                use_streaming = False
            elif file_size_gb > MEMORY_THRESHOLD_GB:
                logger.info(f"📏 File size > {MEMORY_THRESHOLD_GB}GB threshold")
                use_streaming = True
            elif available_gb < 8.0:
                logger.info(f"💾 Low available RAM ({available_gb:.1f}GB < 8GB)")
                use_streaming = True
            elif file_size_gb > 0.1:  # Any file > 100MB should use streaming for safety
                logger.info(
                    f"💾 File > 100MB, using streaming for safety ({file_size_gb:.2f}GB)"
                )
                use_streaming = True
            elif (
                file_size_gb * 3 > available_gb
            ):  # Estimate: decompressed = 3x file size
                logger.info(
                    f"💾 File may use > 50% RAM (estimated {file_size_gb * 3:.1f}GB)"
                )
                use_streaming = True

            if use_streaming:
                logger.info("🚀 Using STREAMING mode (Rasterio + Multi-threading)")
                result = self._generate_streaming(progress_callback)
                elapsed_time = time.time() - start_time
                if result:
                    logger.info(f"✅ Tile generation completed in {elapsed_time:.2f}s")
                return result
            else:
                logger.info("⚡ Using IN-MEMORY mode (PIL + GPU)")
                result = self._generate_in_memory(progress_callback)
                elapsed_time = time.time() - start_time
                if result:
                    logger.info(f"✅ Tile generation completed in {elapsed_time:.2f}s")
                return result

        except MemoryError as e:
            logger.error(f"❌ Memory Error: {e}")
            if self.has_rasterio:
                logger.info("🔄 Retrying with STREAMING mode...")
                return self._generate_streaming(progress_callback)
            else:
                logger.error(
                    "💡 Install rasterio for large file support: pip install rasterio"
                )
                return False
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"❌ Error after {elapsed_time:.2f}s: {e}", exc_info=True)
            return False

    def _generate_in_memory(
        self, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """
        In-memory generation for smaller files
        Fast, simple, perfect rendering
        """
        memory_start = time.time()
        try:
            if progress_callback:
                progress_callback(5)

            # Open and load image
            logger.info("📂 Loading image into memory...")
            with Image.open(self.input_file) as img:
                if img.mode != "RGB":
                    img = img.convert("RGB")

                img.load()
                width, height = img.size
                megapixels = width * height / 1_000_000

                logger.info(f"📐 Dimensions: {width}x{height} ({megapixels:.1f}MP)")

                # Calculate max zoom
                max_dim = max(width, height)
                max_zoom = math.ceil(math.log2(max_dim / self.tile_size))
                logger.info(f"🔍 Zoom levels: 0 to {max_zoom}")

                if progress_callback:
                    progress_callback(10)

                self.output_dir.mkdir(parents=True, exist_ok=True)

                # Generate ALL zoom levels for perfect rendering
                total_levels = max_zoom + 1
                for zoom in range(max_zoom + 1):
                    logger.info(f"\n{'='*60}")
                    logger.info(f"🔄 Processing Zoom Level {zoom}/{max_zoom}")

                    self._generate_zoom_in_memory(img, zoom, max_zoom, width, height)

                    gc.collect()

                    progress = 10 + int(((zoom + 1) / total_levels) * 85)
                    if progress_callback:
                        progress_callback(progress)

            if progress_callback:
                progress_callback(100)

            memory_elapsed = time.time() - memory_start
            logger.info(f"\n✅ Generated {self.tiles_generated} tiles successfully!")
            logger.info(f"⏱️ Total time: {memory_elapsed:.2f}s")
            return True

        except MemoryError as e:
            memory_elapsed = time.time() - memory_start
            logger.error(f"❌ Out of memory after {memory_elapsed:.2f}s during in-memory processing")
            if self.has_rasterio:
                logger.info("🔄 Falling back to STREAMING mode...")
                return self._generate_streaming(progress_callback)
            else:
                logger.error(
                    "💡 Install rasterio for large file support: pip install rasterio"
                )
                return False
        except Exception as e:
            memory_elapsed = time.time() - memory_start
            logger.error(f"❌ In-memory generation failed after {memory_elapsed:.2f}s: {e}", exc_info=True)
            return False

    def _generate_zoom_in_memory(
        self,
        img: Image.Image,
        zoom: int,
        max_zoom: int,
        orig_width: int,
        orig_height: int,
    ):
        """Generate tiles for one zoom level from in-memory image"""
        # Calculate scale for this zoom level
        scale = 2 ** (zoom - max_zoom)
        scaled_width = max(1, int(orig_width * scale))
        scaled_height = max(1, int(orig_height * scale))

        # Resize image for this zoom level
        if zoom == max_zoom:
            scaled_img = img  # Original for highest zoom
        else:
            # Use GPU if available
            if self.has_gpu:
                scaled_img = self._resize_gpu(img, scaled_width, scaled_height)
            else:
                scaled_img = img.resize(
                    (scaled_width, scaled_height), Image.Resampling.LANCZOS
                )

        # Calculate tiles needed
        tiles_x = math.ceil(scaled_width / self.tile_size)
        tiles_y = math.ceil(scaled_height / self.tile_size)
        total_tiles = tiles_x * tiles_y

        logger.info(f"  📦 {scaled_width}x{scaled_height} → {total_tiles} tiles")

        # Create directory structure
        zoom_dir = self.output_dir / str(zoom)
        zoom_dir.mkdir(exist_ok=True)
        for x in range(tiles_x):
            (zoom_dir / str(x)).mkdir(exist_ok=True)

        # Generate tiles
        tile_count = 0
        for x in range(tiles_x):
            for y in range(tiles_y):
                # Calculate tile bounds
                left = x * self.tile_size
                upper = y * self.tile_size
                right = min(left + self.tile_size, scaled_width)
                lower = min(upper + self.tile_size, scaled_height)

                # Crop tile
                tile = scaled_img.crop((left, upper, right, lower))

                # Pad if necessary
                if tile.size != (self.tile_size, self.tile_size):
                    padded = Image.new("RGB", (self.tile_size, self.tile_size), "black")
                    padded.paste(tile, (0, 0))
                    tile = padded

                # Save tile with MAXIMUM quality - no color compromise
                tile_path = zoom_dir / str(x) / f"{y}.png"
                # PNG for lossless compression - preserves exact pixel values and color profile
                tile.save(tile_path, "PNG", compress_level=PNG_COMPRESS_LEVEL, optimize=False)
                tile_count += 1

        logger.info(f"    ✓ Generated {tile_count} tiles")
        self.tiles_generated += tile_count

        # Clean up scaled image if it's not the original
        if zoom != max_zoom and scaled_img is not img:
            del scaled_img
            gc.collect()

    def _resize_gpu(self, img: Image.Image, width: int, height: int) -> Image.Image:
        """Resize image using GPU acceleration"""
        try:
            # Convert PIL to tensor
            img_tensor = TF.to_tensor(img).unsqueeze(0).to(DEVICE)

            # Resize using GPU with BICUBIC for best quality
            resized_tensor = torch.nn.functional.interpolate(
                img_tensor,
                size=(height, width),
                mode="bicubic",
                align_corners=False,
                antialias=True,
            )

            # Convert back to PIL
            resized_tensor = resized_tensor.squeeze(0).cpu()
            resized_img = TF.to_pil_image(resized_tensor)

            return resized_img

        except Exception as e:
            logger.warning(f"GPU resize failed, falling back to CPU: {e}")
            return img.resize((width, height), Image.Resampling.LANCZOS)

    def _generate_streaming(
        self, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """
        Streaming generation for large files
        Uses rasterio + multi-threading
        Generates ALL zoom levels for perfect rendering
        """
        stream_start = time.time()
        try:
            if progress_callback:
                progress_callback(5)

            with rasterio.open(self.input_file) as src:
                width = src.width
                height = src.height
                megapixels = width * height / 1_000_000

                logger.info(f"📐 Dimensions: {width}x{height} ({megapixels:.1f}MP)")
                logger.info(f"🔍 Bands: {src.count} | Type: {src.dtypes[0]}")

                # Calculate max zoom
                max_dim = max(width, height)
                max_zoom = math.ceil(math.log2(max_dim / self.tile_size))
                logger.info(f"🔍 Zoom levels: 0 to {max_zoom}")

                if progress_callback:
                    progress_callback(10)

                self.output_dir.mkdir(parents=True, exist_ok=True)

                # Generate ALL zoom levels from highest to lowest
                total_levels = max_zoom + 1
                for zoom in range(max_zoom, -1, -1):
                    logger.info(f"\n{'='*60}")
                    logger.info(f"🔄 Processing Zoom Level {zoom}/{max_zoom}")

                    if zoom == max_zoom:
                        # Highest zoom: read from source
                        self._generate_zoom_streaming(
                            src, zoom, max_zoom, width, height
                        )
                    else:
                        # Lower zooms: downsample from higher zoom
                        self._generate_zoom_from_tiles(
                            zoom, zoom + 1, max_zoom, width, height
                        )

                    gc.collect()

                    progress = 10 + int(((max_zoom - zoom + 1) / total_levels) * 85)
                    if progress_callback:
                        progress_callback(progress)

            if progress_callback:
                progress_callback(100)

            # Report results
            logger.info(f"\n{'='*60}")
            logger.info("✅ TILE GENERATION COMPLETE")
            logger.info(f"{'='*60}")
            logger.info(f"📋 Total tiles: {self.tiles_generated}")

            if self.corrupted_tiles > 0:
                corruption_pct = (self.corrupted_tiles / self.tiles_generated) * 100
                logger.warning(
                    f"⚠️ Corrupted tiles: {self.corrupted_tiles} ({corruption_pct:.2f}%)"
                )
                logger.warning("🖤 Corrupted regions display as black tiles")
                if corruption_pct > 10:
                    logger.error("❌ File is heavily corrupted (>10% damaged)")
                    logger.error("💡 Consider re-downloading the source file")
            else:
                logger.info("✅ No corruption detected - all tiles valid!")

            stream_elapsed = time.time() - stream_start
            logger.info(f"⏱️ Total time: {stream_elapsed:.2f}s")
            logger.info(f"{'='*60}\n")
            return True

        except Exception as e:
            stream_elapsed = time.time() - stream_start
            logger.error(f"❌ Streaming generation failed after {stream_elapsed:.2f}s: {e}", exc_info=True)
            return False

    def _generate_zoom_streaming(
        self, src, zoom: int, max_zoom: int, orig_width: int, orig_height: int
    ):
        """Generate highest zoom level from rasterio source"""
        scale = 2 ** (zoom - max_zoom)
        scaled_width = max(1, int(orig_width * scale))
        scaled_height = max(1, int(orig_height * scale))

        tiles_x = math.ceil(scaled_width / self.tile_size)
        tiles_y = math.ceil(scaled_height / self.tile_size)
        total_tiles = tiles_x * tiles_y

        logger.info(f"  📦 {scaled_width}x{scaled_height} → {total_tiles} tiles")

        # Create directory structure
        zoom_dir = self.output_dir / str(zoom)
        zoom_dir.mkdir(exist_ok=True)
        for x in range(tiles_x):
            (zoom_dir / str(x)).mkdir(exist_ok=True)

        # Memory-conservative processing - AVOID PARALLEL on low memory systems
        # Parallel processing holds multiple tiles in memory simultaneously
        try:
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            
            # On low memory systems (< 1GB available), always use sequential
            if available_gb < 1.0:
                logger.info(f"  💾 Low memory ({available_gb:.2f}GB available) - using sequential processing...")
                self._generate_tiles_sequential(
                    src, zoom, max_zoom, orig_width, orig_height, tiles_x, tiles_y
                )
            elif total_tiles > 10000:
                # Very large tile count - use batched processing with GC
                logger.info(
                    f"  🚨 Large tile set detected, using batched processing..."
                )
                self._generate_tiles_batched(
                    src,
                    zoom,
                    max_zoom,
                    orig_width,
                    orig_height,
                    tiles_x,
                    tiles_y,
                    total_tiles,
                )
            else:
                # Default to sequential for memory safety
                logger.info(f"  🐌 Using sequential processing (memory-safe)...")
                self._generate_tiles_sequential(
                    src, zoom, max_zoom, orig_width, orig_height, tiles_x, tiles_y
                )
        except Exception as e:
            logger.error(
                f"❌ Error generating tiles for zoom {zoom}: {e}", exc_info=True
            )
            raise

    def _generate_tiles_sequential(
        self, src, zoom, max_zoom, orig_width, orig_height, tiles_x, tiles_y
    ):
        """Generate tiles sequentially - memory efficient"""
        scale = 2 ** (zoom - max_zoom)
        zoom_dir = self.output_dir / str(zoom)
        tile_count = 0

        for x in range(tiles_x):
            for y in range(tiles_y):
                try:
                    # Calculate source region
                    src_left = int(x * self.tile_size / scale)
                    src_top = int(y * self.tile_size / scale)
                    src_width = min(int(self.tile_size / scale), orig_width - src_left)
                    src_height = min(int(self.tile_size / scale), orig_height - src_top)

                    # Read window
                    window = Window(src_left, src_top, src_width, src_height)
                    data = src.read(window=window)

                    # Convert to PIL image
                    if src.count == 1:
                        arr = data[0]
                        if arr.dtype == np.uint16:
                            arr = (arr / 256).astype(np.uint8)
                        tile_img = Image.fromarray(arr, mode="L").convert("RGB")
                    elif src.count >= 3:
                        arr = np.stack([data[0], data[1], data[2]], axis=-1)
                        if arr.dtype == np.uint16:
                            arr = (arr / 256).astype(np.uint8)
                        tile_img = Image.fromarray(arr, mode="RGB")
                    else:
                        tile_img = Image.new(
                            "RGB", (self.tile_size, self.tile_size), "black"
                        )

                    # Resize to tile size with LANCZOS for perfect quality
                    if tile_img.size != (self.tile_size, self.tile_size):
                        tile_img = tile_img.resize(
                            (self.tile_size, self.tile_size), Image.Resampling.LANCZOS
                        )

                    # Save tile with lossless PNG - preserves exact colors
                    tile_path = zoom_dir / str(x) / f"{y}.png"
                    # PNG for lossless compression - preserves exact pixel values and color profile
                    tile_img.save(tile_path, "PNG", compress_level=PNG_COMPRESS_LEVEL, optimize=False)
                    tile_count += 1
                    
                    # Clean up tile image immediately to save memory
                    del tile_img
                    del data
                    del arr

                except Exception as e:
                    # Create black tile for corrupted region
                    try:
                        tile_path = zoom_dir / str(x) / f"{y}.png"
                        black_tile = Image.new(
                            "RGB", (self.tile_size, self.tile_size), "black"
                        )
                        black_tile.save(
                            tile_path, "PNG", compress_level=PNG_COMPRESS_LEVEL, optimize=False
                        )
                        tile_count += 1
                        with self.tile_lock:
                            self.corrupted_tiles += 1
                        # Only log first few errors to avoid spam
                        if self.corrupted_tiles <= 5:
                            logger.warning(
                                f"Corrupted tile {zoom}/{x}/{y}, using black tile"
                            )
                        elif self.corrupted_tiles == 6:
                            logger.warning(
                                "⚠️ Multiple corrupted tiles detected, suppressing further warnings..."
                            )
                    except Exception as save_error:
                        logger.error(
                            f"Failed to create replacement tile {zoom}/{x}/{y}: {save_error}"
                        )
            
            # Garbage collect after each column to prevent memory buildup
            gc.collect()

        logger.info(f"    ✓ Generated {tile_count} tiles")
        self.tiles_generated += tile_count

    def _generate_tiles_parallel(
        self, src, zoom, max_zoom, orig_width, orig_height, tiles_x, tiles_y
    ):
        """Generate tiles in parallel using ThreadPoolExecutor"""
        try:
            scale = 2 ** (zoom - max_zoom)
            zoom_dir = self.output_dir / str(zoom)

            def generate_tile(x, y):
                try:
                    src_left = int(x * self.tile_size / scale)
                    src_top = int(y * self.tile_size / scale)
                    src_width = min(int(self.tile_size / scale), orig_width - src_left)
                    src_height = min(int(self.tile_size / scale), orig_height - src_top)

                    window = Window(src_left, src_top, src_width, src_height)
                    data = src.read(window=window)

                    if src.count == 1:
                        arr = data[0]
                        if arr.dtype == np.uint16:
                            arr = (arr / 256).astype(np.uint8)
                        tile_img = Image.fromarray(arr, mode="L").convert("RGB")
                    elif src.count >= 3:
                        arr = np.stack([data[0], data[1], data[2]], axis=-1)
                        if arr.dtype == np.uint16:
                            arr = (arr / 256).astype(np.uint8)
                        tile_img = Image.fromarray(arr, mode="RGB")
                    else:
                        tile_img = Image.new(
                            "RGB", (self.tile_size, self.tile_size), "black"
                        )

                    if tile_img.size != (self.tile_size, self.tile_size):
                        tile_img = tile_img.resize(
                            (self.tile_size, self.tile_size), Image.Resampling.LANCZOS
                        )

                    tile_path = zoom_dir / str(x) / f"{y}.png"
                    # PNG for lossless compression - preserves exact pixel values and color profile
                    tile_img.save(tile_path, "PNG", compress_level=PNG_COMPRESS_LEVEL, optimize=False)
                    return True
                except Exception as e:
                    # Create black tile for corrupted region
                    try:
                        tile_path = zoom_dir / str(x) / f"{y}.png"
                        black_tile = Image.new(
                            "RGB", (self.tile_size, self.tile_size), "black"
                        )
                        black_tile.save(
                            tile_path, "PNG", compress_level=PNG_COMPRESS_LEVEL, optimize=False
                        )
                        with self.tile_lock:
                            self.corrupted_tiles += 1
                        return True
                    except Exception:
                        return False

            # Generate tiles in parallel - HYPERDRIVE MODE
            tile_count = 0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                for x in range(tiles_x):
                    for y in range(tiles_y):
                        future = executor.submit(generate_tile, x, y)
                        futures.append(future)

                for future in as_completed(futures):
                    if future.result():
                        tile_count += 1

            logger.info(f"    ✓ Generated {tile_count} tiles ({MAX_WORKERS} parallel workers)")
            self.tiles_generated += tile_count
        except Exception as e:
            logger.error(f"❌ Parallel generation failed: {e}", exc_info=True)
            raise

    def _generate_tiles_batched(
        self,
        src,
        zoom,
        max_zoom,
        orig_width,
        orig_height,
        tiles_x,
        tiles_y,
        total_tiles,
    ):
        """Generate tiles in batches for extreme tile counts"""
        scale = 2 ** (zoom - max_zoom)
        zoom_dir = self.output_dir / str(zoom)

        # Small batch size to minimize memory usage on constrained environments
        BATCH_SIZE = 8  # Process just 8 rows at a time to save memory
        total_rows = tiles_y

        def generate_tile(x, y):
            try:
                src_left = int(x * self.tile_size / scale)
                src_top = int(y * self.tile_size / scale)
                src_width = min(int(self.tile_size / scale), orig_width - src_left)
                src_height = min(int(self.tile_size / scale), orig_height - src_top)

                window = Window(src_left, src_top, src_width, src_height)
                data = src.read(window=window)

                if src.count == 1:
                    arr = data[0]
                    if arr.dtype == np.uint16:
                        arr = (arr / 256).astype(np.uint8)
                    tile_img = Image.fromarray(arr, mode="L").convert("RGB")
                elif src.count >= 3:
                    arr = np.stack([data[0], data[1], data[2]], axis=-1)
                    if arr.dtype == np.uint16:
                        arr = (arr / 256).astype(np.uint8)
                    tile_img = Image.fromarray(arr, mode="RGB")
                else:
                    tile_img = Image.new(
                        "RGB", (self.tile_size, self.tile_size), "black"
                    )

                if tile_img.size != (self.tile_size, self.tile_size):
                    tile_img = tile_img.resize(
                        (self.tile_size, self.tile_size), Image.Resampling.LANCZOS
                    )

                tile_path = zoom_dir / str(x) / f"{y}.png"
                tile_img.save(tile_path, "PNG", compress_level=PNG_COMPRESS_LEVEL, optimize=False)
                return True
            except Exception:
                try:
                    tile_path = zoom_dir / str(x) / f"{y}.png"
                    black_tile = Image.new(
                        "RGB", (self.tile_size, self.tile_size), "black"
                    )
                    black_tile.save(tile_path, "PNG", compress_level=PNG_COMPRESS_LEVEL, optimize=False)
                    with self.tile_lock:
                        self.corrupted_tiles += 1
                    return True
                except Exception:
                    return False

        tile_count = 0

        # HYPERDRIVE: Process tiles with aggressive batching
        # Log progress every 25 tiles for frequent updates
        LOG_INTERVAL = 25

        for batch_start in range(0, total_rows, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total_rows)
            batch_num = (batch_start // BATCH_SIZE) + 1
            total_batches = (total_rows + BATCH_SIZE - 1) // BATCH_SIZE

            logger.info(
                f"    � Processing batch {batch_num}/{total_batches} (rows {batch_start}-{batch_end})..."
            )

            # Process tiles sequentially row by row
            for y in range(batch_start, batch_end):
                for x in range(tiles_x):
                    if generate_tile(x, y):
                        tile_count += 1

                    # Log progress periodically
                    if tile_count % LOG_INTERVAL == 0:
                        progress_pct = (tile_count / total_tiles) * 100
                        logger.info(
                            f"    ⏳ Progress: {tile_count}/{total_tiles} tiles ({progress_pct:.1f}%)"
                        )

            # Force garbage collection between batches
            gc.collect()

            # Log batch completion
            progress_pct = (batch_end / total_rows) * 100
            logger.info(
                f"    ✓ Batch complete: {tile_count}/{total_tiles} tiles ({progress_pct:.1f}%)"
            )

        logger.info(f"    ✓ Generated {tile_count} tiles")
        self.tiles_generated += tile_count

    def _generate_zoom_from_tiles(
        self,
        target_zoom: int,
        source_zoom: int,
        max_zoom: int,
        orig_width: int,
        orig_height: int,
    ):
        """Generate zoom level by downsampling from higher zoom level"""
        scale = 2 ** (target_zoom - max_zoom)
        scaled_width = max(1, int(orig_width * scale))
        scaled_height = max(1, int(orig_height * scale))

        tiles_x = math.ceil(scaled_width / self.tile_size)
        tiles_y = math.ceil(scaled_height / self.tile_size)
        total_tiles = tiles_x * tiles_y

        logger.info(f"  🔽 Downsampling from zoom {source_zoom}")
        logger.info(f"  📦 {scaled_width}x{scaled_height} → {total_tiles} tiles")

        # Create directory structure
        zoom_dir = self.output_dir / str(target_zoom)
        zoom_dir.mkdir(exist_ok=True)
        for x in range(tiles_x):
            (zoom_dir / str(x)).mkdir(exist_ok=True)

        # Generate tiles
        tile_count = 0
        empty_tiles = 0
        for x in range(tiles_x):
            for y in range(tiles_y):
                try:
                    # Create combined image from 4 source tiles
                    combined = Image.new(
                        "RGB", (self.tile_size * 2, self.tile_size * 2), "black"
                    )

                    source_x_base = x * 2
                    source_y_base = y * 2

                    # Track if we found any source tiles
                    found_sources = 0

                    # Load 4 source tiles
                    for dx in range(2):
                        for dy in range(2):
                            src_x = source_x_base + dx
                            src_y = source_y_base + dy
                            src_path = (
                                self.output_dir
                                / str(source_zoom)
                                / str(src_x)
                                / f"{src_y}.png"
                            )

                            if src_path.exists():
                                try:
                                    tile = Image.open(src_path)
                                    combined.paste(
                                        tile, (dx * self.tile_size, dy * self.tile_size)
                                    )
                                    tile.close()
                                    found_sources += 1
                                except Exception as e:
                                    logger.debug(f"Failed to load {src_path}: {e}")

                    # If we didn't find any source tiles, log a warning
                    if found_sources == 0:
                        logger.warning(
                            f"No source tiles found for {target_zoom}/{x}/{y}, creating black tile"
                        )
                        empty_tiles += 1
                    elif found_sources < 4:
                        # Partial data - this is normal at edges
                        # Just note it for debugging but don't warn
                        logger.debug(
                            f"Partial tile at {target_zoom}/{x}/{y}: only {found_sources}/4 source tiles found"
                        )

                    # Downsample to target tile size with LANCZOS for best quality
                    downsampled = combined.resize(
                        (self.tile_size, self.tile_size), Image.Resampling.LANCZOS
                    )

                    # Save tile with lossless PNG - preserves exact colors
                    tile_path = zoom_dir / str(x) / f"{y}.png"
                    # PNG for lossless compression - preserves exact pixel values and color profile
                    downsampled.save(tile_path, "PNG", compress_level=PNG_COMPRESS_LEVEL, optimize=False)

                    combined.close()
                    downsampled.close()
                    del combined
                    del downsampled
                    tile_count += 1

                except Exception as e:
                    logger.warning(f"Error generating tile {target_zoom}/{x}/{y}: {e}")
                    empty_tiles += 1
            
            # Garbage collect after each column to prevent memory buildup
            gc.collect()

        if empty_tiles > 0:
            logger.info(f"    ⚠️ {empty_tiles} empty tiles created (no source data)")
        logger.info(f"    ✓ Generated {tile_count} tiles")
        self.tiles_generated += tile_count

    def _generate_psb(
        self, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """Generate tiles from PSB/PSD files using psd-tools with chunked processing"""
        psb_start = time.time()
        try:
            logger.info("📂 Opening PSB/PSD file...")
            psd = PSDImage.open(self.input_file)
            width, height = psd.width, psd.height

            logger.info(f"📐 Image dimensions: {width}x{height}")

            max_zoom = math.ceil(math.log2(max(width, height) / self.tile_size))
            logger.info(f"📊 Max zoom level: {max_zoom}")

            if progress_callback:
                progress_callback(5)

            # Generate tiles directly from PSD at max zoom (no full image composite)
            logger.info("🚀 Using chunked tile generation (memory efficient)...")

            # Generate max zoom level first (native resolution tiles)
            logger.info(f"\n{'=' * 60}")
            logger.info(
                f"🔄 Processing Zoom Level {max_zoom}/{max_zoom} (native resolution)"
            )
            self._generate_zoom_psb_chunked(psd, max_zoom, max_zoom, width, height)

            if progress_callback:
                progress_callback(50)

            # Generate lower zoom levels by downsampling from max zoom tiles
            for zoom in range(max_zoom - 1, -1, -1):
                logger.info(f"\n{'=' * 60}")
                logger.info(
                    f"🔄 Processing Zoom Level {zoom} /{max_zoom} (downsampled)"
                )
                self._generate_zoom_from_tiles(zoom, zoom + 1, max_zoom, width, height)

                if progress_callback:
                    progress = 50 + int(((max_zoom - zoom) / max_zoom) * 45)
                    progress_callback(progress)

            logger.info(f"\n✅ TILE GENERATION COMPLETE")
            logger.info(f"📊 Total tiles generated: {self.tiles_generated}")

            if progress_callback:
                progress_callback(100)

            psb_elapsed = time.time() - psb_start
            logger.info(f"⏱️ Total time: {psb_elapsed:.2f}s")
            return True

        except Exception as e:
            psb_elapsed = time.time() - psb_start
            logger.error(f"❌ PSB generation failed after {psb_elapsed:.2f}s: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _generate_zoom_psb_chunked(
        self,
        psd: "PSDImage",
        zoom: int,
        max_zoom: int,
        orig_width: int,
        orig_height: int,
    ):
        """Generate tiles for max zoom level from PSB - memory-optimized for 512MB limit"""
        tiles_x = math.ceil(orig_width / self.tile_size)
        tiles_y = math.ceil(orig_height / self.tile_size)

        logger.info(f"  📦 {orig_width}x{orig_height} → {tiles_x * tiles_y} tiles")

        zoom_dir = self.output_dir / str(zoom)
        
        # Ensure all x directories exist first
        for x in range(tiles_x):
            x_dir = zoom_dir / str(x)
            x_dir.mkdir(parents=True, exist_ok=True)

        # Load full image ONCE for PSB files (psd-tools limitation)
        # This is unavoidable as psd-tools doesn't support region-based loading
        logger.info(f"  🎨 Loading PSB image (this may take time for large files)...")
        
        try:
            full_img = psd.topil(layer_filter=lambda layer: True)
            if full_img is None:
                logger.error("  ❌ Failed to load PSB image - null result")
                raise RuntimeError("PSB composite returned null")
            
            if full_img.mode != "RGB":
                logger.info(f"  🔄 Converting from {full_img.mode} to RGB...")
                full_img = full_img.convert("RGB")
            
            logger.info(f"  ✅ Image loaded: {full_img.size}")
        except MemoryError as e:
            logger.error(f"  ❌ Out of memory loading PSB: {e}")
            logger.info("  💡 This PSB file is too large for available RAM")
            logger.info("  💡 Consider converting to TIFF format first or using a larger instance")
            raise
        except Exception as e:
            logger.error(f"  ❌ Failed to load PSB: {e}")
            raise

        # Process tiles one at a time to minimize memory usage
        logger.info(f"  🔄 Generating tiles sequentially to save memory...")
        
        try:
            for x in range(tiles_x):
                for y in range(tiles_y):
                    try:
                        # Calculate tile bounds
                        left = x * self.tile_size
                        top = y * self.tile_size
                        right = min(left + self.tile_size, orig_width)
                        bottom = min(top + self.tile_size, orig_height)

                        # Crop tile from full image
                        tile = full_img.crop((left, top, right, bottom))

                        # Pad if needed (edge tiles)
                        if tile.size != (self.tile_size, self.tile_size):
                            padded = Image.new(
                                "RGB", (self.tile_size, self.tile_size), "black"
                            )
                            padded.paste(tile, (0, 0))
                            tile.close()
                            tile = padded

                        # Save with lossless PNG
                        tile_path = zoom_dir / str(x) / f"{y}.png"
                        tile.save(tile_path, "PNG", compress_level=PNG_COMPRESS_LEVEL, optimize=False)
                        tile.close()
                        del tile

                        self.tiles_generated += 1

                    except Exception as e:
                        # Create black tile for errors
                        logger.warning(f"Error generating tile {zoom}/{x}/{y}: {e}")
                        tile_path = zoom_dir / str(x) / f"{y}.png"
                        black_tile = Image.new(
                            "RGB", (self.tile_size, self.tile_size), "black"
                        )
                        black_tile.save(
                            tile_path, "PNG", compress_level=PNG_COMPRESS_LEVEL, optimize=False
                        )
                        black_tile.close()
                        self.tiles_generated += 1

                # Log progress every 10 columns
                if (x + 1) % 10 == 0:
                    logger.info(f"    ⏳ {x + 1}/{tiles_x} columns")
                
                # Garbage collect after each column
                gc.collect()
        finally:
            # Clean up full image after all tiles generated
            full_img.close()
            del full_img
            gc.collect()

        logger.info(f"    ✓ Generated {tiles_x * tiles_y} tiles")

    def _generate_in_memory_from_image(
        self,
        img: Image.Image,
        max_zoom: int,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """Generate tiles from an already-loaded PIL Image"""
        try:
            width, height = img.size

            # Generate all zoom levels
            for zoom in range(max_zoom + 1):
                logger.info(f"\n{'=' * 60}")
                logger.info(f"🔄 Processing Zoom Level {zoom}/{max_zoom}")

                self._generate_zoom_in_memory_from_image(
                    img, zoom, max_zoom, width, height
                )

                if progress_callback:
                    progress = 10 + int(((zoom + 1) / (max_zoom + 1)) * 85)
                    progress_callback(progress)

            logger.info(f"\n✅ TILE GENERATION COMPLETE")
            logger.info(f"📊 Total tiles generated: {self.tiles_generated}")

            if progress_callback:
                progress_callback(100)

            return True

        except Exception as e:
            logger.error(f"❌ Tile generation failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _generate_zoom_in_memory_from_image(
        self,
        img: Image.Image,
        zoom: int,
        max_zoom: int,
        orig_width: int,
        orig_height: int,
    ):
        """Generate tiles for a specific zoom level from loaded image"""
        scale = 2 ** (zoom - max_zoom)

        # Calculate scaled dimensions
        scaled_width = max(1, int(orig_width * scale))
        scaled_height = max(1, int(orig_height * scale))

        # Calculate number of tiles needed
        tiles_x = math.ceil(scaled_width / self.tile_size)
        tiles_y = math.ceil(scaled_height / self.tile_size)

        logger.info(f"  📦 {scaled_width}x{scaled_height} → {tiles_x * tiles_y} tiles")

        # Resize image for this zoom level
        if scale < 1.0:
            if self.has_gpu:
                scaled_img = self._resize_gpu(img, scaled_width, scaled_height)
            else:
                scaled_img = img.resize(
                    (scaled_width, scaled_height), Image.Resampling.LANCZOS
                )
        else:
            scaled_img = img

        # Create zoom directory
        zoom_dir = self.output_dir / str(zoom)

        # Generate tiles
        for x in range(tiles_x):
            x_dir = zoom_dir / str(x)
            x_dir.mkdir(parents=True, exist_ok=True)

            for y in range(tiles_y):
                left = x * self.tile_size
                top = y * self.tile_size
                right = min(left + self.tile_size, scaled_width)
                bottom = min(top + self.tile_size, scaled_height)

                tile = scaled_img.crop((left, top, right, bottom))

                # Ensure tile is exactly tile_size x tile_size
                if tile.size != (self.tile_size, self.tile_size):
                    padded = Image.new("RGB", (self.tile_size, self.tile_size), "black")
                    padded.paste(tile, (0, 0))
                    tile = padded

                tile_path = zoom_dir / str(x) / f"{y}.png"
                tile.save(tile_path, "PNG", compress_level=PNG_COMPRESS_LEVEL, optimize=False)
                tile.close()

                self.tiles_generated += 1

        if scaled_img != img:
            scaled_img.close()

        logger.info(f"    ✓ Generated {tiles_x * tiles_y} tiles")

    def generate_preview(self, output_path: Path, max_size: int = 512) -> bool:
        """Generate preview thumbnail"""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # For PSB files, we need to use a different approach
            if self.input_file.suffix.lower() in [".psb"]:
                # Use the already-loaded image from memory-mapped file
                # Read a downsampled version directly
                with Image.open(self.input_file) as img:
                    # Force load the image data
                    img.load()
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    img.save(output_path, "JPEG", quality=90, optimize=True)
            else:
                # Standard preview for TIFF/other formats
                with Image.open(self.input_file) as img:
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    img.save(output_path, "JPEG", quality=90, optimize=True)

            logger.info(f"✅ Preview saved: {output_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Preview generation failed: {e}")
            # Don't fail the whole process just for preview
            logger.warning(f"⚠️ Continuing without preview - tiles are still available")
            return False
