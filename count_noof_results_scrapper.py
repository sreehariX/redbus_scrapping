from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
import time
import re
import os
import csv

def safe_find_text(element, by, value, default=None):
    """Safely find a sub-element and return its text, or default if not found."""
    try:
        return element.find_element(by, value).text
    except NoSuchElementException:
        return default

def safe_find_attribute(element, by, value, attribute, default=None):
    """Safely find a sub-element and return its attribute, or default if not found."""
    try:
        found = element.find_element(by, value)
        # Special handling for location: prefer title, fallback to text
        if attribute == 'title' and (value == ".dp-loc" or value == ".bp-loc"):
             title_val = found.get_attribute(attribute)
             return title_val if title_val else found.text
        return found.get_attribute(attribute)
    except NoSuchElementException:
        return default

def safe_extract_prices(element, selector, data_attr="data-price", exclude_values=None):
    """
    Safely extract price values from elements using a data attribute.
    
    Args:
        element: Parent element to search within
        selector: CSS selector to find price elements
        data_attr: Name of the data attribute containing the price value (default: "data-price")
        exclude_values: List of values to exclude (e.g., ["ALL"])
        
    Returns:
        List of floats representing prices, or empty list if none found
    """
    if exclude_values is None:
        exclude_values = ["ALL"]
        
    price_values = []
    try:
        price_elements = element.find_elements(By.CSS_SELECTOR, selector)
        for price_el in price_elements:
            price_text = price_el.get_attribute(data_attr)
            if price_text and price_text not in exclude_values:
                try:
                    # Remove any non-numeric characters and convert to float
                    price_clean = re.sub(r'[^\d.]', '', price_text)
                    price_values.append(float(price_clean))
                except ValueError:
                    print(f"Warning: Could not parse price '{price_text}'")
    except Exception as e:
        print(f"Error extracting prices with selector '{selector}': {e}")
    
    return price_values

def setup_driver(headless=False):
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--start-maximized')
    
    # Add options to bypass anti-scraping measures
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Add more realistic user agent
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    if headless:
        options.add_argument('--headless=new')  # Using newer headless mode
        options.add_argument('--window-size=1920,1080')  # Set window size in headless mode
    
    driver = webdriver.Chrome(options=options)
    
    # Execute CDP commands to bypass detection
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Overwrite the 'plugins' property to use a custom getter
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Overwrite the 'languages' property to use a custom getter
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        '''
    })
    
    return driver

def count_buses(from_city, to_city, target_month_year, target_day, visible=False):
    """
    Search for buses between cities on a specific date and print the number of buses found.
    
    Args:
        from_city: Origin city
        to_city: Destination city
        target_month_year: Month and year (e.g., "Apr 2025")
        target_day: Day of month (e.g., "20")
        visible: Whether to run the browser in visible mode (default: False)
    """
    driver = setup_driver(headless=not visible)  # Enable visible mode if requested
    
    try:
        driver.get("https://www.redbus.in/")
        print(f"Searching for buses from {from_city} to {to_city} on {target_month_year} {target_day}...")
        
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "src"))
        )
        time.sleep(1)
        
        # Enter origin city
        from_input = driver.find_element(By.ID, "src")
        from_input.clear()
        from_input.send_keys(from_city)
        
        try:
            first_suggestion_from = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.sc-dnqmqq li:first-child"))
            )
            first_suggestion_from.click()
        except TimeoutException:
            print(f"Error: Suggestion dropdown for '{from_city}' did not appear or wasn't clickable.")
            raise

        time.sleep(0.5)

        # Enter destination city
        to_input = driver.find_element(By.ID, "dest")
        to_input.clear()
        to_input.send_keys(to_city)

        try:
            first_suggestion_to = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.sc-dnqmqq li:first-child"))
            )
            first_suggestion_to.click()
        except TimeoutException:
            print(f"Error: Suggestion dropdown for '{to_city}' field did not appear or wasn't clickable.")
            raise

        time.sleep(0.5)
        
        # Click on calendar field
        try:
            calendar_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onwardCal"))
            )
            driver.execute_script("arguments[0].click();", calendar_field)
        except (TimeoutException, ElementClickInterceptedException) as e:
            print(f"Error clicking calendar field: {e}")
            raise

        # Wait for calendar to appear
        try:
            calendar_container_xpath = "//div[contains(@class,'DatePicker__MainBlock') or contains(@class,'sc-jzJRlG')]"
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, calendar_container_xpath))
            )
        except TimeoutException:
            print("Error: Calendar container did not become visible.")
            raise

        # Navigate to target month/year
        max_attempts = 24
        attempts = 0
        while attempts < max_attempts:
            try:
                month_year_element_xpath = f"{calendar_container_xpath}//div[contains(@class,'DayNavigator__IconBlock')][position()=2]"
                current_month_year = WebDriverWait(driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, month_year_element_xpath))
                ).text

                if target_month_year in current_month_year:
                    break
                else:
                    next_button_xpath = f"{calendar_container_xpath}//div[contains(@class,'DayNavigator__IconBlock')][position()=3]"
                    next_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, next_button_xpath))
                    )
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(0.5)

            except (NoSuchElementException, TimeoutException) as e:
                time.sleep(1)

            attempts += 1
            if attempts == max_attempts:
                print(f"Error: Could not navigate to {target_month_year} within {max_attempts} attempts.")
                raise TimeoutException(f"Failed to find month {target_month_year}")

        # Select target day
        try:
            day_xpath = f"//div[contains(@class,'DayTiles__CalendarDaysBlock') and not(contains(@class,'DayTiles__CalendarDaysBlock--inactive'))][text()='{target_day}'] | //span[contains(@class,'DayTiles__CalendarDaysSpan') and not(contains(@class,'DayTiles__CalendarDaysSpan--inactive'))][text()='{target_day}']"

            day_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, day_xpath))
            )
            driver.execute_script("arguments[0].click();", day_element)
        except TimeoutException:
            try:
                simple_day_xpath = f"//div[text()='{target_day}'] | //span[text()='{target_day}']"
                day_elements = driver.find_elements(By.XPATH, simple_day_xpath)
                clicked = False
                for el in day_elements:
                    if el.is_displayed():
                        driver.execute_script("arguments[0].click();", el)
                        clicked = True
                        break
                if not clicked:
                    raise TimeoutException("Could not click on day")
            except Exception as fallback_e:
                print(f"Error selecting day: {fallback_e}")
                raise

        time.sleep(1)

        # Click search button
        try:
            search_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "search_button"))
            )
            driver.execute_script("arguments[0].click();", search_button)
        except (TimeoutException, ElementClickInterceptedException) as e:
            try:
                search_button_xpath = "//button[normalize-space()='SEARCH BUSES']"
                search_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, search_button_xpath))
                )
                driver.execute_script("arguments[0].click();", search_button)
            except Exception as fallback_e:
                print(f"Error clicking Search button: {fallback_e}")
                raise

        # Wait for search results to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//ul[contains(@class,'bus-items')] | //div[contains(@class,'result-section')] | //div[contains(@class,'travels')]"))
        )
        
        # Look for the bus count element
        try:
            # Try to find the bus count element with class 'busFound'
            bus_count_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".busFound"))
            )
            bus_count_text = bus_count_element.text.strip()
            
            # Extract number of buses using regex
            match = re.search(r'(\d+)\s*Buses', bus_count_text)
            if match:
                num_buses = match.group(1)
                    else:
                # If regex fails, try to extract only numbers
                num_buses = re.sub(r'[^\d]', '', bus_count_text)
                if not num_buses:
                    num_buses = "0"  # Default if extraction fails
            
            print(f"Route: {from_city} to {to_city} - {num_buses} buses found")
            
            # Return the count for potential logging
            return num_buses
            
        except (TimeoutException, NoSuchElementException):
            # If busFound element not found, look for "no buses found" message
                try:
                    no_buses_xpath = "//*[contains(text(),'Oops! No buses found')] | //*[contains(text(),'No buses found')]"
                driver.find_element(By.XPATH, no_buses_xpath)
                print(f"Route: {from_city} to {to_city} - 0 buses found")
                return "0"
                except NoSuchElementException:
                # If neither element is found, count the bus elements directly
                bus_elements = driver.find_elements(By.CSS_SELECTOR, "ul.bus-items li.row-sec")
                count = len(bus_elements)
                print(f"Route: {from_city} to {to_city} - {count} buses found (counted directly)")
                return str(count)

    except Exception as e:
        print(f"Error searching {from_city} to {to_city}: {e}")
        return "Error"

    finally:
            driver.quit()

def process_routes(routes_list, target_month_year, target_day, visible=False, output_file="route_counts.csv"):
    """
    Process multiple routes and save the counts to a CSV file.
    """
    print(f"Processing {len(routes_list)} routes for {target_month_year} {target_day}")
    print("-" * 60)
    
    # Check if output file exists and create it with headers if not
    file_exists = os.path.exists(output_file)
    
    with open(output_file, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["From City", "To City", "Date", "Buses Found"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        for from_city, to_city in routes_list:
            try:
                bus_count = count_buses(from_city, to_city, target_month_year, target_day, visible)
                
                # Write to CSV
                writer.writerow({
                    "From City": from_city,
                    "To City": to_city,
                    "Date": f"{target_month_year} {target_day}",
                    "Buses Found": bus_count
                })
                
                # Space between routes for better readability
                print("-" * 60)
            
        # Add a delay between routes to avoid overloading the server
                time.sleep(5)
                
            except Exception as e:
                print(f"Failed to process {from_city} to {to_city}: {e}")
                # Write error to CSV
                writer.writerow({
                    "From City": from_city,
                    "To City": to_city,
                    "Date": f"{target_month_year} {target_day}",
                    "Buses Found": "Error"
                })
                print("-" * 60)
        time.sleep(5)
    
    print(f"Completed processing all routes. Results saved to {output_file}")

if __name__ == "__main__":
    # Parse the route list
    routes_to_process = [
        # ("Delhi", "Manali"),
        # ("Delhi", "Rishikesh"),
        # ("Delhi", "Shimla"),
        # ("Delhi", "Nainital"),
        # ("Delhi", "Katra"),
        # ("Bangalore", "Goa"),
        # ("Bangalore", "Hyderabad"),
        # ("Bangalore", "Tirupathi"),
        # ("Bangalore", "Chennai"),
        # ("Bangalore", "Pondicherry"),
        # ("Hyderabad", "Bangalore"),
        # ("Hyderabad", "Goa"),
        # ("Hyderabad", "Srisailam"),
        # ("Hyderabad", "Vijayawada"),
        # ("Hyderabad", "Tirupathi"),
        # ("Pune", "Goa"),
        # ("Pune", "Mumbai"),
        # ("Pune", "Nagpur"),
        # ("Pune", "Kolhapur"),
        # ("Pune", "Nashik"),
        # ("Mumbai", "Goa"),
        # ("Mumbai", "Pune"),
        # ("Mumbai", "Shirdi"),
        # ("Mumbai", "Mahabaleshwar"),
        # ("Mumbai", "Kolhapur"),
        # ("Kolkata", "Digha"),
        # ("Kolkata", "Siliguri"),
        # ("Kolkata", "Puri"),
        # ("Kolkata", "Bakkhali"),
        # ("Kolkata", "Mandarmani"),
        # ("Chennai", "Bangalore"),
        # ("Chennai", "Pondicherry"),
        # ("Chennai", "Coimbatore"),
        # ("Chennai", "Madurai"),
        # ("Chennai", "Tirupathi"),
        # ("Chandigarh", "Manali"),
        # ("Chandigarh", "Shimla"),
        # ("Chandigarh", "Delhi"),
        # ("Chandigarh", "Dehradun"),
        # ("Chandigarh", "Amritsar"),
        # ("Coimbatore", "Chennai"),
        # ("Coimbatore", "Bangalore"),
        # ("Coimbatore", "Ooty"),
        # ("Coimbatore", "Tiruchendur"),
        # ("Coimbatore", "Madurai"),
        # ("Agra", "Bareilly"),
        # ("Hisar", "Chandigarh"),
        # ("Ayodhya", "Varanasi"),
        # ("Lucknow", "Ballia"),
        # ("Lucknow", "Moradabad"),
        # ("Rajkot", "Dwarka"),
        # ("Siliguri", "Gangtok"),
        # ("Ahmedabad", "Goa"),
        # ("Ahmedabad", "Kanpur"),
        # ("Akola", "Pune"),
        ("Delhi", "Dehradun"),
        ("Delhi", "Haridwar"),
        ("Dehradun", "Delhi"),
        ("Delhi", "Agra"),
        # ("Delhi", "Varanasi")
    ]
    
    # Set common date for all routes
    target_month_year = "Apr 2025"
    target_day = "20"
    
    # Parse command line arguments
    import sys
    
    visible_browser = "--visible" in sys.argv
    single_route = "--single" in sys.argv
    
    if single_route:
        # Process just a single route for testing
        print("Running in single route mode (for testing)")
        print(f"Browser mode: {'Visible' if visible_browser else 'Headless'}")
        input_from_city = "Mumbai"
        input_to_city = "Thane"
        count_buses(input_from_city, input_to_city, target_month_year, target_day, visible=visible_browser)
    else:
        # Process all routes
        process_routes(routes_to_process, target_month_year, target_day, visible=visible_browser)