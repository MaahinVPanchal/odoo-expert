#!/bin/bash

# Define the repository and the versions
REPO_URL="https://github.com/odoo/documentation.git"
REMOTE_NAME="odoo-docs"
VERSIONS=("16.0" "17.0" "18.0")
BASE_DIR="raw_data/versions"

# Initialize the main repository directory if it doesn't exist
mkdir -p $BASE_DIR

# Navigate to the base directory
cd $BASE_DIR || exit 1

# Loop through each version
for VERSION in "${VERSIONS[@]}"; do
    echo "Setting up version $VERSION..."

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
    # The pattern /content/** will match the content directory and everything under it
    # While excluding root level files
    echo "content/**" > .git/info/sparse-checkout

    # Fetch and checkout the specific branch
    git fetch $REMOTE_NAME $VERSION
    git checkout -b $VERSION $REMOTE_NAME/$VERSION

    echo "Version $VERSION setup complete."

    # Return to the base directory
    cd .. || exit 1
done

echo "All versions have been set up successfully."