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
Without a valid API key, rflogs commands will not work. Ensure you have set this environment variable before proceeding with any operations.

After setting up your API key and installing rflogs, you can start using the tool. Here are the main commands:

- `rflogs upload`: Upload test results
- `rflogs list`: List available runs
- `rflogs info`: Get information about a specific run
- `rflogs download`: Download test results
- `rflogs delete`: Delete a specific run

### Uploading Test Results

Upload test results after running your Robot Framework tests:

```bash
rflogs upload [OPTIONS] [OUTPUTDIR]
```

- `OUTPUTDIR`: Optional. Specifies the location of the test output files. Default is the current directory.
- The command does not perform a recursive search.

Options:
- `-o`, `--output`: Specify the XML output file. Default: output.xml
- `-l`, `--log`: Specify the HTML log file. Default: log.html
- `-r`, `--report`: Specify the HTML report file. Default: report.html
- Use `NONE` as the value to skip uploading a specific file type.

This command will:
1. Find relevant test result files in the specified directory
2. Compress output.xml using gzip if it's larger than 1MB
3. Upload all files to the RF Logs server
4. Provide a link to view the uploaded results

Example usage:

```bash
rflogs upload ./results --output custom_output.xml --log custom_log.html --report NONE
```

Example output:

```
$ rflogs upload ./results
Uploading results
  output.xml    1.20 MB - compressed to 800.00 KB [OK]
  log.html    256.00 KB [OK]
  report.html 128.00 KB [OK]
  screenshot1.png 45.00 KB [OK]
  screenshot2.png 52.00 KB [OK]

Run ID: 1234abcd
Files:  5
Size:   1.28 MB

HTML Files:
  Log:      https://rflogs.io/files/log.html
  Report:   https://rflogs.io/files/report.html
  Run:      https://rflogs.io/run-details.html?runId=1234abcd
```

## Tagging Runs

You can associate tags with your test runs to categorize and filter them. Tags can be specified using the `--tag` or `-t` option when uploading results.

### Tag Format

- **Key-Value Tags:** `key:value`
- **Simple Tags:** `tag`

### Examples

```bash
rflogs upload -t env:production -t browser:chrome -t regression
```

Tags help in organizing and filtering your test runs on the RF Logs platform.
