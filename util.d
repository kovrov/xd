module xd.util;


version (Posix)
{
	import core.sys.posix.sys.socket: sockaddr;
}
import std.socket;
import std.stream: File;
import std.process: getenv;



auto pad4(T)(T i) { return -i & 3; }

struct iovec
{
	const(void)* iov_base;
	size_t iov_len;
}


/* ripped from Tango */
class LocalAddress : std.socket.Address
{
	align(1)
	struct sockaddr_un
	{
		ushort sun_family = std.socket.AddressFamily.UNIX;
		char[108] sun_path;
	}

	this(string path)
	{
		assert (path.length < 108);

		this.sun.sun_path[0 .. path.length] = path;
		this.sun.sun_path[path.length .. $] = 0;
		this.path = this.sun.sun_path[0 .. path.length];
	}

	bool isAbstract()
	{
		return this.path[0] == 0;
	}

	override
	std.socket.AddressFamily addressFamily()
	{
		return cast(std.socket.AddressFamily)this.sun.sun_family;
	}

	override
	string toString()
	{
		if (this.isAbstract)
			return "unix:abstract=" ~ this.path[1..$].idup;
		else
		   return "unix:path=" ~ this.path.idup;
	}

  protected:
	sockaddr_un sun;
	char[] path;

	override
	sockaddr* name()
	{
		return cast(sockaddr*)&this.sun;
	}

	override
	int nameLen()
	{
		return this.path.length + ushort.sizeof;
	}
}



enum Family
{
	Wild = 65535,
	LocalHost = 252,     // for local non-net authentication
	Krb5Principal = 253, // Kerberos 5 principal name
	Netname = 254,       // not part of X standard
	Local = 256,	     // not part of X standard (i.e. X.h)
}

struct Xauth
{
	Family family;
	string address, number, name;
	immutable(ubyte)[] data;
}

Xauth get_auth(Family family, string name)
{
	scope auth_file = new File(getenv("XAUTHORITY"));

	Xauth auth;
	ubyte[2] short_buf;
	ubyte[] buf;
	while (!auth_file.eof())
	{
		auth_file.read(short_buf);
		auth.family = cast(Family)(short_buf[0] * 256 + short_buf[1]);

		auth_file.read(short_buf);
		buf.length = short_buf[0] * 256 + short_buf[1];
		auth_file.read(buf);
		auth.address = (cast(char[])buf).idup;

		auth_file.read(short_buf);
		buf.length = short_buf[0] * 256 + short_buf[1];
		auth_file.read(buf);
		auth.number = (cast(char[])buf).idup;

		auth_file.read(short_buf);
		buf.length = short_buf[0] * 256 + short_buf[1];
		auth_file.read(buf);
		auth.name = (cast(char[])buf).idup;

		auth_file.read(short_buf);
		buf.length = short_buf[0] * 256 + short_buf[1];
		auth_file.read(buf);
		auth.data = buf.idup;

		if (family != Family.Wild && auth.family != Family.Wild && auth.family != family)
			continue;

		if (name.length && auth.name.length && name != auth.name)
	   		continue;

	   	return auth;
	}
	throw new Exception("auth not found");
}
