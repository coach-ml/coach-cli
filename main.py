import click
import json
from pathlib import Path
import os
import requests

from datetime import datetime
import boto3

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

    def list_objects(self, key):
        pass

    def object_exists(self, key):
        bucket = self.s3.Bucket(self.bucket)
        objs = list(bucket.objects.filter(Prefix=key))
        if len(objs) > 0 and objs[0].key == key:
            return True
        else:
            return False

    def __get_categories(self, model):
        key = f'data/{model}/'
        client = self.s3.meta.client
        result = client.list_objects_v2(Bucket=bucket_name, Prefix=key, Delimiter='/')
        return [os.path.split(o.get('Prefix').rstrip('/'))[1] for o in result.get('CommonPrefixes')]

    
    def __get_category_files(self, model, category):
        key = f'data/{model}/{category}'
        bucket = self.s3.Bucket(bucket_name)
        result = list(bucket.objects.filter(Prefix=key))    
        return [os.path.split(o.key)[1] for o in result]

    def upload_local(self, path):
        bucket = self.s3.Bucket(self.bucket)
        root = os.path.split(path)[1]

        remote_categories = self.__get_categories(model)
        if len(remote_categories) > 0:
            raise ValueError(f"{root} already exists. Did you mean to `coach sync {root}`?`")
       
        walk = os.walk(path)
        local_categories = next(walk)[1]

        if len(local_categories) <= 0:
            raise ValueError("Invalid directory structure, no category subdirectories")
        
        # Upload everything we have locally      
        for subdir, dirs, files in walk:
            subdir_path = os.path.split(subdir)
            if subdir_path[0] != '':
                click.echo(f"Syncing {subdir_path[1]}...")
            for file in files:
                full_path = os.path.join(subdir, file)
                with open(full_path, 'rb') as data:
                    bucket.put_object(Key=f'data/{root}/' + full_path[len(path)+1:], Body=data)


    def sync_local(self, path):
        model = os.path.split(path)[1]
        bucket = self.s3.Bucket(self.bucket)

        walk = os.walk(path)
        local_categories = next(walk)[1]

        if len(local_categories) <= 0:
            raise ValueError("Invalid directory structure, no category subdirectories")

        # Delete remote categories if they don't exist locally
        remote_categories = self.__get_categories(model)
        for category in remote_categories:
            if category not in local_categories:
                self.rm(model, category)

        # Iterate through our local categories, check for consistency with remote
        for category in local_categories:
            click.echo(f"Syncing {category}...")

            category_walk = os.walk(os.path.join(path, category))
            category_subs = next(category_walk)[1] # Get subdirectories in our cats
            if len(category_subs) > 0:
                click.echo("W: Directories in categories will be ignored")

            local_files = [files for root, dirs, files in os.walk(os.path.join(path, category))][0]
            remote_files = self.__get_category_files(model, category)

            for remote_file in remote_files:
                if remote_file not in local_files:
                    self.rm(model, category, remote_file)

            for local_file in local_files:
                if local_file not in remote_files:
                    with open(os.path.join(path, category, local_file), 'rb') as data:
                        bucket.put_object(Key=f'data/{model}/{category}/{local_file}', Body=data)

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

    def rm(self, model, category=None, file=None):
        prefix = f"data/{model}/"
        if category != None:
            prefix += category + '/'
            if file != None:
                prefix += file

        bucket = self.s3.Bucket(bucket_name)
        bucket.objects.filter(Prefix=prefix).delete()

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
            
            if name not in status:
                return None
            elif 'currentStatus' not in status[name]:
                return None
            elif 'Status' not in status[name]['currentStatus']:
                return None

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
                r = pretty_print(status, model)
                if r is not None:
                    result += r
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

config_folder = os.path.join(str(Path.home()), '.coach')
model_folder = os.path.join(config_folder, 'models')

def read_creds():
    creds = os.path.join(config_folder, 'creds.json')
    with open(creds, 'r') as creds_file:
        body = creds_file.read()
        creds_file.close()
        return json.loads(body)

def get_coach():
    creds = read_creds()
    return CoachApi(creds['api'], creds['key'], creds['secret'], creds['id'], creds['bucket'])

@click.command()
@click.option("--api", type=str, prompt="API Key", help="API Key", hide_input=True)
@click.option("--key", type=str, prompt="Storage Key", help="Storage Key", hide_input=True)
@click.option("--secret", type=str, prompt="Storage Key Secret", help="Storage Key Secret", hide_input=True)
def login(api, key, secret):
    """
    Authenticates with Coach.
    Get your API key here: https://coach.lkuich.com/
    """
    def get_profile():
        id = api[0:5]
        url = 'https://2hhn1oxz51.execute-api.us-east-1.amazonaws.com/prod/' + id
        response = requests.get(url, headers={"X-Api-Key": api}).json()
        return response

    profile = get_profile()

    if 'id' not in profile:
        click.echo("Invalid API key, could not authenticate")
        return

    if not os.path.exists(config_folder):
        os.mkdir(config_folder)

    creds = os.path.join(config_folder, 'creds.json')
    click.echo(f"Storing credentials in: {creds}")
    
    with open(creds, 'w') as creds_file:
        content = {
            'api': api,
            'key': key,
            'secret': secret,
            'bucket': profile['bucket'],
            'id': profile['id']
        }
        creds_file.write(json.dumps(content))
        creds_file.close()

@click.command()
@click.argument("model", type=str)
@click.option("--steps", type=int, default=500, help="Number of training steps")
@click.option("--module", type=click.Choice(
    [
        'mobilenet_v2_035_128', 'mobilenet_v2_050_128', 'mobilenet_v2_075_128', 'mobilenet_v2_100_128',
        'mobilenet_v2_035_224', 'mobilenet_v2_050_224', 'mobilenet_v2_075_224', 'mobilenet_v2_100_224', 'mobilenet_v2_130_224', 'mobilenet_v2_140_224'
    ]
), default="mobilenet_v2_100_224", help="Module to use as transfer learning base")
def train(model, steps, module):
    """
    Starts a Coach training session.

    You can specify a base module for transfer learning. This will impact the size and accuracy of your model.
    You may also want to adjust the number of training steps to account for under/overfitting
    """
    click.confirm(f'Are you sure you want to train {model} for {str(steps)} steps?', abort=True)

    try:
        coach = get_coach()
        coach.train(model, steps, module)
        click.echo(f"Training {model} for {str(steps)} steps...")
    except Exception as e:
        click.echo(e)

@click.command()
@click.argument('model', type=str)
def rm(model):
    """Deletes synced training data."""
    click.confirm(f"You're about to delete the training data for {model}, are you sure you want to continue?", abort=True)

    try:
        coach = get_coach()
        coach.rm(model)
        click.echo(f"Deleted {model}")
    except Exception:
        click.echo(f"Failed to delete {model}")

@click.command()
@click.argument("path")
def new(path):
    """
    Uploads your local training directory to Coach.
    """
    path = path.rstrip('\\').rstrip('/')
    click.confirm(f'Are you sure you want to upload {path}?', abort=True)
    
    try:
        coach = get_coach()
        coach.upload_local(path)
    except Exception:
        click.echo(f"Failed to sync {path}")

@click.command()
@click.argument("path")
def sync(path):
    """
    Syncs a local data directory with Coach.

    The default operation is to upload local contents, remote data will be deleted if it is no longer present locally.
    """
    path = path.rstrip('\\').rstrip('/')
    click.confirm(f'This will DELETE remote data that is not present.\Are you sure you want to sync {path}?', abort=True)
    
    try:
        coach = get_coach()
        coach.sync_local(path)
    except Exception:
        click.echo(f"Failed to sync {path}")

@click.command()
def ls():
    """Lists synced projects in Coach."""
    try:
        coach = get_coach()
        for obj in coach.list_objects():
            click.echo(obj)
    except Exception:
        click.echo(f"Unable to list {prefix}")

@click.command()
@click.option("--model", type=str, help="Trained model name")
def status(model):
    """Retreives the status of models."""
    try:
        coach = get_coach()
        status = coach.status(model)
        click.echo('-----------------------------------------------------')
        click.echo(status)
        click.echo('-----------------------------------------------------')
    except ValueError as err:
        click.echo(err)

@click.command()
@click.argument("model", type=str)
@click.option("--path", type=str, default=model_folder, help="Folder to store cached model")
def cache(model, path):
    """Caches a model locally."""
    if path == model_folder and not os.path.isdir(path):
        os.mkdir(path)

    try:
        coach = get_coach()
        coach.cache(model, path)
    except ValueError as err:
        click.echo(err)

@click.command()
@click.argument("image", type=str)
@click.argument("model_name", type=str)
@click.option("--root", type=str, default=model_folder, help="Path containing model directories")
def predict(image, model_name, root):
    """
    Locally runs model prediction on specified image.

    Models must already be cached. See cache command for usage.
    For example:
    coach cache flowers
    coach predict rose.jpg flowers
    """
    try:
        model_path = os.path.join(root, model_name)    
        coach = get_coach()
        coach.predict(image, model_path)
    except ValueError as err:
        click.echo(err)

@click.group()
def cli():
    """
    💖 Welcome to the Coach CLI Utility! 💖

    Grab your API keys and view example usage at:
    https://coach.lkuich.com

    Happy training! ⚽
    """
    pass

cli.add_command(train)
cli.add_command(login)
cli.add_command(new)
cli.add_command(sync)
cli.add_command(ls)
cli.add_command(rm)
cli.add_command(status)
cli.add_command(cache)
cli.add_command(predict)