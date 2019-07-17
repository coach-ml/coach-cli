import click

@click.command()
@click.argument("train")
@click.option("--imageDir", type=str, prompt="Directory of sample images", help="Directory of sample images")
@click.option("--steps", type=int, prompt="Number of steps to train for", help="Number of steps to train for")
def train(imageDir, steps):
    print("Training " + imageDir + " for " + str(steps) + " steps")

@click.group()
def main():
    pass

if __name__ == "__main__":
    main()