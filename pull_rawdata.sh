#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    source .env
else
    echo "Error: .env file not found. Please create one from .env.example"
    exit 1
fi

# Check if ODOO_VERSIONS is set
if [ -z "$ODOO_VERSIONS" ]; then
    echo "Error: ODOO_VERSIONS not set in .env file"
    exit 1
fi

# Define the repository
REPO_URL="https://github.com/odoo/documentation.git"
REMOTE_NAME="odoo-docs"
BASE_DIR="raw_data/versions"

# Initialize the main repository directory if it doesn't exist
mkdir -p $BASE_DIR

# Navigate to the base directory
cd $BASE_DIR || exit 1

# Convert comma-separated versions to array
IFS=',' read -ra VERSIONS <<< "$ODOO_VERSIONS"

# Loop through each version
for VERSION in "${VERSIONS[@]}"; do
    # Trim whitespace from version
    VERSION=$(echo "$VERSION" | tr -d '[:space:]')
    echo "Processing version $VERSION..."

    # Check if the version directory exists and contains a git repository
    if [ -d "$VERSION/.git" ]; then
        echo "Repository for version $VERSION already exists. Updating..."
        cd $VERSION || exit 1
        
        # Just fetch and pull the specific branch
        git fetch $REMOTE_NAME $VERSION
        git merge $REMOTE_NAME/$VERSION --ff-only
        
        cd .. || exit 1
    else
        echo "Setting up new repository for version $VERSION..."
        
        # Create a directory for the version
        mkdir -p $VERSION
        cd $VERSION || exit 1

        # Initialize a git repository
        git init

        # Add the remote repository
        git remote add $REMOTE_NAME $REPO_URL

        # Enable sparse checkout
        git sparse-checkout init

        # Configure sparse checkout to be more specific
        echo "content/**" > .git/info/sparse-checkout

        # Fetch and checkout the specific branch
        git fetch $REMOTE_NAME $VERSION
        git checkout -b $VERSION $REMOTE_NAME/$VERSION

        echo "Version $VERSION setup complete."
        
        cd .. || exit 1
    fi
done

echo "All versions have been processed successfully."