#!/bin/bash

# R Compilation and Installation Script for Ubuntu
# Usage: ./install_r.sh [VERSION]
# Example: ./install_r.sh 4.4.2

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if running as root
check_not_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root!"
        print_error "Run it as a regular user. It will ask for sudo when needed."
        exit 1
    fi
}

# Function to get R version
get_r_version() {
    if [[ $# -eq 0 ]]; then
        print_error "No R version specified!"
        echo "Usage: $0 [VERSION]"
        echo "Example: $0 4.4.2"
        echo ""
        echo "Available versions can be found at: https://cran.r-project.org/src/base/"
        exit 1
    fi
    
    R_VERSION="$1"
    R_MAJOR=$(echo $R_VERSION | cut -d. -f1)
    
    print_status "Target R version: $R_VERSION"
}

# Function to install dependencies
install_dependencies() {
    print_status "Updating package lists..."
    sudo apt update
    
    print_status "Installing essential build tools..."
    sudo apt install -y build-essential gfortran
    
    print_status "Installing R dependencies..."
    sudo apt install -y \
        libreadline-dev \
        libx11-dev \
        libxt-dev \
        libpng-dev \
        libjpeg-dev \
        libcairo2-dev \
        xvfb \
        libbz2-dev \
        libzstd-dev \
        liblzma-dev \
        libcurl4-openssl-dev \
        texinfo \
        libpcre2-dev \
        libblas-dev \
        liblapack-dev \
        libssl-dev \
        libxml2-dev \
        libfontconfig1-dev \
        libharfbuzz-dev \
        libfribidi-dev \
        libfreetype6-dev \
        libtiff5-dev \
        libicu-dev
    
    print_success "Dependencies installed successfully"
}

# Function to download and extract R source
download_r_source() {
    WORK_DIR="$HOME/r-build-$R_VERSION"
    
    print_status "Creating working directory: $WORK_DIR"
    mkdir -p "$WORK_DIR"
    cd "$WORK_DIR"
    
    # Construct download URL
    R_URL="https://cran.r-project.org/src/base/R-${R_MAJOR}/R-${R_VERSION}.tar.gz"
    R_TARBALL="R-${R_VERSION}.tar.gz"
    R_DIR="R-${R_VERSION}"
    
    print_status "Downloading R source from: $R_URL"
    
    if ! wget -q --show-progress "$R_URL"; then
        print_error "Failed to download R source!"
        print_error "Please check if version $R_VERSION exists at:"
        print_error "https://cran.r-project.org/src/base/R-${R_MAJOR}/"
        exit 1
    fi
    
    print_status "Extracting R source..."
    tar -xzf "$R_TARBALL"
    
    if [[ ! -d "$R_DIR" ]]; then
        print_error "Failed to extract R source or directory not found!"
        exit 1
    fi
    
    cd "$R_DIR"
    print_success "R source downloaded and extracted"
}

# Function to configure R build
configure_r() {
    print_status "Configuring R build..."
    
    # Temporarily remove conda from PATH to avoid conflicts
    if command_exists conda; then
        print_warning "Conda detected. Temporarily removing from PATH to avoid conflicts..."
        export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    fi
    
    # Basic configuration - reliable and widely compatible
    ./configure --prefix=/usr/local \
                --enable-R-shlib \
                --enable-memory-profiling \
                --with-blas \
                --with-lapack \
                --with-readline \
                --with-cairo \
                --with-libpng \
                --with-jpeglib \
                --with-libtiff \
                --enable-BLAS-shlib=no
    
    if [[ $? -eq 0 ]]; then
        print_success "R configured successfully"
    else
        print_error "R configuration failed!"
        exit 1
    fi
}

# Function to compile R
compile_r() {
    print_status "Starting R compilation (this may take 15-30 minutes)..."
    
    # Get number of CPU cores
    NCORES=$(nproc)
    
    # Use all cores but limit to avoid memory issues
    if [[ $NCORES -gt 4 ]]; then
        MAKE_JOBS=4
    else
        MAKE_JOBS=$NCORES
    fi
    
    print_status "Using $MAKE_JOBS parallel jobs for compilation"
    
    if make -j$MAKE_JOBS; then
        print_success "R compiled successfully"
    else
        print_warning "Compilation with $MAKE_JOBS jobs failed. Trying with single job..."
        make clean
        if make -j1; then
            print_success "R compiled successfully (single-threaded)"
        else
            print_error "R compilation failed!"
            exit 1
        fi
    fi
}

# Function to install R
install_r() {
    print_status "Installing R to /usr/local..."
    
    if sudo make install; then
        print_success "R installed successfully"
    else
        print_error "R installation failed!"
        exit 1
    fi
    
    # Update library cache
    print_status "Updating library cache..."
    sudo ldconfig
    
    # Update PATH for current session
    export PATH="/usr/local/bin:$PATH"
    
    # Add to user's bashrc if not already there
    if ! grep -q "/usr/local/bin" "$HOME/.bashrc"; then
        print_status "Adding /usr/local/bin to PATH in ~/.bashrc"
        echo 'export PATH="/usr/local/bin:$PATH"' >> "$HOME/.bashrc"
    fi
}

# Function to verify installation
verify_installation() {
    print_status "Verifying R installation..."
    
    # Check if R binary exists
    if ! command_exists R; then
        print_error "R command not found in PATH!"
        return 1
    fi
    
    # Check R version
    INSTALLED_VERSION=$(R --version | head -n1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    
    if [[ "$INSTALLED_VERSION" == "$R_VERSION" ]]; then
        print_success "R version $INSTALLED_VERSION installed successfully!"
    else
        print_error "Version mismatch! Expected: $R_VERSION, Found: $INSTALLED_VERSION"
        return 1
    fi
    
    # Test basic R functionality
    print_status "Testing basic R functionality..."
    
    if R --slave --no-restore --no-save -e "cat('R is working correctly!\n'); sessionInfo()" >/dev/null 2>&1; then
        print_success "R is working correctly!"
    else
        print_error "R is installed but not working properly!"
        return 1
    fi
    
    # Show installation info
    echo ""
    print_success "=== R Installation Complete ==="
    echo "R Version: $INSTALLED_VERSION"
    echo "R Location: $(which R)"
    echo "Installation Directory: /usr/local"
    echo ""
    echo "To start R, simply type: R"
    echo "To check R version: R --version"
    echo ""
    print_status "Build directory saved at: $WORK_DIR"
    print_status "You can remove it to save space: rm -rf $WORK_DIR"
}

# Function to cleanup on error
cleanup_on_error() {
    print_error "Installation failed!"
    print_status "Build directory preserved for debugging: $WORK_DIR"
    print_status "Check the error messages above for troubleshooting."
    exit 1
}

# Main function
main() {
    echo "======================================"
    echo "    R Compilation and Installation"
    echo "======================================"
    echo ""
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    # Check if not running as root
    check_not_root
    
    # Get R version from command line
    get_r_version "$@"
    
    # Install dependencies
    install_dependencies
    
    # Download and extract R source
    download_r_source
    
    # Configure R build
    configure_r
    
    # Compile R
    compile_r
    
    # Install R
    install_r
    
    # Verify installation
    verify_installation
    
    print_success "All done! Enjoy your new R installation!"
}

# Run main function with all arguments
main "$@"
