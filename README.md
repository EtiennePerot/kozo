# 構造 - Kōzō
*(Prounounced "Kouzou"; means "Structure")*

## What is it?

#### Short answer

Kōzō is a framework for running jobs and passing messages among many nodes. It was made primarily for home automation purposes, in order to have many small computers notifying each other about events happening around them.

#### Long answer

A Kōzō system is made of many *Nodes*, each of which have many *Roles* which can send/receive *Messages* to/from other *Roles* using various *Transports*.

##### Glossary
* **Node**: A physical machine on the network. Has a bunch of *Roles* and a bunch of *Transports*.
* **Role**: A task that can be performed by a *Node*. It may send *Messages*, may define which *Messages* it is interested in, and receive such *Messages* from other *Roles*.
* **Transport**: A way for *Nodes* to communicate, and over which *Messages* from *Roles* traverse.
* **Message**: Arbitrary data sent by a *Role*, which other *Roles* may or may not declare to be interested in and receive.

##### Communication model

All Transports feature reliability, integrity, encryption, and authentication. However, Kōzō has no notion of group consensus and doesn't guarantee that all messages will be delivered to all available interested parties. It will simply try its best to ensure that this is the case as often as possible, nothing more.

To do this, every Node `A` keeps trying to reach every other Node `B` using any possible {`A`-Transport, `B`-Transport} pair. Once a connection is made, Messages sent by Roles running on `A` will reach interested Roles running on `B`. When the connection drops, Messages sent by Roles running on `A` will not reach interested Roles running on `B`. Once the link is reestablished, Messages can flow from `A` to `B` again.

This design decision reflects the intended purpose of Kōzō's Messages: Event notifications. As working on old events should be considered meaningless, cutting a link simply cuts the event flow. The event flow will resume once the link is re-established.

## Dependencies
### Hard dependencies
* [Python 2]
* [Paramiko], which itself depends on:
    * [PyCrypto] - which unfortunately prevents the use of [PyPy]
* Either [PyYAML] or [LibYAML]
* [Python-six]

### Optional dependencies
* [MessagePack] - Used as serializer if available; otherwise, [cPickle] or [pickle] is used. Be careful: if a node doesn't have it, it will not be able to deserialize messages from nodes that do have it.

### Testnet dependencies
* [tmuxinator], which itself depends on:
    * [Ruby]
    * [tmux]
* Regular Kōzō dependencies

### Specific Role dependencies
* `roles/bluetooth-discover.py`: [PyBluez]
* `roles/motion-detect.py`: Either [RPIO] or [RPi.GPIO]

### Specific Transport dependencies
* `transports/bluetooth.py`: [PyBluez]

## Usage

In a Kōzō network, each Node possesses the following:

* A name
* A copy of the [YAML] configuration file describing the network
* A public/private [SSH] keypair (used for communication authentication, encryption, and integrity)
* Zero or more Roles
* Zero or more Transports

### Configuration file

Here is an example configuration file:

```yaml
system:
	clock:
		privateKey: /var/lib/kozo/mykey
		publicKey: ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDAVLVzV9IEDn4+oEM7vNd7gs1Sq3Lgt7/2RQ0s+80bJbpSBUkwmdGcX0Zi5cGRFAAOnSaZfrAJxB+nL6Ofq3VjOmD8kkn4NmKYIRJiSTYbOy/7lwPAXDqMtOGG7JsgMA0EmQrr5U4Q99Wy21vmMw60vH5sHeSLDYm3O7r4JpxLXIlCjWVqxV5lL9XyidwYZbS/Yux26M/XJxl80DSe0tPyrtN0b28XzSqSpdfscZGom3fvVjStjlqkwKhlCPJmT8HBy9KQ/E0ufM1lop850ZarLcrsQV4HCJ2ljcsNO9497vPXxELZLjVRWavISCK1BNEL20UTGcbl/1vGWsVFPUlr
		roles:
			timer1:
				type: timer
				tick: 60
		transports:
			tcp:
				address: clock.local, 10.13.37.2, gnreiuoyh5rrtkjhe4r5j5423t4egyr.onion
	scribe:
		privateKey: /var/lib/kozo/mykey
		publicKey: ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDPqI1iSlFvhrB9ZIvCbuVBGnd0vzUgO+HnqzB8gwb2gOjmUXN13TGjGsyEXvYZvIPHUYHp/A9Ob/afkeA7UiDOrxNMmYco9Aczu63IuEbqS7CWUQVAq84mEhi9j2bQJp7wr1FSAz8Lg1A2jEBYDJo06gvsUJc8UW4ONjgCc4fszCrqvfoZ8reESe2+UaZN+yE+cjpN1Mn1DXwkINRqyXYv6cZHJwAeY04QrwYZWRaQe2BxNzcTo9Kb+emJQupDRx3YKoJuGr+mO6sHDvKY0pAB3ERLKfKKk37X0GK3INBWha4h8RFuTebchP/QVOESC5uTklXtpMGxLxFeYYM0r8T/
		roles:
			cuckoo:
				timer: timer1
			logger:
				file: /var/log/kozo/scribe.log
				clearLog: true
		transports:
			tcp:
				address: scribe.local, 10.13.37.51, oierhgioenhi54j4jnmr56kdshbded.onion
heartbeat: 30
cipher: aes256-ctr
```

Here is a detailed description of what each block does and accepts as options:

* `system`: Main configuration block, which describes the structure of the network.
    * Each child of the `system` block is a Node block. Its name determines the Node's name. Each Node block contains Node-specific information.
        * `privateKey` is a (preferrably absolute) path to the private key of the Node. Note that this file should only be valid on the Node in question, i.e. only the Node being described should have such a file. As such, it is entirely possible to have the same `privateKey` value for all Node blocks, as long as each Node has its own private key saved at that location on its filesystem.
        * `publicKey` is the contents of the public half of `privateKey`. Since all Nodes need to know this information, it is provided directly into the configuration file, as opposed to being pointed at by a path.
        * `roles` is a list of Role blocks.
            * Each child of the `roles` block is a Role block, containing Role-specific information. Its name determines the Role's name. Role names need not be unique across Nodes, but should be unique among a single Node. All Role blocks accept the following configuration options, on top of Role-specific ones:
                * `type`: *Optional but highly recommended*. If specified, this must refer to the name of the Role module to use. If unspecified, the name of the Role is used as the name of the Role module to use. In the above example, `timer1` is a Role of type `timer`, whereas `cuckoo` is a Role of type `cuckoo`.
                * `description`: *Optional*. A textual description about the purpose of this Role. Not used internally, just there for human consumption.
                * `messageQueueSize`: *Optional*. If specified, this refers to the size of the buffer containing incoming Messages for this Role. Note that Role modules may override this; if they do, their value takes precedence over the configuration value (unless, of course, their overridden method decides to give precedence to the value in the configuration, if one is present).
        * `transports` is a list of Transport blocks.
            * Each child of the `transports` block is a Transport block, containing Transport-specific information. Its name determines the Transport's name. Transport names need not be unique across Nodes, but should be unique among a single Node. All Transport blocks accept the following configuration options, on top of Transport-specific ones:
                * `type`: *Optional*. If specified, this must refer to the name of the Transport module to use. If unspecified, the name of the Transport is used as the name of the Transport module to use. In the above example, `tcp` is both the name and the Transport module of the only Transport available to both nodes in the system.
* `heartbeat`: Interval (in seconds) to send heartbeat Messages to all connected Nodes. These Messages never reach Roles; they are used by Nodes to keep all active connections alive and in check. Default: `10`.
* `connectionRetry`: How long (in seconds) to wait after a disconnection before trying to reconnect again. Default: `60`.
* `outgoingQueueSize`: The size of the buffer for outgoing Messages (in number of Messages). Each Node holds such a buffer for every other Node in the system. Default: `128`.
* `cipher`: The cipher to use for all communication. Default: `aes256-ctr`.
* `hmac`: The MAC algorithm to use for all communication. Default: `hmac-sha1`.
* `rolePath`: A colon-separated list of directories in which custom Role files are located. Default: Empty.
* `transportPath`: A colon-separated list of directories in which custom Transport files are located. Default: Empty.
* `importPath`: A colon-separated list of directories which will be prepended to the import paths, available for use in all Roles and Transports. This can be further extended with the KOZOIMPORTPATH environment variable. Default: Empty.

#### Available Roles

The following Roles are distributed as part of Kōzō:

* `timer`: A simple Role that emits a timer message (events of type `tick`) at a regular interval.
    * `tick` (Optional): Number of seconds between each message. Default: 1 seccond
    * `message` (Optional): A string to insert into every message
* `cuckoo`: A simple Role that listens for `tick` events (messages sent by the `timer` Role) and prints them.
    * `timer` (Optional): The name of the `timer` Role to listen to. Other `timer` Roles will be ignored. If unspecified, will listen to all `timer` Roles in the system.
* `logger`: A Role that listens for `log` events. Roles may send log messages, and the `logger` role will pick them up, print them, and write them to a file. Useful to have a central Node log everything going on in the system.
    * `file` (Optional): Path to a file where the log messages will be written. Default is `/var/log/kozo/kozo.log`
    * `timePrefix` (Optional): Timestamp format used as prefix on each line. See [strftime](http://docs.python.org/2/library/time.html#time.strftime) for the available variables. Default is `[%Y-%m-%d %H:%M:%S] `, with a space at the end so that there is a gap between the timestamp and the message itself.
    * `flushEvery` (Optional): The log file will be flushed every `flushEvery` messages. By default, it is flushed every 1024 messages.
    * `clearLog` (Optional): Whether to clear any existing log file when starting up. The default is not to do so.
* `bluetooth-discover`: Scans around for discoverable Bluetooth devices every so often.
    * `searchDuration` (Optional): How long to spend searching for devices. The default is 8 seconds.
    * `cooldown` (Optional): How long to wait between searches. The default is 30 seconds.
    * `log` (Optional): Whether or not to send a `log` message whenever one or more devices enter or leave the set of nearby Bluetooth devices. Note that the `bluetooth-discover` Role will send a `bluetooth devices in range` event regularly after each search containing all information about all devices in range at the time; the `log` parameter is simply there to make it easy to log this information in a concise manner.
* `motion-detect`: Reports movement given by a GPIO pin. Meant to be used with the Raspberry Pi, as [helpfully described by Adafruit Industries here](http://learn.adafruit.com/adafruits-raspberry-pi-lesson-12-sensing-movement).
    * `pin` (Optional): Pin number of the motion detector's output wire. Default is pin 18.
    * `period`: How many seconds to wait between motion detection checks. Default is 0.5.
    * `log` (Optional): Whether or not to send a log message every time motion starts or stops. Note that the `motion-detect` Role will send a `motion detection` event regularly every `period` seconds saying whether there was motion or not; the `log` parameter is simply there to make it easy to log this information in a concise manner.

#### Available Transports

*Note*: All communication is encrypted and authenticated regardless of the Transport used. The only purpose of a Transport is to move bits from one Node to another, nothing more.

* `tcp`: A standard TCP connection. This is the fastest and most reliable Transport.
    * `address`: A comma-separated list of addresses (can be IP addresses, domain names, .onion addresses, local network names, etc) that all point to the Node. These addresses are not used for binding; they are used by other Nodes in order to make a connection.
    * `port` (Optional): The local TCP port to bind to. The `tcp` Transport will always bind on all interfaces on that port.
    * `socketConnectionBacklog` (Optional): The maximum number of incoming connections to keep open but non-processed yet. This should not need to exceed the number of nodes in the network, but it doesn't hurt if it does.
* `bluetooth`: Communication over Bluetooth. Useful when a device has no Wi-Fi networking capability (or you don't want to give it access to your Wi-Fi network).
    * `uuid`: A random UUID that will identify this service. Can be any valid UUID; you can generate one by running `uuidgen`.
    * `address` (Optional): The MAC address of the Bluetooth interface of the Node. If specified, other Nodes will know instantly which Bluetooth device to connect to, which makes the connection process a lot faster. If unspecified, other Nodes will need to poke every Bluetooth device in range and ask for their list of services, until they find one with a matching UUID. This approach takes a lot longer, but it allows you to make the Node spoof its MAC address every so often without adverse consequences. Once the Bluetooth connection is established, the performance is the same whether or not the MAC address was specified.
    * `socketConnectionBacklog` (Optional): The maximum number of incoming connections to keep open but non-processed yet. This should not need to exceed the number of nodes in the network, but it doesn't hurt if it does.

### Running the system

Once all of the above is properly declared, copy the configuration file to each Node. Then, run the following:

	kozo path/to/config.yml <localNodeName>

Where `<localNodeName>` is the name of the Node that you are running the command on. The network may take a while to converge, but once all Nodes are online and reachable, connections will form over time.

## Extending Kōzō

### Writing custom Roles

TODO

### Writing custom Transports

Writing Transports is a matter of extending either the `Transport` or the `AuthenticatedTransport` class. You should preferrably extend `AuthenticatedTransport` and you will get encryption and authentication for free. If your underlying Transport already includes encryption and authentication, then it may be worth subclassing `Transport` directly to avoid doubling the cryptographic overhead.

Once you have done that, you must register the Transport with the system.

#### Subclassing `AuthenticatedTransport`

The `AuthenticatedTransport` class deals with socket-like objects. A socket-like object is an object which presents the following methods:

* `send(self, bytes)`: Writes between 1 and `len(bytes)` bytes from `bytes` to the socket, and returns the number of bytes that were written. On timeout, raises `socket.timeout()`.
* `recv(self, numBytes)`: Reads between 1 and `numBytes` bytes from the socket, and returns them. On remote socket closed, raises `socket.error(104, 'Connection reset by peer')`. On timeout, raises `socket.timeout()`.
* `settimeout(self, timeout)`: Accepts a float value (in seconds) as timeout on read and write operations.
* `close(self)`: Closes the socket. No `send` or `recv` operations will be executed on the socket once this method is called.

An `AuthenticatedTransport` subclass **must** implement the following methods:

* `acceptUnauthenticatedConnection(self)`: This will be called on the Node offering the Transport once it is ready to accept connections on this Transport. The method should block until a connection is made to this Transport. Then, the method should return a socket-like object corresponding to the connection that was just made.
* `getUnauthenticatedConnectAddresses(self, otherTransport)`: Should return an iterable of objects (which often just contains one value), each of which should be meaningful as input to the `getUnauthenticatedSocket` method described below, that allows the local Node to connect to the `otherTransport` Node. Each value will be tested in the order of iteration until a connection is made. For example, for the TCP transport, this list simply contains the IP addresses and domain names that `otherTransport`'s Node can be reached at.
* `getUnauthenticatedSocket(self, otherTransport, addressIndex, address)`: Should attempt to connect to `otherTransport` via the provided `address`, which is just one of the objects returned by `getUnauthenticatedConnectAddresses`, at index `addressIndex` in the iteration. If a connection is successful, this should return a socket-like object. Otherwise, this should return `None`.

Additionally, an `AuthenticatedTransport` subclass **may** override the following methods:

* `init(self)`: This will be called during initialization on **all Nodes in the system**. As such, no networking should ever happen here, only basic initialization and state-setting. It is better to do such work here rather than in the constructor, because the whole network may not be completely represented at the time the constructor is called. If you override this, you should **always** call the `.init()` method of the parent class as well.
* `bind(self)`: This will be called during initialization, but **only on the Node the Transport is available on**. If you override this, you should **always** call the `.bind()` method of the parent class as well.
* `getPriority(self)`: Returns a priority indicator (from `Transport.Priority_WORST` to `Transport.Priority_BEST`) indicating the preference the system should have regarding the Transport to pick in order to establish a connection from one Node to another. The faster and the more reliable the Transport, the higher its priority should be. The default is `Transport.Priority_MEH`.
* `canConnect(self, otherTransport)`: This should return `True` if this Transport can be used to connect to `otherTransport`, otherwise `False`. The default implementation returns `True` if both Transports are of the same class, so there is no need to override this method if that is the only check you will be doing.

An `AuthenticatedTransport` subclass **should not** override the following methods (but may call them, if appropriate):

* `getNode(self)`: Returns the Node object that offers this Transport.
* `isSelf(self)`: Returns whether the Node running the Python interpreter right now is the same as the Node offering this Transport.
* `self['key']`: Returns the value (default or not) associated with `key` in the configuration of this subclass. See the metadata section for details.

*Note*: Other methods exist but are not meant to be interacted with.

#### Subclassing `Transport` directly

**Important**: If you decide to go this route, it is up to you to properly implement encryption and authentication for all communication.

The `Transport` class deals with `Channel` instances. It is up to you to build these instances with all the state they need. A `Channel` subclass **must** override the following methods:

* `__init__(self, *args, **kwargs)`: You may design the constructor as you like, but it must call the `Channel`'s base constructor: `Channel(fromNode, toNode)`.
* `send(self, bytes)`: Writes between 1 and `len(bytes)` bytes from `bytes`, and returns the number of bytes that were transmitted. On error, returns `None`.
* `receive(self, bytes, timeout)`: Reads between 1 and `numBytes` bytes from the socket, and returns them. On error or timeout (specified as a float in seconds), returns `None`.

`Channel` subclasses have the following methods available to them (but they should not be overridden):

* `getFromNode(self)`: Returns the Node object on the Sender side of the Channel.
* `getToNode(self)`: Returns the Node object on the Receiver side of the Channel.
* `isAlive(self)`: Returns whether this Channel should still be used for communication or not.

*Note*: Other methods exist but are not meant to be interacted with.

Once your `Channel` subclass is properly defined, you can create your `Transport` subclass. A `Transport` subclass **must** implement the following methods:

* `accept(self)`: This will be called on the Node offering the Transport once it is ready to accept connections on this Transport. The method should block until a connection is made to this Transport. It should then perform authentication and set up an encryption key for communication. Then, the method should return a `Channel` object corresponding to the connection that was just made.
* `connect(self, otherTransport)`: Should attempt to connect to `otherTransport`, perform authentication and set up encryption, and then return a `Channel` object on success, or `None` on failure.

Additionally, a `Transport` subclass **may** override the following methods:

* `init(self)`: This will be called during initialization on **all Nodes in the system**. As such, no networking should ever happen here, only basic initialization and state-setting. It is better to do such work here rather than in the constructor, because the whole network may not be completely represented at the time the constructor is called. If you override this, you should **always** call the `.init()` method of the parent class as well.
* `bind(self)`: This will be called during initialization, but **only on the Node the Transport is available on**. If you override this, you should **always** call the `.bind()` method of the parent class as well.
* `getPriority(self)`: Returns a priority indicator (from `Transport.Priority_WORST` to `Transport.Priority_BEST`) indicating the preference the system should have regarding the Transport to pick in order to establish a connection from one Node to another. The faster and the more reliable the Transport, the higher its priority should be. The default is `Transport.Priority_MEH`.
* `canConnect(self, otherTransport)`: This should return `True` if this Transport can be used to connect to `otherTransport`, otherwise `False`. The default implementation returns `True` if both Transports are of the same class, so there is no need to override this method if that is the only check you will be doing.

An `AuthenticatedTransport` subclass **should not** override the following methods (but may call them, if appropriate):

* `getNode(self)`: Returns the Node object that offers this Transport.
* `isSelf(self)`: Returns whether the Node running the Python interpreter right now is the same as the Node offering this Transport.
* `self['key']`: Returns the value (default or not) associated with `key` in the configuration of this subclass. See the metadata section for details.

*Note*: Other methods exist but are not meant to be interacted with.

#### Adding Transport metadata

Once you have defined your subclass, you need to provide information about it to Kōzō. This is done by adding a dictionary called `transportInfo` at the end of the file. Here is an annotated example of such a dictionary:

```python
transportInfo = {
    'format': '1.0',                                      # Should always be 1.0 for now
    'class': MyTransport,                                 # Direct reference to the subclass
    'author': 'John Smith',                               # Author name
    'version': '1.0',                                     # Version of this Transport
    'description': 'A simple TCP socket transport.',      # Description of this Transport
    'config': {                                           # Configuration options
        'port': {                                         # Name of the configuration option
            'default': 9001,                              # Default value of the configuration option
            'description': 'TCP port to bind to.'         # Description of the configuration option
        },
        'address': {                                      # Name of the configuration option
            'description': 'An address or a list of addresses that the node can be reached from.'
                                                          # ^ Description of this configuration option
            # Since this configuration option doesn't have a default value, it will be considered
            # to be a required option. The system will refuse to start if it is not provided.
        }
    }
}
```

#### Using custom Transports

Once you have written your custom Transport file, you have three options:

* Drop it in `src/kozo/transports` (easy, but not always possible if installed as a system package).
* Set the environment variable `KOZOTRANSPORTPATH` to be a colon-separated list of directories containing custom Transports, then drop your Transport file in one of these directories.
* Set the `transportPath` option in your network configuration file (see above), then drop your Transport file in one of these directories.

To use your custom Transport, you can refer it by its file name in the configuration file. For example, if you name it `mytransport.py`, then your config file should look like this:

```yaml
system:
	mynode:
		transports:
			mytransport:
				port: 9002
				address: hello
```

[Python 2]: http://www.python.org/
[Paramiko]: http://www.lag.net/paramiko/
[PyCrypto]: http://www.pycrypto.org/
[PyPy]: http://pypy.org/
[PyYAML]: http://pyyaml.org/wiki/PyYAML
[LibYAML]: http://pyyaml.org/wiki/LibYAML
[Python-six]: https://pythonhosted.org/six/
[MessagePack]: http://msgpack.org/
[cPickle]: http://docs.python.org/2/library/pickle.html#module-cPickle
[pickle]: http://docs.python.org/2/library/pickle.html
[tmuxinator]: https://github.com/aziz/tmuxinator
[Ruby]: http://www.ruby-lang.org/
[tmux]: http://tmux.sourceforge.net/
[PyBluez]: https://code.google.com/p/pybluez/
[RPIO]: https://pythonhosted.org/RPIO/
[RPi.GPIO]: https://code.google.com/p/raspberry-gpio-python/
[YAML]: http://yaml.org/
[SSH]: https://en.wikipedia.org/wiki/Secure_Shell
