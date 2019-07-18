import click
import json
from pathlib import Path
import os
import requests
from api import CoachApi

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
@click.option("--api", type=str, prompt="API Key", help="API Key")
@click.option("--key", type=str, prompt="Key ID", help="Key ID")
@click.option("--secret", type=str, prompt="Key Secret", help="Key Secret")
def login(api, key, secret):
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
    click.echo(f"Storing creds in: {creds}")
    
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
@click.argument("images")
@click.argument("steps", type=int)
@click.option("--module", type=str, default="mobilenet_v2_100_224", prompt="Which module would you like to use as a base?")
def train(images, steps, module):
    name = os.path.split(images)[1]
    click.confirm(f'Are you sure you want to train {name} for {str(steps)} steps?', abort=True)

    coach = get_coach()
    coach.train(name, steps, module)
    
    click.echo(f"Training {name} for {str(steps)} steps...")

@click.command()
@click.argument("dir")
def sync(dir):
    coach = get_coach()
    click.confirm(f'Are you sure you want to sync {dir}?', abort=True)
    coach.upload_directory(dir)

@click.command()
def ls():
    coach = get_coach()
    print(coach.list_objects())

@click.command()
@click.option("--model", type=str)
def status(model):
    pass

@click.command()
@click.argument("model", type=str)
@click.option("--path", type=str, default=model_folder)
@click.option('--version', type=int, default=0)
def cache(model, path, version):
    coach = get_coach()
    coach.download(model, path, version)

@click.command()
@click.argument("model", type=str)
@click.argument("image", type=str)
def predict(model, image):
    pass

@click.group()
def cli():
    pass

cli.add_command(train)
cli.add_command(login)
cli.add_command(sync)
cli.add_command(ls)
cli.add_command(status)
cli.add_command(cache)
cli.add_command(predict)
