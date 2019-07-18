import click

@click.command()
@click.argument("images") #, type=str, prompt="Directory of sample images", help="Directory of sample images")
@click.argument("steps", type=int) #, type=int, prompt="Number of steps to train for", help="Number of steps to train for")
def train(images, steps):
    print("Training " + images + " for " + str(steps) + " steps")
    click.confirm('Do you want to continue?', abort=True)

@click.command()
@click.option("--api", type=str, prompt="API Key", help="API Key")
@click.option("--key", type=str, prompt="Key ID", help="Key ID")
@click.option("--secret", type=str, prompt="Key Secret", help="Key Secret")
def login(api, key, secret):
    print(api + '/' + key + '/' + secret)

@click.command()
@click.argument("dir")
def sync(dir):
    pass

@click.command()
def ls():
    pass

@click.command()
def rm(model):
    pass

@click.command()
@click.option("--model", type=str)
def status(model):
    pass

@click.command()
@click.argument("model", type=str)
@click.option("--dir", type=str)
def cache(model, dir):
    pass

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
cli.add_command(rm)
cli.add_command(status)
cli.add_command(cache)
cli.add_command(predict)

'''
@click.group()
def main():
    pass

if __name__ == "__main__":
    main()
'''