#!/bin/bash
# Function to check if the current hour is between 1am and 6am
function is_between_1_and_6() {
  current_hour=$(date +"%H")
  [ "$current_hour" -ge 1 ] && [ "$current_hour" -lt 6 ]
}
# FTP variables
FTP_HOST="website"
FTP_USER="username"
FTP_PASS="password"
FTP_PATH="/ftp_directory"

# Google Drive variables
GDRIVE_FOLDER_ID="google_drive_folder_id"  # Replace with the ID of the Google Drive folder where you want to upload files

# Capture the list of files with full paths into a variable
file_list=$(lftp -u "$FTP_USER","$FTP_PASS" "$FTP_HOST" <<EOF
cd "$FTP_PATH"
find
quit
EOF
)


# Loop through the list of file paths
IFS=$'\n' # Set Internal Field Separator to newline
for file_path in $file_list; do
  # Check if the entry is a file and the last character is not "/"
  if [ "${file_path: -1}" != "/" ]; then
    while ! is_between_1_and_6; do
      echo "Waiting for half an hour..."
      sleep 1800  # Wait for half an hour (1800 seconds)
    done
    # Download each file
    lftp -u "$FTP_USER","$FTP_PASS" "$FTP_HOST" -e "cd \"$FTP_PATH\"; get \"$file_path\"; quit"

    # Extract file name from the full path
    file_name=$(basename "$file_path")

    # Print debug information
    echo "Downloaded: $file_path"

    # Run the upload and delete operations in subshells
    (
      # Upload the file to Google Drive using gdrive
      gdrive files upload "$file_name" --parent "$GDRIVE_FOLDER_ID"

      # Print debug information
      echo "Uploaded to Google Drive: $file_name"

      # Delete the downloaded file
      rm "$file_name"

      # Print debug information
      echo "Deleted: $file_name"
    ) &

    # Print debug information
    echo "Initiated upload and delete sub-process for: $file_name"
  else
    # Print debug information for skipped files or directories
    echo "Skipped: $file_path"
  fi
done

# Wait for all background processes to finish
wait

# Add any additional logic that you want to execute after all uploads
echo "All uploads completed."

