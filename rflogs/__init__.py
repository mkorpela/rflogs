import argparse
import datetime
import gzip
from html.parser import HTMLParser
import os
import re
import sys
import warnings
from typing import Any, Dict, List, Set, Tuple
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
from importlib.metadata import version, PackageNotFoundError

import requests

try:
    __version__ = version("rflogs")
except PackageNotFoundError:
    # package is not installed
    __version__ = "unknown"

# Use environment variable to override base URL, defaulting to production
BASE_URL = os.environ.get("RFLOGS_BASE_URL", "https://rflogs.io")
TAG_KEY_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.-]{0,49}$")
TAG_VALUE_PATTERN = re.compile(r"^[a-zA-Z0-9_.\-/\s]{1,100}$")


def get_session():
    api_key = os.environ.get("RFLOGS_API_KEY")
    if not api_key:
        raise Exception(
            "RFLOGS_API_KEY environment variable not set. "
            "Please set it to your RF Logs API key before running the command."
        )
    session = requests.Session()
    session.headers.update({"X-API-Key": api_key})

    # Allow disabling SSL verification (with a warning) as a last resort
    if os.environ.get('RFLOGS_VERIFY_SSL', 'true').lower() == 'false':
        warnings.warn("SSL certificate verification is disabled. This is insecure and should only be used in trusted environments.")
        session.verify = False

    return session


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def compress_file(file_path: str) -> str:
    if (
        os.path.basename(file_path) == "output.xml"
        and os.path.getsize(file_path) > 1 * 1024 * 1024
    ):  # 1MB
        compressed_path = file_path + ".gz"
        with open(file_path, "rb") as f_in:
            with gzip.open(compressed_path, "wb") as f_out:
                f_out.writelines(f_in)
        return compressed_path
    return file_path


def upload_files(directory: str, tags=None, output="output.xml", log="log.html", report="report.html") -> bool:
    try:
        session = get_session()
    except Exception as e:
        print(str(e))
        return False

    # Validate and process tags
    processed_tags = []
    if tags:
        for tag_str in tags:
            if ":" in tag_str:
                key, value = tag_str.split(":", 1)
            else:
                key = tag_str
                value = "true"
            key = key.strip()
            value = value.strip()

            if not TAG_KEY_PATTERN.fullmatch(key):
                print(
                    f"Invalid tag key '{key}'. Must start with a letter, and be 1-50 characters long. Allowed characters: letters, numbers, '_', '-', '.'"
                )
                continue

            if not TAG_VALUE_PATTERN.fullmatch(value):
                print(
                    f"Invalid tag value '{value}'. Must be 1-100 characters long. Allowed characters: letters, numbers, spaces, '_', '-', '.', '/'"
                )
                continue

            processed_tags.append(f"{key}:{value}")

    files_to_upload = find_robot_files(directory, output, log, report)

    if not files_to_upload:
        print(f"Error: No Robot Framework test results found in {directory} with the specified filenames.")
        return False

    # Prepare run data
    run_data = {
        "tags": processed_tags,
    }

    create_run_url = f"{BASE_URL}/api/runs"
    response = session.post(create_run_url, json=run_data)
    if response.status_code != 200:
        print(f"Error creating run: {response.text}")
        return False

    run_id = response.json()["run_id"]
    upload_url = f"{BASE_URL}/api/runs/{run_id}/upload"

    print("Uploading results")

    total_size = 0
    uploaded_files = []
    html_files = []

    for file_path in files_to_upload:
        # Get the relative file path from the base directory, preserving subdirectories
        file_name = os.path.relpath(file_path, start=directory)
        original_size = os.path.getsize(file_path)

        sys.stdout.write(f"  {file_name:<40} {format_size(original_size):>8}")
        sys.stdout.flush()

        file_to_upload = compress_file(file_path)
        upload_size = os.path.getsize(file_to_upload)

        if file_to_upload.endswith(".gz"):
            sys.stdout.write(f" - compressed to {format_size(upload_size)}")
            sys.stdout.flush()

        with open(file_to_upload, "rb") as file:
            file_to_upload_name = os.path.relpath(file_to_upload, start=directory)
            # Send the file_name including subdirectory structure
            files = {"file": (file_to_upload_name, file)}
            data = {"is_output_file": "true" if file_name == output else "false"}
            response = session.post(upload_url, files=files, data=data)

        if response.status_code == 200:
            upload_response = response.json()
            uploaded_files.append(upload_response)
            sys.stdout.write(" [OK]\n")

            if file_name.lower().endswith(".html"):
                html_files.append(
                    {
                        "label": os.path.basename(file_name).capitalize()[:-5],
                        "url": f"{BASE_URL}{upload_response['file_url']}",
                    }
                )
        else:
            sys.stdout.write(" [FAIL]\n")
            print(f"Error uploading {file_name}: {response.text}")

        sys.stdout.flush()

        if file_to_upload.endswith(".gz"):
            os.remove(file_to_upload)

        total_size += upload_size

    if len(uploaded_files) == len(files_to_upload):
        print(f"\nRun ID: {run_id}")
        print(f"Files:  {len(uploaded_files)}")
        print(f"Size:   {format_size(total_size)}")

        # Detect if running in GitHub Actions
        is_github_actions = os.environ.get("GITHUB_ACTIONS", "false") == "true"
        github_step_summary = os.environ.get("GITHUB_STEP_SUMMARY")

        # Prepare the run URL
        run_url = f"{BASE_URL}/run-details.html?runId={run_id}"

        if html_files:
            print("\nHTML Files:")
            for html_file in html_files:
                label = html_file["label"] + ":"
                url = html_file["url"]
                print(f"  {label:<10} {url}")
        print(f"  Run:       {run_url}")

        # Output links differently based on environment
        if is_github_actions and github_step_summary:
            # Write to GitHub Actions summary
            with open(github_step_summary, "a") as summary_file:
                # Build the list of available links
                links = [
                    f"[{html_file['label']}]({html_file['url']})"
                    for html_file in html_files
                ]
                if not links:
                    # No HTML files; provide Run link
                    links.append(f"[Results]({run_url})")

                # Write the links on the same line
                summary_file.write(" ".join(links) + "\n")
            print("\nUploaded results have been added to the GitHub Actions summary.")
        return True
    else:
        print("\nUpload failed. Some files were not uploaded successfully.")
        return False


def find_robot_files(directory: str, output: str, log: str, report: str) -> List[str]:
    robot_files = []
    
    if output.upper() != "NONE":
        output_path = os.path.join(directory, output)
        if os.path.exists(output_path):
            robot_files.append(output_path)
            additional_files = parse_output_xml(output_path, directory)
            robot_files.extend(list(additional_files))
    
    if log.upper() != "NONE":
        log_path = os.path.join(directory, log)
        if os.path.exists(log_path):
            robot_files.append(log_path)
    
    if report.upper() != "NONE":
        report_path = os.path.join(directory, report)
        if os.path.exists(report_path):
            robot_files.append(report_path)

    return robot_files


class MsgHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.file_paths = []

    def handle_starttag(self, tag, attrs):
        for attr_name, attr_value in attrs:
            if attr_name in ["src", "href"]:
                self.file_paths.append(attr_value)


def parse_output_xml(output_xml_path: str, base_directory: str) -> Set[str]:
    additional_files: Set[str] = set()
    base_directory = os.path.abspath(base_directory)

    context = ET.iterparse(output_xml_path, events=("end",))
    
    for _, elem in context:
        if elem.tag == "msg" and elem.get("html") == "true":
            html_content = elem.text or ""
            parser = MsgHTMLParser()
            parser.feed(html_content)
            for file_path in parser.file_paths:
                resolved_path = os.path.join(base_directory, file_path)
                resolved_path = os.path.normpath(resolved_path)
                resolved_path = os.path.abspath(resolved_path)
                if os.path.commonprefix([resolved_path, base_directory]) == base_directory:
                    if os.path.isfile(resolved_path):
                        additional_files.add(resolved_path)
        elem.clear()

    return additional_files


def get_run_info(run_id):
    try:
        session = get_session()
    except Exception as e:
        print(str(e))
        return

    url = f"{BASE_URL}/api/runs/{run_id}"
    response = session.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to retrieve run info: {response.status_code}")
        print(f"Response content: {response.text}")
        return None


def list_runs():
    try:
        session = get_session()
    except Exception as e:
        print(str(e))
        return False

    url = f"{BASE_URL}/api/runs"
    response = session.get(url)
    if response.status_code == 200:
        runs = response.json()["runs"]
        print("Available runs:")
        for run_id in runs:
            print(f"  {run_id}")
        return True
    else:
        print(f"Failed to retrieve runs: {response.status_code}")
        print(f"Response content: {response.text}")
        return False


def download_files(run_id, output_dir):
    try:
        session = get_session()
    except Exception as e:
        print(str(e))
        return False

    # Get run information
    run_info_url = urljoin(BASE_URL, f"/api/runs/{run_id}")
    response = session.get(run_info_url)
    if response.status_code != 200:
        print(f"Failed to retrieve run info: {response.status_code}")
        print(f"Response content: {response.text}")
        return False

    run_info = response.json()
    files = run_info.get("files", [])

    if not files:
        print(f"No files found for run ID: {run_id}")
        return False

    success = True
    for file in files:
        file_name = file["name"]
        file_path = file["path"]
        file_url = urljoin(BASE_URL, f"/files/{file_path}")

        response = session.get(file_url)
        if response.status_code == 200:
            file_path = os.path.join(output_dir, file_name)
            with open(file_path, "wb") as f:
                f.write(response.content)
            print(f"Downloaded {file_name}")
        else:
            print(f"Failed to download {file_name}: {response.status_code}")
            print(f"Response content: {response.text}")
            success = False

    return success


def delete_run(run_id):
    try:
        session = get_session()
    except Exception as e:
        print(str(e))
        return False

    delete_url = f"{BASE_URL}/api/runs/{run_id}"
    response = session.delete(delete_url)

    if response.status_code == 200:
        print(f"Run {run_id} deleted successfully.")
        return True
    elif response.status_code == 404:
        print(f"Run {run_id} not found or you are not authorized to delete it.")
        return False
    else:
        print(f"Failed to delete run {run_id}: {response.status_code}")
        print(f"Response content: {response.text}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description=f"RF Logs CLI v{__version__} - A tool for managing Robot Framework test results with rflogs.io",
        epilog="For more information, visit https://rflogs.io",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    upload_parser = subparsers.add_parser(
        "upload", help="Upload test results to rflogs.io"
    )
    upload_parser.add_argument(
        "-t",
        "--tag",
        action="append",
        help="Tag(s) to associate with the run, e.g., -t env:windows -t regression",
    )
    upload_parser.add_argument(
        "-o", "--output",
        default="output.xml",
        help="XML output file. Use NONE to disable upload. Default: output.xml"
    )
    upload_parser.add_argument(
        "-l", "--log",
        default="log.html",
        help="HTML log file. Use NONE to disable upload. Default: log.html"
    )
    upload_parser.add_argument(
        "-r", "--report",
        default="report.html",
        help="HTML report file. Use NONE to disable upload. Default: report.html"
    )
    upload_parser.add_argument(
        "directory", nargs="?", default=".", help="Directory containing test results"
    )

    info_parser = subparsers.add_parser(
        "info", help="Get run information from rflogs.io"
    )
    info_parser.add_argument("run_id", help="Run ID to get information for")

    download_parser = subparsers.add_parser(
        "download", help="Download test results from rflogs.io"
    )
    download_parser.add_argument("run_id", help="Run ID to download")
    download_parser.add_argument(
        "--output-dir", default=".", help="Directory to save downloaded files"
    )

    delete_parser = subparsers.add_parser(
        "delete", help="Delete a specific run from rflogs.io"
    )
    delete_parser.add_argument("run_id", help="Run ID to delete")

    subparsers.add_parser("list", help="List available runs on rflogs.io")

    args = parser.parse_args()

    try:
        if args.action == "upload":
            success = upload_files(args.directory, tags=args.tag, output=args.output, log=args.log, report=args.report)
            if not success:
                sys.exit(1)
        elif args.action == "info":
            info = get_run_info(args.run_id)
            if info:
                print(f"Run ID: {args.run_id}")
                print(f"Files: {len(info['files'])}")
                for file in info['files']:
                    print(f"  - {file['name']} (ID: {file['id']})")
            else:
                sys.exit(1)
        elif args.action == "download":
            success = download_files(args.run_id, args.output_dir)
            if not success:
                sys.exit(1)
        elif args.action == "list":
            success = list_runs()
            if not success:
                sys.exit(1)
        elif args.action == "delete":
            success = delete_run(args.run_id)
            if not success:
                sys.exit(1)
    except requests.exceptions.SSLError as e:
        print("SSL Certificate Verification Error:")
        print(str(e))
        print("\nTroubleshooting steps:")
        print("1. Ensure your system's root certificates are up to date.")
        print("2. If you're behind a corporate firewall, contact your IT department for assistance.")
        print("3. As a last resort, you can temporarily disable SSL verification (NOT RECOMMENDED) by setting RFLOGS_VERIFY_SSL=false")
        sys.exit(1)


if __name__ == "__main__":
    main()
