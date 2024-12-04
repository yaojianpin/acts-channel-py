from dataclasses import dataclass
import threading
from typing import Any, Optional,Callable
from acts_channel.proto import acts_pb2_grpc, acts_pb2
import grpc
import json
from result import Result, Ok, Err
import nanoid

@dataclass
class ActsOptions:
    type: Optional[str]
    state: Optional[str]
    tag: Optional[str]
    key: Optional[str]
    ack: Optional[bool]

@dataclass
class Package:
    id: str
    name: str
    body: str

@dataclass
class Error:
    name: str
    error: str

class Channel(object):
    """
    Acts client channel class definition

    Args:
        url (str)  server url with port
    """
    
    def __init__(self, url: str) -> None:
        self.url = url
        self.channel = grpc.insecure_channel(url)
        self.stub = acts_pb2_grpc.ActsServiceStub(self.channel)
    
    def __del__(self):
        self.channel.close()

    def send(self, name: str, options: object = {}) -> Result[Any, Error]:
        """
        send action to acts-server
        # example
        ```python
        from acts_channel import Channel

        chan = Channel(url = "127.0.0.1:10080")
        model = \"\"\"
        id: test
        steps:
            - name: step1
        \"\"\"
        # publish a model
        resp = chan.send("pack:publish", model)
        print(resp)
        ```
        """
        try:
            data = json.dumps(options).encode('utf-8')
            message = acts_pb2.Message(seq=self.__create_seq(), name=name, ack=None, data=data)
            resp = self.stub.Send(message)
            return Ok(json.loads(resp.data.decode('utf-8')))
        except Exception as e:
            err = Error(name=name, error=f"{e}")
            if hasattr(e, "details"):
                err = Error(name=name, error=f"{e.details()}")
            return Err(err)

    def publish(self, package: Package) -> Result[bool, str]:
        """publish an acts pakcage to server
           Args:
              package (`Package`) acts pakcage
           Returns
              Result[bool, str] return true if ok, or return error
        """
        data = { "id": package.id, "name": package.name, "body": package.body}
        return self.send("pack:publish", data)
   
    def deploy(self, model: str, mid: str = None) -> Result[bool, str]:
        """ deploy an acts model
            Args:
                model (str): model str in yml format.
                mid   (str): the model id to change.
            Returns
                Result[str, str] return true if ok, or return error
        """
        data = { "model": model, "mid": mid }
        return self.send("model:deploy", data)

    def start(self, mid: str, options: object = {}) -> Result[str, str]:
        """ start a proc from model id
            Args:
                mid     (str):      model id deployed with `deploy` method.
                options (object):   proc input vars.
            Returns
                Result[str, str] return proc id if ok, or return error
        """
        options.update({ "id": mid })
        return self.send("proc:start", options)


    def subscribe(self, clientid: str, callback: Callable[[object, Any], None],  optoins: Optional[ActsOptions] = None):
        """ subscribe messages
            Args:
                clientid     (str):         the client id.
                callback     (object):      callback with messages.
                options      (ActsOptions)  options for type, tag, key and state in glob pattern
        """
        messageOptions = acts_pb2.MessageOptions(client_id = clientid, type="*", state="*", tag="*", key="*")
        ack = True
        if optoins:
            if optoins.type:
                messageOptions.type = optoins.type
            if optoins.state:
                messageOptions.state = optoins.state
            if optoins.tag:
                messageOptions.tag = optoins.tag
            if optoins.key:
                messageOptions.key = optoins.key
            if optoins.ack != None:
                ack = optoins.ack

        thread = threading.Thread(target=self.__on_message, args=(ack, messageOptions, callback))
        thread.daemon = True
        thread.start()


    def ack(self, id: str) -> Result[None, str]:
        """ ack a message, by default the message is auto ack when it is received
            if you subscribe the message with ack = false in ActionsOptions, you should ack the message by manual in you logic
            Args:
                clientid     (str):         the client id.
                callback     (object):      callback with messages.
                options      (ActsOptions)  options for type, tag, key and state in glob pattern
        """
        try:
            message = acts_pb2.Message(seq=self.__create_seq(), 
                                    name="msg:ack", 
                                    ack=id, 
                                    data=None)
            self.stub.Send(message)
            return Ok(None)
        except Exception as e:
            return Err(e.details())
    
    def act(self, name: str, pid: str, tid: str, options: object = {}) -> Result[str, str]:
        """ execute an action
            Args:
                pid     (str):      proc id
                tid     (str)       task id
                options (object):   options with action.
            Returns
                Result[str, str] return proc id if ok, or return error
        """
        options.update({ "pid": pid })
        options.update({ "tid": tid })
        print(name, options)
        return self.send(f"act:{name}", options)

    
    def __on_message(self, ack: bool, options: Any, callback: Callable[[object, Any], None]):
        try:
            messages = self.stub.OnMessage(options)
            for message in messages:
                if ack:
                    self.ack(message.seq)
                data = json.loads(message.data.decode('utf-8'))
                callback(self, data)
        except:
            self.__del__()

    def __create_seq(self) ->str:
        return nanoid.generate(alphabet="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")