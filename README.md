# 構造 - Kōzō
*(Prounounced "Kouzou"; means "Structure")*

Doc coming soon, maybe.

## Dependencies
### Hard dependencies
* [Python 2]
* [Paramiko], which itself depends on:
    * [PyCrypto] - which unfortunately prevents the use of [PyPy]
* Either [PyYAML] or [LibYAML]
* [Python-six]

### Optional dependencies
* [MessagePack] - Used as serializer if available; otherwise, [cPickle] is used

### Testnet dependencies
* [tmuxinator], which itself depends on:
    * [Ruby]
    * [tmux]
* Regular Kōzō dependencies

### Specific role dependencies
* `roles/bluetooth-discover.py`: [PyBluez]
* `roles/motion-detect.py`: Either [RPIO] or [RPi.GPIO]

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
