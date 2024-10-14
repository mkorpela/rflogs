*** Settings ***
Library           Browser

*** Test Cases ***
Capture Screenshot of RF Logs Website
    New Browser    chromium    headless=False
    New Page       https://rflogs.io
    Take Screenshot    fullPage=True    filename=rflogs_browser
    Close Browser
