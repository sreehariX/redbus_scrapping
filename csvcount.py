import csv
import sys
import os

def count_route_rows(csv_file_path, start_point, dest_point):
    """
    Count rows in a CSV file based on specific source and destination.
    
    Args:
        csv_file_path: Path to the CSV file
        start_point: Starting Point Parent to filter by
        dest_point: Destination Point Parent to filter by
    
    Returns:
        int: Number of rows matching the criteria
    """
    try:
        count = 0
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            # Skip header
            header = next(reader, None)
            if not header:
                print(f"Warning: CSV file {csv_file_path} appears to be empty.")
                return 0
                
            # Check if file has the expected columns
            try:
                start_index = header.index("Starting Point Parent")
                dest_index = header.index("Destination Point Parent")
            except ValueError:
                print("Error: CSV file does not have the expected columns.")
                print(f"Expected columns: 'Starting Point Parent' and 'Destination Point Parent'")
                print(f"Found columns: {header}")
                return 0
                
            # Count matching rows
            for row in reader:
                if len(row) > max(start_index, dest_index):
                    if row[start_index] == start_point and row[dest_index] == dest_point:
                        count += 1
                        
        return count
    except FileNotFoundError:
        print(f"Error: File '{csv_file_path}' not found.")
        return 0
    except Exception as e:
        print(f"Error counting rows: {e}")
        return 0

def get_buses_for_route(csv_file_path, start_point, dest_point):
    """
    Get all buses for a specific route.
    
    Args:
        csv_file_path: Path to the CSV file
        start_point: Starting Point Parent to filter by
        dest_point: Destination Point Parent to filter by
        
    Returns:
        list: List of dictionaries with bus details
    """
    buses = []
    try:
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None)
            if not header:
                return buses
                
            # Find required column indices
            column_indices = {}
            required_columns = ["Bus ID", "Bus Name", "Bus Type", "Lowest Price(INR)", "Highest Price(INR)", 
                               "Starting Point Parent", "Destination Point Parent"]
            
            for col in required_columns:
                try:
                    column_indices[col] = header.index(col)
                except ValueError:
                    print(f"Warning: Column '{col}' not found in CSV file.")
                    column_indices[col] = -1
            
            # Process rows matching the route
            for row in reader:
                if len(row) > max(column_indices.values()):
                    start_idx = column_indices["Starting Point Parent"]
                    dest_idx = column_indices["Destination Point Parent"]
                    
                    if row[start_idx] == start_point and row[dest_idx] == dest_point:
                        bus_data = {}
                        for col, idx in column_indices.items():
                            if idx >= 0:
                                bus_data[col] = row[idx]
                        buses.append(bus_data)
        
        return buses
    except FileNotFoundError:
        print(f"Error: File '{csv_file_path}' not found.")
        return buses
    except Exception as e:
        print(f"Error retrieving buses: {e}")
        return buses

def display_route_details(csv_file_path, start_point, dest_point):
    """Display detailed information for all buses on a specific route."""
    buses = get_buses_for_route(csv_file_path, start_point, dest_point)
    
    if not buses:
        print(f"No buses found for route: {start_point} to {dest_point}")
        return
    
    print(f"\nDetailed information for route: {start_point} to {dest_point}")
    print("-" * 100)
    print(f"{'Bus ID':<8} {'Bus Name':<30} {'Bus Type':<25} {'Lowest Price':<15} {'Highest Price':<15}")
    print("-" * 100)
    
    for bus in buses:
        bus_id = bus.get("Bus ID", "N/A")
        bus_name = bus.get("Bus Name", "N/A")
        bus_type = bus.get("Bus Type", "N/A")
        lowest_price = bus.get("Lowest Price(INR)", "N/A")
        highest_price = bus.get("Highest Price(INR)", "N/A")
        
        print(f"{bus_id:<8} {bus_name:<30} {bus_type:<25} {lowest_price:<15} {highest_price:<15}")
    
    print("-" * 100)
    print(f"Total buses: {len(buses)}")

def get_all_routes(csv_file_path):
    """
    Get all unique routes from the CSV file.
    
    Args:
        csv_file_path: Path to the CSV file
    
    Returns:
        set: Set of tuples containing (starting_point, destination_point)
    """
    routes = set()
    try:
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None)
            if not header:
                return routes
                
            try:
                start_index = header.index("Starting Point Parent")
                dest_index = header.index("Destination Point Parent")
            except ValueError:
                return routes
                
            for row in reader:
                if len(row) > max(start_index, dest_index):
                    routes.add((row[start_index], row[dest_index]))
        
        return routes
    except Exception:
        return routes

def show_available_routes(csv_file_path):
    """Show unique routes available in the CSV file."""
    routes = get_all_routes(csv_file_path)
    
    if routes:
        print("\nAvailable routes:")
        for idx, (start, dest) in enumerate(sorted(routes), 1):
            print(f"{idx}. {start} to {dest}")
    else:
        print("No route data found in the CSV file.")
    
    return sorted(routes)

def show_route_statistics(csv_file_path):
    """Show statistics about all routes in the CSV file."""
    try:
        routes = get_all_routes(csv_file_path)
        if not routes:
            print("No route data found in the CSV file.")
            return
            
        print("\nRoute Statistics:")
        print("-" * 60)
        print(f"{'Route':<30} {'Bus Count':<10} {'Percentage':<10}")
        print("-" * 60)
        
        route_counts = {}
        total_buses = 0
        
        # Count buses for each route
        for start, dest in routes:
            count = count_route_rows(csv_file_path, start, dest)
            route_counts[(start, dest)] = count
            total_buses += count
            
        # Display statistics sorted by count (descending)
        for (start, dest), count in sorted(route_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_buses) * 100 if total_buses > 0 else 0
            route_str = f"{start} to {dest}"
            print(f"{route_str:<30} {count:<10} {percentage:.2f}%")
            
        print("-" * 60)
        print(f"Total Routes: {len(routes)}")
        print(f"Total Buses: {total_buses}")
        
    except Exception as e:
        print(f"Error retrieving route statistics: {e}")

def process_specific_routes(csv_file_path):
    """Process the specific list of routes from the assignment."""
    routes_to_process = [
        ("Delhi", "Manali"),
        ("Delhi", "Rishikesh"),
        ("Delhi", "Shimla"),
        ("Delhi", "Nainital"),
        ("Delhi", "Katra"),
        ("Bangalore", "Goa"),
        ("Bangalore", "Hyderabad"),
        ("Bangalore", "Tirupathi"),
        ("Bangalore", "Chennai"),
        ("Bangalore", "Pondicherry"),
        ("Hyderabad", "Bangalore"),
        ("Hyderabad", "Goa"),
        ("Hyderabad", "Srisailam"),
        ("Hyderabad", "Vijayawada"),
        ("Hyderabad", "Tirupathi"),
        ("Pune", "Goa"),
        ("Pune", "Mumbai"),
        ("Pune", "Nagpur"),
        ("Pune", "Kolhapur"),
        ("Pune", "Nashik"),
        ("Mumbai", "Goa"),
        ("Mumbai", "Pune"),
        ("Mumbai", "Shirdi"), 
        ("Mumbai", "Mahabaleshwar"), 
        ("Mumbai", "Kolhapur"), 
        ("Kolkata", "Digha"), 
        ("Kolkata", "Siliguri"), 
        ("Kolkata", "Puri"), 
        ("Kolkata", "Bakkhali"), 
        ("Kolkata", "Mandarmani"), 
        ("Chennai", "Bangalore"), 
        ("Chennai", "Pondicherry"),
        ("Chennai", "Coimbatore"), 
        ("Chennai", "Madurai"), 
        ("Chennai", "Tirupathi"),
        ("Chandigarh", "Manali"),
        ("Chandigarh", "Shimla"),
        ("Chandigarh", "Delhi"),
        ("Chandigarh", "Dehradun"),
        ("Chandigarh", "Amritsar"),
        ("Coimbatore", "Chennai"),
        ("Coimbatore", "Bangalore"),
        ("Coimbatore", "Ooty"),
        ("Coimbatore", "Tiruchendur"),
        ("Coimbatore", "Madurai"),
        ("Agra", "Bareilly"),
        ("Hisar", "Chandigarh"),
        ("Ayodhya", "Varanasi"),
        ("Lucknow", "Ballia"),
        ("Lucknow", "Moradabad"),
        ("Rajkot", "Dwarka"),
        ("Siliguri", "Gangtok"),
        ("Ahmedabad", "Goa"),
        ("Ahmedabad", "Kanpur"),
        ("Akola", "Pune"),
        ("Delhi", "Dehradun"),
        ("Delhi", "Haridwar"),
        ("Dehradun", "Delhi"),
        ("Delhi", "Agra"),
        ("Delhi", "Varanasi")

    ]
    
    print("\n" + "=" * 60)
    print("COUNT REPORT FOR SPECIFIED ROUTES")
    print("=" * 60)
    
    total_routes = len(routes_to_process)
    routes_with_buses = 0
    total_buses = 0
    
    for i, (start, dest) in enumerate(routes_to_process, 1):
        count = count_route_rows(csv_file_path, start, dest)
        print(f"{i:2d}. {start:<15} to {dest:<15} : {count:4d} buses")
        
        if count > 0:
            routes_with_buses += 1
            total_buses += count
    
    print("=" * 60)
    print(f"Total routes checked: {total_routes}")
    print(f"Routes with buses: {routes_with_buses}")
    print(f"Total buses: {total_buses}")
    print("=" * 60)

def interactive_mode(csv_file_path):
    """Interactive mode for when no command-line arguments are provided."""
    if not os.path.exists(csv_file_path):
        print(f"Error: File '{csv_file_path}' not found.")
        return
        
    while True:
        print("\n" + "=" * 50)
        print("Bus Data CSV Counter - Interactive Mode")
        print("=" * 50)
        print("1. Count buses for a specific route")
        print("2. Show all available routes")
        print("3. Show route statistics")
        print("4. Select route from list")
        print("5. Show detailed bus information for a route")
        print("6. Process predefined route list")
        print("7. Exit")
        
        choice = input("\nEnter your choice (1-7): ")
        
        if choice == '1':
            start_point = input("Enter starting point: ")
            dest_point = input("Enter destination point: ")
            
            count = count_route_rows(csv_file_path, start_point, dest_point)
            
            print(f"\nRoute: {start_point} to {dest_point}")
            print(f"Number of buses: {count}")
            
        elif choice == '2':
            show_available_routes(csv_file_path)
            
        elif choice == '3':
            show_route_statistics(csv_file_path)
            
        elif choice == '4':
            # Let user select a route from a numbered list
            routes = sorted(get_all_routes(csv_file_path))
            if not routes:
                print("No route data found in the CSV file.")
                continue
                
            print("\nAvailable routes:")
            for idx, (start, dest) in enumerate(routes, 1):
                print(f"{idx}. {start} to {dest}")
                
            try:
                route_idx = int(input("\nEnter route number to count buses: "))
                if 1 <= route_idx <= len(routes):
                    selected_route = routes[route_idx - 1]
                    start_point, dest_point = selected_route
                    
                    count = count_route_rows(csv_file_path, start_point, dest_point)
                    
                    print(f"\nRoute: {start_point} to {dest_point}")
                    print(f"Number of buses: {count}")
                else:
                    print("Invalid route number.")
            except ValueError:
                print("Please enter a valid number.")
        
        elif choice == '5':
            # Show detailed bus information for a route
            routes = sorted(get_all_routes(csv_file_path))
            if not routes:
                print("No route data found in the CSV file.")
                continue
                
            print("\nSelect a route to view detailed bus information:")
            for idx, (start, dest) in enumerate(routes, 1):
                print(f"{idx}. {start} to {dest}")
                
            try:
                route_idx = int(input("\nEnter route number: "))
                if 1 <= route_idx <= len(routes):
                    selected_route = routes[route_idx - 1]
                    start_point, dest_point = selected_route
                    
                    display_route_details(csv_file_path, start_point, dest_point)
                else:
                    print("Invalid route number.")
            except ValueError:
                print("Please enter a valid number.")
                
        elif choice == '6':
            # Process the predefined route list
            process_specific_routes(csv_file_path)
            
        elif choice == '7':
            print("Exiting program.")
            break
            
        else:
            print("Invalid choice. Please enter a number between 1 and 7.")
        
        input("\nPress Enter to continue...")

def main():
    csv_file_path = 'merged_output_v2_test.csv'
    
    # Check if custom CSV file path is provided
    for arg in sys.argv:
        if arg.endswith('.csv'):
            csv_file_path = arg
            break
    
    # Check for specific flag to directly process the predefined routes
    if any(arg.lower() in ('--routes', '-r', '--process-routes') for arg in sys.argv):
        process_specific_routes(csv_file_path)
        return
    
    # If no command-line arguments or only CSV file specified, enter interactive mode
    if len(sys.argv) <= 2:
        interactive_mode(csv_file_path)
        return
    
    # Command-line mode
    start_point = sys.argv[1]
    dest_point = sys.argv[2]
    
    # Check for detail flag
    show_details = False
    for arg in sys.argv:
        if arg.lower() in ('-d', '--details', '--detail'):
            show_details = True
            break
    
    # Display detailed info if requested, otherwise just count
    if show_details:
        display_route_details(csv_file_path, start_point, dest_point)
    else:
        count = count_route_rows(csv_file_path, start_point, dest_point)
        
        print(f"Route: {start_point} to {dest_point}")
        print(f"Number of buses: {count}")
        
        # If count is zero, offer to show available routes
        if count == 0:
            try_show_routes = input("No buses found for this route. Would you like to see available routes? (y/n): ")
            if try_show_routes.lower() in ('y', 'yes'):
                show_available_routes(csv_file_path)

if __name__ == "__main__":
    # If run directly without arguments, process the specified routes
    if len(sys.argv) == 1:
        process_specific_routes('merged_output_v2_test.csv')
    else:
        main()
