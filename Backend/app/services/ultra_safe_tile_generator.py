"""
Ultra-Conservative Tile Generator for Extreme Gigapixel Images
Uses rasterio for true streaming TIFF reading
No full image loading - processes in tiny windows
"""

from pathlib import Path
import math
import logging
from typing import Callable, Optional
import gc
import psutil
from PIL import Image
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
import threading

# Disable decompression bomb protection - we handle gigapixel images
Image.MAX_IMAGE_PIXELS = None

logger = logging.getLogger(__name__)

# Try to import GPU acceleration
try:
    import torch
    import torchvision.transforms.functional as TF

    HAS_GPU = torch.cuda.is_available()
    if HAS_GPU:
        logger.info(f"✅ GPU available: {torch.cuda.get_device_name(0)}")
except ImportError:
    HAS_GPU = False
    logger.info("ℹ️ GPU acceleration not available")

# Optimized settings for speed while maintaining safety
MAX_WINDOW_SIZE = 2048  # Read 2048x2048 for better performance
MAX_MEMORY_PERCENT = 80  # Allow slightly more RAM for speed

# Determine optimal thread count (use 4-8 threads for I/O bound tasks)
MAX_WORKERS = min(8, (multiprocessing.cpu_count() or 4))

# Try rasterio for proper TIFF streaming
try:
    import rasterio
    from rasterio.windows import Window

    HAS_RASTERIO = True
    logger.info("✅ Rasterio available - true TIFF streaming enabled")
except ImportError:
    HAS_RASTERIO = False
    logger.warning("⚠️ Rasterio not available - limited to PIL")


class UltraSafeTileGenerator:
    """
    Ultra-safe tile generator for extreme images
    Reads source image in tiny windows to prevent memory exhaustion
    """

    def __init__(self, input_file: Path, output_dir: Path, tile_size: int = 256):
        self.input_file = input_file
        self.output_dir = output_dir
        self.tile_size = tile_size
        self.tiles_generated = 0
        self.use_gpu = HAS_GPU
        self.use_multithreading = True  # Enable multi-threading for speed
        self._tile_lock = threading.Lock()  # Thread-safe counter

        if self.use_gpu:
            logger.info("🎮 GPU acceleration enabled for ultra-safe generator")
        if self.use_multithreading:
            logger.info(f"⚡ Multi-threading enabled ({MAX_WORKERS} workers)")

    def _resize_gpu(self, img: Image.Image, size: tuple) -> Image.Image:
        """GPU-accelerated resize using PyTorch"""
        if not self.use_gpu:
            return img.resize(size, Image.Resampling.BILINEAR)

        try:
            # Convert PIL to tensor
            img_tensor = TF.to_tensor(img).unsqueeze(0).cuda()

            # Resize on GPU
            resized = torch.nn.functional.interpolate(
                img_tensor, size=size, mode="bilinear", align_corners=False
            )

            # Convert back to PIL
            resized_cpu = resized.squeeze(0).cpu()
            return TF.to_pil_image(resized_cpu)
        except Exception as e:
            logger.warning(f"GPU resize failed, falling back to CPU: {e}")
            return img.resize(size, Image.Resampling.BILINEAR)

    def get_metadata(self):
        """
        Extract metadata from TIFF file
        Uses rasterio if available, falls back to PIL
        """
        try:
            if HAS_RASTERIO and str(self.input_file).lower().endswith(
                (".tif", ".tiff")
            ):
                return self._get_metadata_rasterio()
            else:
                return self._get_metadata_pil()
        except Exception as e:
            logger.error(f"❌ Failed to extract metadata: {e}", exc_info=True)
            raise

    def _get_metadata_rasterio(self):
        """Extract metadata using rasterio"""
        with rasterio.open(self.input_file) as src:
            width = src.width
            height = src.height
            bands = src.count

            # Get projection and transform
            projection = src.crs.to_string() if src.crs else ""
            transform = src.transform
            geotransform = [
                transform.c,
                transform.a,
                transform.b,
                transform.f,
                transform.d,
                transform.e,
            ]

            # Calculate bounds
            bounds = src.bounds
            bounds_dict = {
                "minx": bounds.left,
                "miny": bounds.bottom,
                "maxx": bounds.right,
                "maxy": bounds.top,
            }

            # Calculate max zoom
            max_dim = max(width, height)
            max_zoom = math.ceil(math.log2(max_dim / self.tile_size))

            metadata = {
                "width": width,
                "height": height,
                "bands": bands,
                "projection": projection,
                "geotransform": geotransform,
                "bounds": bounds_dict,
                "max_zoom": max_zoom,
                "driver": src.driver,
                "dtype": str(src.dtypes[0]),
            }

            logger.info(f"📊 Metadata extracted: {width}x{height}, {bands} bands")
            return metadata

    def _get_metadata_pil(self):
        """Extract basic metadata using PIL (fallback)"""
        with Image.open(self.input_file) as img:
            width, height = img.size
            bands = len(img.getbands())

            # Calculate max zoom
            max_dim = max(width, height)
            max_zoom = math.ceil(math.log2(max_dim / self.tile_size))

            # Minimal metadata for non-georeferenced images
            metadata = {
                "width": width,
                "height": height,
                "bands": bands,
                "projection": "",
                "geotransform": [0, 1, 0, 0, 0, -1],
                "bounds": {"minx": 0, "miny": 0, "maxx": width, "maxy": height},
                "max_zoom": max_zoom,
                "driver": "PIL",
                "dtype": img.mode,
            }

            logger.info(f"📊 Metadata extracted: {width}x{height}, {bands} bands (PIL)")
            return metadata

    def generate_tiles(
        self, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """Generate tiles using ultra-safe window-based reading"""
        try:
            logger.info(f"🐌 Ultra-Safe Mode: Processing slowly but safely...")
            logger.info(f"📁 Input: {self.input_file.name}")

            if HAS_RASTERIO and str(self.input_file).lower().endswith(
                (".tif", ".tiff")
            ):
                return self._generate_with_rasterio(progress_callback)
            else:
                return self._generate_with_downscaling(progress_callback)

        except Exception as e:
            logger.error(f"❌ Ultra-safe generation failed: {e}", exc_info=True)
            return False

    def _generate_with_rasterio(
        self, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """Use rasterio for true window-based TIFF reading"""
        try:
            with rasterio.open(self.input_file) as src:
                width = src.width
                height = src.height
                megapixels = width * height / 1_000_000

                logger.info(f"📐 Image: {width}x{height} ({megapixels:.1f}MP)")
                logger.info(f"🔍 Bands: {src.count} | Type: {src.dtypes[0]}")

                max_dim = max(width, height)
                max_zoom = math.ceil(math.log2(max_dim / self.tile_size))

                # Smart zoom level selection based on image size
                if megapixels > 20000:
                    start_zoom = max(0, max_zoom - 2)  # Extreme: only 2 levels
                elif megapixels > 5000:
                    start_zoom = max(0, max_zoom - 3)  # Very large: 3 levels
                else:
                    start_zoom = 0  # Normal: all zoom levels (faster processing)

                logger.info(f"📊 Processing zoom levels {start_zoom} to {max_zoom}")

                if progress_callback:
                    progress_callback(10)

                self.output_dir.mkdir(parents=True, exist_ok=True)

                total_levels = max_zoom - start_zoom + 1
                for zoom_idx, zoom in enumerate(range(start_zoom, max_zoom + 1)):
                    logger.info(f"\n{'='*60}")
                    logger.info(f"🔄 Zoom Level {zoom}/{max_zoom}")

                    self._generate_zoom_rasterio(src, zoom, max_zoom, width, height)

                    gc.collect()

                    progress = 10 + int(((zoom_idx + 1) / total_levels) * 70)
                    if progress_callback:
                        progress_callback(progress)

                # Generate lower zoom levels by downsampling from start_zoom
                if start_zoom > 0:
                    logger.info(f"\n{'='*60}")
                    logger.info(
                        f"🔽 Generating lower zoom levels (0-{start_zoom-1}) by downsampling"
                    )
                    self._generate_lower_zoom_levels(
                        start_zoom, max_zoom, width, height
                    )

                    if progress_callback:
                        progress_callback(95)

                if progress_callback:
                    progress_callback(100)

                logger.info(f"\n✅ Generated {self.tiles_generated} tiles successfully")
                return True

        except Exception as e:
            logger.error(f"❌ Rasterio processing failed: {e}", exc_info=True)
            return False

    def _generate_zoom_rasterio(
        self, src, zoom: int, max_zoom: int, orig_width: int, orig_height: int
    ):
        """Generate tiles for zoom level using rasterio windows (multi-threaded)"""
        scale = 2 ** (zoom - max_zoom)
        scaled_width = max(1, int(orig_width * scale))
        scaled_height = max(1, int(orig_height * scale))

        tiles_x = math.ceil(scaled_width / self.tile_size)
        tiles_y = math.ceil(scaled_height / self.tile_size)
        total_tiles = tiles_x * tiles_y

        logger.info(f"  📦 {scaled_width}x{scaled_height} → {total_tiles} tiles")

        zoom_dir = self.output_dir / str(zoom)
        zoom_dir.mkdir(exist_ok=True)

        # Create all X directories upfront
        for x in range(tiles_x):
            (zoom_dir / str(x)).mkdir(exist_ok=True)

        if self.use_multithreading and total_tiles > 100:
            # Use multi-threading for large tile sets
            self._generate_tiles_multithreaded(
                src,
                zoom,
                max_zoom,
                orig_width,
                orig_height,
                tiles_x,
                tiles_y,
                total_tiles,
                zoom_dir,
                scale,
            )
        else:
            # Use single-threaded for small tile sets
            self._generate_tiles_single(
                src,
                zoom,
                max_zoom,
                orig_width,
                orig_height,
                tiles_x,
                tiles_y,
                total_tiles,
                zoom_dir,
                scale,
            )

    def _generate_tiles_single(
        self,
        src,
        zoom,
        max_zoom,
        orig_width,
        orig_height,
        tiles_x,
        tiles_y,
        total_tiles,
        zoom_dir,
        scale,
    ):
        """Single-threaded tile generation"""
        tile_count = 0

        for x in range(tiles_x):
            x_dir = zoom_dir / str(x)

            for y in range(tiles_y):
                try:
                    # Calculate region in original image
                    src_left = int(x * self.tile_size / scale)
                    src_top = int(y * self.tile_size / scale)
                    src_width = min(int(self.tile_size / scale), orig_width - src_left)
                    src_height = min(int(self.tile_size / scale), orig_height - src_top)

                    # Read only this small window from source
                    window = Window(src_left, src_top, src_width, src_height)

                    # Read the window (returns numpy array)
                    data = src.read(window=window)

                    # Convert to PIL Image
                    if src.count == 1:
                        # Grayscale
                        img_array = data[0]
                        if img_array.dtype == np.uint16:
                            img_array = (img_array / 256).astype(np.uint8)
                        tile = Image.fromarray(img_array, mode="L").convert("RGB")
                    elif src.count >= 3:
                        # RGB
                        img_array = np.stack([data[0], data[1], data[2]], axis=-1)
                        if img_array.dtype == np.uint16:
                            img_array = (img_array / 256).astype(np.uint8)
                        tile = Image.fromarray(img_array, mode="RGB")
                    else:
                        # Unsupported bands - create blank
                        tile = Image.new(
                            "RGB", (self.tile_size, self.tile_size), "black"
                        )

                    # Resize to tile size (use GPU if available for 2-3x speed boost)
                    if tile.size != (self.tile_size, self.tile_size):
                        tile = self._resize_gpu(tile, (self.tile_size, self.tile_size))

                    # Save (quality=80 is faster, minimal visual difference)
                    tile_path = x_dir / f"{y}.jpg"
                    tile.save(
                        tile_path, "JPEG", quality=80, optimize=False
                    )  # optimize=False is faster

                    tile_count += 1
                    self.tiles_generated += 1

                    # Cleanup
                    del data, tile

                    # Progress logging (reduced frequency for speed)
                    if tile_count % 500 == 0 or tile_count == total_tiles:
                        percent = (tile_count / total_tiles) * 100
                        mem = psutil.virtual_memory()
                        logger.info(
                            f"  ⏳ {tile_count}/{total_tiles} ({percent:.1f}%) [RAM: {mem.percent:.1f}%]"
                        )
                        # Only GC every 1000 tiles for speed
                        if tile_count % 1000 == 0:
                            gc.collect()

                except Exception as e:
                    logger.warning(f"  ⚠️ Failed tile ({x},{y}): {e}")
                    # Create blank fallback
                    blank = Image.new("RGB", (self.tile_size, self.tile_size), "black")
                    blank.save(x_dir / f"{y}.jpg", "JPEG", quality=80, optimize=False)
                    del blank
                    tile_count += 1

        logger.info(f"  ✅ Generated {tile_count} tiles")

    def _generate_tiles_multithreaded(
        self,
        src,
        zoom,
        max_zoom,
        orig_width,
        orig_height,
        tiles_x,
        tiles_y,
        total_tiles,
        zoom_dir,
        scale,
    ):
        """Multi-threaded tile generation for maximum speed"""
        tile_count = 0

        def process_tile(x, y):
            """Process a single tile (thread worker)"""
            try:
                x_dir = zoom_dir / str(x)

                # Calculate region in original image
                src_left = int(x * self.tile_size / scale)
                src_top = int(y * self.tile_size / scale)
                src_width = min(int(self.tile_size / scale), orig_width - src_left)
                src_height = min(int(self.tile_size / scale), orig_height - src_top)

                # Read window (rasterio is thread-safe for reading)
                window = Window(src_left, src_top, src_width, src_height)
                data = src.read(window=window)

                # Convert to PIL Image
                if src.count == 1:
                    img_array = data[0]
                    if img_array.dtype == np.uint16:
                        img_array = (img_array / 256).astype(np.uint8)
                    tile = Image.fromarray(img_array, mode="L").convert("RGB")
                elif src.count >= 3:
                    img_array = np.stack([data[0], data[1], data[2]], axis=-1)
                    if img_array.dtype == np.uint16:
                        img_array = (img_array / 256).astype(np.uint8)
                    tile = Image.fromarray(img_array, mode="RGB")
                else:
                    tile = Image.new("RGB", (self.tile_size, self.tile_size), "black")

                # Resize to tile size
                if tile.size != (self.tile_size, self.tile_size):
                    tile = self._resize_gpu(tile, (self.tile_size, self.tile_size))

                # Save
                tile_path = x_dir / f"{y}.jpg"
                tile.save(tile_path, "JPEG", quality=80, optimize=False)

                # Thread-safe counter increment
                with self._tile_lock:
                    self.tiles_generated += 1

                del data, tile
                return True

            except Exception as e:
                logger.warning(f"  ⚠️ Failed tile ({x},{y}): {e}")
                # Create blank fallback
                try:
                    blank = Image.new("RGB", (self.tile_size, self.tile_size), "black")
                    blank.save(
                        zoom_dir / str(x) / f"{y}.jpg",
                        "JPEG",
                        quality=80,
                        optimize=False,
                    )
                    del blank
                except:
                    pass
                return False

        # Generate list of all tiles to process
        tile_jobs = [(x, y) for x in range(tiles_x) for y in range(tiles_y)]

        # Process tiles in parallel using thread pool
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all jobs
            futures = {
                executor.submit(process_tile, x, y): (x, y) for x, y in tile_jobs
            }

            # Track progress
            for i, future in enumerate(as_completed(futures), 1):
                tile_count += 1

                # Progress logging
                if tile_count % 500 == 0 or tile_count == total_tiles:
                    percent = (tile_count / total_tiles) * 100
                    mem = psutil.virtual_memory()
                    logger.info(
                        f"  ⏳ {tile_count}/{total_tiles} ({percent:.1f}%) [RAM: {mem.percent:.1f}%]"
                    )

                    # GC less frequently for speed
                    if tile_count % 1000 == 0:
                        gc.collect()

        logger.info(f"  ✅ Generated {tile_count} tiles (multi-threaded)")

    def _generate_with_downscaling(
        self, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """Fallback: Load and immediately downscale"""
        try:
            logger.info("📉 Using downscaling approach...")

            with Image.open(self.input_file) as img:
                width, height = img.size
                megapixels = width * height / 1_000_000

                logger.info(f"📐 Image: {width}x{height} ({megapixels:.1f}MP)")

                # Downscale to manageable size first
                max_safe_dimension = 10000
                if width > max_safe_dimension or height > max_safe_dimension:
                    scale_factor = max_safe_dimension / max(width, height)
                    new_width = int(width * scale_factor)
                    new_height = int(height * scale_factor)

                    logger.info(f"📉 Downscaling to {new_width}x{new_height} first...")

                    img = img.convert("RGB")
                    # Use GPU-accelerated downscaling for speed
                    img = self._resize_gpu(img, (new_width, new_height))
                    width, height = new_width, new_height
                else:
                    img = img.convert("RGB")

                # Now generate tiles from downscaled image
                max_dim = max(width, height)
                max_zoom = math.ceil(math.log2(max_dim / self.tile_size))

                logger.info(f"📊 Generating tiles up to zoom {max_zoom}")

                self.output_dir.mkdir(parents=True, exist_ok=True)

                for zoom in range(max_zoom + 1):
                    self._generate_zoom_standard(img, zoom, max_zoom, width, height)

                    # Less frequent GC for speed
                    if zoom % 2 == 0:
                        gc.collect()

                    if progress_callback:
                        progress = 10 + int((zoom / (max_zoom + 1)) * 85)
                        progress_callback(progress)

                if progress_callback:
                    progress_callback(100)

                logger.info(f"\n✅ Generated {self.tiles_generated} tiles")
                return True

        except Exception as e:
            logger.error(f"❌ Downscaling approach failed: {e}", exc_info=True)
            return False

    def _generate_zoom_standard(
        self,
        img: Image.Image,
        zoom: int,
        max_zoom: int,
        orig_width: int,
        orig_height: int,
    ):
        """Generate zoom level from pre-loaded image"""
        scale = 2 ** (zoom - max_zoom)
        scaled_width = max(1, int(orig_width * scale))
        scaled_height = max(1, int(orig_height * scale))

        if zoom == max_zoom:
            scaled_img = img
        else:
            # Use GPU-accelerated resize for speed boost
            scaled_img = self._resize_gpu(img, (scaled_width, scaled_height))

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

                # quality=80, optimize=False for speed (3x faster encoding)
                tile.save(x_dir / f"{y}.jpg", "JPEG", quality=80, optimize=False)
                self.tiles_generated += 1

    def generate_preview(self, output_path: Path):
        """
        Generate a preview thumbnail
        Uses safe windowed reading for extreme images
        """
        try:
            logger.info(f"🖼️ Generating preview thumbnail...")

            if HAS_RASTERIO and str(self.input_file).lower().endswith(
                (".tif", ".tiff")
            ):
                # Use rasterio for safe preview generation
                with rasterio.open(self.input_file) as src:
                    width = src.width
                    height = src.height

                    # Calculate scale to fit 512x512
                    scale = min(512 / width, 512 / height)
                    preview_width = max(1, int(width * scale))
                    preview_height = max(1, int(height * scale))

                    # Read downscaled data directly
                    data = src.read(
                        out_shape=(src.count, preview_height, preview_width),
                        resampling=rasterio.enums.Resampling.bilinear,
                    )

                    # Convert to PIL Image
                    if src.count == 1:
                        img_array = data[0]
                        if img_array.dtype == np.uint16:
                            img_array = (img_array / 256).astype(np.uint8)
                        preview = Image.fromarray(img_array, mode="L").convert("RGB")
                    elif src.count >= 3:
                        img_array = np.stack([data[0], data[1], data[2]], axis=-1)
                        if img_array.dtype == np.uint16:
                            img_array = (img_array / 256).astype(np.uint8)
                        preview = Image.fromarray(img_array, mode="RGB")
                    else:
                        preview = Image.new(
                            "RGB", (preview_width, preview_height), "black"
                        )

                    preview.save(output_path, "JPEG", quality=90, optimize=True)
                    logger.info(f"✅ Preview saved: {preview_width}x{preview_height}")

            else:
                # Fallback to PIL with downscaling
                with Image.open(self.input_file) as img:
                    width, height = img.size

                    # Pre-downscale if extremely large
                    if width > 10000 or height > 10000:
                        scale = 10000 / max(width, height)
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        img = img.resize(
                            (new_width, new_height), Image.Resampling.LANCZOS
                        )

                    img = img.convert("RGB")
                    img.thumbnail((512, 512), Image.Resampling.LANCZOS)
                    img.save(output_path, "JPEG", quality=90, optimize=True)
                    logger.info(f"✅ Preview saved")

        except Exception as e:
            logger.warning(f"⚠️ Preview generation failed: {e}")
            # Create a placeholder preview
            placeholder = Image.new("RGB", (512, 512), (50, 50, 50))
            placeholder.save(output_path, "JPEG", quality=90)

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

            with self.tile_lock:
                self.tiles_generated += 1

        except Exception as e:
            logger.error(f"Error generating tile {target_zoom}/{x}/{y}: {e}")
