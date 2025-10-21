#!/bin/bash

# Universal File Upload Script with Configuration File
# Uploads files to Google Drive with date prefix and integrity verification

# Default configuration file location
CONFIG_FILE="${1:-/etc/rclone_upload/upload.conf}"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file not found: $CONFIG_FILE"
    echo "Usage: $0 [config_file]"
    echo "Default config location: /etc/rclone_upload/upload.conf"
    exit 1
fi

# Source the configuration file
source "$CONFIG_FILE"

# Validate required configuration variables
if [ -z "$SOURCE_DIR" ] || [ -z "$GDRIVE_DEST" ] || [ -z "$FILE_EXTENSIONS" ]; then
    echo "ERROR: Missing required configuration variables"
    echo "Required: SOURCE_DIR, GDRIVE_DEST, FILE_EXTENSIONS"
    exit 1
fi

# Set defaults for optional variables
LOG_FILE="${LOG_FILE:-/var/log/rclone_upload.log}"
DATE_PREFIX="${DATE_PREFIX:-$(date +%Y%m%d)}"
USE_DATE_PREFIX="${USE_DATE_PREFIX:-true}"
DELETE_AFTER_UPLOAD="${DELETE_AFTER_UPLOAD:-true}"
VERIFY_HASH="${VERIFY_HASH:-true}"
FILE_PATTERN="${FILE_PATTERN:-*}"

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to calculate hash
calculate_hash() {
    md5sum "$1" | awk '{print $1}'
}

# Function to check if file matches extension filter
matches_extension() {
    local file=$1
    local ext="${file##*.}"
    
    for allowed_ext in $FILE_EXTENSIONS; do
        if [ "$ext" = "$allowed_ext" ]; then
            return 0
        fi
    done
    return 1
}

# Main upload function
upload_and_verify() {
    local file=$1
    local filename=$(basename "$file")
    
    # Apply date prefix if enabled
    if [ "$USE_DATE_PREFIX" = "true" ]; then
        local new_filename="${DATE_PREFIX}${filename}"
    else
        local new_filename="${filename}"
    fi
    
    local temp_renamed="/tmp/${new_filename}"
    
    log_message "Processing: ${filename}"
    
    # Create temporary copy with new name
    cp "$file" "$temp_renamed"
    if [ $? -ne 0 ]; then
        log_message "ERROR: Failed to create temporary copy of ${filename}"
        return 1
    fi
    
    # Calculate hash if verification enabled
    if [ "$VERIFY_HASH" = "true" ]; then
        local local_hash=$(calculate_hash "$temp_renamed")
        log_message "Local hash for ${new_filename}: ${local_hash}"
    fi
    
    # Upload to Google Drive
    log_message "Uploading ${new_filename} to ${GDRIVE_DEST}..."
    
    if [ "$VERIFY_HASH" = "true" ]; then
        rclone copy "$temp_renamed" "$GDRIVE_DEST" --checksum --verbose >> "$LOG_FILE" 2>&1
    else
        rclone copy "$temp_renamed" "$GDRIVE_DEST" --verbose >> "$LOG_FILE" 2>&1
    fi
    
    if [ $? -ne 0 ]; then
        log_message "ERROR: Upload failed for ${new_filename}"
        rm -f "$temp_renamed"
        return 1
    fi
    
    # Verify upload with hash check if enabled
    if [ "$VERIFY_HASH" = "true" ]; then
        log_message "Verifying upload integrity..."
        rclone check "$temp_renamed" "${GDRIVE_DEST}/${new_filename}" --checksum >> "$LOG_FILE" 2>&1
        
        if [ $? -ne 0 ]; then
            log_message "ERROR: Hash verification failed for ${new_filename}"
            rm -f "$temp_renamed"
            return 1
        fi
        log_message "SUCCESS: Hash verification passed for ${new_filename}"
    fi
    
    log_message "SUCCESS: Upload completed for ${new_filename}"
    
    # Remove temporary file
    rm -f "$temp_renamed"
    
    # Delete original file if enabled
    if [ "$DELETE_AFTER_UPLOAD" = "true" ]; then
        rm -f "$file"
        if [ $? -eq 0 ]; then
            log_message "SUCCESS: Original file ${filename} deleted from source"
            return 0
        else
            log_message "ERROR: Failed to delete original file ${filename}"
            return 1
        fi
    else
        log_message "INFO: Original file ${filename} kept (DELETE_AFTER_UPLOAD=false)"
        return 0
    fi
}

# Main execution
main() {
    log_message "========== Starting File Upload Process =========="
    log_message "Configuration: $CONFIG_FILE"
    log_message "Source: $SOURCE_DIR"
    log_message "Destination: $GDRIVE_DEST"
    log_message "File Extensions: $FILE_EXTENSIONS"
    log_message "File Pattern: $FILE_PATTERN"
    
    # Check if rclone is installed
    if ! command -v rclone &> /dev/null; then
        log_message "ERROR: rclone is not installed or not in PATH"
        exit 1
    fi
    
    # Check if source directory exists
    if [ ! -d "$SOURCE_DIR" ]; then
        log_message "ERROR: Source directory does not exist: $SOURCE_DIR"
        exit 1
    fi
    
    # Test rclone connection
    rclone lsd "$GDRIVE_DEST" &> /dev/null
    if [ $? -ne 0 ]; then
        log_message "ERROR: Cannot connect to Google Drive. Check rclone configuration."
        exit 1
    fi
    
    # Find and process files
    success_count=0
    fail_count=0
    skip_count=0
    
    # Build find command for file extensions
    find_cmd="find \"$SOURCE_DIR\" -maxdepth 1 -type f -name \"${FILE_PATTERN}\""
    
    while IFS= read -r file; do
        filename=$(basename "$file")
        
        # Check if file matches extension filter
        if matches_extension "$filename"; then
            if upload_and_verify "$file"; then
                ((success_count++))
            else
                ((fail_count++))
            fi
        else
            log_message "SKIP: ${filename} (extension not in filter)"
            ((skip_count++))
        fi
        echo "" >> "$LOG_FILE"  # Add blank line between files
    done < <(eval $find_cmd)
    
    # Summary
    log_message "========== Upload Summary =========="
    log_message "Successful uploads: ${success_count}"
    log_message "Failed uploads: ${fail_count}"
    log_message "Skipped files: ${skip_count}"
    log_message "========== Process Complete =========="
    
    # Exit with error if any upload failed
    if [ $fail_count -gt 0 ]; then
        exit 1
    fi
}

# Run main function
main
