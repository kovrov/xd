
module xd.core;


version (Posix)
{
	//import core.sys.posix.unistd;
	import core.sys.posix.sys.uio;
	import core.sys.posix.fcntl; //: fcntl;
}

import std.socket;
//import core.sync.mutex;
//import core.sync.condition;
import std.string;
import std.stdio: writefln;

import xd.xproto;
import xd.util;


class Connection
{
	this(int display)
	{
		string path = std.string.format("/tmp/.X11-unix/X%d", display);
		this.fd = new std.socket.Socket(std.socket.AddressFamily.UNIX, std.socket.SocketType.STREAM);
		this.fd.connect(new LocalAddress(path));

		int flags = fcntl(this.fd.handle(), F_GETFL, 0);
		assert (flags != -1);
		flags |= O_NONBLOCK;
		assert (fcntl(this.fd.handle(), F_SETFL, flags) != -1);
		//this.fd.blocking = false;
		assert (fcntl(this.fd.handle(), F_SETFD, FD_CLOEXEC) != -1);

		this.rfds = new std.socket.SocketSet;
		this.wfds = new std.socket.SocketSet;

		this._setup();

		this._first_xid = 0;
		this._last_xid = this.setup.resource_id_mask;
	}

	/**
	 * Returns the next event or error from the server, or throw in case of an I/O error.
	 * Blocks until either an event or error arrive, or an I/O error occurs.
	 */
	Packet wait_for_packet()
	{
		while (this._incoming_queue.length == 0)
		{
			this._process_io(null, &this._parse_buffer);
		}

		//auto events_ptr = this._incoming_queue.ptr;
		auto event = this._incoming_queue[0];
		this._incoming_queue = this._incoming_queue[1..$];
		//assert (events_ptr == this._incoming_queue.ptr);
		return event;
	}

	void sendRequest(const xd.util.iovec[] vect)
	{
		this._process_io(vect, &this._parse_buffer);
	}

	Setup setup;

  private:
	std.socket.Socket fd;
	std.socket.SocketSet rfds, wfds;
	ubyte[1024*16] _incoming_buffer;
	Packet[] _incoming_queue;

	void _setup()
	{
		SetupRequest setup_request;
		version (BigEndian)
			setup_request.byte_order = 'B';
		version (LittleEndian)
			setup_request.byte_order = 'l';
		setup_request.protocol_major_version = 11;
		setup_request.protocol_minor_version = 0;

		auto auth = xd.util.get_auth(xd.util.Family.Local, "MIT-MAGIC-COOKIE-1");
		setup_request.authorization_protocol_name = auth.name.dup; // FIXME dupless
		setup_request.authorization_protocol_name_len
				= cast(ushort)setup_request.authorization_protocol_name.length;
		setup_request.authorization_protocol_data = auth.data.dup;
		setup_request.authorization_protocol_data_len
				= cast(ushort)setup_request.authorization_protocol_data.length;

		this._process_io(setup_request.toIOVector(), null);
		this._process_io(null, (ubyte[] input){this.setup = Setup(input);});
	}

	void _parse_buffer(ubyte[] input)
	{
		writefln("## _parse_buffer: input.length: %d", input.length);
		//this._incoming_queue <- this._incoming_buffer;

		auto packet = *(cast(Packet*)input.ptr);
		this._incoming_queue ~= packet;
	}

	void _process_io(const xd.util.iovec[] vect, void delegate(ubyte[] input) input_parser)
	{
		writefln("_process_io: vect.length: %d", vect.length);
		this.rfds.add(this.fd);
		if (vect.length)
		{
			writefln("  ###wfds.add");
			this.wfds.add(this.fd);
		}

		// wait for read/write status change while ignoring interrupts
		int ret = -1;
		while (ret == -1)
			ret = std.socket.Socket.select(this.rfds, this.wfds, null);

		writefln("  Socket.select: %d", ret);

		if (0 == ret)
		{
			assert (!this.rfds.isSet(this.fd));
			assert (!this.wfds.isSet(this.fd));
			return;
		}

		if (this.rfds.isSet(this.fd))
		{
			this.rfds.reset();
			writefln("  fd is ready for read...");
			int read_count = this.fd.receive(this._incoming_buffer);

			// TODO: read from socket error? should we throw an exception here?
			assert (read_count > 0);
			writefln("    %d bytes received.", read_count);

			assert (input_parser !is null);
			input_parser(this._incoming_buffer[0..read_count]);
		}

		if (this.wfds.isSet(this.fd))
		{
			this.wfds.reset();
			writefln("  ###fd is ready for write...");
			int written_count = core.sys.posix.sys.uio.writev(this.fd.handle(),
					cast(core.sys.posix.sys.uio.iovec*)vect.ptr, vect.length);
			writefln("    %d bytes sent.", written_count);
			assert (written_count > 0);
		}

		assert (!this.rfds.isSet(this.fd));
		assert (!this.wfds.isSet(this.fd));
	}

	uint _first_xid;
	uint _last_xid;

  public:
	uint generateId()
	{
		immutable xid_increment = this.setup.resource_id_mask & -this.setup.resource_id_mask;
		uint ret = this._first_xid | this.setup.resource_id_base;
		this._first_xid += xid_increment;
		return ret;
	}
}

union Packet
{
	ubyte type;

	struct EventHeader
	{
		ubyte response_type;
		ubyte _pad0;
		ushort sequence;
		ubyte[28] _pad1;
	}
	static assert (EventHeader.sizeof == 32);
	EventHeader event;

	struct ReplyHeader
	{
		ubyte[2] _pad0;
		ushort sequence;
		uint length;
		ubyte[24] _pad1;
	}
	static assert (ReplyHeader.sizeof == 32);
	ReplyHeader reply;

	struct ErrorHeader
	{
		ubyte[1] _pad0;
		ubyte error_code;
		ushort sequence;
		uint resource_id;
		ushort minor_code;
		ubyte major_code;
		ubyte _pad1[21];
	}
	static assert (ErrorHeader.sizeof == 32);
	ErrorHeader error;
}
static assert (Packet.sizeof == 32);
