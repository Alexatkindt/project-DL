#!/usr/bin/env python3
"""
Afbeelding Dataset Processor

Dit script verwerkt kunst afbeeldingen uit een ruwe dataset:
- Valideert dat afbeeldingen niet corrupt zijn
- Standaardiseert bestandsnamen met kunstenaar prefixen
- Converteert niet-JPEG afbeeldingen naar JPEG formaat
- Organiseert ze in een nette mappenstructuur
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

# Configureer logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


class PathUtility:
    @staticmethod
    def sanitize_filename(name: str) -> str:
        """
        Sanitizeert een bestandsnaam voor cross-platform compatibiliteit.
        
        Args:
            name: De bestandsnaam om te sanitizeren
            
        Returns:
            Een gesanitizeerde bestandsnaam
        """
        name = name.strip()
        # Vervang gedachtestreepjes met gewone streepjes
        name = name.replace('–', '-').replace('—', '-')
        # Vervang niet-printbare karakters met underscores
        name = re.sub(r'[^\x20-\x7E]', '_', name)
        # Vervang Windows-illegale karakters met underscores
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        return name

    @staticmethod
    def win_longpath(p: Path) -> str:
        """
        Voegt \\?\\ prefix toe aan paden op Windows om MAX_PATH limieten te omzeilen.
        
        Args:
            p: Het pad om te converteren
            
        Returns:
            Pad string met prefix indien op Windows
        """
        s = str(p.resolve())
        if os.name == 'nt' and not s.startswith('\\\\?\\'):
            s = '\\\\?\\' + s
        return s

    @staticmethod
    def find_project_root(marker_folder: str = 'schilderijen') -> Path:
        """
        Vindt de project root door een marker map te lokaliseren.
        
        Args:
            marker_folder: Mapnaam die de project root aanduidt
            
        Returns:
            Pad naar project root
            
        Raises:
            SystemExit: Als project root niet gevonden kan worden
        """
        here = Path().resolve()
        for anc in (here, *here.parents):
            if (anc / marker_folder).is_dir():
                return anc
        logger.error(f"Kon project root niet vinden (geen '{marker_folder}/' map gevonden)")
        sys.exit(1)


@dataclass
class ImageProcessor:
    """
    Hoofdklasse voor het verwerken van afbeelding datasets.
    Beheert de volledige workflow van ruwe naar schone data.
    """
    project_root: Path          # Root map van het project
    data_dir: Path             # Hoofdmap voor schilderijen data
    raw_base: Path             # Basis map voor ruwe dataset
    clean_base: Path           # Basis map voor schone output
    prefix_map: Dict[str, str] # Mapping van kunstenaars naar prefixen
    input_extensions: Set[str] # Toegestane bestand extensies
    dry_run: bool = False      # Preview modus zonder wijzigingen
    max_workers: int = 4       # Aantal worker threads

    @classmethod
    def create_default(cls, dry_run: bool = False, max_workers: int = 4) -> 'ImageProcessor':
        """Factory methode om processor aan te maken met standaard instellingen"""
        project_root = PathUtility.find_project_root()
        data_dir = project_root / 'schilderijen'
        
        # Zoek naar raw_dataset mappen
        raw_dirs = list(data_dir.rglob('raw_dataset'))
        if not raw_dirs:
            logger.error(f"Geen 'raw_dataset' onder {data_dir}")
            sys.exit(1)
        raw_base = raw_dirs[0]
        
        # Maak output map aan
        clean_base = data_dir / '2_cleaned' / 'cleaned_dataset'
        if not dry_run:
            clean_base.mkdir(parents=True, exist_ok=True)
        
        # Mapping van kunstenaars naar numerieke prefixen
        prefix_map = {
            'Mondriaan': '1',
            'Picasso': '2',
            'Rembrandt': '3',
            'Rubens': '4',
        }
        
        # Ondersteunde afbeelding formaten
        input_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif'}
        
        logger.info(f"Project root:   {project_root}")
        logger.info(f"Ruwe dataset:   {raw_base}")
        logger.info(f"Schone output:  {clean_base}")
        
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
        Verwerkt een enkele afbeelding.
        
        Args:
            src_path: Pad naar bron afbeelding
            painter: Naam van de kunstenaar
            prefix: Prefix code voor de kunstenaar
            counter: Huidige afbeelding teller
            
        Returns:
            True als verwerking succesvol was, anders False
        """
        suffix = src_path.suffix.lower()
        if suffix not in self.input_extensions:
            return False

        # 1) Verifieer en verwijder corrupte bestanden
        try:
            with Image.open(PathUtility.win_longpath(src_path)) as im:
                im.verify()  # Controleer of afbeelding geldig is
        except (UnidentifiedImageError, OSError) as e:
            logger.warning(f"Corrupte afbeelding - verwijderen {src_path.name!r}: {e}")
            if not self.dry_run:
                src_path.unlink(missing_ok=True)
            return False

        # 2) Genereer output bestandsnaam & pad
        out_name = f"{prefix}_{counter:04d}.jpg"  # Bijvoorbeeld: 1_0001.jpg
        painter_out_dir = self.clean_base / painter
        if not self.dry_run:
            painter_out_dir.mkdir(parents=True, exist_ok=True)
        out_path = painter_out_dir / PathUtility.sanitize_filename(out_name)

        # Dry run mode - toon alleen wat er zou gebeuren
        if self.dry_run:
            logger.info(f"[DRY RUN] Zou verwerken: {src_path.name!r} → {out_path.name}")
            return True

        # 3) Kopieer JPEGs of converteer andere formaten naar JPEG
        try:
            if suffix in ('.jpg', '.jpeg'):
                # Directe kopie voor JPEG bestanden
                shutil.copy2(
                    PathUtility.win_longpath(src_path),
                    PathUtility.win_longpath(out_path)
                )
            else:
                # Converteer andere formaten naar JPEG
                with Image.open(PathUtility.win_longpath(src_path)) as im:
                    im = im.convert('RGB')  # Zorg voor RGB kleurmodus
                    im.save(PathUtility.win_longpath(out_path), format='JPEG')
            logger.debug(f"Verwerkt: {src_path.name!r} → {out_path.name}")
            return True
        except Exception as e:
            logger.error(f"Mislukt om te verwerken {src_path.name!r}: {e}")
            return False

    def process_painter(self, painter: str) -> int:
        """
        Verwerkt alle afbeeldingen voor een enkele kunstenaar.
        
        Args:
            painter: Naam van de kunstenaar om te verwerken
            
        Returns:
            Aantal afbeeldingen dat succesvol verwerkt is
        """
        prefix = self.prefix_map.get(painter)
        if not prefix:
            logger.warning(f"Geen prefix gedefinieerd voor kunstenaar '{painter}'")
            return 0
            
        src_folder = self.raw_base / painter
        if not src_folder.is_dir():
            logger.warning(f"Ontbrekende map voor kunstenaar '{painter}': {src_folder}")
            return 0

        # Verkrijg alle geldige afbeelding bestanden
        image_files = [
            f for f in sorted(src_folder.iterdir())
            if f.is_file() and f.suffix.lower() in self.input_extensions
        ]
        
        processed_count = 0
        # Maak voortgangsbalk aan
        progress_bar = tqdm(
            total=len(image_files),
            desc=f"Verwerken {painter}",
            unit="afbeeldingen"
        )
        
        # Verwerk afbeeldingen sequentieel om teller volgorde te behouden
        for counter, src_path in enumerate(image_files, start=1):
            success = self.process_image(src_path, painter, prefix, counter)
            if success:
                processed_count += 1
            progress_bar.update(1)
                
        progress_bar.close()
        logger.info(f"Voltooid {painter}: {processed_count}/{len(image_files)} afbeeldingen verwerkt")
        return processed_count
    
    def run(self) -> Dict[str, int]:
        """
        Verwerkt alle schilderijen van alle kunstenaars.
        
        Returns:
            Dictionary die kunstenaar namen mapt naar aantal verwerkte afbeeldingen
        """
        results = {}
        for painter in self.prefix_map:
            processed = self.process_painter(painter)
            results[painter] = processed
        
        return results


def main():
    """Hoofdingang voor het script."""
    parser = argparse.ArgumentParser(description="Verwerk schilderij datasets")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Preview operaties zonder wijzigingen te maken")
    parser.add_argument("--workers", type=int, default=4, 
                       help="Aantal worker threads")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Toon uitgebreide output")
    args = parser.parse_args()

    # Stel logging niveau in
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Maak processor aan en voer uit
    processor = ImageProcessor.create_default(dry_run=args.dry_run, max_workers=args.workers)
    results = processor.run()
    
    # Print samenvatting
    total = sum(results.values())
    print("\n" + "="*50)
    print(f"SAMENVATTING: {total} afbeeldingen verwerkt")
    for painter, count in results.items():
        print(f"  - {painter}: {count} afbeeldingen")
    print("="*50)


if __name__ == "__main__":
    main()