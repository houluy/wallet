from sawtooth_sdk.protobuf.client_event_pb2 import ClientEventsSubscribeRequest, ClientEventsSubscribeResponse
from sawtooth_sdk.protobuf.events_pb2 import EventSubscription, EventFilter, EventList, Event
from sawtooth_sdk.protobuf.validator_pb2 import Message

import zmq
import time


def subscribe():
    subscription = EventSubscription(
        event_type="sawtooth/state-delta",
        filters=[
            EventFilter(
                key="address",
                match_string="3a8434.*",
                filter_type=EventFilter.REGEX_ANY,
            )
        ],
    )
    
    url = "tcp://127.0.0.1:4004"
    ctx = zmq.Context()
    socket = ctx.socket(zmq.DEALER)
    socket.connect(url)
    
    request = ClientEventsSubscribeRequest(
        subscriptions=[subscription]).SerializeToString()

    correlation_id = "123"
    msg = Message(
        correlation_id=correlation_id,
        message_type=Message.CLIENT_EVENTS_SUBSCRIBE_REQUEST,
        content=request,
    ).SerializeToString()
    socket.send_multipart([msg])

    time.sleep(2)
    resp = socket.recv_multipart()[-1]
    msg = Message()
    msg.ParseFromString(resp)
    if msg.message_type != Message.CLIENT_EVENTS_SUBSCRIBE_RESPONSE:
        print(f"Unexpected message type: {msg.message_type}")
        return

    response = ClientEventsSubscribeResponse()
    response.ParseFromString(msg.content)

    if response.status != ClientEventsSubscribeResponse.OK:
        print(f"Subscription failed, status code is {response.status}")
        return

    while True:
        resp = socket.recv_multipart()[-1]
        msg = Message()
        msg.ParseFromString(resp)
        if msg.message_type != Message.CLIENT_EVENTS:
            print(f"Unexpected message type: {msg.message_type}")

        events = EventList()
        events.ParseFromString(msg.content)
        print(events)

        #@for event in events:
        #@    print(event)

        

subscribe()


