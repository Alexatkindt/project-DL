#!/usr/bin/env python3
"""
Image Dataset Processor

This script processes art images from a raw dataset:
- Validates images aren't corrupt
- Standardizes filenames with artist prefixes
- Converts non-JPEG images to JPEG format
- Organizes them in a clean directory structure
"""

import argparse
import logging
import os
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from PIL import Image, UnidentifiedImageError
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


class PathUtility:
    @staticmethod
    def sanitize_filename(name: str) -> str:
        """
        Sanitize a filename for cross-platform compatibility.
        
        Args:
            name: The filename to sanitize
            
        Returns:
            A sanitized filename
        """
        name = name.strip()
        name = name.replace('–', '-').replace('—', '-')
        name = re.sub(r'[^\x20-\x7E]', '_', name)  # Replace non-printable chars
        name = re.sub(r'[<>:"/\\|?*]', '_', name)  # Replace Windows-illegal chars
        return name

    @staticmethod
    def win_longpath(p: Path) -> str:
        """
        Prefix paths with \\?\\ on Windows to bypass MAX_PATH limits.
        
        Args:
            p: The path to convert
            
        Returns:
            Path string with prefix if on Windows
        """
        s = str(p.resolve())
        if os.name == 'nt' and not s.startswith('\\\\?\\'):
            s = '\\\\?\\' + s
        return s

    @staticmethod
    def find_project_root(marker_folder: str = 'schilderijen') -> Path:
        """
        Find the project root by locating a marker folder.
        
        Args:
            marker_folder: Folder name that indicates project root
            
        Returns:
            Path to project root
            
        Raises:
            SystemExit: If project root cannot be found
        """
        here = Path().resolve()
        for anc in (here, *here.parents):
            if (anc / marker_folder).is_dir():
                return anc
        logger.error(f"Could not locate project root (no '{marker_folder}/' folder found)")
        sys.exit(1)


@dataclass
class ImageProcessor:
    project_root: Path
    data_dir: Path
    raw_base: Path
    clean_base: Path
    prefix_map: Dict[str, str]
    input_extensions: Set[str]
    dry_run: bool = False
    max_workers: int = 4

    @classmethod
    def create_default(cls, dry_run: bool = False, max_workers: int = 4) -> 'ImageProcessor':
        """Factory method to create processor with default settings"""
        project_root = PathUtility.find_project_root()
        data_dir = project_root / 'schilderijen'
        
        raw_dirs = list(data_dir.rglob('raw_dataset'))
        if not raw_dirs:
            logger.error(f"No 'raw_dataset' under {data_dir}")
            sys.exit(1)
        raw_base = raw_dirs[0]
        
        clean_base = data_dir / '2_cleaned' / 'cleaned_dataset'
        if not dry_run:
            clean_base.mkdir(parents=True, exist_ok=True)
        
        prefix_map = {
            'Mondriaan': '1',
            'Picasso': '2',
            'Rembrandt': '3',
            'Rubens': '4',
        }
        
        input_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif'}
        
        logger.info(f"Project root:   {project_root}")
        logger.info(f"Raw dataset:    {raw_base}")
        logger.info(f"Cleaned output: {clean_base}")
        
        return cls(
            project_root=project_root,
            data_dir=data_dir,
            raw_base=raw_base,
            clean_base=clean_base,
            prefix_map=prefix_map,
            input_extensions=input_extensions,
            dry_run=dry_run,
            max_workers=max_workers
        )
    
    def process_image(self, src_path: Path, painter: str, prefix: str, counter: int) -> bool:
        """
        Process a single image file.
        
        Args:
            src_path: Path to source image
            painter: Name of the artist
            prefix: Prefix code for the artist
            counter: Current image counter
            
        Returns:
            True if processing succeeded, False otherwise
        """
        suffix = src_path.suffix.lower()
        if suffix not in self.input_extensions:
            return False

        # 1) Verify and delete corrupt files
        try:
            with Image.open(PathUtility.win_longpath(src_path)) as im:
                im.verify()
        except (UnidentifiedImageError, OSError) as e:
            logger.warning(f"Corrupt image - deleting {src_path.name!r}: {e}")
            if not self.dry_run:
                src_path.unlink(missing_ok=True)
            return False

        # 2) Generate output filename & path
        out_name = f"{prefix}_{counter:04d}.jpg"
        painter_out_dir = self.clean_base / painter
        if not self.dry_run:
            painter_out_dir.mkdir(parents=True, exist_ok=True)
        out_path = painter_out_dir / PathUtility.sanitize_filename(out_name)

        if self.dry_run:
            logger.info(f"[DRY RUN] Would process: {src_path.name!r} → {out_path.name}")
            return True

        # 3) Copy JPEGs or convert other formats to JPEG
        try:
            if suffix in ('.jpg', '.jpeg'):
                shutil.copy2(
                    PathUtility.win_longpath(src_path),
                    PathUtility.win_longpath(out_path)
                )
            else:
                with Image.open(PathUtility.win_longpath(src_path)) as im:
                    im = im.convert('RGB')
                    im.save(PathUtility.win_longpath(out_path), format='JPEG')
            logger.debug(f"Processed: {src_path.name!r} → {out_path.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to process {src_path.name!r}: {e}")
            return False

    def process_painter(self, painter: str) -> int:
        """
        Process all images for a single painter.
        
        Args:
            painter: Name of the artist to process
            
        Returns:
            Number of images successfully processed
        """
        prefix = self.prefix_map.get(painter)
        if not prefix:
            logger.warning(f"No prefix defined for painter '{painter}'")
            return 0
            
        src_folder = self.raw_base / painter
        if not src_folder.is_dir():
            logger.warning(f"Missing folder for painter '{painter}': {src_folder}")
            return 0

        # Get all valid image files
        image_files = [
            f for f in sorted(src_folder.iterdir())
            if f.is_file() and f.suffix.lower() in self.input_extensions
        ]
        
        processed_count = 0
        progress_bar = tqdm(
            total=len(image_files),
            desc=f"Processing {painter}",
            unit="images"
        )
        
        # Process images sequentially to maintain counter order
        for counter, src_path in enumerate(image_files, start=1):
            success = self.process_image(src_path, painter, prefix, counter)
            if success:
                processed_count += 1
            progress_bar.update(1)
                
        progress_bar.close()
        logger.info(f"Completed {painter}: {processed_count}/{len(image_files)} images processed")
        return processed_count
    
    def run(self) -> Dict[str, int]:
        """
        Process all paintings from all artists.
        
        Returns:
            Dictionary mapping painter names to number of images processed
        """
        results = {}
        for painter in self.prefix_map:
            processed = self.process_painter(painter)
            results[painter] = processed
        
        return results


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Process painting datasets")
    parser.add_argument("--dry-run", action="store_true", help="Preview operations without making changes")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker threads")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    processor = ImageProcessor.create_default(dry_run=args.dry_run, max_workers=args.workers)
    results = processor.run()
    
    # Print summary
    total = sum(results.values())
    print("\n" + "="*50)
    print(f"SUMMARY: {total} images processed")
    for painter, count in results.items():
        print(f"  - {painter}: {count} images")
    print("="*50)


if __name__ == "__main__":
    main()