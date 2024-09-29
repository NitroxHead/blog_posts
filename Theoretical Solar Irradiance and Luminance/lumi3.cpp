//g++ -o lumi2 lumi2.cpp -I~/Downloads/cspice/include -L~/Downloads/cspice/lib ~/Downloads/cspice/lib/cspice.a -lm $(pkg-config --cflags --libs netcdf-cxx4)
#include <iostream>
#include <vector>
#include <cmath>
#include <string>
#include <chrono>
#include <netcdf>
#include "./include/SpiceUsr.h"

// Constants
const double SOLAR_CONSTANT = 1361.0; // W/m²
const double CONVERSION_FACTOR = 93.0; // lumens/m² per W/m²
const double DEG_TO_RAD = M_PI / 180.0;
// New 3D Matrix class
class Matrix3D {
private:
    std::vector<double> data_;
    size_t l_, m_, n_;

public:
    Matrix3D(size_t l, size_t m, size_t n) : l_(l), m_(m), n_(n), data_(l*m*n) {}

    double& operator()(size_t i, size_t j, size_t k) {
        return data_[i*m_*n_ + j*n_ + k];
    }

    const double& operator()(size_t i, size_t j, size_t k) const {
        return data_[i*m_*n_ + j*n_ + k];
    }

    double* data() { return data_.data(); }
    const double* data() const { return data_.data(); }
};


void calculateSolarData(double et, double lat, double lon, double& irradiance, double& luminance) {
    double sunPos[3], sunLt;
    
    // Get the Sun's position relative to Earth in J2000 frame
    spkpos_c("SUN", et, "J2000", "LT+S", "EARTH", sunPos, &sunLt);

    // Convert lat/lon to rectangular coordinates in ITRF93 (Earth-fixed) frame
    double observerPos[3];
    double alt = 0.0;  // Assume observer is at sea level
    georec_c(lon * DEG_TO_RAD, lat * DEG_TO_RAD, alt, 6378.137, 0.0033528131, observerPos);

    // Get the transformation matrix from ITRF93 to J2000 at the given time
    double xform[3][3];
    pxform_c("ITRF93", "J2000", et, xform);

    // Transform observer position to J2000 frame
    double observerPosJ2000[3];
    mxv_c(xform, observerPos, observerPosJ2000);

    // Calculate the vector from observer to Sun in J2000 frame
    double observerToSun[3];
    vsub_c(sunPos, observerPosJ2000, observerToSun);

    // Calculate the local zenith vector in ITRF93 frame
    double zenithITRF[3];
    surfnm_c(6378.137, 6378.137, 6356.752, observerPos, zenithITRF);

    // Transform zenith to J2000 frame
    double zenithJ2000[3];
    mxv_c(xform, zenithITRF, zenithJ2000);

    // Calculate the angle between zenith and Sun direction
    double cosSolarZenithAngle = vdot_c(zenithJ2000, observerToSun) / (vnorm_c(zenithJ2000) * vnorm_c(observerToSun));
    double solarZenithAngle = acos(cosSolarZenithAngle);
    double altitude = halfpi_c() - solarZenithAngle;

    if (altitude > 0) {
        irradiance = SOLAR_CONSTANT * sin(altitude);
        luminance = irradiance * CONVERSION_FACTOR;
    } else {
        irradiance = 0.0;
        luminance = 0.0;
    }
}

void createNetCDFOutput(const std::string& filename,
                        const std::vector<double>& times,
                        const std::vector<double>& latitudes,
                        const std::vector<double>& longitudes,
                        const Matrix3D& solarIrradiance,
                        const Matrix3D& luminance) {
    try {
        // Create NetCDF file
        netCDF::NcFile dataFile(filename, netCDF::NcFile::replace);

        // Define dimensions
        auto timeDim = dataFile.addDim("time", times.size());
        auto latDim = dataFile.addDim("latitude", latitudes.size());
        auto lonDim = dataFile.addDim("longitude", longitudes.size());

        // Define coordinate variables
        auto timeVar = dataFile.addVar("time", netCDF::ncDouble, timeDim);
        auto latVar = dataFile.addVar("latitude", netCDF::ncDouble, latDim);
        auto lonVar = dataFile.addVar("longitude", netCDF::ncDouble, lonDim);

        // Define data variables
        std::vector<netCDF::NcDim> dims = {timeDim, latDim, lonDim};
        auto irradianceVar = dataFile.addVar("solar_irradiance", netCDF::ncDouble, dims);
        auto luminanceVar = dataFile.addVar("luminance", netCDF::ncDouble, dims);

        // Add attributes
        timeVar.putAtt("units", "hours since 1950-01-01 00:00:00");
        timeVar.putAtt("calendar", "gregorian");

        irradianceVar.putAtt("units", "W/m²");
        irradianceVar.putAtt("long_name", "Solar Irradiance");

        luminanceVar.putAtt("units", "lux");
        luminanceVar.putAtt("long_name", "Luminance");

        // Global attributes
        auto nowTime = std::chrono::system_clock::now();
        auto now = std::chrono::system_clock::to_time_t(nowTime);
        dataFile.putAtt("Conventions", "CF-1.6");
        dataFile.putAtt("title", "Solar Irradiance and Luminance Data");
        dataFile.putAtt("source", "Generated from SPICE calculations");
        dataFile.putAtt("constants", "93 # lumens/m² per W/m² \n 1361 # W/m²");
        dataFile.putAtt("MadeBy", "NitroxHead");
        dataFile.putAtt("history", "Created on " + std::string(std::ctime(&now)));

        // Write data
        timeVar.putVar(times.data());
        latVar.putVar(latitudes.data());
        lonVar.putVar(longitudes.data());

        // Write irradiance and luminance data
        std::vector<size_t> startp = {0, 0, 0};
        std::vector<size_t> countp = {times.size(), latitudes.size(), longitudes.size()};
        irradianceVar.putVar(startp, countp, solarIrradiance.data());
        luminanceVar.putVar(startp, countp, luminance.data());

    } catch (netCDF::exceptions::NcException& e) {
        std::cerr << "NetCDF exception: " << e.what() << std::endl;
        exit(1);
    }

    std::cout << "Created " << filename << std::endl;
}

int main() {
    // Load SPICE kernels
    furnsh_c("de421.bsp");
    furnsh_c("naif0012.tls");
    furnsh_c("pck00010.tpc");
    furnsh_c("earth_latest_high_prec.bpc");

    // Define the datetime range with more precise format
    std::string startDate = "2019-01-01T00:00:00.000";
    std::string endDate = "2019-01-02T00:00:00.000";

    double startEt, endEt;
    str2et_c(startDate.c_str(), &startEt);
    str2et_c(endDate.c_str(), &endEt);

    // Print loaded start and end times in ET for debug
    std::cout << "Start ET: " << startEt << ", End ET: " << endEt << std::endl;

    // Convert ET to UTC and print it for verification
    char utcStr[30];
    et2utc_c(startEt, "ISOC", 3, 30, utcStr);
    std::cout << "Start Time (UTC): " << utcStr << std::endl;
    et2utc_c(endEt, "ISOC", 3, 30, utcStr);
    std::cout << "End Time (UTC): " << utcStr << std::endl;

    // Create a grid of latitude and longitude coordinates
    std::vector<double> latitudes, longitudes;
    for (double lat = -90.0; lat < 90.0; lat += 0.08333588) {
        latitudes.push_back(lat);
    }
    for (double lon = -180.0; lon < 180.0; lon += 0.08333588) {
        longitudes.push_back(lon);
    }

    // Generate time steps (8 intervals of 3 hours)
    std::vector<double> times;
    double timeStep = 3 * 3600; // 3 hours in seconds
    for (int i = 0; i < 1; ++i) {
        times.push_back(startEt + i * timeStep);
    }

    // Print generated times in UTC for debug
    for (double t : times) {
        et2utc_c(t, "C", 3, 30, utcStr);
        std::cout << "Time (UTC): " << utcStr << std::endl;
    }

    // Initialize data structures using the new Matrix3D class
    Matrix3D solarIrradiance(times.size(), latitudes.size(), longitudes.size());
    Matrix3D luminance(times.size(), latitudes.size(), longitudes.size());

    // Calculate solar data
    size_t t = 0;
    std::cout << times[t] << std::endl;
    for (size_t i = 0; i < latitudes.size(); ++i) {
        for (size_t j = 0; j < longitudes.size(); ++j) {
            double irr, lum;
            calculateSolarData(times[t], latitudes[i], longitudes[j], irr, lum);
            solarIrradiance(t, i, j) = irr;
            luminance(t, i, j) = lum;
        }
    }

    // Create NetCDF output file
    createNetCDFOutput("solar_data_20190101.nc", times, latitudes, longitudes, solarIrradiance, luminance);

    // Unload SPICE kernels
    kclear_c();

    return 0;
}
