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
* [MessagePack] - Used as serializer if available; otherwise, [cPickle] is used. Be careful: either **all** nodes must have it, either **none** of the nodes can have it.

### Testnet dependencies
* [tmuxinator], which itself depends on:
    * [Ruby]
    * [tmux]
* Regular Kōzō dependencies

### Specific role dependencies
* `roles/bluetooth-discover.py`: [PyBluez]
* `roles/motion-detect.py`: Either [RPIO] or [RPi.GPIO]

## Usage

In a Kōzō network, each Node possesses the following:

* A name
* A copy of the [YAML] configuration file
* A public/private [SSH] keypair (used for communication authentication, encryption, and integrity)
* Zero or more Roles
* Zero or more Transports

### Configuration file

Here is an example configuration file:

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

Here is a detailed description of what each block does and accepts as options:

* `system`: Main configuration block, which describes the structure of the network.
    * Each child of the `system` block is a Node block. Its name determines the Node's name. Each Node block contains Node-specific information.
        * `privateKey` is a (preferrably absolute) path to the private key of the Node. Note that this file should only be valid on the Node in question, i.e. only the Node being described should have such a file. As such, it is entirely possible to have the same `privateKey` value for all Node blocks, as long as each Node has its own private key saved at that location on its filesystem.
        * `publicKey` is the contents of the public half of `privateKey`. Since all Nodes need to know this information, it is provided directly into the configuration file, as opposed to being pointed at by a path.
        * `roles` is a list of Role blocks.
            * Each child of the `roles` block is a Role block, containing Role-specific information. Its name determines the Role's name. Role names need not be unique across Nodes, but should be unique among a single Node. All Role blocks accept the following configuration options, on top of Role-specific ones:
                * `type`: *Optional*. If specified, this must refer to the name of the Role module to use. If unspecified, the name of the Role is used as the name of the Role module to use. In the above example, `timer1` is a Role of type `timer`, whereas `cuckoo` is a Role of type `cuckoo`.
                * `messageQueueSize`: *Optional*. If specified, this refers to the size of the buffer containing incoming Messages for this Role. Note that Role modules may override this; if they do, their value takes precedence over the configuration value (unless, of course, their overridden method decides to give precedence to the value in the configuration, if one is present).
        * `transports` is a list of Transport blocks.
            * Each child of the `transports` block is a Transport block, containing Transport-specific information. Its name determines the Transport's name. Transport names need not be unique across Nodes, but should be unique among a single Node. All Transport blocks accept the following configuration options, on top of Transport-specific ones:
                * `type`: *Optional*. If specified, this must refer to the name of the Transport module to use. If unspecified, the name of the Transport is used as the name of the Transport module to use. In the above example, `tcp` is both the name and the Transport module of the only Transport available to both nodes in the system.
* `heartbeat`: Interval (in seconds) to send heartbeat Messages to all connected Nodes. These Messages never reach Roles; they are used by Nodes to keep all active connections alive and in check. Default: `10`.
* `connectionRetry`: How long (in seconds) to wait after a disconnection before trying to reconnect again. Default: `60`.
* `outgoingQueueSize`: The size of the buffer for outgoing Messages (in number of Messages). Each Node holds such a buffer for every other Node in the system. Default: `128`.
* `cipher`: The cipher to use for all communication. Default: `aes256-ctr`.
* `hmac`: The MAC algorithm to use for all communication. Default: `hmac-sha1`.

#### Available roles

TODO

#### Available transports

TODO

### Running the system

Once all of the above is properly declared, copy the configuration file to each Node. Then, run the following:

	kozo path/to/config.yml <localNodeName>

Where `<localNodeName>` is the name of the Node that you are running the command on. The network may take a while to converge, but once all Nodes are online and reachable, connections will form over time.

## Extending Kōzō

### Writing custom Roles

TODO

### Writing custom Transports

TODO

[Python 2]: http://www.python.org/
[Paramiko]: http://www.lag.net/paramiko/
[PyCrypto]: http://www.pycrypto.org/
[PyPy]: http://pypy.org/
[PyYAML]: http://pyyaml.org/wiki/PyYAML
[LibYAML]: http://pyyaml.org/wiki/LibYAML
[Python-six]: https://pythonhosted.org/six/
[MessagePack]: http://msgpack.org/
[cPickle]: http://docs.python.org/2/library/pickle.html#module-cPickle
[tmuxinator]: https://github.com/aziz/tmuxinator
[Ruby]: http://www.ruby-lang.org/
[tmux]: http://tmux.sourceforge.net/
[PyBluez]: https://code.google.com/p/pybluez/
[RPIO]: https://pythonhosted.org/RPIO/
[RPi.GPIO]: https://code.google.com/p/raspberry-gpio-python/
[YAML]: http://yaml.org/
[SSH]: https://en.wikipedia.org/wiki/Secure_Shell
