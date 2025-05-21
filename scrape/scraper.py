import os
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

# Configuration
base_url = 'http://www.rembrandtpainting.net/'
current_dir = os.getcwd()
output_dir = os.path.join(current_dir, 'raw_dataset', 'Rembrandt')

# Create the output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Initialize crawling structures
visited_pages = set()
pages_to_visit = [base_url]
domain = urlparse(base_url).netloc

# Track downloaded images to avoid duplicates
downloaded_images = set()

while pages_to_visit:
    page = pages_to_visit.pop(0)
    if page in visited_pages:
        continue
    visited_pages.add(page)
    print(f"Scraping page: {page}")
    try:
        resp = requests.get(page, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"[Error] Failed to retrieve {page}: {e}")
        continue
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Download images on this page
    for img in soup.find_all('img'):
        src = img.get('src')
        if not src:
            continue
        img_url = urljoin(page, src)
        if img_url in downloaded_images:
            continue
        try:
            img_resp = requests.get(img_url, timeout=10)
            img_resp.raise_for_status()
            path = urlparse(img_url).path
            filename = os.path.basename(path)
            if not filename:
                continue
            output_path = os.path.join(output_dir, filename)
            with open(output_path, 'wb') as f:
                f.write(img_resp.content)
            print(f"Downloaded {img_url} -> {output_path}")
            downloaded_images.add(img_url)
        except Exception as e:
            print(f"[Error] Failed to download {img_url}: {e}")

    # Find and queue new internal links
    for a in soup.find_all('a', href=True):
        href = a['href'].split('#')[0]
        link = urljoin(page, href)
        parsed_link = urlparse(link)
        if parsed_link.netloc != domain:
            continue
        if link not in visited_pages and link not in pages_to_visit:
            pages_to_visit.append(link)

print("Scraping complete.")