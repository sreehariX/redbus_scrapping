import os
import pandas as pd

# Specify the output file here
output_file = 'merged_output_v2_test.csv'

# Specify the input CSV files to merge (in the order they should be merged)
input_files = [
    'bus_data.csv',
    'Hyderabad_to_Vijayawada.csv',
    'Hyderabad_to_Tirupathi.csv',
    'Pune_to_Goa.csv',
    'Pune_to_Mumbai.csv',
    'Pune_to_Nagpur.csv',
    'Pune_to_Kolhapur.csv',
    'Pune_to_Nashik.csv',
    'Mumbai_to_Goa.csv',
    'Mumbai_to_Pune.csv',
    'Mumbai_to_Shirdi.csv',
    'Mumbai_to_Mahabaleshwar.csv',
    'Mumbai_to_Kolhapur.csv',
    'Kolkata_to_Digha.csv',
    'Kolkata_to_Siliguri.csv',
    'Kolkata_to_Puri.csv',
    'Kolkata_to_Bakkhali.csv',
    'Kolkata_to_Mandarmani.csv',
    'Chennai_to_Bangalore.csv',
    'Chennai_to_Pondicherry.csv',
    'Chennai_to_Coimbatore.csv',
    'Chennai_to_Madurai.csv',
    'Chennai_to_Tirupathi.csv',
    'Chandigarh_to_Manali.csv',
    'Chandigarh_to_Shimla.csv',
    'Chandigarh_to_Delhi.csv',
    'Chandigarh_to_Dehradun.csv',
    'Chandigarh_to_Amritsar.csv',
    'Coimbatore_to_Chennai.csv',
    'Coimbatore_to_Bangalore.csv',
    'Coimbatore_to_Ooty.csv',
    'Coimbatore_to_Tiruchendur.csv',
    'Coimbatore_to_Madurai.csv',
    'Agra_to_Bareilly.csv',
    'Hisar_to_Chandigarh.csv',
    'Ayodhya_to_Varanasi.csv',
    'Lucknow_to_Ballia.csv',
    'Lucknow_to_Moradabad.csv',
    'Rajkot_to_Dwarka.csv',
    'Siliguri_to_Gangtok.csv',
    'Ahmedabad_to_Goa.csv',
    'Ahmedabad_to_Kanpur.csv',
    'Akola_to_Pune.csv',
    'Delhi_to_Dehradun.csv',
    'Delhi_to_Haridwar.csv',
    'Dehradun_to_Delhi.csv',
    'Delhi_to_Agra.csv',
    'Delhi_to_Varanasi.csv'
    # Add more files here as needed
]

# Check for files in the current directory
current_dir_files = os.listdir('.')
csv_files_in_dir = [f for f in current_dir_files if f.endswith('.csv')]

print(f"CSV files found in current directory: {', '.join(csv_files_in_dir)}")

# Check if all files exist
missing_files = [f for f in input_files if not os.path.exists(f)]
if missing_files:
    print(f"Warning: The following files could not be found and will be skipped: {', '.join(missing_files)}")
    # Filter out missing files from the input list
    input_files = [f for f in input_files if os.path.exists(f)]
    print(f"Continuing with {len(input_files)} available files")

try:
    # Initialize an empty DataFrame to store the merged data
    merged_df = pd.DataFrame()
    
    # Process each file in the provided order
    for file in input_files:
        print(f"Processing: {file}")
        # Read the current CSV file
        df = pd.read_csv(file)
        # Append the data to the merged DataFrame
        merged_df = pd.concat([merged_df, df], ignore_index=True)
    
    # Save the merged data to the output file
    merged_df.to_csv(output_file, index=False)
    print(f"Successfully merged {len(input_files)} files into {output_file}")
    print(f"Total rows in merged file: {len(merged_df)}")
    print("Merge completed successfully!")

except Exception as e:
    print(f"Error merging files: {e}")
    print("Merge failed.")
    exit(1)
