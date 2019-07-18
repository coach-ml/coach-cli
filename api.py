import boto3
import os
import requests
from coach.coach import Coach


class CoachApi:
    def __init__(self, api, key, secret, id, bucket):
        self.api = api
        self.id = id
        self.bucket = bucket

        session = boto3.Session(
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            region_name='us-east-1'
        )
        self.s3 = session.resource('s3')

    def upload_directory(self, path):
        bucket = self.s3.Bucket(self.bucket)
        root = os.path.split(path)[1]
    
        for subdir, dirs, files in os.walk(path):
            for file in files:
                full_path = os.path.join(subdir, file)
                with open(full_path, 'rb') as data:
                    bucket.put_object(Key=f'data/{root}/' + full_path[len(path)+1:], Body=data)

    def list_objects(self):
        results = []
        response = self.s3.meta.client.list_objects_v2(
            Bucket=self.bucket,
            Delimiter='/',
            EncodingType='url',
            MaxKeys=100,
            Prefix='data/',
            FetchOwner=False
        )
        for prefix in response['CommonPrefixes']:
            name = prefix['Prefix'].lstrip('data').strip('/').strip('\\')
            results.append(name)
        
        return results

    def train(self, name, steps, module):
        url = 'https://9fqai4xymb.execute-api.us-east-1.amazonaws.com/latest/new-job'
        response = requests.get(url, params={ "steps": steps, "module": module }, headers={"X-Api-Key": self.api}).json()
        return response
        
    def status(self, name):
        url = 'https://9fqai4xymb.execute-api.us-east-1.amazonaws.com/latest/status'
        response = requests.get(url, headers={"X-Api-Key": self.api}).json()
        return response

    def download(self, name, path, version=0):
        coach = Coach().login(self.api)
        coach.cache_model(name, path, version)
