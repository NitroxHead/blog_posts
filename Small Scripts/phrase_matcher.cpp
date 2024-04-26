#include <iostream>
#include <fstream>
#include <string>
#include <vector>

/*
This script reads a list of phrases from a file and then searches for those phra
ses within a large text file. When a line in the large file contains any of the 
specified phrases, it's saved to an output file.
*/

// Function to check if a line contains any of the specified phrases
bool containsPhrase(const std::string& line, const std::vector<std::string>& phrases) {
    for (const auto& phrase : phrases) {
        if (line.find(phrase) != std::string::npos) {
            return true;
        }
    }
    return false;
}

int main(int argc, char* argv[]) {
    // Check if the correct number of command-line arguments is provided
    if (argc != 4) {
        std::cerr << "Usage: " << argv[0] << " <phrases_file> <large_file> <output_file>\n";
        return 1;
    }

    // Open the file containing the phrases
    std::ifstream phrasesFile(argv[1]);
    if (!phrasesFile) {
        std::cerr << "Error: Unable to open " << argv[1] << std::endl;
        return 1;
    }

    // Read the phrases into a vector
    std::vector<std::string> phrases;
    std::string phrase;
    while (std::getline(phrasesFile, phrase)) {
        phrases.push_back(phrase);
    }
    phrasesFile.close();

    // Open the large text file to search
    std::ifstream largeFile(argv[2]);
    if (!largeFile) {
        std::cerr << "Error: Unable to open " << argv[2] << std::endl;
        return 1;
    }

    // Open the output file to save matching lines
    std::ofstream outputFile(argv[3]);
    if (!outputFile) {
        std::cerr << "Error: Unable to create " << argv[3] << std::endl;
        return 1;
    }

    // Search line by line in the large file
    std::string line;
    while (std::getline(largeFile, line)) {
        if (containsPhrase(line, phrases)) {
            outputFile << line << "\n";
        }
    }

    // Close files
    largeFile.close();
    outputFile.close();

    std::cout << "Matching lines saved to " << argv[3] << std::endl;
    return 0;
}
