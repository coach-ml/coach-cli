import click
import json
from pathlib import Path
import os
import requests

from datetime import datetime
import boto3
from urllib.parse import unquote_plus

from coach import *

__API__ = 'https://9fqai4xymb.execute-api.us-east-1.amazonaws.com/latest'

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
        result = client.list_objects_v2(Bucket=self.bucket, Prefix=key, Delimiter='/')
        common_prefixes = result.get('CommonPrefixes')
        if common_prefixes is None:
            return []
        return [os.path.split(unquote_plus(o.get('Prefix')).rstrip('/'))[1] for o in common_prefixes]

    
    def __get_category_files(self, model, category):
        key = f'data/{model}/{category}'
        bucket = self.s3.Bucket(self.bucket)
        result = list(bucket.objects.filter(Prefix=key))    
        return [os.path.split(o.key)[1] for o in result]

    def validate_files(self, path):
        result = True
        walk = os.walk(path)
        local_categories = next(walk)[1]

        if len(local_categories) <= 0:
            raise ValueError("Invalid directory structure, no category subdirectories")
        
        # Upload everything we have locally      
        for subdir, dirs, files in walk:
            subdir_path = os.path.split(subdir)
            if subdir_path[0] != '':
                click.echo(f"Validating {subdir_path[1]}...")
            for file in files:
                full_path = os.path.join(subdir, file)
                valid = coach.validate_file(full_path)
                if valid == False:
                    click.echo(f'Invalid image found: {full_path}')
                    result = False
        return result

    def upload_local(self, path):
        model = os.path.split(path)[1]
        bucket = self.s3.Bucket(self.bucket)

        remote_categories = self.__get_categories(model)
        if len(remote_categories) > 0:
            raise ValueError(f"{model} already exists. Did you mean to `coach sync {model}`?`")
       
        walk = os.walk(path)
        local_categories = next(walk)[1]

        if self.validate_files(path) == False:
            raise ValueError("Corrupt images found, aborting sync")
        
        # Upload everything we have locally      
        for subdir, dirs, files in walk:
            subdir_path = os.path.split(subdir)
            category = subdir_path[1];
            if subdir_path[0] != '':
                click.echo(f"Syncing {category}...")
            for file in files:
                full_path = os.path.join(subdir, file)
                with open(full_path, 'rb') as data:
                    bucket.put_object(Key=f'data/{model}/{category}/{file}', Body=data)


    def sync_local(self, path):
        model = os.path.split(path)[1]
        bucket = self.s3.Bucket(self.bucket)

        walk = os.walk(path)
        local_categories = next(walk)[1]

        if self.validate_files(path) == False:
            raise ValueError("Corrupt images found, aborting sync")

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

    def list_objects(self, prefix):
        results = []
        response = self.s3.meta.client.list_objects_v2(
            Bucket=self.bucket,
            Delimiter='/',
            EncodingType='url',
            MaxKeys=100,
            Prefix=prefix,
            FetchOwner=False
        )

        commonPrefixes = 'CommonPrefixes'

        if commonPrefixes in response:
            for prefix in response[commonPrefixes]:
                name = unquote_plus(prefix['Prefix'])
                results.append(name)
            return results
        else:
            return []

    def ls(self):
        prefix = 'data/'
        return [obj.split(prefix, 1)[1].strip('/').strip('\\') for obj in self.list_objects(prefix)]


    def rm(self, model, category=None, file=None):
        bucket = self.s3.Bucket(self.bucket)

        def delete(root):
            prefix = f"{root}/{model}/"
            if category != None:
                prefix += category + '/'
                if file != None:
                    prefix += file

            bucket.objects.filter(Prefix=prefix).delete()

        delete('data')
        delete('trained')

        self.api_rm(model)
        

    def download_remote(self, training_data, path):
        prefix = f"data/{training_data}/"
        bucket = self.s3.Bucket(self.bucket)

        local_dir = os.path.join(path, training_data)
        
        for dir_prefix in self.list_objects(prefix):
            if not os.path.exists(local_dir):
                os.mkdir(local_dir)
        
            _dir = dir_prefix.split(prefix, 1)[1].strip('/')
            
            target_dir = os.path.join(local_dir, _dir)
            if not os.path.exists(target_dir):
                os.mkdir(target_dir)

            for file in bucket.objects.filter(Prefix=dir_prefix):
                remote_filename = file.key
                local_filename = remote_filename.split(prefix, 1)[1]

                if local_filename.split('/')[1] != '':
                    click.echo(local_filename)
                    bucket.download_file(remote_filename, os.path.join(path, training_data, local_filename))

    def train(self, model, steps, module):
        try:
            url = f'{__API__}/new-job'
            response = requests.get(url, params={ "name": model, "steps": steps, "module": module }, headers={"X-Api-Key": self.api})
            response.raise_for_status()
        except Exception as e:
            raise ValueError(f"Failed to start training session ({e})")

        return response.json()

    def api_rm(self, model_name):
        try:
            url = f'{__API__}/rm'
            response = requests.get(url, params={ "name": model_name }, headers={"X-Api-Key": self.api})
            response.raise_for_status()
        except Exception as e:
            raise ValueError(f"Failed to delete ({e})")

        return response.json()
        
    def status(self, name=None):
        try:
            url = f'{__API__}/status'
            response = requests.get(url, headers={"X-Api-Key": self.api})
            response.raise_for_status()
        except Exception as e:
            raise ValueError(f"Failed to check status ({e})")
        
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


    def cache(self, model, path, model_type='frozen'):
        coach = CoachClient().login(self.api)
        coach.cache_model(model_name=model, path=path, skip_match=False, model_type=model_type)

    def predict(self, image_or_directory, model, path):
        coach = CoachClient().login(self.api)
        coach.cache_model(model, path)

        model = coach.get_model(os.path.join(path, model))
        if os.path.isdir(image_or_directory):
            for subdir, dirs, files in os.walk(image_or_directory):
                subdir_path = os.path.split(subdir)
                for file in files:
                    img = os.path.join(subdir, file)
                    click.echo(f'{img}: {model.predict(img)}')
        else:
            img = model.predict(image_or_directory)
            click.echo(f'{image_or_directory}: {img}')

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
    try:
        id = api[0:5]
        profile = coach.get_profile(api, id)
    except Exception as e:
        click.echo(f"Failed to authenticate:\n{e}")
        return

    if profile is None:
        return

    if 'bucket' not in profile:
        click.echo(f"Failed to authenticate, invalid API/ID: {id}")
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
            'id': id
        }
        creds_file.write(json.dumps(content))
        creds_file.close()

@click.command()
@click.argument("model", type=str)
@click.option("--steps", type=int, default=1000, help="Number of training steps")
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
    except Exception as e:
        click.echo(e)

@click.command()
@click.argument("path", type=str)
def new(path):
    """
    Uploads your local training directory to Coach.
    """
    path = path.rstrip('\\').rstrip('/')
    click.confirm(f'Are you sure you want to upload {path}?', abort=True)
    
    try:
        coach = get_coach()
        coach.upload_local(path)
    except Exception as e:
        click.echo(e)

@click.command()
@click.argument("path")
def sync(path):
    """
    Syncs a local data directory with Coach.

    The default operation is to upload local contents, remote data will be deleted if it is no longer present locally.
    """
    path = path.rstrip('\\').rstrip('/')
    click.confirm(f'This will DELETE remote data that is not present.\nAre you sure you want to sync {path}?', abort=True)
    
    try:
        coach = get_coach()
        coach.sync_local(path)
    except Exception as e:
        click.echo(e)


@click.command()
@click.argument("training_data")
@click.option("--path", type=str, default=".")
def download(training_data, path):
    """
    Downloads remote training data locally.

    By default local data with the same name will be replaced.
    """
    path = path.rstrip('\\').rstrip('/')
    click.confirm(f'This will OVERWRITE local data in {path}/{training_data}\nAre you sure you want to download {training_data}?', abort=True)
    
    try:
        coach = get_coach()
        coach.download_remote(training_data, path)
    except Exception as e:
        click.echo(e)


@click.command()
def ls():
    """Lists synced projects in Coach."""
    try:
        coach = get_coach()
        for obj in coach.ls():
            click.echo(obj)
    except Exception as e:
        click.echo(e)

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
@click.option("--model_type", type=str, default='frozen', help="Type of model to cache. Can be one of:\nfrozen\nunity\nmobile")
def cache(model, path, model_type):
    """Caches a model locally."""
    if path == model_folder and not os.path.isdir(path):
        os.mkdir(path)

    try:
        coach = get_coach()
        coach.cache(model, path, model_type)
        click.echo(f'Cached {model_type} model to {path}')
    except ValueError as err:
        click.echo(err)

@click.command()
@click.argument("image_or_directory", type=str)
@click.argument("model_name", type=str)
@click.option("--root", type=str, default=model_folder, help="Path containing model directories")
def predict(image_or_directory, model_name, root):
    """
    Locally runs model prediction on specified image.

    Models must already be cached. See cache command for usage.
    For example:
    coach cache flowers
    coach predict rose.jpg flowers
    """
    try: 
        if root == model_folder and not os.path.isdir(root):
            os.mkdir(model_folder)

        coach = get_coach()
        coach.predict(image_or_directory, model_name, root)
    except ValueError as err:
        click.echo(err)

@click.group()
@click.version_option()
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
cli.add_command(download)
cli.add_command(rm)
cli.add_command(status)
cli.add_command(cache)
cli.add_command(predict)
