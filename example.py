import signal
import sys
import time

from acts_channel import Channel


def signal_handler(signal, frame):
    print('Caught Ctrl+C / SIGINT signal')
    sys.exit(0)
    
def main():
    chan = Channel(url = "127.0.0.1:10080")
    signal.signal(signal.SIGINT, signal_handler)
    model = """
    id: test
    name: workflow in python
    steps:
        - name: step 1
          id: step1
          acts:
              - uses: acts.core.irq
                key: abc
    """
    resp = chan.deploy(model)

    ret = resp.unwrap_or_raise(ValueError)
    print("chan.deploy:", ret)

    resp = chan.send("model:get", { "id": "test", "fmt": "tree"})
    print(resp.ok_value["data"])
    
    chan.subscribe("client-1", on_message)
    
    resp = chan.start("test", { "custom": "aaa" })
    print(resp.ok_value)

    print("waiting for all messages...")
    time.sleep(5)

def on_message(chan: Channel, message):
    print(f"on_message: {message}")
    if message["key"] == "abc":
        chan.act("complete", message["pid"], message["tid"], {})


if __name__ == "__main__":
    main()