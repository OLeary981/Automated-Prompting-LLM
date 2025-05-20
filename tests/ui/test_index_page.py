import time

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


@pytest.fixture(scope="module")
def driver():
    """Set up the WebDriver for testing."""
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    # Run in headless mode (no visible browser)
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=service, options=options)
    yield driver
    driver.quit()

@pytest.fixture(scope="module")
def app_running():
    """Ensure the Flask app is running for the tests."""
    # You can skip this if you're already running the app separately
    import subprocess
    import time
    
    # Start the Flask app on port 5000
    process = subprocess.Popen(["flask", "run"])
    time.sleep(2)  # Give the app time to start
    
    yield
    
    # Shut down the Flask app
    process.terminate()
    process.wait()

def test_home_page_links(driver, app_running):
    """Test that all links on the home page lead to working pages."""
    # Navigate to the home page
    driver.get("http://localhost:5000/")
    
    # Get all links from the home page
    links = driver.find_elements(By.TAG_NAME, "a")
    
    # Store original window handle
    original_window = driver.current_window_handle
    
    # Create a list to store any failed links
    failed_links = []
    
    # Click each link and verify the page loads
    for link in links:
        # Skip external links or JavaScript actions
        href = link.get_attribute("href")
        if not href or "javascript:" in href or "mailto:" in href or "#" in href:
            continue
            
        # Get the link text for better error reporting
        link_text = link.text.strip() or href
        
        try:
            # Click the link (in a new tab to preserve our place)
            driver.execute_script('window.open(arguments[0]);', href)
            
            # Switch to the new tab
            new_window = [window for window in driver.window_handles if window != original_window][0]
            driver.switch_to.window(new_window)
            
            # Wait for the page to load (up to 10 seconds)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check for specific error indicators that would mean the page is broken
            # Only look for error status codes in headings or error messages
            serious_errors = driver.find_elements(By.XPATH, 
                "//h1[contains(text(), 'Error') or contains(text(), '404') or contains(text(), '500')] | " + 
                "//div[contains(@class, 'alert-danger')]")
                
            if serious_errors:
                failed_links.append(f"Link '{link_text}' loaded with errors: {[e.text for e in serious_errors]}")
            
            # Check for modal and dismiss it if present
            try:
                modal = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.ID, "sessionPreservationModal"))
                )
                # If modal is visible, click the close button
                if modal.is_displayed():
                    close_button = modal.find_element(By.XPATH, ".//button[contains(@class, 'close') or contains(@class, 'btn-close')]")
                    close_button.click()
            except:
                # No modal found or not visible, continue
                pass
            
            # Close the tab and switch back to the original
            driver.close()
            driver.switch_to.window(original_window)
            
        except Exception as e:
            # If any exception occurred, log it
            failed_links.append(f"Link '{link_text}' failed: {str(e)}")
            
            # Make sure we get back to the original window
            if len(driver.window_handles) > 1:
                driver.close()
            driver.switch_to.window(original_window)
    
    # Assert that no links failed
    assert not failed_links, f"The following links failed: {failed_links}"

def test_specific_section_navigation(driver, app_running):
    """Test specific navigation paths through important sections."""
    # Start at the home page
    driver.get("http://localhost:5000/")
    
    # Test Story workflow
    story_section = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'card-header') and contains(text(), 'Work with Stories')]"))
    )
    story_section.find_element(By.XPATH, "..//a[contains(text(), 'See All Stories')]").click()
    
    # Check that we're on the stories list page
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'All Stories')]"))
    )
    
    # Go back to home
    driver.get("http://localhost:5000/")
    
    # Test Models workflow
    models_section = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'card-header') and contains(text(), 'Manage LLM Models')]"))
    )
    models_section.find_element(By.XPATH, "..//a[contains(text(), 'View All Models')]").click()
    
    # Check that we're on the models list page
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Models')]"))
    )
    
    # Go back to home
    driver.get("http://localhost:5000/")
    
    # Test Questions workflow
    questions_section = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'card-header') and contains(text(), 'Work with Questions')]"))
    )
    questions_section.find_element(By.XPATH, "..//a[contains(text(), 'Questions')]").click()
    
    # Check that we're on the questions page
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Questions')]"))
    )