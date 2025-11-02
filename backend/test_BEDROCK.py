import boto3

# Simple Bedrock test using OpenAI GPT
client = boto3.client('bedrock-runtime', region_name='us-east-2')

try:
    response = client.converse(
        modelId='openai.gpt-oss-120b-1:0',
        messages=[
            {
                "role": "user",
                "content": [{"text": "what is the purpose of life, one word"}]
            }
        ],
        inferenceConfig={
            "maxTokens": 512,
            "temperature": 0.4,
            "topP": 0.5
        }
    )
    
    print("✅ Bedrock working!")
    
    # Extract the text response (skip reasoning content)
    content = response['output']['message']['content']
    for item in content:
        if 'text' in item:
            print(f"Response: {item['text']}")
            break
    
except Exception as e:
    print(f"❌ Error: {e}")