# Guardrails : {"sensitive": {"pii": [], "regex": []}, "topic": ["confidential Business information"], "content": [], "words": []}

import json
import boto3
import os
from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import workflow # For decorator usage, not required if decorators/manual instrumentation is not used
 
# Traceloop Environment Variables ##############################################
 
# Include Bedrock prompts as span attributes
os.environ["TRACELOOP_TRACE_CONTENT"] = "true"
# Enable metrics
os.environ["OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE"] = "Delta"
 
DT_ENDPOINT = os.getenv("DT_ENDPOINT")
DT_API_TOKEN = os.getenv("DT_API_TOKEN")
 
 
# Auto-instrument Traceloop into all Bedrock calls
if DT_ENDPOINT and DT_API_TOKEN:
    Traceloop.init(
        app_name="Bedrockapptester", # Service name as it will appear in Dynatrace
        api_endpoint=DT_ENDPOINT,
        headers={"Authorization": f"Api-Token {DT_API_TOKEN}"}  
    )
else:
    print("Warning: Dynatrace environment variables missing. Traceloop not initialized.")
 
 
# Initialize AWS Bedrock Client
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
bedrock = boto3.client(service_name="bedrock-runtime", region_name=AWS_REGION)
    
# Build json payload and invoke Bedrock model
# Includes Traceloop decorator (@workflow) to delinate functions as separate spans - for demo/testing purposes
#@workflow(name="invoke_model")
def invoke_model(prompt, model_id):
    # Prepare payload
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 200,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": prompt}],
    })
    
    # Invoke Bedrock model
    response = bedrock.invoke_model(
        modelId=model_id,
        body=body,
        trace="ENABLED", # Required for guardrail metric and span data
        guardrailIdentifier="q11ljlbw5lki",
        guardrailVersion="1",
        contentType="application/json",
        accept="application/json"
    )
        
    return response
 
# Lambda Handler (main entry point) with Traceloop decorator
# Decorators for demo/testing purposes
#@workflow(name="lambda_handler")
def lambda_handler(event, context):
    
    # Test prompt
    prompt = event.get("prompt", "Test - Topic - what are Q4 earnings before release")
 
    # Model ID
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
   
    # Build json package and invoke model
    response =invoke_model(prompt, model_id)
 
    # Process Response
    result = json.loads(response["body"].read())
    output_text = result.get("content", [{}])[0].get("text", "").strip()
    
 
    return {
        "statusCode": 200,
        "body": json.dumps({"response": output_text})
    }
 
