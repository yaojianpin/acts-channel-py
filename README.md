# acts-channel

Acts-channel is a workflow client to connect to [`acts-server`](https://github.com/yaojianpin/acts-server)

# Usage

Before connecting, please download [`acts-server`](https://github.com/yaojianpin/acts-server) and start it

```console
pip install acts-channel
```

## Example

```py
import signal
import sys
import time
import acts_channel

def signal_handler(signal, frame):
    print('Caught Ctrl+C / SIGINT signal')
    sys.exit(0)

def main():
    chan = channel.Channel(url = "127.0.0.1:10080")
    signal.signal(signal.SIGINT, signal_handler)
    model = """
    id: test
    name: workflow in python
    steps:
        - name: step 1
          id: step1
          acts:
              - act: irq
                key: abc
    """
    # deploy a workflow model
    resp = chan.deploy(model)
    print(resp.ok_value)

    # get the model info
    resp = chan.send("model:get", { "id": "test", "fmt": "tree"})
    print(resp.ok_value["data"])

    # subscribe messages from server
    chan.subscribe("client-1", on_message)

    # start a workflow by model id and custom data
    resp = chan.start("test", { "custom": "aaa" })
    print(resp.ok_value)

    print("waiting for all messages...")
    time.sleep(5)

def on_message(chan: channel.Channel, message):
    print(f"on_message: {message}")
    if message["key"] == "abc":
        # execute act from client
        chan.act("complete", message["pid"], message["tid"], {})


if __name__ == "__main__":
    main()
```
