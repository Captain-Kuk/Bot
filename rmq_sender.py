import pika

import workconfig

config = workconfig.read_config('config')


def send_data_to_rmq(data, routing_key=None, binary=False):
    credentials = pika.PlainCredentials(config.get('ConnectRMQ', 'username'),
                                        config.get('ConnectRMQ', 'password'))
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=config.get('ConnectRMQ', 'server'),
                                  port=config.get('ConnectRMQ', 'port'),
                                  virtual_host=config.get('ConnectRMQ', 'vhost'),
                                  credentials=credentials))
    channel = connection.channel()
    if binary:
        channel.basic_publish(
            exchange=config.get('ConnectRMQ', 'exchange'),
            routing_key=routing_key,
            body=data,
            properties=pika.BasicProperties(content_type='binary',
                delivery_mode=2,
            ))
    else:
        channel.basic_publish(
            exchange=config.get('ConnectRMQ', 'exchange'),
            routing_key=routing_key,
            body=data,
            properties=pika.BasicProperties(delivery_mode=2)
        )
    connection.close()
