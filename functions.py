import csv
import boto3
import time


logs_client = boto3.client('logs')

def calculate_log_class_pricing(csv_filename):
    """
    Calculate the cost for each log group based on StandardLogClassPricing.
    
    Parameters:
    - csv_filename (str): The name of the CSV file to read and update.
    
    The function reads the CSV file, calculates the cost based on the IncomingBytes,
    and appends the cost to the CSV file.
    """
    time.sleep(3)

    updated_rows = []
    
    with open(csv_filename, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        print(reader)
        fieldnames = reader.fieldnames + ['StandardLogClassPricing'] + ['IALogClassPricing']+ ["Reduction%"]
        print(fieldnames)
        print(reader)
        
        for row in reader:
            incoming_bytes = float(row['Total IncomingBytes'])
            cost_standard = (incoming_bytes / (1024 ** 3)) * 0.50  # Convert bytes to GB and multiply by $0.50
            cost_IA = (incoming_bytes / (1024 ** 3)) * 0.25           
            if cost_standard != 0:
                percentage_reduction = ((cost_standard - cost_IA) / cost_standard) * 100
            else:
                percentage_reduction = 0  # Handle the case where cost_standard is zero
            
            row['StandardLogClassPricing'] = cost_standard
            row['IALogClassPricing'] = cost_IA
            row['Reduction%'] = percentage_reduction
            updated_rows.append(row)
    
    with open("cost_analysis.csv", 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
    
    print(f"Updated CSV with StandardLogClassPricing: cost_analysis.csv")

#Example usage
# calculate_log_class_pricing('log_group_metrics.csv')

# import boto3

# # Initialize the client for CloudWatch Logs
# logs_client = boto3.client('logs')

# def check_subscription_filters(log_groups):
#     if isinstance(log_groups, str):
#         log_groups = [log_groups]  # Convert single log group to list
    
#     log_group_subscription_filters = {log_group: False for log_group in log_groups}
    
#     for log_group in log_groups:
#         try:
#             response = logs_client.describe_subscription_filters(logGroupName=log_group)
#             if response['subscriptionFilters']:
#                 log_group_subscription_filters[log_group] = True
#                 print(response)
#                 print(log_group_subscription_filters)
#         except logs_client.exceptions.ResourceNotFoundException:
#             continue
    
#     return log_group_subscription_filters

# # Test the function with a specific log group
# test_log_group = "staging--ms-messaging"
# subscription_filters_output = check_subscription_filters(test_log_group)
# print(subscription_filters_output.get(test_log_group))