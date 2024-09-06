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

Authenticate with the RF Logs service:

```bash
rflogs login
```

This opens your default web browser to complete the authentication process. Once authenticated, a token is stored securely on your machine for future use.

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
Recent uploads:
1. Run ID: 1234abcd - Uploaded on 2023-06-15 14:30:00 UTC
   https://rflogs.io/runs/1234abcd
2. Run ID: 5678efgh - Uploaded on 2023-06-14 09:15:00 UTC
   https://rflogs.io/runs/5678efgh
3. Run ID: 90ijklmn - Uploaded on 2023-06-13 16:45:00 UTC
   https://rflogs.io/runs/90ijklmn

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
Uploaded on: 2023-06-15 14:30:00 UTC
Files:
  - log.html    (size: 256 KB)
  - report.html (size: 128 KB)
  - output.xml  (size: 1.2 MB)
  - screenshot1.png (size: 45 KB)
  - screenshot2.png (size: 52 KB)
Links:
  - Overview: https://rflogs.io/runs/1234abcd
  - Log:      https://rflogs.io/runs/1234abcd/log.html
  - Report:   https://rflogs.io/runs/1234abcd/report.html
Test Summary:
  - Total Tests: 50
  - Passed: 48
  - Failed: 2
  - Skipped: 0
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
Downloading files for run ID 1234abcd...
  - Downloading log.html...    Done
  - Downloading report.html... Done
  - Downloading output.xml...  Done
  - Downloading screenshot1.png... Done
  - Downloading screenshot2.png... Done
All files downloaded successfully to ./rflogs_1234abcd/
```
### Deleting a Test Run

To delete a specific run:

```bash
rflogs delete <run_id>
```

This command will immediately delete the specified run and its associated files from the server.

## Configuration

`rflogs` uses a configuration file located at `~/.config/rflogs/config.ini`. You can edit this file to change default behaviors or set environment-specific options.

## Integration with CI/CD Systems

### GitHub Actions

To integrate `rflogs` with GitHub Actions, add the following step to your workflow:

```yaml
- name: Upload Robot Framework results
  env:
    RFLOGS_TOKEN: ${{ secrets.RFLOGS_TOKEN }}
  run: |
    pipx install rflogs
    echo "Uploading Robot Framework test results..."
    output=$(rflogs upload ./results)
    echo "$output"
    echo "$output" >> $GITHUB_OUTPUT
```

Make sure to set the `RFLOGS_TOKEN` secret in your GitHub repository settings.

The `rflogs upload` command, when run in a CI environment, produces a simplified output optimized for GitHub Actions:

```
RFLOGS_RUN_ID=1234abcd
RFLOGS_OVERVIEW=https://rflogs.io/runs/1234abcd
RFLOGS_LOG=https://rflogs.io/runs/1234abcd/log.html
RFLOGS_REPORT=https://rflogs.io/runs/1234abcd/report.html
```

You can then use these outputs in subsequent steps of your workflow, for example:

```yaml
- name: Create workflow summary
  run: |
    echo "## RF Logs Test Results" >> $GITHUB_STEP_SUMMARY
    echo "✅ [Results Overview](${{ steps.upload.outputs.RFLOGS_OVERVIEW }})" >> $GITHUB_STEP_SUMMARY
    echo "📄 [Log](${{ steps.upload.outputs.RFLOGS_LOG }})" >> $GITHUB_STEP_SUMMARY
    echo "📊 [Report](${{ steps.upload.outputs.RFLOGS_REPORT }})" >> $GITHUB_STEP_SUMMARY

- name: Post links to PR comment
  if: github.event_name == 'pull_request'
  uses: actions/github-script@v6
  with:
    github-token: ${{secrets.GITHUB_TOKEN}}
    script: |
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.name,
        body: `## RF Logs Test Results for this PR
        - [Results Overview](${process.env.RFLOGS_OVERVIEW})
        - [Log](${process.env.RFLOGS_LOG})
        - [Report](${process.env.RFLOGS_REPORT})`
      })
```

### Other CI/CD Systems

For other CI/CD systems:

1. Install the RF Logs CLI tool in your CI environment
2. Set the `RFLOGS_TOKEN` environment variable
3. Run `rflogs upload` with the appropriate output directory

For more information about the RF Logs project, please refer to the [main README](../README.md).