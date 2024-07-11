import boto3
import json
import csv
from datetime import datetime, timedelta, timezone
from functions import calculate_log_class_pricing
from botocore.exceptions import ClientError


# Initialize clients for CloudWatch Logs and CloudTrail
logs_client = boto3.client('logs')
cloudtrail_client = boto3.client('cloudtrail')
cloudwatch_client = boto3.client('cloudwatch')

def describe_log_groups():
    """
    Describe all log groups and return their names.
    
    Returns:
    - log_groups (list): A list of log group names.
    """
    log_groups = []
    response = logs_client.describe_log_groups()
    
    while 'nextToken' in response:
        for log_group in response['logGroups']:
            log_groups.append(log_group['logGroupName'])
        
        response = logs_client.describe_log_groups(nextToken=response['nextToken'])
    
    # Add the last batch of log groups
    for log_group in response['logGroups']:
        log_groups.append(log_group['logGroupName'])
    
    print(f"Found {len(log_groups)} log groups.")
    
    return log_groups

def check_get_log_events(log_groups, start_time, end_time):
    """
    Check CloudTrail for GetLogEvents and count the occurrences for each log group.
    
    Parameters:
    - log_groups (list): A list of log group names.
    - start_time (datetime): The start time for the event retrieval.
    - end_time (datetime): The end time for the event retrieval.
    
    Returns:
    - log_group_event_counts (dict): A dictionary with log group names as keys and GetLogEvents counts as values.
    """
    log_group_event_counts = {log_group: 0 for log_group in log_groups}
    print(log_group_event_counts)
    
    try:
        response = cloudtrail_client.lookup_events(
            LookupAttributes=[
                {
                    'AttributeKey': 'EventName',
                    'AttributeValue': 'GetLogEvents'
                },
            ],
            StartTime=start_time,
            EndTime=end_time,
            MaxResults=50  # Retrieve a maximum of 50 events per API call (pagination handled below)
        )
        
        # Process the events to count GetLogEvents per log group
        events = response['Events']
        while 'NextToken' in response:
            response = cloudtrail_client.lookup_events(
                LookupAttributes=[
                    {
                        'AttributeKey': 'EventName',
                        'AttributeValue': 'GetLogEvents'
                    },
                ],
                StartTime=start_time,
                EndTime=end_time,
                NextToken=response['NextToken'],
                MaxResults=50
            )
            events.extend(response['Events'])
        
        for event in events:
            try:
                cloud_trail_event = json.loads(event['CloudTrailEvent'])
                if 'requestParameters' in cloud_trail_event and 'logGroupName' in cloud_trail_event['requestParameters']:
                    log_group_name = cloud_trail_event['requestParameters']['logGroupName']
                    if log_group_name in log_group_event_counts:
                        log_group_event_counts[log_group_name] += 1  # Increment the count for the log group
                else:
                    print(f"Missing 'requestParameters' or 'logGroupName' in event: {event}")
            except KeyError as e:
                print(f"KeyError: {str(e)} in event: {event}")
            except json.JSONDecodeError as e:
                print(f"JSONDecodeError: {str(e)} in event: {event}")
    
    except Exception as e:
        print(f"Error checking GetLogEvents: {str(e)}")
    
    return log_group_event_counts

def get_incoming_bytes(log_group_name, start_time, end_time, period=86400):
    """
    Retrieve and sum the IncomingBytes for the specified CloudWatch log group.
    
    Parameters:
    - log_group_name (str): The name of the log group.
    - start_time (datetime): The start time for the metric retrieval.
    - end_time (datetime): The end time for the metric retrieval.
    - period (int): The granularity, in seconds, of the returned data points. Default is 86400 (1 day).
    
    Returns:
    - total_incoming_bytes (float): The total IncomingBytes for the specified period.
    """
    response = cloudwatch_client.get_metric_statistics(
        Namespace='AWS/Logs',
        MetricName='IncomingBytes',
        Dimensions=[
            {
                'Name': 'LogGroupName',
                'Value': log_group_name
            },
        ],
        StartTime=start_time,
        EndTime=end_time,
        Period=period,
        Statistics=['Sum']
    )

    total_incoming_bytes = sum([point['Sum'] for point in response['Datapoints'] if 'Sum' in point])
    return total_incoming_bytes

def check_filter_log_events(log_groups, start_time, end_time):
    log_group_filter_event_counts = {log_group: 0 for log_group in log_groups}
    
    try:
        response = cloudtrail_client.lookup_events(
            LookupAttributes=[
                {
                    'AttributeKey': 'EventName',
                    'AttributeValue': 'FilterLogEvents'
                },
            ],
            StartTime=start_time,
            EndTime=end_time,
            MaxResults=50
        )
        
        events = response['Events']
        while 'NextToken' in response:
            response = cloudtrail_client.lookup_events(
                LookupAttributes=[
                    {
                        'AttributeKey': 'EventName',
                        'AttributeValue': 'FilterLogEvents'
                    },
                ],
                StartTime=start_time,
                EndTime=end_time,
                NextToken=response['NextToken'],
                MaxResults=50
            )
            events.extend(response['Events'])
        
        for event in events:
            try:
                cloud_trail_event = json.loads(event['CloudTrailEvent'])
                if 'requestParameters' in cloud_trail_event and 'logGroupName' in cloud_trail_event['requestParameters']:
                    log_group_name = cloud_trail_event['requestParameters']['logGroupName']
                    if log_group_name in log_group_filter_event_counts:
                        log_group_filter_event_counts[log_group_name] += 1
                else:
                    print("Missing 'requestParameters' or 'logGroupName' in event.")
            except KeyError as e:
                print(f"KeyError: {str(e)} in event: {event}")
            except json.JSONDecodeError as e:
                print(f"JSONDecodeError: {str(e)} in event: {event}")
    
    except Exception as e:
        print(f"Error checking FilterLogEvents: {str(e)}")
    
    return log_group_filter_event_counts

def check_subscription_filters(log_groups):
    log_group_subscription_filters = {log_group: False for log_group in log_groups}
    
    for log_group in log_groups:
            try:
                response = logs_client.describe_subscription_filters(logGroupName=log_group)
                if response['subscriptionFilters']:
                    log_group_subscription_filters[log_group] = True
                    print(log_group_subscription_filters)
            except ClientError as e:
                print(e)
                continue
    
    return log_group_subscription_filters

def check_metric_filters(log_groups):
    log_group_metric_filters = {log_group: False for log_group in log_groups}
    for log_group in log_groups:
        try:
            response = logs_client.describe_metric_filters(logGroupName=log_group)
            if response['metricFilters']:
                log_group_metric_filters[log_group] = True
        except ClientError as e:
                print(e)           
                continue
        
    return log_group_metric_filters

def main():
    log_groups = describe_log_groups()    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=30)

    log_group_subscription_filters = check_subscription_filters(log_groups)
    log_group_event_counts = check_get_log_events(log_groups, start_time, end_time)
    log_group_filter_event_counts = check_filter_log_events(log_groups, start_time, end_time)
    log_group_metric_filters = check_metric_filters(log_groups)
    
    log_group_metrics = []
    for log_group_name in log_groups:
        total_incoming_bytes = get_incoming_bytes(log_group_name, start_time, end_time)
        log_group_metrics.append({
            'Log Group Name': log_group_name,
            'GetLogEvents Count': log_group_event_counts.get(log_group_name, 0),
            'FilterLogEvents Count': log_group_filter_event_counts.get(log_group_name, 0),
            'Has Subscription Filters': log_group_subscription_filters.get(log_group_name, False),
            'Has Metric Filters': log_group_metric_filters.get(log_group_name, False),
            'Total IncomingBytes': total_incoming_bytes
        })
    
    fieldnames = [
        'Log Group Name',
        'GetLogEvents Count',
        'FilterLogEvents Count',
        'Has Subscription Filters',
        'Has Metric Filters',
        'Total IncomingBytes'
    ]
    try:
        for metrics in log_group_metrics:
            print(f"Log Group: {metrics['Log Group Name']}, GetLogEvents Count: {metrics['GetLogEvents Count']}, Total IncomingBytes: {metrics['Total IncomingBytes']} bytes")
    except:
        print("Error printing log group metrics")
    # Save the results to a CSV file
    with open('log_group_metrics.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for metrics in log_group_metrics:
            writer.writerow(metrics)



# Run the main function
if __name__ == "__main__":
    main()
    calculate_log_class_pricing('log_group_metrics.csv')