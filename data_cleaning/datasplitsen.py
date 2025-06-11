import os
import shutil
import random

# Definieer de directories
original_dir = "schilderijen/3_processed/dataset_2Painters"  # Hoofd dataset directory
new_base_dir = "dataset_2Painters_organized"  # Waar de georganiseerde data komt

# Definieer de categorieën (kunstenaars in dit geval)
artists = ('Mondriaan', 'Picasso')
subsets = ('train', 'validation', 'test')

# Maak directories aan voor elke subset en kunstenaar
for subset in subsets:
    for artist in artists:
        os.makedirs(os.path.join(new_base_dir, subset, artist), exist_ok=True)

# Verwerk elke kunstenaar afzonderlijk om balanced ratios te behouden
for artist in artists:
    artist_dir = os.path.join(original_dir, artist)
    if not os.path.exists(artist_dir):
        print(f"Waarschuwing: Directory {artist_dir} niet gevonden!")
        continue
    
    # Haal bestanden op voor deze kunstenaar
    files = os.listdir(artist_dir)
    random.seed(42)  # Voor reproduceerbaarheid
    random.shuffle(files)
    
    # Bereken split punten (70% train, 15% validation, 15% test)
    total = len(files)
    train_end = int(0.7 * total)
    val_end = int(0.85 * total)
    
    # Verdeel in subsets
    train_files = files[:train_end]
    val_files = files[train_end:val_end]
    test_files = files[val_end:]
    
    # Kopieer bestanden naar hun respectievelijke directories
    for filename in train_files:
        shutil.copy2(os.path.join(artist_dir, filename),
                     os.path.join(new_base_dir, 'train', artist, filename))
    
    for filename in val_files:
        shutil.copy2(os.path.join(artist_dir, filename),
                     os.path.join(new_base_dir, 'validation', artist, filename))
    
    for filename in test_files:
        shutil.copy2(os.path.join(artist_dir, filename),
                     os.path.join(new_base_dir, 'test', artist, filename))
    
    print(f"{artist}: Verdeeld in {len(train_files)} train, {len(val_files)} validation, {len(test_files)} test")

# Controleer de resultaten
print("\n--- Finale verdeling per subset ---")
for subset in subsets:
    for artist in artists:
        count = len(os.listdir(os.path.join(new_base_dir, subset, artist)))
        print(f"{subset.capitalize()} - {artist}: {count} afbeeldingen")