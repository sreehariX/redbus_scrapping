import os
import pandas as pd
import sys

def update_bus_ids(csv_file, output_file=None):
    """
    Read a CSV file, update the Bus ID field with sequential numbers from 1,
    and save to a new or the same file.
    
    Args:
        csv_file (str): Path to the input CSV file
        output_file (str, optional): Path to save the modified CSV. If None, overwrites the input file.
    """
    # Check if the file exists
    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found.")
        return False
    
    try:
        # Read the CSV file
        print(f"Reading file: {csv_file}")
        df = pd.read_csv(csv_file)
        
        # Check if 'Bus ID' column exists (case insensitive)
        bus_id_col = None
        for col in df.columns:
            if col.lower() == 'bus id':
                bus_id_col = col
                break
                
        if bus_id_col is None:
            print("Error: Could not find 'Bus ID' column in the CSV file.")
            print(f"Available columns: {', '.join(df.columns)}")
            return False
            
        # Generate sequential IDs from 1 to number of rows
        print(f"Updating {bus_id_col} column with sequential numbers 1 to {len(df)}")
        df[bus_id_col] = range(1, len(df) + 1)
        
        # Save the updated DataFrame
        if output_file is None:
            output_file = csv_file
            
        df.to_csv(output_file, index=False)
        print(f"Successfully updated Bus IDs in '{output_file}'")
        return True
        
    except Exception as e:
        print(f"Error processing file: {e}")
        return False

if __name__ == "__main__":
    # If run from command line
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        update_bus_ids(input_file, output_file)
    else:
        # Interactive mode
        input_file = input("Enter the path to the CSV file: ")
        
        if not os.path.exists(input_file):
            print(f"Error: File '{input_file}' not found.")
            sys.exit(1)
            
        save_option = input("Save as a new file? (y/n): ").lower()
        
        if save_option == 'y':
            output_file = input("Enter the path for the output file: ")
        else:
            output_file = None
            
        if update_bus_ids(input_file, output_file):
            print("Operation completed successfully.")
        else:
            print("Operation failed.")
