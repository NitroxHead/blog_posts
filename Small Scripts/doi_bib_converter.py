#!/usr/bin/env python3
"""
DOI Bibliography Converter
A Flask web service to convert DOIs to BibTeX or MS Word XML format
Production version for Apache2 deployment
"""

import re
import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
from flask import Flask, render_template_string, request, Response, jsonify
from urllib.parse import quote
import logging
import time
import os
import json
from typing import List, Set, Dict, Tuple

# Configure logging for production
try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
        handlers=[
            logging.FileHandler('/var/log/apache2/bib-convert.log'),
            logging.StreamHandler()
        ]
    )
except PermissionError:
    # Fallback if can't write to log file
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s:%(name)s:%(message)s'
    )

app = Flask(__name__)

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>DOI Bibliography Converter</title>
    <meta charset="utf-8">
    <style>
        body { 
            font-family: Helvetica, sans-serif; 
            max-width: 800px; 
            margin: 50px auto; 
            padding: 20px;
            line-height: 1.6;
        }
        .container { 
            background: #f9f9f9; 
            padding: 30px; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #333; 
            text-align: center; 
            margin-bottom: 30px;
        }
        textarea { 
            width: 100%; 
            height: 200px; 
            padding: 10px; 
            border: 1px solid #ddd; 
            border-radius: 4px; 
            font-family: monospace;
            resize: vertical;
        }
        .form-group { 
            margin: 20px 0; 
        }
        label { 
            display: block; 
            margin-bottom: 8px; 
            font-weight: bold;
        }
        .radio-group { 
            margin: 10px 0; 
        }
        .radio-group label { 
            display: inline; 
            margin-left: 8px; 
            font-weight: normal;
        }
        .checkbox-group { 
            margin: 10px 0; 
        }
        .checkbox-group label { 
            display: inline; 
            margin-left: 8px; 
            font-weight: normal;
        }
        button { 
            background: #007cba; 
            color: white; 
            padding: 12px 24px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
            font-size: 16px;
            width: 100%;
        }
        button:hover { 
            background: #005a8b; 
        }
        .result { 
            margin-top: 20px; 
            padding: 15px; 
            background: white; 
            border: 1px solid #ddd; 
            border-radius: 4px;
            white-space: pre-wrap;
            font-family: monospace;
            max-height: 400px;
            overflow-y: auto;
        }
        .error { 
            color: #d32f2f; 
            background: #ffebee; 
            border-color: #d32f2f;
        }
        .info { 
            font-size: 14px; 
            color: #666; 
            margin-top: 10px;
        }
        .progress-container {
            margin: 20px 0;
            display: none;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: #f0f0f0;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.2);
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #007cba, #005a8b);
            width: 0%;
            transition: width 0.3s ease;
            border-radius: 10px;
        }
        .progress-text {
            text-align: center;
            margin-top: 5px;
            font-size: 14px;
            color: #666;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            font-size: 14px;
            color: #666;
        }
        .footer a {
            color: #007cba;
            text-decoration: none;
        }
        .footer a:hover {
            text-decoration: underline;
        }
        .tex-info {
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-top: 5px;
            color: #856404;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>DOI Bibliography Converter</h1>
        <div class="info" style="background: #e3f2fd; padding: 10px; border-radius: 4px; margin-bottom: 20px;">
            <strong>How it works:</strong> Paste text containing DOIs or enter DOIs directly. The service will automatically extract and convert them to your chosen format.
            <br><strong>Rate limiting:</strong> Processing is throttled to respect CrossRef API limits (~10 requests/second).
        </div>
        
        <form id="doiForm">
            <div class="form-group">
                <label for="dois">Enter DOIs or paste text containing DOIs:</label>
                <textarea id="dois" name="dois" placeholder="10.1038/nature12373
10.1126/science.1234567
10.1016/j.cell.2020.01.001

Or paste any text like:
Recent studies (doi:10.1038/nature12373) show that...
See https://doi.org/10.1126/science.1234567 for details..."></textarea>
                <div class="info">Enter DOIs one per line, or paste any text - DOIs will be automatically extracted. Supports various formats including URLs and doi: prefixes.</div>
            </div>
            
            <div class="form-group">
                <label>Output Format:</label>
                <div class="radio-group">
                    <input type="radio" id="bibtex" name="format" value="bibtex" checked>
                    <label for="bibtex">BibTeX</label>
                </div>
                <div class="radio-group">
                    <input type="radio" id="xml" name="format" value="xml">
                    <label for="xml">MS Word XML</label>
                </div>
            </div>
            
            <div class="form-group">
                <div class="checkbox-group">
                    <input type="checkbox" id="autoDownload" name="autoDownload" checked>
                    <label for="autoDownload">Automatically download result file</label>
                </div>
                <div class="checkbox-group">
                    <input type="checkbox" id="forTex" name="forTex">
                    <label for="forTex">For TeX (generate TeX file with \\cite{} commands)</label>
                    <div class="tex-info" id="texInfo" style="display: none;">
                        This will create an additional TeX file where DOIs in your original text are replaced with \\cite{bibkey} commands matching the generated BibTeX entries.
                    </div>
                </div>
                <div class="checkbox-group">
                    <input type="checkbox" id="forMarkdown" name="forMarkdown">
                    <label for="forMarkdown">For Markdown (generate Markdown file with @bibkey citations)</label>
                    <div class="tex-info" id="markdownInfo" style="display: none;">
                        This will create an additional Markdown file where DOIs in your original text are replaced with @bibkey citations for use with Pandoc and the generated BibTeX file.
                    </div>
                </div>
            </div>
            
            <button type="submit">Convert DOIs</button>
        </form>
        
        <div class="progress-container" id="progressContainer">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <div class="progress-text" id="progressText">Processing...</div>
        </div>
        
        <div id="result"></div>
        
        <div class="footer">
            <p>Script available at: <a href="https://github.com/NitroxHead/blog_posts/blob/main/Small%20Scripts/doi_bib_converter.py" target="_blank">Github</a></p>
            <p>Created by: NitroxHead</p>
        </div>
    </div>

    <script>
        // Show/hide TeX info when checkbox is toggled
        document.getElementById('forTex').addEventListener('change', function() {
            const texInfo = document.getElementById('texInfo');
            texInfo.style.display = this.checked ? 'block' : 'none';
        });
        
        // Show/hide Markdown info when checkbox is toggled
        document.getElementById('forMarkdown').addEventListener('change', function() {
            const markdownInfo = document.getElementById('markdownInfo');
            markdownInfo.style.display = this.checked ? 'block' : 'none';
        });
        
        document.getElementById('doiForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const resultDiv = document.getElementById('result');
            const submitButton = document.querySelector('button[type="submit"]');
            const progressContainer = document.getElementById('progressContainer');
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            const autoDownload = document.getElementById('autoDownload').checked;
            const forTex = document.getElementById('forTex').checked;
            const forMarkdown = document.getElementById('forMarkdown').checked;
            const format = formData.get('format');
            
            // Count approximate DOIs for progress indication
            const inputText = formData.get('dois');
            const approxDoiCount = (inputText.match(/10\\.\\d{4,}/g) || []).length;
            
            let progressMessage = 'Processing...';
            if (approxDoiCount > 1) {
                progressMessage = `Processing ${approxDoiCount} DOIs (estimated ${Math.ceil(approxDoiCount * 0.2)} seconds)...`;
            }
            
            // Show progress bar and start animation
            progressContainer.style.display = 'block';
            progressText.textContent = progressMessage;
            progressFill.style.width = '0%';
            
            // Animate progress bar
            let progress = 0;
            const estimatedTime = Math.max(2, approxDoiCount * 0.2) * 1000; // Convert to milliseconds
            const progressInterval = setInterval(() => {
                progress += (100 / (estimatedTime / 100)); // Update every 100ms
                if (progress < 90) { // Don't go to 100% until actually done
                    progressFill.style.width = progress + '%';
                }
            }, 100);
            
            resultDiv.innerHTML = '';
            submitButton.disabled = true;
            submitButton.textContent = 'Processing...';
            
            try {
                const response = await fetch('convert', {
                    method: 'POST',
                    body: formData
                });
                
                clearInterval(progressInterval);
                progressFill.style.width = '100%';
                progressText.textContent = 'Complete!';
                
                if (response.ok) {
                    const contentType = response.headers.get('content-type');
                    
                    if (contentType.includes('application/json')) {
                        // Multi-file response (when TeX or Markdown is enabled)
                        const result = await response.json();
                        
                        // Display the main result
                        resultDiv.innerHTML = '<div class="result">' + escapeHtml(result.main_content) + '</div>';
                        
                        // Auto-download if enabled
                        if (autoDownload) {
                            downloadFile(result.main_content, format);
                            
                            // Also download TeX file if available
                            if (result.tex_content) {
                                downloadFile(result.tex_content, 'tex');
                            }
                            
                            // Also download Markdown file if available
                            if (result.markdown_content) {
                                downloadFile(result.markdown_content, 'markdown');
                            }
                        }
                    } else {
                        // Single file response
                        const result = await response.text();
                        resultDiv.innerHTML = '<div class="result">' + escapeHtml(result) + '</div>';
                        
                        // Auto-download if enabled
                        if (autoDownload) {
                            downloadFile(result, format);
                        }
                    }
                } else {
                    const error = await response.text();
                    resultDiv.innerHTML = '<div class="result error">Error: ' + escapeHtml(error) + '</div>';
                }
            } catch (error) {
                clearInterval(progressInterval);
                resultDiv.innerHTML = '<div class="result error">Network error: ' + escapeHtml(error.message) + '</div>';
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = 'Convert DOIs';
                
                // Hide progress bar after 2 seconds
                setTimeout(() => {
                    progressContainer.style.display = 'none';
                }, 2000);
            }
        });
        
        function downloadFile(content, format) {
            const timestamp = new Date().toISOString().slice(0, 19).replace(/[:.]/g, '-');
            let extension, mimeType, prefix;
            
            switch(format) {
                case 'xml':
                    extension = 'xml';
                    mimeType = 'application/xml';
                    prefix = 'doi-bibliography';
                    break;
                case 'tex':
                    extension = 'tex';
                    mimeType = 'text/plain';
                    prefix = 'doi-text-with-citations';
                    break;
                case 'markdown':
                    extension = 'md';
                    mimeType = 'text/markdown';
                    prefix = 'doi-text-with-citations';
                    break;
                default: // bibtex
                    extension = 'bib';
                    mimeType = 'text/plain';
                    prefix = 'doi-bibliography';
                    break;
            }
            
            const filename = `${prefix}-${timestamp}.${extension}`;
            
            const blob = new Blob([content], { type: mimeType });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }
        
        function escapeHtml(unsafe) {
            return unsafe
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }
    </script>
</body>
</html>
"""

# Rate limiting
last_request_time = 0
MIN_REQUEST_INTERVAL = 0.1  # 100ms between requests (10 requests/second to be polite)

def clean_doi(doi_string):
    """Extract clean DOI from various input formats"""
    # Remove whitespace
    doi_string = doi_string.strip()
    
    # Extract DOI from URL if present
    if 'doi.org/' in doi_string:
        doi_string = doi_string.split('doi.org/')[-1]
    
    # Remove 'doi:' prefix if present
    if doi_string.lower().startswith('doi:'):
        doi_string = doi_string[4:]
    
    # Remove trailing punctuation that might be from sentence context
    while doi_string and doi_string[-1] in '.,;:)]}':
        doi_string = doi_string[:-1]
    
    return doi_string

def extract_dois_from_text(text: str) -> List[Tuple[str, int, int]]:
    """Extract all DOIs from text using regex patterns, returning DOI, start, end positions"""
    doi_patterns = [
        # Standard DOI pattern - more permissive, stops at whitespace, brackets, or end of sentence
        r'10\.\d{4,}\/[^\s\(\)\[\]\,\;]+',
        # DOI with doi: prefix
        r'doi:\s*10\.\d{4,}\/[^\s\(\)\[\]\,\;]+',
        # DOI URLs
        r'https?:\/\/(?:dx\.)?doi\.org\/10\.\d{4,}\/[^\s\(\)\[\]\,\;]+',
        # DOI URLs without protocol
        r'(?:dx\.)?doi\.org\/10\.\d{4,}\/[^\s\(\)\[\]\,\;]+'
    ]
    
    found_dois = []
    
    app.logger.info(f"Extracting DOIs from text: {text[:200]}...")
    
    for i, pattern in enumerate(doi_patterns):
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            raw_doi = match.group()
            start_pos = match.start()
            end_pos = match.end()
            
            app.logger.info(f"Pattern {i+1} found raw match: '{raw_doi}' at {start_pos}-{end_pos}")
            
            # Clean the DOI
            cleaned_doi = clean_doi(raw_doi)
            app.logger.info(f"Cleaned to: '{cleaned_doi}'")
            
            # Validate that it's actually a DOI (has the right structure)
            if re.match(r'^10\.\d{4,}\/[a-zA-Z0-9\.\-_\(\)\/]+$', cleaned_doi):
                found_dois.append((cleaned_doi, start_pos, end_pos))
                app.logger.info(f"Added valid DOI: '{cleaned_doi}' at {start_pos}-{end_pos}")
            else:
                app.logger.warning(f"Rejected invalid DOI format: '{cleaned_doi}'")
    
    # Sort by start position to maintain order
    found_dois.sort(key=lambda x: x[1])
    
    app.logger.info(f"Final extracted DOIs with positions: {found_dois}")
    return found_dois

def parse_input_text(input_text: str) -> List[str]:
    """Parse input text to extract DOIs, handling both line-by-line DOIs and full text"""
    input_text = input_text.strip()
    
    if not input_text:
        return []
    
    app.logger.info(f"Parsing input text of length {len(input_text)}")
    
    # First, try to extract DOIs from the entire text
    extracted_dois_with_pos = extract_dois_from_text(input_text)
    extracted_dois = [doi for doi, _, _ in extracted_dois_with_pos]
    app.logger.info(f"Extracted DOIs from full text: {extracted_dois}")
    
    # Also check if input looks like line-by-line DOIs
    lines = [line.strip() for line in input_text.split('\n') if line.strip()]
    line_dois = set()
    
    app.logger.info(f"Processing {len(lines)} lines for line-by-line DOIs")
    
    for line in lines:
        # If line looks like it might be a DOI (contains the typical pattern)
        if re.search(r'10\.\d{4,}', line):
            clean_doi_str = clean_doi(line)
            app.logger.info(f"Line '{line[:50]}...' -> cleaned: '{clean_doi_str}'")
            if clean_doi_str and re.match(r'^10\.\d{4,}\/[a-zA-Z0-9\.\-_\(\)\/]+$', clean_doi_str):
                line_dois.add(clean_doi_str)
                app.logger.info(f"Added line DOI: '{clean_doi_str}'")
    
    # Combine both methods, preferring extracted DOIs if we found any
    all_dois_set = set(extracted_dois).union(line_dois) if extracted_dois else line_dois
    
    # Preserve order from extracted DOIs, then add any additional from line parsing
    result = []
    for doi in extracted_dois:
        if doi not in result:
            result.append(doi)
    
    for doi in line_dois:
        if doi not in result:
            result.append(doi)
    
    app.logger.info(f"Final combined DOIs: {result}")
    return result

def fetch_doi_metadata(doi):
    """Fetch metadata for a DOI from CrossRef with rate limiting"""
    global last_request_time
    
    try:
        # Rate limiting - ensure we don't exceed CrossRef's limits
        current_time = time.time()
        time_since_last = current_time - last_request_time
        if time_since_last < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - time_since_last)
        
        clean_doi_str = clean_doi(doi)
        url = f"https://api.crossref.org/works/{quote(clean_doi_str)}"
        
        headers = {
            'User-Agent': 'DOI-Bibliography-Converter/1.0 (mailto:user@example.com)',
            'Accept': 'application/json'
        }
        
        last_request_time = time.time()
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        return data['message']
    
    except Exception as e:
        app.logger.error(f"Error fetching DOI {doi}: {str(e)}")
        return None

def format_authors_bibtex(authors):
    """Format authors for BibTeX"""
    if not authors:
        return ""
    
    author_list = []
    for author in authors:
        if 'family' in author and 'given' in author:
            author_list.append(f"{author['family']}, {author['given']}")
        elif 'family' in author:
            author_list.append(author['family'])
    
    return " and ".join(author_list)

def format_authors_xml(authors):
    """Format authors for XML"""
    if not authors:
        return ""
    
    author_list = []
    for author in authors:
        if 'family' in author and 'given' in author:
            author_list.append(f"{author['given']} {author['family']}")
        elif 'family' in author:
            author_list.append(author['family'])
    
    return "; ".join(author_list)

def generate_bibtex_key(metadata):
    """Generate a BibTeX key from metadata"""
    # Use first author's last name + year
    authors = metadata.get('author', [])
    year = ""
    
    if 'created' in metadata:
        year = str(metadata['created']['date-parts'][0][0])
    elif 'published-print' in metadata:
        year = str(metadata['published-print']['date-parts'][0][0])
    elif 'published-online' in metadata:
        year = str(metadata['published-online']['date-parts'][0][0])
    
    if authors and 'family' in authors[0]:
        first_author = authors[0]['family'].replace(' ', '').replace('-', '')
        key = f"{first_author}{year}"
    else:
        key = f"unknown{year}"
    
    return key

def metadata_to_bibtex(metadata):
    """Convert CrossRef metadata to BibTeX format"""
    entry_type = "article"  # Default to article
    
    # Determine entry type based on publication type
    pub_type = metadata.get('type', '').lower()
    if 'book' in pub_type:
        entry_type = "book"
    elif 'conference' in pub_type or 'proceedings' in pub_type:
        entry_type = "inproceedings"
    
    key = generate_bibtex_key(metadata)
    
    bibtex = f"@{entry_type}{{{key},\n"
    
    # Title
    if 'title' in metadata and metadata['title']:
        title = metadata['title'][0].replace('{', '').replace('}', '')
        bibtex += f"  title = {{{title}}},\n"
    
    # Authors
    if 'author' in metadata:
        authors = format_authors_bibtex(metadata['author'])
        if authors:
            bibtex += f"  author = {{{authors}}},\n"
    
    # Journal
    if 'container-title' in metadata and metadata['container-title']:
        journal = metadata['container-title'][0]
        bibtex += f"  journal = {{{journal}}},\n"
    
    # Year
    year = ""
    if 'created' in metadata:
        year = str(metadata['created']['date-parts'][0][0])
    elif 'published-print' in metadata:
        year = str(metadata['published-print']['date-parts'][0][0])
    elif 'published-online' in metadata:
        year = str(metadata['published-online']['date-parts'][0][0])
    
    if year:
        bibtex += f"  year = {{{year}}},\n"
    
    # Volume
    if 'volume' in metadata:
        bibtex += f"  volume = {{{metadata['volume']}}},\n"
    
    # Issue/Number
    if 'issue' in metadata:
        bibtex += f"  number = {{{metadata['issue']}}},\n"
    
    # Pages
    if 'page' in metadata:
        bibtex += f"  pages = {{{metadata['page']}}},\n"
    
    # DOI
    if 'DOI' in metadata:
        bibtex += f"  doi = {{{metadata['DOI']}}},\n"
    
    # URL
    if 'URL' in metadata:
        bibtex += f"  url = {{{metadata['URL']}}},\n"
    
    bibtex += "}\n"
    
    return bibtex, key

def metadata_to_msword_xml(metadata_list):
    """Convert list of CrossRef metadata to MS Word XML bibliography format"""
    # Create root element
    root = ET.Element("b:Sources")
    root.set("SelectedStyle", "\\APASixthEditionOfficeOnline.xsl")
    root.set("StyleName", "APA")
    root.set("xmlns:b", "http://schemas.openxmlformats.org/officeDocument/2006/bibliography")
    root.set("xmlns", "http://schemas.openxmlformats.org/officeDocument/2006/bibliography")
    
    for i, metadata in enumerate(metadata_list):
        source = ET.SubElement(root, "b:Source")
        
        # Tag (unique identifier)
        tag = ET.SubElement(source, "b:Tag")
        tag.text = f"Source{i+1}"
        
        # Source type (most will be journal articles)
        source_type = ET.SubElement(source, "b:SourceType")
        source_type.text = "ArticleInAPeriodical"
        
        # Title
        if 'title' in metadata and metadata['title']:
            title = ET.SubElement(source, "b:Title")
            title.text = metadata['title'][0]
        
        # Authors
        if 'author' in metadata and metadata['author']:
            authors_elem = ET.SubElement(source, "b:Author")
            name_list = ET.SubElement(authors_elem, "b:NameList")
            
            for author in metadata['author'][:10]:  # Limit to first 10 authors
                person = ET.SubElement(name_list, "b:Person")
                
                if 'given' in author:
                    first = ET.SubElement(person, "b:First")
                    first.text = author['given']
                
                if 'family' in author:
                    last = ET.SubElement(person, "b:Last")
                    last.text = author['family']
        
        # Journal name
        if 'container-title' in metadata and metadata['container-title']:
            journal = ET.SubElement(source, "b:JournalName")
            journal.text = metadata['container-title'][0]
        
        # Year
        year = ""
        if 'created' in metadata:
            year = str(metadata['created']['date-parts'][0][0])
        elif 'published-print' in metadata:
            year = str(metadata['published-print']['date-parts'][0][0])
        elif 'published-online' in metadata:
            year = str(metadata['published-online']['date-parts'][0][0])
        
        if year:
            year_elem = ET.SubElement(source, "b:Year")
            year_elem.text = year
        
        # Volume
        if 'volume' in metadata:
            volume = ET.SubElement(source, "b:Volume")
            volume.text = metadata['volume']
        
        # Issue
        if 'issue' in metadata:
            issue = ET.SubElement(source, "b:Issue")
            issue.text = metadata['issue']
        
        # Pages
        if 'page' in metadata:
            pages = ET.SubElement(source, "b:Pages")
            pages.text = metadata['page']
        
        # DOI
        if 'DOI' in metadata:
            doi = ET.SubElement(source, "b:DOI")
            doi.text = metadata['DOI']
    
    # Convert to pretty-printed XML string
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent="  ")

def create_tex_file_with_citations(original_text: str, doi_to_key_mapping: Dict[str, str]) -> str:
    """Replace DOIs in original text with TeX citation commands"""
    
    # Get all DOIs with their positions
    dois_with_positions = extract_dois_from_text(original_text)
    
    # Sort by position in reverse order to replace from end to beginning
    # This prevents position shifts from affecting subsequent replacements
    dois_with_positions.sort(key=lambda x: x[1], reverse=True)
    
    result_text = original_text
    
    for doi, start_pos, end_pos in dois_with_positions:
        clean_doi_str = clean_doi(doi)
        
        if clean_doi_str in doi_to_key_mapping:
            bibtex_key = doi_to_key_mapping[clean_doi_str]
            citation_command = f"\\cite{{{bibtex_key}}}"
            
            # Replace the DOI with the citation command
            result_text = result_text[:start_pos] + citation_command + result_text[end_pos:]
            
            app.logger.info(f"Replaced DOI '{doi}' at {start_pos}-{end_pos} with '{citation_command}'")
    
    return result_text

def create_markdown_file_with_citations(original_text: str, doi_to_key_mapping: Dict[str, str]) -> str:
    """Replace DOIs in original text with Markdown citation commands for Pandoc"""
    
    # Get all DOIs with their positions
    dois_with_positions = extract_dois_from_text(original_text)
    
    # Sort by position in reverse order to replace from end to beginning
    # This prevents position shifts from affecting subsequent replacements
    dois_with_positions.sort(key=lambda x: x[1], reverse=True)
    
    result_text = original_text
    
    for doi, start_pos, end_pos in dois_with_positions:
        clean_doi_str = clean_doi(doi)
        
        if clean_doi_str in doi_to_key_mapping:
            bibtex_key = doi_to_key_mapping[clean_doi_str]
            citation_command = f"@{bibtex_key}"
            
            # Replace the DOI with the citation command
            result_text = result_text[:start_pos] + citation_command + result_text[end_pos:]
            
            app.logger.info(f"Replaced DOI '{doi}' at {start_pos}-{end_pos} with '{citation_command}'")
    
    return result_text

@app.route('/')
def index():
    """Serve the main page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/convert', methods=['POST'])
def convert_dois():
    """Convert DOIs to requested format"""
    try:
        input_text = request.form.get('dois', '').strip()
        output_format = request.form.get('format', 'bibtex')
        for_tex = request.form.get('forTex') == 'on'
        for_markdown = request.form.get('forMarkdown') == 'on'
        
        if not input_text:
            return "Please enter some text or DOIs", 400
        
        # Parse input text to extract DOIs
        dois = parse_input_text(input_text)
        
        if not dois:
            return "No valid DOIs found in the input text", 400
        
        # Remove duplicates while preserving order
        unique_dois = list(dict.fromkeys(dois))
        
        app.logger.info(f"Found {len(unique_dois)} unique DOIs: {unique_dois}")
        
        # Fetch metadata for all DOIs
        metadata_list = []
        failed_dois = []
        doi_to_key_mapping = {}  # For TeX citation mapping
        
        for i, doi in enumerate(unique_dois):
            app.logger.info(f"Processing DOI {i+1}/{len(unique_dois)}: {doi}")
            metadata = fetch_doi_metadata(doi)
            if metadata:
                metadata_list.append(metadata)
                # Store the mapping from DOI to BibTeX key for TeX generation
                if output_format == 'bibtex':
                    _, bibtex_key = metadata_to_bibtex(metadata)
                    doi_to_key_mapping[doi] = bibtex_key
            else:
                failed_dois.append(doi)
        
        if not metadata_list:
            return f"Failed to fetch metadata for all DOIs: {', '.join(failed_dois)}", 400
        
        # Generate output based on format
        if output_format == 'bibtex':
            result = f"% Generated {len(metadata_list)} BibTeX entries from {len(unique_dois)} DOIs\n\n"
            for metadata in metadata_list:
                bibtex_entry, _ = metadata_to_bibtex(metadata)
                result += bibtex_entry + "\n"
            
            if failed_dois:
                result += f"\n% Failed to process: {', '.join(failed_dois)}\n"
            
            # Generate TeX and/or Markdown files if requested
            if for_tex or for_markdown:
                response_data = {
                    'main_content': result
                }
                
                if for_tex:
                    tex_content = create_tex_file_with_citations(input_text, doi_to_key_mapping)
                    response_data['tex_content'] = tex_content
                
                if for_markdown:
                    markdown_content = create_markdown_file_with_citations(input_text, doi_to_key_mapping)
                    response_data['markdown_content'] = markdown_content
                
                # Return all files as JSON
                return Response(json.dumps(response_data), mimetype='application/json')
            else:
                return Response(result, mimetype='text/plain')
        
        elif output_format == 'xml':
            result = metadata_to_msword_xml(metadata_list)
            
            if failed_dois:
                result += f"\n<!-- Generated {len(metadata_list)} entries from {len(unique_dois)} DOIs -->\n"
                result += f"<!-- Failed to process: {', '.join(failed_dois)} -->\n"
            
            # Note: TeX/Markdown generation doesn't make sense for XML format
            return Response(result, mimetype='application/xml')
        
        else:
            return "Invalid output format", 400
    
    except Exception as e:
        app.logger.error(f"Error in convert_dois: {str(e)}")
        return f"Server error: {str(e)}", 500

# Production configuration
if __name__ == "__main__":
    # This section won't be used in WSGI deployment
    app.run(host='0.0.0.0', port=5000, debug=False)
