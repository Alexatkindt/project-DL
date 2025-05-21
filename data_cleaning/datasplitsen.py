import os
import shutil
import random

# Define your directories
original_dir = "schilderijen/3_processed/dataset_2Painters"  # Your main dataset directory
new_base_dir = "dataset_2Painters_organized"  # Where to put the organized data

# Define the categories (artists in your case)
artists = ('Mondriaan', 'Picasso')
subsets = ('train', 'validation', 'test')

# Create directories
for subset in subsets:
    for artist in artists:
        os.makedirs(os.path.join(new_base_dir, subset, artist), exist_ok=True)

# Process each artist separately to maintain balanced ratios
for artist in artists:
    artist_dir = os.path.join(original_dir, artist)
    if not os.path.exists(artist_dir):
        print(f"Warning: Directory {artist_dir} not found!")
        continue
    
    # Get files for this artist
    files = os.listdir(artist_dir)
    random.seed(42)  # For reproducibility
    random.shuffle(files)
    
    # Calculate split points
    total = len(files)
    train_end = int(0.7 * total)
    val_end = int(0.85 * total)
    
    # Split into subsets
    train_files = files[:train_end]
    val_files = files[train_end:val_end]
    test_files = files[val_end:]
    
    # Copy files to their respective directories
    for filename in train_files:
        shutil.copy2(os.path.join(artist_dir, filename), 
                    os.path.join(new_base_dir, 'train', artist, filename))
    
    for filename in val_files:
        shutil.copy2(os.path.join(artist_dir, filename), 
                    os.path.join(new_base_dir, 'validation', artist, filename))
    
    for filename in test_files:
        shutil.copy2(os.path.join(artist_dir, filename), 
                    os.path.join(new_base_dir, 'test', artist, filename))
    
    print(f"{artist}: Split {len(train_files)} train, {len(val_files)} validation, {len(test_files)} test")

# Check results
for subset in subsets:
    for artist in artists:
        print(subset, artist, ':', len(os.listdir(os.path.join(new_base_dir, subset, artist))))