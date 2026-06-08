import boto3
import random
import string
import json
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('url-shortener')
counter_table = dynamodb.Table('url-counter')


def to_base62(num):
    chars = string.digits + string.ascii_letters
    result = ''
    while num > 0:
        result = chars[num % 62] + result
        num //= 62
    return result.zfill(6)


def generate_short_code():
    response = counter_table.update_item(
        Key={'id': 'global_counter'},
        UpdateExpression='SET #cnt = if_not_exists(#cnt, :zero) + :val',
        ExpressionAttributeNames={'#cnt': 'count'},
        ExpressionAttributeValues={':val': 1, ':zero': 0},
        ReturnValues='UPDATED_NEW'
    )
    count = int(response['Attributes']['count'])
    return to_base62(count)


def is_expired(item):
    last_clicked = item.get('lastClickedAt', item.get('createdAt', ''))
    if not last_clicked:
        return False
    last_date = datetime.fromisoformat(last_clicked)
    return last_date < datetime.now() - timedelta(days=180)


def expiry_response(website_url):
    return {
        'statusCode': 410,
        'headers': {
            'Content-Type': 'text/html',
            'Access-Control-Allow-Origin': '*'
        },
        'body': f'''
        <html>
        <head><title>URL Expired</title></head>
        <body style="font-family:Arial;text-align:center;padding:60px;background:#080810;color:#e8e8f8;">
            <h1 style="font-size:3rem;">⏰</h1>
            <h2>URL Expired</h2>
            <p>This short URL was not used for 6 months and has expired.</p>
            <a href="{website_url}" 
               style="display:inline-block;margin-top:20px;padding:12px 24px;
                      background:#3d5afe;color:white;border-radius:8px;text-decoration:none;">
                Create a new short URL
            </a>
        </body>
        </html>
        '''
    }


def response(status, body=None, extra_headers=None):
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
    }
    if extra_headers:
        headers.update(extra_headers)
    return {
        'statusCode': status,
        'headers': headers,
        'body': json.dumps(body) if body else ''
    }


def shorten_url(event):
    try:
        body = json.loads(event.get('body', '{}'))
        long_url = body.get('url', '').strip()

        if not long_url:
            return response(400, {'error': 'URL is required.'})
        if not long_url.startswith(('http://', 'https://')):
            return response(400, {'error': 'URL must start with http:// or https://'})

        short_code = generate_short_code()
        now = datetime.now().isoformat()

        table.put_item(Item={
            'shortCode': short_code,
            'longURL': long_url,
            'createdAt': now,
            'lastClickedAt': now,
            'clickCount': 0
        })

        api_base = "https://YOUR_API_GATEWAY_URL/prod"
        return response(200, {
            'shortURL': f"{api_base}/{short_code}",
            'shortCode': short_code,
            'longURL': long_url,
            'message': 'URL shortened successfully!'
        })

    except json.JSONDecodeError:
        return response(400, {'error': 'Invalid JSON in request body.'})
    except Exception as e:
        print(f"ERROR in shorten_url: {e}")
        return response(500, {'error': 'Something went wrong. Try again.'})


def redirect_url(event):
    try:
        path_params = event.get('pathParameters') or {}
        short_code = path_params.get('shortCode', '').strip()

        if not short_code:
            return response(400, {'error': 'Short code missing.'})

        db_response = table.get_item(Key={'shortCode': short_code})
        if 'Item' not in db_response:
            return response(404, {'error': f'/{short_code} not found.'})

        item = db_response['Item']
        website_url = "https://url-shortener-frontend-sumit.s3-website-ap-southeast-1.amazonaws.com"

        if is_expired(item):
            return expiry_response(website_url)

        long_url = item['longURL']

        try:
            table.update_item(
                Key={'shortCode': short_code},
                UpdateExpression='SET clickCount = clickCount + :val, lastClickedAt = :now',
                ExpressionAttributeValues={
                    ':val': 1,
                    ':now': datetime.now().isoformat()
                }
            )
        except Exception as e:
            print(f"WARNING: Could not update click count: {e}")

        return {
            'statusCode': 301,
            'headers': {
                'Location': long_url,
                'Access-Control-Allow-Origin': '*'
            },
            'body': ''
        }

    except Exception as e:
        print(f"ERROR in redirect_url: {e}")
        return response(500, {'error': 'Something went wrong. Try again.'})


def lambda_handler(event, context):
    print(f"Event: {json.dumps(event)}")
    http_method = event.get('requestContext', {}).get('http', {}).get('method', '')
    route_key = event.get('routeKey', '')

    if http_method == 'OPTIONS':
        return response(200)
    elif route_key == 'POST /shorten':
        return shorten_url(event)
    elif route_key == 'GET /{shortCode}':
        return redirect_url(event)
    else:
        return response(404, {'error': f'Route not found: {route_key}'})