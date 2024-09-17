import argparse
import gzip
from html.parser import HTMLParser
import os
import sys
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

def get_session():
    api_key = os.environ.get("RFLOGS_API_KEY")
    if not api_key:
        raise Exception(
            "RFLOGS_API_KEY environment variable not set. "
            "Please set it to your RF Logs API key before running the command."
        )
    session = requests.Session()
    session.headers.update({"X-API-Key": api_key})
    return session

def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def compress_file(file_path):
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

def upload_files(directory):
    try:
        session = get_session()
    except Exception as e:
        print(str(e))
        return

    create_run_url = f"{BASE_URL}/api/runs"
    response = session.post(create_run_url)
    if response.status_code != 200:
        print(f"Error creating run: {response.text}")
        return

    run_id = response.json()["run_id"]
    upload_url = f"{BASE_URL}/api/runs/{run_id}/upload"
    files_to_upload = find_robot_files(directory)

    if not files_to_upload:
        print(f"No Robot Framework test results found in {directory}")
        return

    print("Uploading results")

    total_size = 0
    uploaded_files = []

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
            # Send the file_name including subdirectory structure
            files = {"file": (file_name, file)}
            response = session.post(upload_url, files=files)

        if response.status_code == 200:
            uploaded_files.append(response.json())
            sys.stdout.write(" [OK]\n")
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
        print("\nUploaded files:")
        for file in uploaded_files:
            print(f"  {file['file_name']}: {BASE_URL}{file['file_url']}")
        print("\nNote: You need to be logged in to access these files in your browser.")
    else:
        print("\nUpload failed. Some files were not uploaded successfully.")

def find_robot_files(directory):
    robot_files = []
    standard_files = ["log.html", "report.html", "output.xml"]
    for filename in os.listdir(directory):
        if filename in standard_files:
            robot_files.append(os.path.join(directory, filename))

    # Parse output.xml to find additional files
    output_xml_path = os.path.join(directory, "output.xml")

    additional_files = set()
    if os.path.exists(output_xml_path):
        additional_files.update(parse_output_xml(output_xml_path, directory))

    robot_files.extend(list(additional_files))
    return robot_files

class MsgHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.file_paths = []

    def handle_starttag(self, tag, attrs):
        for attr_name, attr_value in attrs:
            if attr_name in ["src", "href"]:
                self.file_paths.append(attr_value)

def parse_output_xml(output_xml_path, base_directory):
    # Efficiently parse output.xml
    additional_files = set()
    base_directory = os.path.abspath(base_directory)  # Get absolute path of base directory

    context = ET.iterparse(output_xml_path, events=("end",))
    for event, elem in context:
        if elem.tag == "msg" and elem.get("html") == "true":
            html_content = elem.text or ""
            parser = MsgHTMLParser()
            parser.feed(html_content)
            for file_path in parser.file_paths:
                # Resolve the file path relative to base_directory
                resolved_path = os.path.join(base_directory, file_path)
                # Normalize the path to handle any .. or .
                resolved_path = os.path.normpath(resolved_path)
                # Get absolute path
                resolved_path = os.path.abspath(resolved_path)
                # Check if the resolved path is within the base_directory
                if os.path.commonprefix([resolved_path, base_directory]) == base_directory:
                    # Check if the file exists
                    if os.path.isfile(resolved_path):
                        additional_files.add(resolved_path)
                else:
                    # The file is outside the base_directory; ignore it
                    pass
        # Clear the element to free memory
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
        return

    url = f"{BASE_URL}/api/runs"
    response = session.get(url)
    if response.status_code == 200:
        runs = response.json()["runs"]
        print("Available runs:")
        for run_id in runs:
            print(f"  {run_id}")
    else:
        print(f"Failed to retrieve runs: {response.status_code}")
        print(f"Response content: {response.text}")

def download_files(run_id, output_dir):
    try:
        session = get_session()
    except Exception as e:
        print(str(e))
        return

    # Get run information
    run_info_url = urljoin(BASE_URL, f"/api/runs/{run_id}")
    response = session.get(run_info_url)
    if response.status_code != 200:
        print(f"Failed to retrieve run info: {response.status_code}")
        print(f"Response content: {response.text}")
        return

    run_info = response.json()
    files = run_info.get("files", [])

    for file in files:
        file_name = file["name"]
        file_path = file["path"]
        file_url = urljoin(BASE_URL, f"/api/files/{file_path}")

        response = session.get(file_url)
        if response.status_code == 200:
            file_path = os.path.join(output_dir, file_name)
            with open(file_path, "wb") as f:
                f.write(response.content)
            print(f"Downloaded {file_name}")
        else:
            print(f"Failed to download {file_name}: {response.status_code}")
            print(f"Response content: {response.text}")

def delete_run(run_id):
    try:
        session = get_session()
    except Exception as e:
        print(str(e))
        return

    delete_url = f"{BASE_URL}/api/runs/{run_id}"
    response = session.delete(delete_url)

    if response.status_code == 200:
        print(f"Run {run_id} deleted successfully.")
    elif response.status_code == 404:
        print(f"Run {run_id} not found or you are not authorized to delete it.")
    else:
        print(f"Failed to delete run {run_id}: {response.status_code}")
        print(f"Response content: {response.text}")

def main():
    parser = argparse.ArgumentParser(
        description=f"RF Logs CLI v{__version__} - A tool for managing Robot Framework test results with rflogs.io",
        epilog="For more information, visit https://rflogs.io"
    )
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
    subparsers = parser.add_subparsers(dest="action", required=True)

    upload_parser = subparsers.add_parser("upload", help="Upload test results to rflogs.io")
    upload_parser.add_argument(
        "directory", nargs="?", default=".", help="Directory containing test results"
    )

    info_parser = subparsers.add_parser("info", help="Get run information from rflogs.io")
    info_parser.add_argument("run_id", help="Run ID to get information for")

    download_parser = subparsers.add_parser("download", help="Download test results from rflogs.io")
    download_parser.add_argument("run_id", help="Run ID to download")
    download_parser.add_argument(
        "--output-dir", default=".", help="Directory to save downloaded files"
    )

    delete_parser = subparsers.add_parser("delete", help="Delete a specific run from rflogs.io")
    delete_parser.add_argument("run_id", help="Run ID to delete")

    subparsers.add_parser("list", help="List available runs on rflogs.io")

    args = parser.parse_args()

    if args.action == "upload":
        upload_files(args.directory)
    elif args.action == "info":
        info = get_run_info(args.run_id)
        if info:
            print(f"Run ID: {args.run_id}")
            print(f"Files: {len(info['files'])}")
            for file in info['files']:
                print(f"  - {file['name']} (ID: {file['id']})")
    elif args.action == "download":
        download_files(args.run_id, args.output_dir)
    elif args.action == "list":
        list_runs()
    elif args.action == "delete":
        delete_run(args.run_id)

if __name__ == "__main__":
    main()