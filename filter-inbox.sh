#!/bin/bash

# Read the configuration file
SOURCE_DIR=$(yq e '.downloads_folder' config.yaml)
OUTPUT_DIR=$(yq e '.inbox_folder' config.yaml)
KEEP_COPY=$(yq e '.keep_copy' config.yaml)

# Define the log file path
LOG_FILE="$OUTPUT_DIR/copied.log"

# Ensure the log file exists
mkdir -p "$OUTPUT_DIR"
touch "$LOG_FILE"

# (1) Loop through all files in the source directory
for file in "$SOURCE_DIR/full/"*; do
    # Skip if it's not a file
    if [ ! -f "$file" ]; then
        echo "Skipping non-file: $file"
        continue
    fi

    # Check if the file is already logged
    if grep -Fxq "$(basename "$file")" "$LOG_FILE"; then
        echo "File already logged: $(basename "$file"). Skipping."
        continue
    else
        # Append the filename if not previously logged
        echo "$(basename "$file")" >> "$LOG_FILE" 
    fi

    # Get the course's name (prefix before the first underscore)
    prefix=$(basename "$file" | cut -d'_' -f1)
    
    # Create the folder for the prefix if it doesn't exist
    mkdir -p "$OUTPUT_DIR/$prefix"

    # Define the destination file path
    dest_file="$OUTPUT_DIR/$prefix/$(basename "$file")"

    # Check if the file already exists in the destination folder
    if [ ! -f "$dest_file" ]; then
        if [ "$KEEP_COPY" = "false" ]; then
            mv "$file" "$dest_file"
            echo "Moved: $file to $dest_file"
        else
            cp "$file" "$dest_file"
            echo "Copied: $file to $dest_file"
        fi
    else
        echo "File already exists: $dest_file. Skipping."
    fi
done
echo "Inbox updated!"