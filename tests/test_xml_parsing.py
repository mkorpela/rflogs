import os
import pytest
from rflogs import parse_output_xml
import xml.etree.ElementTree as ET
from io import BytesIO
import datetime

def create_mock_xml(content):
    return BytesIO(f"""<?xml version="1.0" encoding="UTF-8"?>
<robot generator="Robot 7.0.1 (Python 3.11.7 on darwin)" generated="2024-10-11T22:26:20.293949" rpa="false" schemaversion="5">
{content}
</robot>""".encode('utf-8'))

def test_parse_output_xml_empty():
    mock_xml = create_mock_xml("")
    additional_files, stats = parse_output_xml(mock_xml, ".")
    
    assert len(additional_files) == 0
    assert stats == {
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "verdict": "pass",
        "start_time": None,
        "end_time": None,
    }

def test_parse_output_xml_with_tests():
    mock_xml = create_mock_xml("""
    <suite id="s1" name="Example Test">
        <status status="FAIL" start="2024-10-11T22:26:20.295908" elapsed="0.041915"/>
    </suite>
    <statistics>
        <total>
            <stat pass="1" fail="3" skip="0">All Tests</stat>
        </total>
    </statistics>
    """)
    
    additional_files, stats = parse_output_xml(mock_xml, ".")
    
    assert len(additional_files) == 0
    assert stats == {
        "total_tests": 4,
        "passed": 1,
        "failed": 3,
        "skipped": 0,
        "verdict": "fail",
        "start_time": datetime.datetime(2024, 10, 11, 22, 26, 20, 295908),
        "end_time": datetime.datetime(2024, 10, 11, 22, 26, 20, 337823),
    }

def test_parse_output_xml_with_html_msg():
    mock_xml = create_mock_xml("""
    <suite id="s1" name="Example Test">
        <status status="PASS" start="2024-10-11T22:26:20.295908" elapsed="0.041915"/>
        <test id="s1-t1" name="Test with HTML message">
            <kw name="Log" owner="BuiltIn">
                <msg html="true">
                    &lt;img src="screenshot.png" alt="Screenshot"&gt;
                    &lt;a href="report.html"&gt;Report&lt;/a&gt;
                </msg>
            </kw>
        </test>
    </suite>
    <statistics>
        <total>
            <stat pass="1" fail="0" skip="0">All Tests</stat>
        </total>
    </statistics>
    """)
    
    additional_files, stats = parse_output_xml(mock_xml, "/test/dir")
    
    #assert additional_files == {"/test/dir/screenshot.png", "/test/dir/report.html"}
    assert stats["verdict"] == "pass"

def test_parse_output_xml_with_video_msg():
    mock_xml = create_mock_xml("""
    <suite id="s1" name="Example Test">
        <status status="PASS" start="2024-10-11T10:34:51.295908" elapsed="0.356225"/>
        <test id="s1-t1" name="Test with video message">
            <kw name="Log" owner="BuiltIn">
                <msg time="2024-10-11T10:34:51.652133" level="INFO" html="true">&lt;/td&gt;&lt;/tr&gt;&lt;tr&gt;&lt;td colspan="3"&gt;&lt;video width="1280" height="720" controls&gt;&lt;source src="video/0-73a067fbe34b2b5cf7d977739ae2bf76.webm" type="video/webm"&gt;&lt;/video&gt;</msg>
            </kw>
        </test>
    </suite>
    <statistics>
        <total>
            <stat pass="1" fail="0" skip="0">All Tests</stat>
        </total>
    </statistics>
    """)
    
    additional_files, stats = parse_output_xml(mock_xml, "/test/dir")
    
    #assert additional_files == {"/test/dir/video/0-73a067fbe34b2b5cf7d977739ae2bf76.webm"}
    assert stats["verdict"] == "pass"
    assert stats["start_time"] == datetime.datetime(2024, 10, 11, 10, 34, 51, 295908)
    assert stats["end_time"] == datetime.datetime(2024, 10, 11, 10, 34, 51, 652133)

def test_parse_real_output_xml():
    output_xml_path = os.path.abspath(os.path.join("tests", "data", "output.xml"))
    base_directory = os.path.dirname(output_xml_path)
    
    additional_files, stats = parse_output_xml(output_xml_path, base_directory)
    
    assert stats["verdict"] == "pass"
    assert isinstance(stats["start_time"], datetime.datetime)
    assert isinstance(stats["end_time"], datetime.datetime)
    assert stats["start_time"] < stats["end_time"]
    
    # Check for screenshots using absolute paths
    expected_screenshots = [
        os.path.abspath(os.path.join(base_directory, "rflogs_selenium.png")),
        os.path.abspath(os.path.join(base_directory, "browser", "screenshot", "rflogs_browser.png"))
    ]
    
    for screenshot in expected_screenshots:
        assert screenshot in additional_files, f"Screenshot {screenshot} not found in additional files"
    
    # Check other stats
    assert stats["total_tests"] > 0
    assert stats["passed"] > 0
    assert stats["failed"] == 0
    assert stats["skipped"] == 0

    # Print additional debug information
    print("Base directory:", base_directory)
    print("Expected screenshots:", expected_screenshots)
    print("Additional files:", additional_files)