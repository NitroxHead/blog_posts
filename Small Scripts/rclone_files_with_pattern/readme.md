# RClone Universal Upload Script

A flexible bash script for automated file uploads to Google Drive with date prefixing, integrity verification, and configurable options. Designed for scheduled backups and file transfers on Linux systems.

## Features

- Upload any file type to Google Drive using rclone
- Automatic date prefix for uploaded files (YYYYMMDD format)
- MD5 hash verification to ensure upload integrity
- Configurable file extension filtering
- Pattern matching for selective file uploads
- Safe deletion of source files only after successful verification
- Comprehensive logging with timestamps
- Multiple configuration support for different upload tasks
- Flexible scheduling with crontab

## Prerequisites

- Ubuntu/Debian Linux system (or any Linux with bash)
- rclone installed and configured with Google Drive
- Appropriate permissions for source and destination directories

### Install rclone

```bash
sudo apt update
sudo apt install rclone
```

### Configure rclone with Google Drive

```bash
rclone config
```

Follow the prompts to set up your Google Drive remote. Note the remote name (e.g., `my_gdrive`).

## Installation

### 1. Clone or Download Files

Place the following files in your preferred location:
- `rclone_upload.sh` - Main script
- `upload.conf.example` - Example configuration file
- `README.md` - This file

### 2. Install the Script

```bash
# Copy script to system bin directory
sudo cp rclone_upload.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/rclone_upload.sh
```

### 3. Create Configuration Directory

```bash
sudo mkdir -p /etc/rclone_upload
```

### 4. Create Configuration File

```bash
# Copy example config
sudo cp upload.conf.example /etc/rclone_upload/csv_upload.conf

# Edit with your settings
sudo nano /etc/rclone_upload/csv_upload.conf
```

### 5. Set Up Log File

```bash
sudo touch /var/log/rclone_upload.log
sudo chmod 666 /var/log/rclone_upload.log
```

## Configuration

Edit your configuration file with the following required and optional settings:

### Required Settings

```bash
# Source directory containing files to upload
SOURCE_DIR="/path/to/your/files"

# Google Drive destination (format: remote_name:path)
GDRIVE_DEST="my_gdrive:backups/files"

# File extensions to upload (space-separated, no dots)
FILE_EXTENSIONS="csv"
```

### Optional Settings

```bash
# Log file location
LOG_FILE="/var/log/rclone_upload.log"

# Date prefix format (uses date command syntax)
DATE_PREFIX="$(date +%Y%m%d)"

# Enable/disable date prefix on uploaded files
USE_DATE_PREFIX="true"

# Delete original files after successful upload
DELETE_AFTER_UPLOAD="true"

# Verify file integrity using MD5 checksums
VERIFY_HASH="true"

# File pattern matching (shell glob)
FILE_PATTERN="*"
```

### Date Prefix Formats

You can customize the date format using standard `date` command syntax:

- `$(date +%Y%m%d)` - 20251021
- `$(date +%Y-%m-%d)` - 2025-10-21
- `$(date +%Y_W%V)` - 2025_W43 (year and week number)
- `$(date +%Y%m%d_%H%M%S)` - 20251021_143045

### File Extension Examples

- Single type: `FILE_EXTENSIONS="csv"`
- Multiple types: `FILE_EXTENSIONS="csv json txt"`
- Documents: `FILE_EXTENSIONS="pdf docx xlsx"`
- Images: `FILE_EXTENSIONS="jpg jpeg png gif"`

### Pattern Matching Examples

- All files: `FILE_PATTERN="*"`
- Prefix match: `FILE_PATTERN="report_*"`
- Suffix match: `FILE_PATTERN="*_backup.csv"`
- Specific files: `FILE_PATTERN="data_*.{csv,json}"`

## Usage

### Manual Execution

Run the script manually with a specific configuration file:

```bash
/usr/local/bin/rclone_upload.sh /etc/rclone_upload/csv_upload.conf
```

Or use the default configuration location:

```bash
/usr/local/bin/rclone_upload.sh
```

### Automated Scheduling with Crontab

Edit your crontab:

```bash
crontab -e
```

Add one or more scheduled tasks:

#### Monthly Upload (1st day of month at 2:00 AM)

```
0 2 1 * * /usr/local/bin/rclone_upload.sh /etc/rclone_upload/csv_upload.conf
```

#### Weekly Upload (Every Sunday at 3:00 AM)

```
0 3 * * 0 /usr/local/bin/rclone_upload.sh /etc/rclone_upload/weekly_backup.conf
```

#### Daily Upload (Every day at 1:00 AM)

```
0 1 * * * /usr/local/bin/rclone_upload.sh /etc/rclone_upload/daily_logs.conf
```

#### Hourly Upload

```
0 * * * * /usr/local/bin/rclone_upload.sh /etc/rclone_upload/photos.conf
```

## Example Use Cases

### Use Case 1: Monthly CSV Export

**Config:** `/etc/rclone_upload/csv_upload.conf`

```bash
SOURCE_DIR="/home/user/data/exports"
GDRIVE_DEST="my_gdrive:archives/monthly_data"
FILE_EXTENSIONS="csv"
LOG_FILE="/var/log/csv_upload.log"
USE_DATE_PREFIX="true"
DELETE_AFTER_UPLOAD="true"
VERIFY_HASH="true"
FILE_PATTERN="*"
```

**Crontab:** `0 2 1 * * /usr/local/bin/rclone_upload.sh /etc/rclone_upload/csv_upload.conf`

Result: All CSV files uploaded on the 1st of each month with date prefix (e.g., `20251021report.csv`)

### Use Case 2: Daily Log Backup (Keep Originals)

**Config:** `/etc/rclone_upload/logs_backup.conf`

```bash
SOURCE_DIR="/var/log/application"
GDRIVE_DEST="backup_drive:logs/daily"
FILE_EXTENSIONS="log"
LOG_FILE="/var/log/log_backup.log"
USE_DATE_PREFIX="true"
DELETE_AFTER_UPLOAD="false"
VERIFY_HASH="false"
FILE_PATTERN="app_*.log"
```

**Crontab:** `0 1 * * * /usr/local/bin/rclone_upload.sh /etc/rclone_upload/logs_backup.conf`

Result: Application logs backed up daily, originals kept, faster upload without hash verification

### Use Case 3: Multiple File Types

**Config:** `/etc/rclone_upload/data_export.conf`

```bash
SOURCE_DIR="/opt/app/output"
GDRIVE_DEST="company_drive:exports"
FILE_EXTENSIONS="csv json xml txt"
LOG_FILE="/var/log/data_export.log"
USE_DATE_PREFIX="true"
DELETE_AFTER_UPLOAD="true"
VERIFY_HASH="true"
FILE_PATTERN="export_*"
```

**Crontab:** `0 3 * * 0 /usr/local/bin/rclone_upload.sh /etc/rclone_upload/data_export.conf`

Result: Weekly backup of multiple file types starting with "export_"

## Monitoring and Logs

### View Recent Log Entries

```bash
tail -50 /var/log/rclone_upload.log
```

### Monitor Logs in Real-Time

```bash
tail -f /var/log/rclone_upload.log
```

### Search Logs for Errors

```bash
grep ERROR /var/log/rclone_upload.log
```

### Log Output Format

Each log entry includes:
- Timestamp: `[2025-10-21 14:30:45]`
- Event type: Processing, Upload, Verification, Error
- File details: Filename, hash values
- Summary: Success/failure counts

Example log output:

```
[2025-10-21 02:00:01] ========== Starting File Upload Process ==========
[2025-10-21 02:00:01] Configuration: /etc/rclone_upload/csv_upload.conf
[2025-10-21 02:00:01] Source: /home/user/csvfiles
[2025-10-21 02:00:01] Destination: my_gdrive:archives/monthly
[2025-10-21 02:00:01] File Extensions: csv
[2025-10-21 02:00:02] Processing: data_export.csv
[2025-10-21 02:00:02] Local hash for 20251021data_export.csv: a1b2c3d4e5f6
[2025-10-21 02:00:03] Uploading 20251021data_export.csv to Google Drive...
[2025-10-21 02:00:15] Verifying upload integrity...
[2025-10-21 02:00:16] SUCCESS: Hash verification passed for 20251021data_export.csv
[2025-10-21 02:00:16] SUCCESS: Upload completed for 20251021data_export.csv
[2025-10-21 02:00:16] SUCCESS: Original file data_export.csv deleted from source
[2025-10-21 02:00:16] ========== Upload Summary ==========
[2025-10-21 02:00:16] Successful uploads: 1
[2025-10-21 02:00:16] Failed uploads: 0
[2025-10-21 02:00:16] Skipped files: 0
[2025-10-21 02:00:16] ========== Process Complete ==========
```

## How It Works

1. **Initialization**
   - Loads configuration from specified file
   - Validates required settings
   - Checks rclone installation and connectivity

2. **File Discovery**
   - Scans source directory for files matching extension filter
   - Applies pattern matching if specified
   - Lists all matching files for processing

3. **Processing Each File**
   - Creates temporary copy with date prefix (if enabled)
   - Calculates MD5 hash of local file
   - Uploads file to Google Drive using rclone
   - Verifies upload integrity by comparing hashes
   - Deletes original file only if verification succeeds

4. **Error Handling**
   - Continues processing remaining files if one fails
   - Logs all errors with details
   - Returns non-zero exit code if any uploads fail
   - Never deletes originals if upload or verification fails

5. **Summary Report**
   - Logs total successful uploads
   - Logs failed uploads count
   - Logs skipped files count

## Troubleshooting

### Script fails with "rclone not found"

Ensure rclone is installed and in PATH:

```bash
which rclone
sudo apt install rclone
```

### Cannot connect to Google Drive

Verify rclone configuration:

```bash
rclone listremotes
rclone lsd my_gdrive:
```

### Files not being uploaded

Check configuration:
- Verify SOURCE_DIR exists and contains files
- Confirm FILE_EXTENSIONS matches your files
- Check FILE_PATTERN if using pattern matching
- Review logs for specific errors

### Hash verification fails

This indicates upload corruption. The script will:
- Not delete the original file
- Log the error
- Retry on next scheduled run

To disable verification (faster but less safe):

```bash
VERIFY_HASH="false"
```

### Permission denied errors

Ensure proper permissions:

```bash
# For script
sudo chmod +x /usr/local/bin/rclone_upload.sh

# For log file
sudo chmod 666 /var/log/rclone_upload.log

# For source directory
ls -la /path/to/source/dir
```

### Crontab not running

Verify crontab entry:

```bash
crontab -l
```

Check cron logs:

```bash
grep CRON /var/log/syslog
```

Test script manually first:

```bash
/usr/local/bin/rclone_upload.sh /etc/rclone_upload/csv_upload.conf
```

## Security Considerations

- Store configuration files in `/etc/rclone_upload/` with restricted permissions
- Protect rclone configuration (contains OAuth tokens)
- Use service accounts for automated access if possible
- Review logs regularly for unauthorized access attempts
- Consider encrypting sensitive data before upload

```bash
# Secure configuration files
sudo chmod 600 /etc/rclone_upload/*.conf
sudo chown root:root /etc/rclone_upload/*.conf
```

## Advanced Configuration

### Dynamic Destination Paths

Use date-based destination folders:

```bash
GDRIVE_DEST="my_gdrive:backups/$(date +%Y)/$(date +%m)"
```

Result: Files uploaded to `backups/2025/10/`

### Custom Date Prefixes

```bash
# Include time: 20251021_143045
DATE_PREFIX="$(date +%Y%m%d_%H%M%S)"

# Week-based: 2025_W43
DATE_PREFIX="$(date +%Y_W%V)"

# Month-based: 2025-10
DATE_PREFIX="$(date +%Y-%m)"
```

### Conditional Processing

Create wrapper scripts for complex logic:

```bash
#!/bin/bash
# Upload only if files exist

if [ -n "$(ls /path/to/files/*.csv 2>/dev/null)" ]; then
    /usr/local/bin/rclone_upload.sh /etc/rclone_upload/csv_upload.conf
fi
```

## License

This script is provided as-is without warranty. Use at your own risk.

## Support

For issues, questions, or contributions:
- Check logs first: `/var/log/rclone_upload.log`
- Verify rclone configuration: `rclone config`
- Test manually before automating
- Review this README for common solutions
