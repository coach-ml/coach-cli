import boto3
import os
import requests
from datetime import datetime
from coach import CoachClient

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

        commonPrefixes = 'CommonPrefixes'

        if commonPrefixes in response:
            for prefix in response[commonPrefixes]:
                name = prefix['Prefix'].lstrip('data').strip('/').strip('\\')
                results.append(name)
            return results
        else:
            return []

    def rm(self, model):
        bucket = self.s3.Bucket(self.bucket)
        bucket.objects.filter(Prefix=f"data/{model}/").delete()

    def train(self, model, steps, module):
        try:
            url = 'https://9fqai4xymb.execute-api.us-east-1.amazonaws.com/latest/new-job'
            response = requests.get(url, params={ "name": model, "steps": steps, "module": module }, headers={"X-Api-Key": self.api})
            response.raise_for_status()
        except Exception:
            raise ValueError("Failed to start training session, check your API key")

        return response.json()
        
    def status(self, name=None):
        try:
            url = 'https://9fqai4xymb.execute-api.us-east-1.amazonaws.com/latest/status'
            response = requests.get(url, headers={"X-Api-Key": self.api})
            response.raise_for_status()
        except Exception:
            raise ValueError("Failed to check status, check your API key")
        
        def pretty_print(status, name):
            if not name in status:
                raise ValueError(f'No model named {name} exists')
            
            status = status[name]['currentStatus']
            status_message = status['Status']
            
            if 'EndTime' in status:
                time = status['EndTime']
            else:
                time = status['StartTime']
            time = datetime.fromtimestamp(time / 1000).replace(microsecond=0)
            return "{:<12}{:<5}{:<12}{:<5}{}".format(name, '|', status_message, '|', str(time))

        status = response.json()

        if name:
            return pretty_print(status, name)
        else:
            result = ''
            keys = status.keys()
            for i, model in enumerate(keys, start=1):
                result += pretty_print(status, model)
                if i < len(keys):
                    result += '\n'
            return result


    def cache(self, model, path):
        coach = CoachClient().login(self.api)
        coach.cache_model(model, path)

    def predict(self, image, path):
        coach = CoachClient()
        model = coach.get_model(path)
        return model.predict(image)