#!/bin/bash

# Check if input PDF filename is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 input.pdf"
    exit 1
fi

input_pdf="$1"
output_pdf="cleaned_${input_pdf}"

# Check if input file exists
if [ ! -f "$input_pdf" ]; then
    echo "Error: Input file '$input_pdf' not found"
    exit 1
fi

# Create a temporary directory for processing
temp_dir=$(mktemp -d)
echo "Creating temporary directory: $temp_dir"

# Convert PDF to PNG images
echo "Converting PDF to images..."
gm convert -density 300 "$input_pdf" "$temp_dir/page-%03d.png"

# Process each image to remove yellow background
echo "Removing yellow background from each page..."
for image in "$temp_dir"/page-*.png; do
    echo "Processing $(basename "$image")..."
    gm convert "$image" -fuzz 40% -fill white -opaque "#FAEBD7" "$image"
done

# Combine back into PDF
echo "Combining pages back into PDF..."
gm convert $(ls "$temp_dir"/page-*.png | sort -V) "$output_pdf"

# Cleanup
echo "Cleaning up temporary files..."
rm -rf "$temp_dir"

echo "Process complete! Output saved as: $output_pdf"
