import collections

import maya.cmds as cmds
import maya.OpenMaya as om
from six import text_type as basestring

class Connection(object):
    """
    This class abstracts the concept of connection between two modules. Each connection has four attributes:
    The name of the connection, the type of connection, the object (geometry, controller, IK handle, etc), the
    connection will operate on and the module this connection belong to.
    For instance if a module rigs the eyes and his name is 'eyes' _owner will be 'eyes', the node could be the head
    controller of the 'head' module the eyes want to connect to and _type is the object type the module is expecting to
    connect to. In the case of the eyes a transform.
    """

    def __init__(self, name="", connect_type="", owner=None):
        """
        Initialize the Connection class
        @param name: The name of the connection.
        @param connect_type: TThe Maya node type that the connection will accept as connection.
        @param owner: The module the connection belong to.
        """
        self._name = name
        self._connect_type = connect_type
        self._owner = owner

    @property
    def name(self):
        """
        @return: the name given to the connection.
        """
        return self._name

    @name.setter
    def name(self, value):
        """
        @param value: the name the user wants to give to a connection.
        """
        if isinstance(value, basestring):
            self._name = value
        else:
            raise TypeError("{0} is not a valid name".format(value))

    @property
    def type(self):
        """
        @return: the type of object this connection is expecting to connect to. The available types are provided by the
        ConnectTypes class.
        """
        return self._connect_type

    @type.setter
    def type(self, value):
        """
        @param value: The type of object this connection is expecting to connect to.
        It needs to be of type ConnectTypes.
        """
        possible_types = ConnectTypes()
        members = [
            attr
            for attr in dir(possible_types)
            if not callable(getattr(possible_types, attr)) and not attr.startswith("__")
        ]
        if value in members:
            self._connect_type = value
        else:
            raise RuntimeError(
                "{0} is not a valid object to pass through modules".format(value)
            )


class ConnectTypes(object):
    """
    This class implements a list of possible Maya object supported by rigOmatic connections. Only
    what is listed in this class can be connected. This is to prevent that typos in connection 'type' could
    prevent plugs and sockets to connect.
    """

    ## A Maya transform node.
    transform = "transform"

    ## No node at all.
    none = "none"

    ## Abstract data connection like a dictionary
    data = "data"


class Plug(Connection):
    """
    This class implements the concept of a Plug. In rigOmatic a plug is a Module interface
    able to pass its information to a Socket. Multiple sockets can be attached to a plug but
    only one plug can be connected to a socket.
    """

    def __init__(
        self, name="", connect_type="", data=None, owner=None, node=None, sockets=[]
    ):
        """
        Initialize an instance of the Plug class
        @param name: The name of the plug.
        @param connect_type: The Maya node type that the plug will accept as connection.
        @param owner: The module the plug belong to. Most often it's reasonable to use self if the plug is created\
        from within a module.
        @param node: The object (geometry, controller, IK handle, etc) the plug will pass to the connected module.
        @param sockets: The socket of a node this plug is connecting to.
        """
        super(Plug, self).__init__(name, connect_type, owner)

        self._node = node
        self._data = {}

        if node is not None:
            if isinstance(node, basestring):
                self._node = node
            else:
                raise TypeError(
                    "The Maya object attached to a plug needs to be a string"
                )

        if data is not None:
            if isinstance(data, dict):
                self._data = data
            else:
                raise TypeError("The Plug data is not a dictionary")

        # The socket of the node this plug is connecting to
        # copy the sockets list by value as we don't want other objects share connected plugs.
        self._other_sockets = sockets[:]

        # add the plug to the module
        if self._owner:
            self._owner.set_plug(self)
        else:
            plug_no_owner_warning = "The Plug {0} has no owner. ".format(name)
            plug_no_owner_warning += (
                "It will fail to connect until an owner is assigned"
            )
            cmds.warning(plug_no_owner_warning)

    @property
    def node(self):
        """
        @return: the object (geometry, controller, IK handle, etc) the plug will pass to the connected module.
        """
        return self._node

    @node.setter
    def node(self, value):
        """
        @param value: the object (geometry, controller, IK handle, etc) the plug will pass to the connected module.
        """
        if isinstance(value, basestring):
            self._node = value
        else:
            raise TypeError("The Maya object attached to a plug needs to be a string")

    @property
    def data(self):
        """
        The data type Plug connection (dictionary)
        """
        return self._data

    @data.setter
    def data(self, value):
        """
        Sets the data dictionary for the Plug
        @param value: The dictionary with the data for the Plug
        """
        if isinstance(value, dict):
            self._data = value
        else:
            raise TypeError("Trying to set data to a non-dictionary value")

    @property
    def owner(self):
        """
        @return: The owner module for this Plug
        """
        return self._owner

    @owner.setter
    def owner(self, value):
        """
        Sets the owner of this Plug to the input module
        @param value: RigOMatic module
        """

        self._owner = value
        self._owner.set_plug(self)

    @property
    def connected_socket(self):
        """
        @return: Returns the sockets connected to the plug.
        """
        return self._other_sockets

    @connected_socket.setter
    def connected_socket(self, value):
        """
        Add the passed socket to the list of sockets connected to the plug.
        @param value: The socket to connect to the plug.
        """
        if isinstance(value, Socket):
            self._other_sockets.append(value)

    def disconnect_socket(self, value):
        """
        Remove the passed socket from the list of sockets connected to the plug.
        @param value: The socket to disconnect from the plug.
        """
        if isinstance(value, Socket):
            self._other_sockets.remove(value)

    @property
    def is_connected(self):
        """
        Returns the sockets connected to this plug if there any.
        @return: The socket connected to this plug.
        """
        if self._other_sockets:
            return self._other_sockets


class Socket(Connection):
    """
    This class implements the concept of a Socket. In rigOmatic a Socket is a module
    interface able to receive information from a Plug and execute code that operated between the plug and socket's
    modules. Multiple sockets can be attached to a plug but only one plug can be connected to a socket.
    """

    def __init__(
        self,
        name="",
        connect_type=ConnectTypes.transform,
        owner=None,
        connect_method=None,
        plug=None,
    ):
        """
        Initialize an instance of the Socket class
        @param name: The socket name.
        @param connect_type: The Maya node type that the connection will accept as connection.
        @param owner: The module the connection belong to. Most often it's reasonable to use self if the socket is \
        created from within a module.
        @param connect_method: The method to run when the connection with a plug is established.
        @param plug: The plug of another node this socket is connecting to.
        """
        super(Socket, self).__init__(name, connect_type, owner)

        self._connect_method = connect_method

        # The plug of the other node this socket is connecting to.
        self._other_plug = plug

        # add the socket to the module
        if self._owner:
            self._owner.set_socket(self)
        else:
            raise ValueError("The module this socket belongs to doesn't exist")

    @property
    def func_to_exec_on_connect(self):
        """
        @return: The function that is executed when the socket is connected.
        """
        return self._connect_method

    @func_to_exec_on_connect.setter
    def func_to_exec_on_connect(self, value):
        """
        Assign the function to execute when the socket is connected
        """
        if isinstance(value, collections.Callable):
            self._connect_method = value
        else:
            raise TypeError("The passed value is not a function")

    @property
    def connected_plug(self):
        """
        @return: Returns the plug connected to the socket.
        """
        return self._other_plug

    @connected_plug.setter
    def connected_plug(self, value):
        """
        Connect the passed plug to the socket.
        @param value: The plug connected to the socket.
        """
        if isinstance(value, Plug):
            self._other_plug = value

    def disconnect_plug(self, value):
        """
        Disconnect the passed plug from the socket.
        @param value: The plug to connected from the socket.
        """
        if isinstance(value, Plug):
            self._other_plug = None

    @property
    def is_connected(self):
        """
        Returns the socket connected to this plug if there is one.
        @return: the socket connected to this plug.
        """
        if self._other_plug:
            return self._other_plug
