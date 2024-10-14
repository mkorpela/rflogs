*** Settings ***
Library           SeleniumLibrary

*** Test Cases ***
Capture Screenshot of RF Logs Website
    Open Browser    https://rflogs.io    chrome
    Maximize Browser Window
    Capture Page Screenshot    rflogs_selenium.png
    Close Browser
