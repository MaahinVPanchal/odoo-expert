import re
import subprocess
import sys
import os
from pathlib import Path


def preprocess_rst_content(input_file, temp_file):
    """
    Preprocess RST content to remove references to {ODOO_RELPATH}, <{GITHUB_PATH}/, and :file: directives.
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove '.. example::' blocks with problematic paths
        content = re.sub(
            r'\.\. example::.*?(?:\{ODOO_RELPATH\}|\{GITHUB_PATH\}|:file:).*?\n(?:[ \t]+.*?\n)*?(?=\S|$)',
            '',
            content,
            flags=re.DOTALL
        )

        # Remove literalinclude directives with problematic paths
        content = re.sub(
            r'\.\. literalinclude::.*?(?:\{ODOO_RELPATH\}|\{GITHUB_PATH\}).*?\n(?:[ \t]+.*?\n)*?(?=\S|$)',
            '',
            content,
            flags=re.DOTALL
        )

        # Clean up :file: directives by removing the directive and keeping just the filename
        content = re.sub(
            r':file:`([^`]+)`',
            r'file',
            content
        )

        # Remove standalone references to {ODOO_RELPATH} or <{GITHUB_PATH}/
        content = re.sub(
            r'(?:\{ODOO_RELPATH\}|\{GITHUB_PATH\}).*?\n',
            '',
            content
        )

        # Write the cleaned content to a temporary file
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(content)

        return temp_file

    except Exception as e:
        print(f"Error preprocessing RST file {input_file}: {e}")
        return None

def run_pandoc(input_file, intermediate_file):
    """
    Convert RST to Markdown using Pandoc, with preprocessing to handle problematic directives.
    """
    try:
        # Check if Pandoc is installed
        subprocess.run(['pandoc', '--version'], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("Error: Pandoc is not installed. Please install Pandoc first.")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: Pandoc is not installed or not in PATH. Please install Pandoc first.")
        sys.exit(1)

    # Preprocess the RST content to handle unresolved paths
    temp_file = Path(input_file).with_suffix('.temp.rst')
    preprocessed_file = preprocess_rst_content(input_file, temp_file)
    if not preprocessed_file:
        return False

    try:
        # Run Pandoc command
        cmd = ['pandoc', str(preprocessed_file), '-f', 'rst', '-t', 'markdown', '-o', str(intermediate_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Pandoc conversion failed with error:\n{result.stderr}")
            return False
            
        return True

    except Exception as e:
        print(f"An error occurred during Pandoc conversion: {e}")
        return False

    finally:
        # Clean up temporary file
        if temp_file.exists():
            temp_file.unlink()

def fix_line_breaks(content):
    """
    Fix unnecessary line breaks in the markdown content while preserving formatting,
    including code blocks and other structured sections.
    """
    lines = content.split('\n')
    result = []
    current_line = ''
    in_code_block = False
    in_table = False
    
    def should_preserve_line_break(line):
        # Preserve line breaks for headings, code blocks, special sections, and table markers
        return (line.strip().startswith('#') or
                line.strip().startswith(':::') or
                line.strip().startswith('- ') or
                line.strip().startswith('* ') or
                line.strip().startswith('[') or
                line.strip().startswith('+') or  # Table markers
                line.strip().startswith('|') or  # Table content
                not line.strip())  # Empty lines

    for i, line in enumerate(lines):
        stripped_line = line.strip()
        
        # Check for table markers
        if stripped_line.startswith('+') and '-' in stripped_line:
            in_table = True
            result.append(line)
            continue
            
        # If in table, preserve formatting
        if in_table:
            if stripped_line.startswith('+'):  # End of table section
                in_table = False
            result.append(line)
            continue
        
        # Handle start or end of code blocks
        if stripped_line.startswith('```'):
            if current_line:
                result.append(current_line)
                current_line = ''
            result.append(line)
            in_code_block = not in_code_block
            continue
        
        # If inside a code block, preserve lines as-is
        if in_code_block:
            result.append(line)
            continue
        
        # If this is a line we should preserve as-is
        if should_preserve_line_break(line):
            if current_line:
                result.append(current_line)
                current_line = ''
            result.append(line)
            continue
        
        # Handle regular content
        if current_line:
            # Append the current line to the ongoing content
            current_line += ' ' + stripped_line
        else:
            current_line = stripped_line
    
    # Add any remaining content
    if current_line:
        result.append(current_line)
    
    return '\n'.join(result)

def clean_markdown(content):
    """
    Clean up the markdown content
    """
    # Remove initial metadata before first heading while preserving structure
    lines = content.split('\n')
    first_content_line = 0
    in_metadata = True
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Stop looking for metadata if we hit a heading, table, or other structured content
        if (stripped.startswith('#') or
            stripped.startswith('+--') or
            stripped.startswith('|') or
            (stripped and not stripped == ':' and 
             not any(marker in stripped.lower() for marker in 
                    ['show-content', 'hide-page-toc', 'show-toc', 'nosearch', 'orphan']))):
            in_metadata = False
            first_content_line = i
            break
        # Skip empty lines and known metadata markers while in metadata section
        if in_metadata and (not stripped or stripped == ':' or 
            any(marker in stripped.lower() for marker in 
                ['show-content', 'hide-page-toc', 'show-toc', 'nosearch', 'orphan'])):
            continue
            
    # Keep content from first non-metadata line onwards
    content = '\n'.join(lines[first_content_line:])
    
    # First fix line breaks (but preserve tables and other formatted content)
    content = fix_line_breaks(content)
    
    # Clean up the seealso block
    content = re.sub(r'::: seealso\n(.*?)\n:::', r'::: seealso\n\1\n:::', content, flags=re.DOTALL)
    
    # Clean up the tip section
    content = re.sub(r':::: tip\n::: title\nTip\n:::\n\n(.*?)\n::::', r'Tip: \1', content, flags=re.DOTALL)
    
    # Clean up the note section
    content = re.sub(r':::: note\n::: title\nNote\n:::\n\n(.*?)\n::::', r'Note: \1', content, flags=re.DOTALL)
    
    # Clean up the important section
    content = re.sub(r':::: important\n::: title\nImportant\n:::\n\n(.*?)\n::::', r'Important: \1', content, flags=re.DOTALL)
    
    # Clean up all RST-style roles (including multi-line ones)
    content = re.sub(r'\{\.interpreted-text\s+role="[^"]+"\}', '', content, flags=re.DOTALL)
    
    # Convert related content block to a list
    def format_related_content(match):
        items = match.group(1).split()
        formatted_items = "\n".join(f"- {item.strip()}" for item in items if item.strip())
        return f"## Related content:\n\n{formatted_items}"
    
    content = re.sub(
        r'::: \{\.toctree titlesonly=""\}\n(.*?)\n:::',
        format_related_content,
        content,
        flags=re.DOTALL,
    )

    # Remove extra blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()

def process_file(rst_file, output_file):
    """
    Process a single RST file to cleaned markdown
    """
    # Create intermediate filename in the same directory as the output file
    intermediate_file = output_file.parent / "intermediate_pandoc.md"
    
    try:
        # Create output directory if it doesn't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Convert RST to Markdown using pandoc
        if not run_pandoc(rst_file, intermediate_file):
            return
        
        # Step 2: Read the intermediate markdown file
        with open(intermediate_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Step 3: Clean the content
        cleaned_content = clean_markdown(content)
        
        # Step 4: Write to final output file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
    except Exception as e:
        print(f"An error occurred processing {rst_file}: {str(e)}")
    finally:
        # Clean up intermediate file
        if intermediate_file.exists():
            intermediate_file.unlink()

def process_directory(base_dir):
    """
    Process all RST files in the given directory and its subdirectories
    """
    base_path = Path(base_dir)
    versions = ['16.0', '17.0', '18.0']
    
    for version in versions:
        source_dir = base_path / 'versions' / version / 'content'
        target_dir = base_path / 'markdown' / 'versions' / version / 'content'
        
        if not source_dir.exists():
            print(f"Warning: Source directory {source_dir} does not exist")
            continue
            
        # Walk through all files in the source directory
        for rst_file in source_dir.rglob('*.rst'):
            # Calculate the relative path from the source_dir
            rel_path = rst_file.relative_to(source_dir)
            
            # Create the corresponding markdown file path
            md_file = target_dir / rel_path.with_suffix('.md')
            
            print(f"Processing: {rst_file} -> {md_file}")
            process_file(rst_file, md_file)

if __name__ == "__main__":
    base_dir = "raw_data"
    process_directory(base_dir)