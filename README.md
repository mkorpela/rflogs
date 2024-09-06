# rflogs CLI

`rflogs` is a command-line interface tool for uploading and managing Robot Framework test results with the RF Logs service. It provides an easy way to integrate RF Logs with your CI/CD pipelines or local development workflow.

## Installation

Install `rflogs` using pipx (recommended) or pip:

```bash
pipx install rflogs
```

or

```bash
pip install rflogs
```

## Usage

### Authentication

`rflogs` uses an API key for authentication. Set your RF Logs API key as an environment variable:

```bash
export RFLOGS_API_KEY=your_api_key_here
```

You can add this line to your shell configuration file (e.g., `.bashrc`, `.zshrc`) to make it permanent.

### Uploading Test Results

Upload test results after running your Robot Framework tests:

```bash
rflogs upload [OUTPUTDIR]
```

- `OUTPUTDIR`: Optional. Specifies the location of the test output files. Default is the current directory.
- The command does not perform a recursive search.

This command will:
1. Find relevant test result files (log.html, report.html, output.xml, and screenshots) in the specified directory
2. Compress output.xml using tar.gz
3. Upload all files to the RF Logs server
4. Provide a link to view the uploaded results

Example output:

```
$ rflogs upload ./results
Uploading results
  output.xml    1.20 MB - compressed to 800.00 KB ✓
  log.html    256.00 KB ✓
  report.html 128.00 KB ✓
  screenshot1.png 45.00 KB ✓
  screenshot2.png 52.00 KB ✓

Run ID: 1234abcd
Files:  5
Size:   1.28 MB

Overview: https://rflogs.io/runs/1234abcd
Log:      https://rflogs.io/runs/1234abcd/log.html
Report:   https://rflogs.io/runs/1234abcd/report.html
```

### Listing Uploads

View your recent uploads:

```bash
rflogs list
```

Example output:

```
$ rflogs list
Available runs:
  1234abcd
  5678efgh
  90ijklmn

To view details of a specific run, use: rflogs info <run_id>
```

### View Upload Details

Get details about a specific result:

```bash
rflogs info <run_id>
```

Example output:

```
$ rflogs info 1234abcd
Run ID: 1234abcd
Files: 5
  - log.html (ID: 1)
  - report.html (ID: 2)
  - output.xml (ID: 3)
  - screenshot1.png (ID: 4)
  - screenshot2.png (ID: 5)
```

### Downloading Test Results

Download test results to your local machine:

```bash
rflogs download <run_id>
```

This command downloads all files associated with the specified test result to your current directory.

Example output:

```
$ rflogs download 1234abcd
Downloaded log.html
Downloaded report.html
Downloaded output.xml
Downloaded screenshot1.png
Downloaded screenshot2.png
```

### Deleting a Test Run

To delete a specific run:

```bash
rflogs delete <run_id>
```

This command will immediately delete the specified run and its associated files from the server.

## Integration with CI/CD Systems

### GitHub Actions

To integrate `rflogs` with GitHub Actions, add the following step to your workflow:

```yaml
- name: Upload Robot Framework results
  env:
    RFLOGS_API_KEY: ${{ secrets.RFLOGS_API_KEY }}
  run: |
    pipx install rflogs
    rflogs upload ./results
```

Make sure to set the `RFLOGS_API_KEY` secret in your GitHub repository settings.

### Other CI/CD Systems

For other CI/CD systems:

1. Install the RF Logs CLI tool in your CI environment
2. Set the `RFLOGS_API_KEY` environment variable
3. Run `rflogs upload` with the appropriate output directory
