import asyncio
import os
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import CrawlerRunConfig
from bs4 import BeautifulSoup

async def process_html_files():
    """Prcess HTML files in the html directory and convert them to Markdown."""

    html_dir = "html"  # Path to the HTML folder
    markdown_dir = "markdown"  # Path to save the Markdown files

    # Ensure the markdown directory exists
    os.makedirs(markdown_dir, exist_ok=True)

    # Traverse through the html folder and process all .html files
    for root, _, files in os.walk(html_dir):
        for file in files:
            if file.endswith(".html"):
                # Construct the full file path
                html_file_path = os.path.join(root, file)
                
                # Create the corresponding markdown file path
                relative_path = os.path.relpath(html_file_path, html_dir)
                markdown_file_path = os.path.join(markdown_dir, os.path.splitext(relative_path)[0] + ".md")
                
                # Ensure the markdown file's parent directory exists
                os.makedirs(os.path.dirname(markdown_file_path), exist_ok=True)

                # Convert and save the markdown
                await convert_to_markdown(html_file_path, markdown_file_path)

async def convert_to_markdown(html_file_path, markdown_file_path):
    """Convert an HTML file to Markdown and save it to a file with the same relative path.

    Args:
        html_file_path: Path to the HTML file. 
        markdown_file_path: Path to save the Markdown file.
    """

    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Check for meta-refresh redirects using BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    meta_refresh = soup.find("meta", attrs={"http-equiv": "refresh"})
    if meta_refresh:
        print(f"Skipping file due to meta-refresh redirect: {html_file_path}")
        return

    file_url = f"file://{os.path.abspath(html_file_path)}"
    config = CrawlerRunConfig(bypass_cache=True)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=file_url, config=config)
        if result.success:
            # Save the markdown content to the markdown file
            with open(markdown_file_path, "w", encoding="utf-8") as f:
                f.write(result.markdown)
            print(f"Converted: {html_file_path} -> {markdown_file_path}")
        else:
            print(f"Failed to convert {html_file_path}: {result.error_message}")

# Run the script
if __name__ == "__main__":
    asyncio.run(process_html_files())