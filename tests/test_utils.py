"""
Utility functions for tests.
Centralizes common test setup and helper functions.
"""
import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

def setup_test_environment():
    """Setup the test environment with correct Python path and environment variables."""
    # Load environment variables
    load_dotenv()
    
    # Add src directory to Python path
    src_path = str(Path(__file__).parent.parent / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    # Verify API key is available
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY environment variable not set")

def get_results_dir(test_type: str) -> Path:
    """Get the results directory for a specific test type."""
    test_dir = Path(__file__).parent
    results_dir = test_dir / "results" / test_type
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir

def get_log_file(test_name: str) -> Path:
    """Get log file path for a test."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logs_dir = get_results_dir("logs")
    return logs_dir / f"{test_name}_{timestamp}.log"

def save_test_response(test_type: str, test_number: int, test_name: str, content: str) -> Path:
    """Save test response to organized file structure."""
    results_dir = get_results_dir(test_type)
    filename = f"test_response_{test_number:02d}_{test_name.replace(' ', '_').lower()}.txt"
    file_path = results_dir / filename
    
    with open(file_path, "w") as f:
        f.write(content)
    
    return file_path

def print_test_header(test_name: str, description: str = ""):
    """Print standardized test header."""
    print(f"🚀 {test_name}")
    if description:
        print(f"📝 {description}")
    print("=" * max(len(test_name), len(description), 50))

def print_test_result(success: bool, message: str = ""):
    """Print standardized test result."""
    if success:
        print(f"✅ SUCCESS" + (f": {message}" if message else ""))
    else:
        print(f"❌ FAILED" + (f": {message}" if message else ""))