# Coach CLI

This utility is responsible for managing user interaction with Coach's services.

Specifically you can:

- Sync local training data with remote
- Start and watch training sessions
- Locally evaluate models
- Download models

## Installation

```bash
pip3 install -U coach-cli
```

To do anything we must be logged in

```bash
coach login
API Key: *****
Storage Key: *****
Storage Key Secret: *****
```

## Usage

```
Usage: coach [OPTIONS] COMMAND [ARGS]...

  💖 Welcome to the Coach CLI Utility! 💖

  Grab your API keys and view example usage at:
  https://coach.lkuich.com

  Happy training! ⚽

Options:
  --help  Show this message and exit.

Commands:
  cache    Caches a model locally.
  login    Authenticates with Coach.
  ls       Lists synced projects in Coach.
  new      Alias for sync command.
  predict  Locally runs model prediction on specified image.
  rm       Deletes synced training data.
  status   Retreives the status of models.
  sync     Syncs a local data directory with Coach.
  train    Starts a Coach training session.
```

## Examples

We're going to train a `flowers` dataset to recognise the following subjects:

- daisy
- dandelion
- roses
- sunflowers
- tulips

Start by downloading and extracting our dataset

```bash
wget https://storage.googleapis.com/download.tensorflow.org/example_images/flower_photos.tgz
tar -xvf flower_photos.tgz
mv flower_photos flowers # Our model's going to be called flowers
```

Note the structure of the dataset, this is important as it defines both the model and label names

```
flowers
    |-daisy
        |-10090824183_d02c613f10_m.jpg
        |-17040847367_b54d05bf52.jpg
        |-...
    |-dandelion
    |-roses
    |-sunflowers
    |-tulips
```

Now we're going to upload our dataset to Coach

```bash
coach new flowers

# If you make any changes to this data, simply run:
# coach sync flowers
```

Now we're going to train. We must specify the name of our synced project, the number of training steps, and the base module to use for transfer learning.  
In our case, since we have quite a few images, we're going to increase the typical number of steps to `1000`, and we're going to use the default `mobilenet_v2_100_224` as our base model, since this gives us a decent tradeoff between final model size, speed, and quality. Make sure to consult the help docs to find our more about supported base modules and find the right fit for your model based on your needs.

```bash
coach train flowers --steps 1000 --module mobilenet_v2_100_224
```

This will start a new training session. You can monitor its progress with the `status` command, by default with no arguments it'll show the status of all models. Since we're just interested in our `flowers` model, well run with the `--model` parameter

```bash
coach status --model flowers
-----------------------------------------------------
flowers     |    Training   |     2019-06-15 14:30:20
-----------------------------------------------------
```

Once complete, your status should look something like this

```bash
coach status --model flowers
-----------------------------------------------------
flowers     |    Completed   |    2019-06-15 14:32:00
-----------------------------------------------------
```

Now we can download and run our model locally on some training data

```bash
coach cache flowers # Only have to run once
coach predict flowers/roses/13342823005_16d3df58df_n.jpg flowers
{ roses: 0.90, tulips: 0.05, sunflowers: 0.03, daisy: 0.01, dandelion: 0.01 }
```

Our cached model is stored in:  
`~/.coach/models/flowers`

## Conclusions

That's all it takes to train a model end-to-end!

For implementation, check out our client side SDK's:

- [Python](https://github.com/lkuich/coach-python)
- [.NET](https://github.com/lkuich/coach-dotnet)
- [Unity](https://github.com/lkuich/coach-unity)
